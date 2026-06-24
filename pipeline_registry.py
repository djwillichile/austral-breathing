"""Loader for the South American carbon-observation registries.

Single source of truth for reading the curated CSV inventories in ``research/``:
    * ``south_america_flux_towers.csv``           (eddy-covariance CO2 towers)
    * ``south_america_carbon_stock_programs.csv``  (biomass/peat/soil stock)

Both files start with ``#`` comment lines documenting their schema; those are
skipped here. Empty numeric fields (e.g. unknown coordinates) resolve to
``None``. The loader is pure-stdlib so it is trivially unit-testable offline.
"""

from __future__ import annotations

import csv
from pathlib import Path

from pipeline_paths import RESEARCH_DIR

FLUX_TOWERS_CSV = RESEARCH_DIR / "south_america_flux_towers.csv"
STOCK_PROGRAMS_CSV = RESEARCH_DIR / "south_america_carbon_stock_programs.csv"


def _read_csv(path: Path) -> list[dict]:
    """Read a registry CSV, skipping leading ``#`` comment lines."""
    with path.open(encoding="utf-8") as fh:
        rows = [line for line in fh if not line.lstrip().startswith("#")]
    reader = csv.DictReader(rows)
    return [dict(r) for r in reader]


def _to_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def load_flux_towers(path: Path | None = None) -> list[dict]:
    """Return the EC CO2 flux-tower registry with typed lat/lon/year fields."""
    records = _read_csv(path or FLUX_TOWERS_CSV)
    for r in records:
        r["lat"] = _to_float(r.get("lat"))
        r["lon"] = _to_float(r.get("lon"))
        r["year_start"] = _to_int(r.get("year_start"))
        r["year_end"] = _to_int(r.get("year_end"))
        r["availability_tier"] = _to_int(r.get("availability_tier"))
    return records


def load_stock_programs(path: Path | None = None) -> list[dict]:
    """Return the carbon-stock program registry."""
    records = _read_csv(path or STOCK_PROGRAMS_CSV)
    for r in records:
        r["availability_tier"] = _to_int(r.get("availability_tier"))
    return records


def open_co2_flux_towers(path: Path | None = None) -> list[dict]:
    """Open (tier-1), CO2-measuring flux towers — the harvestable subset."""
    return [
        r
        for r in load_flux_towers(path)
        if r.get("measures_co2") == "yes" and r.get("availability_tier") == 1
    ]


def outreach_co2_flux_towers(path: Path | None = None) -> list[dict]:
    """Restricted-access (tier 2/3), CO2-measuring towers — the Phase-2 outreach
    target set: published-but-not-archived (tier 2) and national/private (tier 3)
    sites whose data must be obtained by contacting the operator/PI."""
    return [
        r
        for r in load_flux_towers(path)
        if r.get("measures_co2") == "yes" and r.get("availability_tier") in (2, 3)
    ]


def located_co2_flux_towers(path: Path | None = None) -> list[dict]:
    """CO2 flux towers with known coordinates — usable by the spatial analysis."""
    return [
        r
        for r in load_flux_towers(path)
        if r.get("measures_co2") == "yes" and r["lat"] is not None and r["lon"] is not None
    ]
