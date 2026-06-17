"""Offline, fixture-based tests for Southern-Cone station discovery."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts_discover_southern_cone_stations as disc  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def _load_amf():
    return disc.parse_ameriflux_sites(
        json.loads((FIXTURES / "ameriflux_sites_sample.json").read_text(encoding="utf-8"))
    )


def test_southern_cone_predicate_lat_box():
    # Tropical Brazil excluded by the latitude box even with a BR- prefix.
    assert disc.is_southern_cone("BR-CST", -7.97) is False
    assert disc.is_southern_cone("AR-CCg", -35.9244) is True
    assert disc.is_southern_cone("CL-SDF", -41.883) is True
    # Non Southern-Cone prefix excluded regardless of latitude.
    assert disc.is_southern_cone("US-Var", 38.41) is False


def test_parse_ameriflux_maps_schema():
    recs = _load_amf()
    by_id = {r["site_id"]: r for r in recs}
    assert "CL-SDF" in by_id
    rec = by_id["CL-SDF"]
    assert rec["data_hub"] == "AmeriFlux"
    assert rec["igbp"] == "EBF"
    assert float(rec["location_lat"]) == -41.883


def test_parse_fluxnet_html():
    recs = disc.parse_fluxnet_html((FIXTURES / "fluxnet_sites_sample.html").read_text())
    ids = {r["site_id"] for r in recs}
    assert {"CL-SDF", "AR-Vir", "UY-PIC", "BR-Sa1"} <= ids


def test_filter_excludes_tropical_includes_southern():
    recs = _load_amf() + disc.parse_fluxnet_html(
        (FIXTURES / "fluxnet_sites_sample.html").read_text()
    )
    merged = disc.merge_records(recs)
    in_scope, audit = disc.filter_southern_cone(merged, disc.DEFAULT_MAX_LAT)
    ids = {r["site_id"] for r in in_scope}
    # Original six + the two new Southern-Cone fixtures.
    assert {"CL-SDF", "CL-SDP", "CL-ACF", "AR-TF1", "AR-TF2", "AR-CCg"} <= ids
    assert {"AR-Vir", "UY-PIC"} <= ids
    assert "BR-CST" not in ids
    assert "BR-Sa1" not in ids
    assert "US-Var" not in ids
    # Audit records every discovered site.
    assert len(audit) == len(merged)


def test_dedup_collapses_cross_network():
    recs = _load_amf() + disc.parse_fluxnet_html(
        (FIXTURES / "fluxnet_sites_sample.html").read_text()
    )
    merged = disc.merge_records(recs)
    cl_sdf = [r for r in merged if r["site_id"] == "CL-SDF"]
    assert len(cl_sdf) == 1
    # AmeriFlux precedence preserves IGBP that FLUXNET HTML lacked.
    assert cl_sdf[0]["igbp"] == "EBF"
    assert "ameriflux" in cl_sdf[0]["_discovery_source"]
    assert "fluxnet" in cl_sdf[0]["_discovery_source"]


def test_catalog_schema_matches_existing_snapshot(tmp_path, monkeypatch):
    existing = disc.latest_snapshot()
    with open(existing, newline="", encoding="utf-8") as fh:
        existing_header = next(csv.reader(fh))
    assert disc.SNAPSHOT_COLUMNS == existing_header

    # write_catalog must emit exactly those columns.
    out = tmp_path / "catalog.csv"
    monkeypatch.setattr(disc, "catalog_path", lambda ts: out)
    recs = _load_amf()
    path = disc.write_catalog(recs)
    with open(path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header == disc.SNAPSHOT_COLUMNS
