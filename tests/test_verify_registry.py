"""Tests for the registry verifier (scripts_verify_registry.py)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts_verify_registry as v  # noqa: E402


def _codes(findings, severity=None):
    return {f.code for f in findings if severity is None or f.severity == severity}


# -- The real registry must stay clean -------------------------------------

def test_real_registry_has_no_errors():
    """Regression guard: the committed registries audit ERROR-free."""
    findings = v.verify_all(online=False)
    errors = [f for f in findings if f.severity == "ERROR"]
    assert errors == [], f"registry has ERROR findings: {errors}"


def test_main_offline_exit_zero():
    assert v.main(["--json", "/tmp/_reg_report.json"]) == 0


# -- Offline checks catch synthetic defects --------------------------------

def _good_flux_row(**over):
    row = {
        "site_id": "AR-CCg", "country": "Argentina", "site_name": "x",
        "lat": -35.0, "lon": -61.0, "biome": "Grassland", "igbp": "GRA",
        "network": "AmeriFlux", "year_start": 2018, "year_end": 2020,
        "measures_co2": "yes", "availability_tier": 1,
        "data_access": "AmeriFlux download", "institution_pi": "INTA",
        "confidence": "high", "coord_note": "exact",
        "source_url": "https://ameriflux.lbl.gov/sites/siteinfo/AR-CCg",
    }
    row.update(over)
    return row


def test_clean_row_produces_no_errors():
    assert _codes(v.verify_flux_towers([_good_flux_row()]), "ERROR") == set()


def test_bad_vocabularies_flagged():
    bad = _good_flux_row(measures_co2="maybe", availability_tier=9,
                         confidence="ok", coord_note="roughly", network="MyNet")
    codes = _codes(v.verify_flux_towers([bad]), "ERROR")
    assert {"bad-measures_co2", "bad-tier", "bad-confidence",
            "bad-coord_note", "bad-network"} <= codes


def test_duplicate_site_id_flagged():
    codes = _codes(v.verify_flux_towers([_good_flux_row(), _good_flux_row()]), "ERROR")
    assert "duplicate-id" in codes


def test_coordinates_out_of_continent_flagged():
    codes = _codes(v.verify_flux_towers([_good_flux_row(lat=48.0, lon=2.0)]), "ERROR")
    assert {"lat-out-of-range", "lon-out-of-range"} <= codes


def test_exact_without_coords_flagged():
    codes = _codes(v.verify_flux_towers([_good_flux_row(lat=None, lon=None)]), "ERROR")
    assert "exact-without-coords" in codes


def test_inverted_year_span_flagged():
    codes = _codes(v.verify_flux_towers([_good_flux_row(year_start=2020, year_end=2016)]), "ERROR")
    assert "year-inverted" in codes


def test_prefix_country_mismatch_flagged():
    codes = _codes(v.verify_flux_towers([_good_flux_row(country="Chile")]), "ERROR")
    assert "prefix-country-mismatch" in codes


def test_bad_source_url_flagged():
    codes = _codes(v.verify_flux_towers([_good_flux_row(source_url="ameriflux.lbl.gov")]), "ERROR")
    assert "bad-source-url" in codes


def test_column_count_detects_unquoted_comma(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "# comment\n"
        "program,stock_type,countries,measures,institution,availability_tier,data_access,confidence,source_url\n"
        "Foo,soil,Brazil,SOC,Inst,1,ORNL DAAC (open, Earthdata),high,https://example.org\n",
        encoding="utf-8",
    )
    codes = _codes(v.verify_column_counts(csv_path, "stock"), "ERROR")
    assert "column-count" in codes


# -- Online cross-check degrades gracefully --------------------------------

def test_cross_check_skips_when_unreachable():
    """A blocked egress (no payload, status 0) yields one INFO, never an error."""
    client = SimpleNamespace(fetch_json=lambda url: (None, SimpleNamespace(status=0)))
    findings = v.cross_check_ameriflux([_good_flux_row()], client=client)
    assert len(findings) == 1
    assert findings[0].severity == "INFO" and findings[0].code == "api-unreachable"


def test_cross_check_detects_coord_drift():
    payload = [{"SITE_ID": "AR-CCg", "LOCATION_LAT": -10.0, "LOCATION_LONG": -61.0}]
    client = SimpleNamespace(fetch_json=lambda url: (payload, SimpleNamespace(status=200)))
    codes = _codes(v.cross_check_ameriflux([_good_flux_row(lat=-35.0, lon=-61.0)], client=client))
    assert "coord-drift-lat" in codes and "coord-drift-lon" not in codes


def test_cross_check_clean_when_matching():
    payload = [{"SITE_ID": "AR-CCg", "LOCATION_LAT": -35.0, "LOCATION_LONG": -61.0}]
    client = SimpleNamespace(fetch_json=lambda url: (payload, SimpleNamespace(status=200)))
    findings = v.cross_check_ameriflux([_good_flux_row(lat=-35.0, lon=-61.0)], client=client)
    assert any(f.code == "cross-check-clean" for f in findings)
