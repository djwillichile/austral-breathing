"""Loop-driven, idempotent download driver for Southern-Cone stations.

One invocation == one pass. Designed for the ``/loop`` skill, which re-runs the
command on an interval. The driver:

    * skips stations whose data is already present (idempotent),
    * retries failed downloads with exponential backoff persisted in
      ``download_log.csv`` (so backoff survives across ``/loop`` ticks),
    * marks stations that hit the attempt ceiling as ``exhausted``,
    * prints / writes a "complete N/total, remaining ..." summary and a
      machine-readable sentinel so the loop knows when to stop.

The state-machine core is pure (operates on plain dicts) and unit-testable
without network access; pandas is used only at the CSV I/O edge.
"""

from __future__ import annotations

import argparse
import datetime as dt

import pandas as pd

from pipeline_paths import (
    DOWNLOAD_LOG_PATH,
    LOGS_DIR,
    METADATA_DIR,
    OUTPUTS_TABLES_DIR,
    RAW_DIR,
    latest_snapshot,
)
import scripts_download_fluxnet_data as dl

MAX_ATTEMPTS = 6
BACKOFF_BASE_SECONDS = 30
BACKOFF_CAP_SECONDS = 3600

# Extra state columns added to the existing download_log schema.
STATE_COLUMNS = ["attempts", "last_attempt_utc", "next_eligible_utc", "next_backoff_seconds"]

SENTINEL_DONE = "LOOP_STATUS: COMPLETE"
SENTINEL_REMAINING = "LOOP_STATUS: WORK REMAINING"


# --------------------------------------------------------------------------
# Pure state-machine helpers
# --------------------------------------------------------------------------
def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_ts(value) -> dt.datetime | None:
    if value in (None, "") or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None


def compute_backoff(attempts: int, base: int = BACKOFF_BASE_SECONDS, cap: int = BACKOFF_CAP_SECONDS) -> int:
    """Exponential backoff: base * 2**(attempts-1), capped."""
    if attempts <= 0:
        return 0
    return int(min(base * (2 ** (attempts - 1)), cap))


def is_eligible(row: dict, now: dt.datetime, max_attempts: int = MAX_ATTEMPTS) -> bool:
    """A row is eligible for a download attempt this pass."""
    if row.get("download_status") in ("success", "exhausted", "skipped_restricted"):
        return False
    if int(row.get("attempts") or 0) >= max_attempts:
        return False
    next_eligible = parse_ts(row.get("next_eligible_utc"))
    if next_eligible is not None and now < next_eligible:
        return False
    return True


def apply_attempt_result(
    row: dict,
    succeeded: bool,
    now: dt.datetime,
    base: int = BACKOFF_BASE_SECONDS,
    cap: int = BACKOFF_CAP_SECONDS,
    max_attempts: int = MAX_ATTEMPTS,
) -> dict:
    """Update a state row after an attempt. Returns the same dict."""
    attempts = int(row.get("attempts") or 0) + 1
    row["attempts"] = attempts
    row["last_attempt_utc"] = now.isoformat()
    if succeeded:
        row["download_status"] = "success"
        row["failure_reason"] = ""
        row["next_eligible_utc"] = ""
        row["next_backoff_seconds"] = 0
        row["notes"] = "Downloaded with fluxnet-shuttle (loop driver)."
    elif attempts >= max_attempts:
        row["download_status"] = "exhausted"
        row["next_eligible_utc"] = ""
        row["next_backoff_seconds"] = 0
        row["failure_reason"] = f"Reached max attempts ({max_attempts})."
        row["notes"] = "Gave up after exhausting retries; review manually."
    else:
        backoff = compute_backoff(attempts, base, cap)
        row["download_status"] = "failed"
        row["next_backoff_seconds"] = backoff
        row["next_eligible_utc"] = (now + dt.timedelta(seconds=backoff)).isoformat()
        row["failure_reason"] = "Download attempt failed; will retry after backoff."
        row["notes"] = f"Attempt {attempts} failed; next eligible in {backoff}s."
    return row


def completion_summary(rows: list[dict]) -> dict:
    """Aggregate state across all target rows."""
    total = len(rows)
    success = [r["site_id"] for r in rows if r.get("download_status") == "success"]
    exhausted = [r["site_id"] for r in rows if r.get("download_status") == "exhausted"]
    restricted = [r["site_id"] for r in rows if r.get("download_status") == "skipped_restricted"]
    remaining = [
        r["site_id"]
        for r in rows
        if r.get("download_status") not in ("success", "exhausted", "skipped_restricted")
    ]
    done = len(remaining) == 0
    return {
        "total": total,
        "complete": len(success),
        "success": sorted(success),
        "exhausted": sorted(exhausted),
        "restricted": sorted(restricted),
        "remaining": sorted(remaining),
        "all_done": done,
    }


# --------------------------------------------------------------------------
# Idempotency check (filesystem)
# --------------------------------------------------------------------------
def site_data_present(site_id: str, product_name) -> bool:
    """True if the product ZIP or an extracted FLUXMET CSV already exists."""
    if isinstance(product_name, str) and product_name and (RAW_DIR / product_name).exists():
        return True
    site_dir = RAW_DIR / site_id
    if site_dir.exists():
        if any(site_dir.glob("*_FLUXMET_DD_*.csv")):
            return True
        if any(site_dir.glob("*.zip")):
            return True
    return False


# --------------------------------------------------------------------------
# CSV I/O edge
# --------------------------------------------------------------------------
def load_state() -> pd.DataFrame:
    df = pd.read_csv(DOWNLOAD_LOG_PATH)
    for col in STATE_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col != "attempts" else 0
    df["attempts"] = pd.to_numeric(df["attempts"], errors="coerce").fillna(0).astype(int)
    return df


def save_state(df: pd.DataFrame) -> None:
    df.to_csv(DOWNLOAD_LOG_PATH, index=False)
    for path in (METADATA_DIR / "download_log.csv", OUTPUTS_TABLES_DIR / "download_log.csv"):
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)


def write_status(summary: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    sentinel = SENTINEL_DONE if summary["all_done"] else SENTINEL_REMAINING
    lines = [
        sentinel,
        f"complete: {summary['complete']}/{summary['total']}",
        f"success: {', '.join(summary['success']) or 'none'}",
        f"remaining: {', '.join(summary['remaining']) or 'none'}",
        f"exhausted: {', '.join(summary['exhausted']) or 'none'}",
        f"restricted: {', '.join(summary['restricted']) or 'none'}",
    ]
    (LOGS_DIR / "loop_status.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for line in lines:
        print(line)


# --------------------------------------------------------------------------
# One pass
# --------------------------------------------------------------------------
def run_one_pass(max_attempts: int = MAX_ATTEMPTS, dry_run: bool = False) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = latest_snapshot()
    sites = dl.default_sites()
    products = dl.expected_products(snapshot_file, sites)

    df = load_state()
    # Restrict to current target sites present in the log.
    state_rows = df[df["site_id"].isin(sites)].to_dict("records")
    now = _utcnow()

    # 1) Mark already-present sites as success (idempotent).
    for row in state_rows:
        if row.get("download_status") != "success" and site_data_present(
            row["site_id"], products.get(row["site_id"])
        ):
            row["download_status"] = "success"
            row["failure_reason"] = ""
            row["notes"] = "Data already present (idempotent skip)."

    # 2) Select eligible sites for a download attempt.
    eligible = [r for r in state_rows if is_eligible(r, now, max_attempts)]
    eligible_ids = [r["site_id"] for r in eligible]

    if eligible_ids and not dry_run:
        result = dl.run_download(snapshot_file, eligible_ids)
        stdout = "" if result is None else result.stdout
        stderr = "" if result is None else result.stderr
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        (LOGS_DIR / "download_stdout.log").write_text(stdout or "", encoding="utf-8")
        (LOGS_DIR / "download_stderr.log").write_text(stderr or "", encoding="utf-8")
        for row in eligible:
            succeeded = site_data_present(row["site_id"], products.get(row["site_id"]))
            apply_attempt_result(row, succeeded, now, max_attempts=max_attempts)
    elif eligible_ids and dry_run:
        print(f"[dry-run] would attempt: {', '.join(eligible_ids)}")

    # Write updated rows back into the DataFrame.
    by_id = {r["site_id"]: r for r in state_rows}
    for col in ["download_status", "failure_reason", "notes", *STATE_COLUMNS]:
        df[col] = df.apply(
            lambda r: by_id.get(r["site_id"], {}).get(col, r.get(col)), axis=1
        )

    summary = completion_summary(state_rows)
    if not dry_run:
        save_state(df)
    write_status(summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--dry-run", action="store_true", help="Plan only; no download, no writes.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_one_pass(max_attempts=args.max_attempts, dry_run=args.dry_run)
    # Exit 0 when there is no retriable work left (loop can stop).
    raise SystemExit(0 if summary["all_done"] else 1)


if __name__ == "__main__":
    main()
