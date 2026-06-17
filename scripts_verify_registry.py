"""Verify the South American carbon-observation registries.

This is the auditing counterpart to ``pipeline_registry.py``. It runs a battery
of **offline** consistency and plausibility checks over both curated CSVs and,
optionally, an **online** cross-check of the AmeriFlux/FLUXNET-coded flux towers
against the public AmeriFlux ``site_display`` API.

Why this exists
---------------
PR #6 shipped the registry with an explicit caveat: *"per-country counts and
codes should be verified against the AmeriFlux site_display API and primary
sources before publication."* This module makes that verification reproducible
and CI-gateable:

    * Offline checks need no network and run in restricted sandboxes.
    * The ``--online`` cross-check degrades gracefully when the AmeriFlux host is
      not reachable (e.g. blocked by an egress allowlist), reporting an INFO
      finding instead of failing -- so the same command works locally and in CI.

Findings have three severities:
    ERROR  a real data defect (controlled-vocabulary violation, duplicate id,
           impossible coordinate, inverted year span, ...). Fails the run.
    WARN   a likely problem or internal contradiction worth a human look.
    INFO   advisory only (ambiguous CO2 status, provisional id, online skips).

Usage
-----
    python scripts_verify_registry.py                 # offline audit
    python scripts_verify_registry.py --online        # + AmeriFlux cross-check
    python scripts_verify_registry.py --strict         # WARN also fails the run
    python scripts_verify_registry.py --json PATH      # write machine report
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pipeline_registry as reg
from pipeline_paths import OUTPUTS_TABLES_DIR

# --------------------------------------------------------------------------
# Controlled vocabularies and bounds (single source of truth for the audit).
# --------------------------------------------------------------------------

MEASURES_CO2 = {"yes", "no", "ambiguous"}
TIERS = {1, 2, 3}
CONFIDENCE = {"high", "medium", "low"}
COORD_NOTE = {"exact", "approx", "unknown"}
FLUX_NETWORKS = {"AmeriFlux", "FLUXNET2015", "ICOS", "LBA", "AndesFlux", "SulFlux", "none"}
STOCK_TYPES = {"biomass", "peat", "soil", "lidar-biomass", "blue-carbon", "mixed"}

# Networks that issue an official ``CC-XXX`` code; provisional ``none`` sites are
# allowed a free-form suffix because no canonical code exists yet.
CODED_NETWORKS = FLUX_NETWORKS - {"none"}
CANONICAL_CODE = re.compile(r"^[A-Z]{2}-[A-Za-z0-9]{3}$")

# Two-letter site-id prefix -> country/territory it must belong to.
COUNTRY_PREFIX = {
    "AR": "Argentina",
    "BO": "Bolivia",
    "BR": "Brazil",
    "CL": "Chile",
    "CO": "Colombia",
    "EC": "Ecuador",
    "GF": "French Guiana",
    "GY": "Guyana",
    "PE": "Peru",
    "PY": "Paraguay",
    "SR": "Suriname",
    "UY": "Uruguay",
    "VE": "Venezuela",
}

# Generous continental bounding box (decimal degrees). Anything outside this is
# almost certainly a transcription error for a South American site.
SA_LAT = (-56.0, 13.0)
SA_LON = (-82.0, -34.0)

# Plausible operating-year window for modern EC towers.
YEAR_MIN = 1990
YEAR_MAX = _dt.date.today().year + 1

# Tokens that signal restricted access (used to flag tier/access contradictions).
_REQUEST_RX = re.compile(r"request|on request|by request|pending|to authors?|to pi", re.I)
_OPEN_RX = re.compile(r"download|archived?|base\b|fluxnet|osti|icos|doi", re.I)

REQUIRED_FLUX_FIELDS = (
    "site_id", "country", "site_name", "biome", "network",
    "measures_co2", "availability_tier", "data_access", "confidence",
    "coord_note", "source_url",
)
REQUIRED_STOCK_FIELDS = (
    "program", "stock_type", "countries", "measures", "institution",
    "availability_tier", "data_access", "confidence", "source_url",
)


@dataclass(frozen=True)
class Finding:
    severity: str          # ERROR | WARN | INFO
    scope: str             # flux | stock | online
    record_id: str
    code: str
    message: str


# --------------------------------------------------------------------------
# Offline checks
# --------------------------------------------------------------------------

def _http_ok(url: str | None) -> bool:
    return bool(url) and url.strip().lower().startswith(("http://", "https://"))


def verify_column_counts(path: Path, scope: str) -> list[Finding]:
    """Structural check: every data row must have exactly as many columns as the
    header. Catches unquoted commas that silently shift fields -- a defect the
    vocabulary checks only catch by luck when a shifted value happens to be
    invalid.
    """
    with path.open(encoding="utf-8") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    rows = list(csv.reader(lines))
    if not rows:
        return [Finding("ERROR", scope, path.name, "empty-file", "no header/data rows")]
    width = len(rows[0])
    out: list[Finding] = []
    for row in rows[1:]:
        if not row:
            continue
        if len(row) != width:
            rid = row[0] if row else "<blank>"
            out.append(Finding("ERROR", scope, rid, "column-count",
                               f"{len(row)} columns, expected {width} "
                               "(likely an unquoted comma in a field)"))
    return out


def verify_flux_towers(records: list[dict]) -> list[Finding]:
    """Audit the eddy-covariance flux-tower registry."""
    out: list[Finding] = []
    seen: dict[str, int] = {}

    for r in records:
        sid = (r.get("site_id") or "").strip()
        rid = sid or "<missing id>"

        # Required fields present and non-empty.
        for field in REQUIRED_FLUX_FIELDS:
            val = r.get(field)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                out.append(Finding("ERROR", "flux", rid, "missing-field",
                                    f"required field '{field}' is empty"))

        # Duplicate ids.
        seen[sid] = seen.get(sid, 0) + 1

        # Controlled vocabularies.
        if r.get("measures_co2") not in MEASURES_CO2:
            out.append(Finding("ERROR", "flux", rid, "bad-measures_co2",
                                f"measures_co2={r.get('measures_co2')!r} not in {sorted(MEASURES_CO2)}"))
        if r.get("availability_tier") not in TIERS:
            out.append(Finding("ERROR", "flux", rid, "bad-tier",
                                f"availability_tier={r.get('availability_tier')!r} not in {sorted(TIERS)}"))
        if r.get("confidence") not in CONFIDENCE:
            out.append(Finding("ERROR", "flux", rid, "bad-confidence",
                                f"confidence={r.get('confidence')!r} not in {sorted(CONFIDENCE)}"))
        if r.get("coord_note") not in COORD_NOTE:
            out.append(Finding("ERROR", "flux", rid, "bad-coord_note",
                                f"coord_note={r.get('coord_note')!r} not in {sorted(COORD_NOTE)}"))
        net = r.get("network")
        if net not in FLUX_NETWORKS:
            out.append(Finding("ERROR", "flux", rid, "bad-network",
                                f"network={net!r} not in {sorted(FLUX_NETWORKS)}"))

        # Site-id format + country prefix.
        prefix = sid.split("-", 1)[0] if "-" in sid else ""
        if prefix not in COUNTRY_PREFIX:
            out.append(Finding("WARN", "flux", rid, "id-prefix",
                                f"id prefix {prefix!r} is not a known SA country code"))
        elif COUNTRY_PREFIX[prefix] != (r.get("country") or "").strip():
            out.append(Finding("ERROR", "flux", rid, "prefix-country-mismatch",
                                f"id prefix {prefix!r} maps to {COUNTRY_PREFIX[prefix]!r}, "
                                f"but country is {r.get('country')!r}"))
        if net in CODED_NETWORKS and not CANONICAL_CODE.match(sid):
            out.append(Finding("WARN", "flux", rid, "noncanonical-code",
                                f"network {net} expects a canonical CC-XXX code; got {sid!r}"))

        # Coordinates.
        lat, lon, note = r.get("lat"), r.get("lon"), r.get("coord_note")
        has_coords = lat is not None and lon is not None
        if has_coords:
            if not (SA_LAT[0] <= lat <= SA_LAT[1]):
                out.append(Finding("ERROR", "flux", rid, "lat-out-of-range",
                                    f"lat={lat} outside South America {SA_LAT}"))
            if not (SA_LON[0] <= lon <= SA_LON[1]):
                out.append(Finding("ERROR", "flux", rid, "lon-out-of-range",
                                    f"lon={lon} outside South America {SA_LON}"))
        else:
            if note == "exact":
                out.append(Finding("ERROR", "flux", rid, "exact-without-coords",
                                    "coord_note=exact but lat/lon are missing"))
            elif note != "unknown":
                out.append(Finding("WARN", "flux", rid, "missing-coords",
                                    f"lat/lon missing but coord_note={note!r} (expected 'unknown')"))

        # Year span.
        ys, ye = r.get("year_start"), r.get("year_end")
        for label, y in (("year_start", ys), ("year_end", ye)):
            if y is not None and not (YEAR_MIN <= y <= YEAR_MAX):
                out.append(Finding("WARN", "flux", rid, "year-range",
                                    f"{label}={y} outside plausible [{YEAR_MIN},{YEAR_MAX}]"))
        if ys is not None and ye is not None and ys > ye:
            out.append(Finding("ERROR", "flux", rid, "year-inverted",
                                f"year_start={ys} > year_end={ye}"))

        # Tier / access contradictions.
        access = r.get("data_access") or ""
        tier = r.get("availability_tier")
        if tier == 1 and _REQUEST_RX.search(access):
            out.append(Finding("WARN", "flux", rid, "tier1-request",
                                f"tier 1 (open) but data_access reads {access!r}"))
        if tier == 3 and _OPEN_RX.search(access) and not _REQUEST_RX.search(access):
            out.append(Finding("WARN", "flux", rid, "tier3-open-access",
                                f"tier 3 (private) but data_access reads {access!r}"))

        # Source URL.
        if not _http_ok(r.get("source_url")):
            out.append(Finding("ERROR", "flux", rid, "bad-source-url",
                                f"source_url is not http(s): {r.get('source_url')!r}"))

        # Advisory: ambiguous CO2 lives in the flux file but won't be harvested.
        if r.get("measures_co2") == "ambiguous":
            out.append(Finding("INFO", "flux", rid, "ambiguous-co2",
                                "measures_co2=ambiguous: confirm CO2 flux before relying on it"))

    for sid, n in seen.items():
        if n > 1:
            out.append(Finding("ERROR", "flux", sid or "<missing id>", "duplicate-id",
                                f"site_id appears {n} times"))
    return out


def verify_stock_programs(records: list[dict]) -> list[Finding]:
    """Audit the carbon-stock program registry."""
    out: list[Finding] = []
    seen: dict[str, int] = {}
    for r in records:
        name = (r.get("program") or "").strip()
        rid = name or "<missing program>"
        seen[name] = seen.get(name, 0) + 1

        for field in REQUIRED_STOCK_FIELDS:
            val = r.get(field)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                out.append(Finding("ERROR", "stock", rid, "missing-field",
                                    f"required field '{field}' is empty"))

        if r.get("stock_type") not in STOCK_TYPES:
            out.append(Finding("ERROR", "stock", rid, "bad-stock_type",
                                f"stock_type={r.get('stock_type')!r} not in {sorted(STOCK_TYPES)}"))
        if r.get("availability_tier") not in TIERS:
            out.append(Finding("ERROR", "stock", rid, "bad-tier",
                                f"availability_tier={r.get('availability_tier')!r} not in {sorted(TIERS)}"))
        if r.get("confidence") not in CONFIDENCE:
            out.append(Finding("ERROR", "stock", rid, "bad-confidence",
                                f"confidence={r.get('confidence')!r} not in {sorted(CONFIDENCE)}"))
        if not _http_ok(r.get("source_url")):
            out.append(Finding("ERROR", "stock", rid, "bad-source-url",
                                f"source_url is not http(s): {r.get('source_url')!r}"))

    for name, n in seen.items():
        if n > 1:
            out.append(Finding("ERROR", "stock", name or "<missing program>", "duplicate-program",
                                f"program appears {n} times"))
    return out


# --------------------------------------------------------------------------
# Online cross-check (optional, degrades gracefully)
# --------------------------------------------------------------------------

AMERIFLUX_SITE_API = "https://amfcdn.lbl.gov/api/v1/site_display/AmeriFlux"
# Coordinate drift (degrees) beyond which the registry and AmeriFlux disagree.
_COORD_TOL = 0.5


def _index_ameriflux(payload: list[dict]) -> dict[str, dict]:
    """Index the AmeriFlux site_display payload by SITE_ID (defensive about keys)."""
    index: dict[str, dict] = {}
    for site in payload or []:
        sid = site.get("SITE_ID") or site.get("Site_ID") or site.get("siteId")
        if sid:
            index[str(sid).strip()] = site
    return index


def cross_check_ameriflux(records: list[dict], client=None) -> list[Finding]:
    """Compare AmeriFlux-coded towers against the public site_display API.

    Returns a single INFO finding (and stops) if the host is unreachable, so the
    audit never fails merely because the network egress is restricted.
    """
    coded = [r for r in records if r.get("network") in {"AmeriFlux", "FLUXNET2015"}]
    if not coded:
        return []

    if client is None:
        from pipeline_http import RespectfulHttpClient
        client = RespectfulHttpClient()

    payload, result = client.fetch_json(AMERIFLUX_SITE_API)
    if payload is None:
        hint = ""
        if getattr(result, "status", 0) in (0, 403):
            hint = (" — host likely blocked by the environment egress allowlist; "
                    "add amfcdn.lbl.gov to network egress settings and re-run with --online")
        return [Finding("INFO", "online", "AmeriFlux", "api-unreachable",
                        f"could not fetch {AMERIFLUX_SITE_API} (status={getattr(result,'status',0)}){hint}")]

    index = _index_ameriflux(payload)
    out: list[Finding] = []
    for r in coded:
        sid = (r.get("site_id") or "").strip()
        site = index.get(sid)
        if site is None:
            out.append(Finding("WARN", "online", sid, "not-in-ameriflux",
                                "site code not found in the AmeriFlux site registry"))
            continue
        lat = r.get("lat")
        lon = r.get("lon")
        amf_lat = site.get("GRP_LOCATION", {}).get("LOCATION_LAT") if isinstance(site.get("GRP_LOCATION"), dict) else site.get("LOCATION_LAT")
        amf_lon = site.get("GRP_LOCATION", {}).get("LOCATION_LONG") if isinstance(site.get("GRP_LOCATION"), dict) else site.get("LOCATION_LONG")
        try:
            if lat is not None and amf_lat is not None and abs(float(lat) - float(amf_lat)) > _COORD_TOL:
                out.append(Finding("WARN", "online", sid, "coord-drift-lat",
                                   f"registry lat={lat} vs AmeriFlux {amf_lat}"))
            if lon is not None and amf_lon is not None and abs(float(lon) - float(amf_lon)) > _COORD_TOL:
                out.append(Finding("WARN", "online", sid, "coord-drift-lon",
                                   f"registry lon={lon} vs AmeriFlux {amf_lon}"))
        except (TypeError, ValueError):
            pass
    if not out:
        out.append(Finding("INFO", "online", "AmeriFlux", "cross-check-clean",
                           f"{len(coded)} coded towers matched the AmeriFlux registry within {_COORD_TOL}°"))
    return out


# --------------------------------------------------------------------------
# Reporting / CLI
# --------------------------------------------------------------------------

def verify_all(online: bool = False) -> list[Finding]:
    flux = reg.load_flux_towers()
    stock = reg.load_stock_programs()
    findings = (
        verify_column_counts(reg.FLUX_TOWERS_CSV, "flux")
        + verify_column_counts(reg.STOCK_PROGRAMS_CSV, "stock")
        + verify_flux_towers(flux)
        + verify_stock_programs(stock)
    )
    if online:
        findings += cross_check_ameriflux(flux)
    return findings


def _counts(findings: list[Finding]) -> dict[str, int]:
    c = {"ERROR": 0, "WARN": 0, "INFO": 0}
    for f in findings:
        c[f.severity] = c.get(f.severity, 0) + 1
    return c


def format_report(findings: list[Finding]) -> str:
    lines = ["Registry verification report", "=" * 28]
    c = _counts(findings)
    lines.append(f"ERROR={c['ERROR']}  WARN={c['WARN']}  INFO={c['INFO']}  (total {len(findings)})")
    lines.append("")
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    for f in sorted(findings, key=lambda x: (order.get(x.severity, 9), x.scope, x.record_id)):
        lines.append(f"[{f.severity:5}] {f.scope:6} {f.record_id:16} {f.code:22} {f.message}")
    if not findings:
        lines.append("(no findings)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the South American carbon registries.")
    parser.add_argument("--online", action="store_true",
                        help="also cross-check AmeriFlux-coded towers against the site_display API")
    parser.add_argument("--strict", action="store_true",
                        help="treat WARN findings as failures too")
    parser.add_argument("--json", type=Path, default=None,
                        help="write a machine-readable report (default: outputs/tables/registry_verification_report.json)")
    args = parser.parse_args(argv)

    findings = verify_all(online=args.online)
    print(format_report(findings))

    out_path = args.json or (OUTPUTS_TABLES_DIR / "registry_verification_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "counts": _counts(findings),
        "online": args.online,
        "findings": [asdict(f) for f in findings],
    }, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    c = _counts(findings)
    failed = c["ERROR"] > 0 or (args.strict and c["WARN"] > 0)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
