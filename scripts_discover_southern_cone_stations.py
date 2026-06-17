"""Discover eddy-covariance stations across the Southern Cone.

Queries/scrapes official portals (AmeriFlux JSON, FLUXNET HTML) and, when
available, the ``fluxnet-shuttle listall`` inventory, filters to the Southern
Cone, dedupes across networks, and writes a snapshot-compatible catalog CSV so
the existing pipeline picks up the new stations with no downstream changes.

HTML scraping is used only for DISCOVERY/metadata. Data ZIP acquisition stays
on the official ``fluxnet-shuttle`` path (see ``scripts_loop_download_driver``).

The filtering / dedup / merge core is pure-stdlib (operates on plain dicts) so
it is unit-testable without pandas or network access.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

from pipeline_paths import RESEARCH_DIR, catalog_path, latest_snapshot

# 18-column schema shared with the existing fluxnet-shuttle snapshots.
SNAPSHOT_COLUMNS = [
    "data_hub",
    "site_id",
    "site_name",
    "location_lat",
    "location_long",
    "igbp",
    "network",
    "team_member_name",
    "team_member_role",
    "team_member_email",
    "first_year",
    "last_year",
    "download_link",
    "fluxnet_product_name",
    "product_citation",
    "product_id",
    "oneflux_code_version",
    "product_source_network",
]

SOUTHERN_CONE_PREFIXES = {"CL", "AR", "UY", "PY", "BR"}
DEFAULT_MAX_LAT = -20.0

# Source precedence when merging duplicate site_ids (higher wins per field).
SOURCE_PRECEDENCE = {"shuttle": 3, "ameriflux": 2, "fluxnet": 1, "snapshot": 2}

# Candidate public AmeriFlux site-list endpoints (tried in order).
AMERIFLUX_SITE_ENDPOINTS = [
    "https://amfcdn.lbl.gov/api/v1/site_display/AmeriFlux",
    "https://ameriflux-data.lbl.gov/api/v1/site_display/AmeriFlux",
]
FLUXNET_SITES_URL = "https://fluxnet.org/sites/site-list-and-pages/"

AUDIT_PATH = RESEARCH_DIR / "southern_cone_discovery_audit.csv"


# --------------------------------------------------------------------------
# Pure helpers (no network, no pandas) -- unit testable
# --------------------------------------------------------------------------
def country_prefix(site_id: str) -> str:
    return (site_id or "").split("-", 1)[0].upper()


def _to_float(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def is_southern_cone(site_id: str, lat, max_lat: float = DEFAULT_MAX_LAT) -> bool:
    """A site is in scope when its country prefix is Southern-Cone AND it lies
    south of ``max_lat``. The latitude box is the real discriminator (it keeps
    tropical Brazilian sites such as BR-CST out)."""
    prefix_ok = country_prefix(site_id) in SOUTHERN_CONE_PREFIXES
    lat_f = _to_float(lat)
    lat_ok = lat_f is not None and lat_f < max_lat
    return prefix_ok and lat_ok


def _blank_record() -> dict:
    rec = {col: "" for col in SNAPSHOT_COLUMNS}
    rec["_source"] = ""
    return rec


def normalize_ameriflux_record(obj: dict) -> dict:
    """Map an AmeriFlux site JSON object onto the snapshot schema.

    AmeriFlux JSON keys vary across endpoints; we look up several aliases.
    """

    def pick(*keys):
        for key in keys:
            if key in obj and obj[key] not in (None, ""):
                return obj[key]
        return ""

    rec = _blank_record()
    rec["data_hub"] = "AmeriFlux"
    rec["site_id"] = str(pick("SITE_ID", "site_id", "Site_ID", "siteId"))
    rec["site_name"] = str(pick("SITE_NAME", "site_name", "Name"))
    rec["location_lat"] = pick("LOCATION_LAT", "location_lat", "lat", "Latitude")
    rec["location_long"] = pick("LOCATION_LONG", "location_long", "lon", "Longitude")
    rec["igbp"] = str(pick("IGBP", "igbp", "vegetation_igbp"))
    rec["network"] = str(pick("NETWORK", "network")) or "AmeriFlux"
    rec["first_year"] = pick("DATA_START", "first_year", "data_start_year")
    rec["last_year"] = pick("DATA_END", "last_year", "data_end_year")
    rec["product_source_network"] = "AmeriFlux"
    rec["_source"] = "ameriflux"
    return rec


def parse_ameriflux_sites(payload) -> list[dict]:
    """Extract a list of site dicts from an AmeriFlux JSON payload."""
    if payload is None:
        return []
    if isinstance(payload, dict):
        for key in ("data", "results", "sites"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload]
    if not isinstance(payload, list):
        return []
    out = []
    for obj in payload:
        if isinstance(obj, dict):
            rec = normalize_ameriflux_record(obj)
            if rec["site_id"]:
                out.append(rec)
    return out


def parse_fluxnet_html(html: str) -> list[dict]:
    """Parse a FLUXNET site-list HTML table into snapshot-schema dicts.

    Defensive: scans every table row for a FLUXNET site code (e.g. ``AR-TF1``)
    and best-effort latitude/longitude/name columns.
    """
    if not html:
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    import re

    site_code = re.compile(r"^[A-Z]{2}-[A-Za-z0-9]{2,}$")
    soup = BeautifulSoup(html, "lxml")
    out: list[dict] = []
    for row in soup.find_all("tr"):
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        site_id = next((c for c in cells if site_code.match(c)), "")
        if not site_id:
            continue
        floats = [c for c in cells if _to_float(c) is not None]
        rec = _blank_record()
        rec["data_hub"] = "FLUXNET"
        rec["site_id"] = site_id
        # Name = the longest non-numeric, non-code cell.
        names = [c for c in cells if c != site_id and _to_float(c) is None]
        rec["site_name"] = max(names, key=len) if names else ""
        if len(floats) >= 2:
            rec["location_lat"] = floats[0]
            rec["location_long"] = floats[1]
        rec["network"] = "FLUXNET"
        rec["product_source_network"] = "FLUXNET"
        rec["_source"] = "fluxnet"
        out.append(rec)
    return out


def merge_records(records: list[dict]) -> list[dict]:
    """Dedupe by ``site_id``, merging fields by source precedence."""
    by_site: dict[str, dict] = {}
    sources: dict[str, set] = {}
    for rec in records:
        site_id = rec.get("site_id", "")
        if not site_id:
            continue
        sources.setdefault(site_id, set()).add(rec.get("_source", ""))
        if site_id not in by_site:
            by_site[site_id] = {col: rec.get(col, "") for col in SNAPSHOT_COLUMNS}
            by_site[site_id]["_winner"] = {
                col: SOURCE_PRECEDENCE.get(rec.get("_source", ""), 0)
                for col in SNAPSHOT_COLUMNS
                if rec.get(col) not in (None, "")
            }
            continue
        existing = by_site[site_id]
        rank = SOURCE_PRECEDENCE.get(rec.get("_source", ""), 0)
        for col in SNAPSHOT_COLUMNS:
            val = rec.get(col)
            if val in (None, ""):
                continue
            if rank >= existing["_winner"].get(col, -1):
                existing[col] = val
                existing["_winner"][col] = rank
    merged = []
    for site_id, rec in by_site.items():
        rec.pop("_winner", None)
        rec["_discovery_source"] = ";".join(sorted(s for s in sources[site_id] if s))
        merged.append(rec)
    return merged


def filter_southern_cone(records: list[dict], max_lat: float) -> tuple[list[dict], list[dict]]:
    """Split records into (in_scope, audit_rows_for_all)."""
    in_scope = []
    audit = []
    for rec in records:
        prefix_ok = country_prefix(rec["site_id"]) in SOUTHERN_CONE_PREFIXES
        lat_f = _to_float(rec.get("location_lat"))
        lat_ok = lat_f is not None and lat_f < max_lat
        keep = prefix_ok and lat_ok
        audit.append(
            {
                "site_id": rec["site_id"],
                "site_name": rec.get("site_name", ""),
                "location_lat": rec.get("location_lat", ""),
                "country_prefix": country_prefix(rec["site_id"]),
                "prefix_in_scope": prefix_ok,
                "lat_in_scope": lat_ok,
                "kept": keep,
                "discovery_source": rec.get("_discovery_source", rec.get("_source", "")),
            }
        )
        if keep:
            in_scope.append(rec)
    return in_scope, audit


# --------------------------------------------------------------------------
# I/O edges
# --------------------------------------------------------------------------
def load_existing_snapshot_rows() -> list[dict]:
    try:
        path = latest_snapshot()
    except FileNotFoundError:
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for row in rows:
        rec = {col: row.get(col, "") for col in SNAPSHOT_COLUMNS}
        rec["_source"] = "snapshot"
        out.append(rec)
    return out


def load_fixtures() -> list[dict]:
    """Load discovery fixtures for offline / dry-run mode."""
    fixtures_dir = Path(__file__).resolve().parent / "tests" / "fixtures"
    records: list[dict] = []
    amf = fixtures_dir / "ameriflux_sites_sample.json"
    if amf.exists():
        records.extend(parse_ameriflux_sites(json.loads(amf.read_text(encoding="utf-8"))))
    flx = fixtures_dir / "fluxnet_sites_sample.html"
    if flx.exists():
        records.extend(parse_fluxnet_html(flx.read_text(encoding="utf-8")))
    return records


def fetch_ameriflux(client) -> list[dict]:
    for url in AMERIFLUX_SITE_ENDPOINTS:
        payload, result = client.fetch_json(url)
        if payload is not None:
            return parse_ameriflux_sites(payload)
    return []


def fetch_fluxnet(client) -> list[dict]:
    result = client.fetch(FLUXNET_SITES_URL)
    return parse_fluxnet_html(result.text) if result.status else []


def fetch_shuttle() -> list[dict]:
    """Parse ``fluxnet-shuttle listall ameriflux`` if the CLI is installed."""
    if shutil.which("fluxnet-shuttle") is None:
        return []
    try:
        proc = subprocess.run(
            ["fluxnet-shuttle", "listall", "ameriflux"],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    out = []
    for line in proc.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if parts and parts[0] and "-" in parts[0]:
            rec = _blank_record()
            rec["data_hub"] = "AmeriFlux"
            rec["site_id"] = parts[0]
            rec["network"] = "AmeriFlux"
            rec["product_source_network"] = "AmeriFlux"
            rec["_source"] = "shuttle"
            out.append(rec)
    return out


def write_catalog(records: list[dict]) -> Path:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = catalog_path(timestamp)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SNAPSHOT_COLUMNS)
        writer.writeheader()
        for rec in sorted(records, key=lambda r: r["site_id"]):
            writer.writerow({col: rec.get(col, "") for col in SNAPSHOT_COLUMNS})
    return path


def write_audit(audit_rows: list[dict]) -> Path:
    fieldnames = [
        "site_id",
        "site_name",
        "location_lat",
        "country_prefix",
        "prefix_in_scope",
        "lat_in_scope",
        "kept",
        "discovery_source",
    ]
    with open(AUDIT_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(audit_rows, key=lambda r: r["site_id"]))
    return AUDIT_PATH


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-lat", type=float, default=DEFAULT_MAX_LAT)
    parser.add_argument("--sources", default="ameriflux,fluxnet,shuttle,snapshot")
    parser.add_argument("--dry-run", action="store_true", help="No network; use fixtures/cache only.")
    parser.add_argument("--offline", action="store_true", help="Cache-only; no network.")
    return parser.parse_args()


def collect_records(sources: set[str], offline: bool, dry_run: bool) -> list[dict]:
    records: list[dict] = []
    if "snapshot" in sources:
        records.extend(load_existing_snapshot_rows())
    if dry_run:
        records.extend(load_fixtures())
        return records
    from pipeline_http import RespectfulHttpClient

    client = RespectfulHttpClient(offline=offline)
    if "ameriflux" in sources:
        records.extend(fetch_ameriflux(client))
    if "fluxnet" in sources:
        records.extend(fetch_fluxnet(client))
    if "shuttle" in sources:
        records.extend(fetch_shuttle())
    if offline and not any(r["_source"] != "snapshot" for r in records):
        records.extend(load_fixtures())
    return records


def main() -> None:
    args = parse_args()
    sources = {s.strip() for s in args.sources.split(",") if s.strip()}
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    raw = collect_records(sources, offline=args.offline, dry_run=args.dry_run)
    merged = merge_records(raw)
    in_scope, audit = filter_southern_cone(merged, args.max_lat)

    write_audit(audit)
    if args.dry_run:
        print(f"[dry-run] discovered {len(merged)} sites, {len(in_scope)} in Southern Cone:")
        for rec in sorted(in_scope, key=lambda r: r["site_id"]):
            print(f"  {rec['site_id']:8} {rec.get('location_lat',''):>8}  {rec.get('site_name','')}")
        print(f"[dry-run] audit written to {AUDIT_PATH}; catalog NOT written.")
        return

    catalog = write_catalog(in_scope)
    print(f"Wrote catalog with {len(in_scope)} Southern-Cone stations: {catalog}")
    print(f"Audit (all {len(merged)} discovered sites): {AUDIT_PATH}")


if __name__ == "__main__":
    main()
