"""Offline tests for the loop download driver's state machine."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts_loop_download_driver as loop  # noqa: E402


def _now():
    return dt.datetime(2026, 6, 17, 12, 0, 0, tzinfo=dt.timezone.utc)


def test_backoff_grows_and_caps():
    assert loop.compute_backoff(0) == 0
    assert loop.compute_backoff(1) == 30
    assert loop.compute_backoff(2) == 60
    assert loop.compute_backoff(3) == 120
    # Caps at BACKOFF_CAP_SECONDS.
    assert loop.compute_backoff(20) == loop.BACKOFF_CAP_SECONDS


def test_eligibility_respects_status_attempts_and_window():
    now = _now()
    assert loop.is_eligible({"download_status": "pending", "attempts": 0}, now) is True
    assert loop.is_eligible({"download_status": "success", "attempts": 0}, now) is False
    assert loop.is_eligible({"download_status": "exhausted", "attempts": 6}, now) is False
    # At attempt ceiling -> not eligible.
    assert loop.is_eligible({"download_status": "failed", "attempts": 6}, now) is False
    # Inside backoff window -> not eligible.
    future = (now + dt.timedelta(minutes=5)).isoformat()
    assert loop.is_eligible(
        {"download_status": "failed", "attempts": 1, "next_eligible_utc": future}, now
    ) is False
    # Past backoff window -> eligible again.
    past = (now - dt.timedelta(minutes=5)).isoformat()
    assert loop.is_eligible(
        {"download_status": "failed", "attempts": 1, "next_eligible_utc": past}, now
    ) is True


def test_apply_attempt_success_and_failure_and_exhaustion():
    now = _now()
    row = {"site_id": "CL-SDF", "download_status": "pending", "attempts": 0}
    loop.apply_attempt_result(row, succeeded=True, now=now)
    assert row["download_status"] == "success"
    assert row["attempts"] == 1
    assert row["next_eligible_utc"] == ""

    row = {"site_id": "AR-TF1", "download_status": "pending", "attempts": 0}
    loop.apply_attempt_result(row, succeeded=False, now=now)
    assert row["download_status"] == "failed"
    assert row["attempts"] == 1
    assert row["next_backoff_seconds"] == 30
    assert loop.parse_ts(row["next_eligible_utc"]) is not None

    # One attempt below the ceiling -> exhausted on this failure.
    row = {"site_id": "AR-TF2", "download_status": "failed", "attempts": loop.MAX_ATTEMPTS - 1}
    loop.apply_attempt_result(row, succeeded=False, now=now)
    assert row["download_status"] == "exhausted"
    assert row["attempts"] == loop.MAX_ATTEMPTS


def test_completion_summary_done_only_when_no_retriable_work():
    rows = [
        {"site_id": "A", "download_status": "success"},
        {"site_id": "B", "download_status": "exhausted"},
        {"site_id": "C", "download_status": "skipped_restricted"},
    ]
    summary = loop.completion_summary(rows)
    assert summary["all_done"] is True
    assert summary["complete"] == 1
    assert summary["remaining"] == []

    rows.append({"site_id": "D", "download_status": "failed"})
    summary = loop.completion_summary(rows)
    assert summary["all_done"] is False
    assert summary["remaining"] == ["D"]


def test_run_one_pass_idempotent_and_drives_to_completion(tmp_path, monkeypatch):
    """End-to-end pass with a fake downloader and temp filesystem."""
    import pandas as pd

    raw = tmp_path / "raw"
    raw.mkdir()
    logs = tmp_path / "logs"
    meta = tmp_path / "meta"
    tables = tmp_path / "tables"
    log_path = tmp_path / "download_log.csv"

    # Two target sites, both pending.
    pd.DataFrame(
        [
            {"site_id": "CL-SDF", "site_name": "a", "download_status": "pending"},
            {"site_id": "AR-TF1", "site_name": "b", "download_status": "pending"},
        ]
    ).to_csv(log_path, index=False)

    monkeypatch.setattr(loop, "RAW_DIR", raw)
    monkeypatch.setattr(loop, "LOGS_DIR", logs)
    monkeypatch.setattr(loop, "METADATA_DIR", meta)
    monkeypatch.setattr(loop, "OUTPUTS_TABLES_DIR", tables)
    monkeypatch.setattr(loop, "DOWNLOAD_LOG_PATH", log_path)
    monkeypatch.setattr(loop, "latest_snapshot", lambda: tmp_path / "snap.csv")
    monkeypatch.setattr(loop.dl, "default_sites", lambda: ["CL-SDF", "AR-TF1"])
    monkeypatch.setattr(
        loop.dl,
        "expected_products",
        lambda snap, sites: {"CL-SDF": "CL-SDF.zip", "AR-TF1": "AR-TF1.zip"},
    )

    # Fake downloader: only CL-SDF "downloads" (creates its ZIP); AR-TF1 fails.
    def fake_run_download(snap, sites):
        if "CL-SDF" in sites:
            (raw / "CL-SDF.zip").write_text("data")
        return None

    monkeypatch.setattr(loop.dl, "run_download", fake_run_download)

    # Simulated clock; advance well past the backoff window between passes.
    clock = {"t": dt.datetime(2026, 6, 17, 12, 0, 0, tzinfo=dt.timezone.utc)}
    monkeypatch.setattr(loop, "_utcnow", lambda: clock["t"])

    summary = loop.run_one_pass()
    assert "CL-SDF" in summary["success"]
    assert "AR-TF1" in summary["remaining"]
    assert summary["all_done"] is False

    # Second pass: CL-SDF is skipped idempotently; AR-TF1 retried (still fails).
    clock["t"] += dt.timedelta(hours=1)
    summary2 = loop.run_one_pass()
    assert "CL-SDF" in summary2["success"]
    df = pd.read_csv(log_path)
    ar = df[df["site_id"] == "AR-TF1"].iloc[0]
    assert int(ar["attempts"]) >= 2
