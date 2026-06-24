"""Tests for the Phase-2 outreach planner (scripts_build_outreach_plan.py)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline_registry as reg  # noqa: E402
import scripts_build_outreach_plan as op  # noqa: E402


# -- Target set: only restricted-access (tier 2/3) CO2 towers ---------------

def test_outreach_set_is_tier2_and_tier3_co2_only():
    towers = reg.outreach_co2_flux_towers()
    assert towers, "expected a non-empty tier-2/3 outreach set"
    for t in towers:
        assert t["measures_co2"] == "yes"
        assert t["availability_tier"] in (2, 3)


def test_outreach_counts_match_registry():
    """Regression guard on the campaign size (25 tier-2 + 7 tier-3 = 32)."""
    towers = reg.outreach_co2_flux_towers()
    tier2 = [t for t in towers if t["availability_tier"] == 2]
    tier3 = [t for t in towers if t["availability_tier"] == 3]
    assert len(tier2) == 25
    assert len(tier3) == 7
    assert len(towers) == 32


def test_non_co2_site_excluded():
    """UY-Estanzuela is tier-2 but ET/energy-only — must not be solicited."""
    ids = {t["site_id"] for t in reg.outreach_co2_flux_towers()}
    assert "UY-Estanzuela" not in ids


# -- institution_pi parsing -------------------------------------------------

def test_parse_clean_institution_and_pi():
    inst, pi, known = op.parse_institution_pi("University of Arizona / Scott Saleska")
    assert known and pi == "Scott Saleska" and inst == "University of Arizona"


def test_parse_unknown_is_not_a_pi():
    assert op.parse_institution_pi("unknown") == ("", "", False)
    assert op.parse_institution_pi("") == ("", "", False)


def test_parse_institution_only_has_no_pi():
    # A lone organisation (no person) must not be misread as a PI name.
    inst, pi, known = op.parse_institution_pi("INTA Rio Mayo")
    assert not known and pi == ""


def test_parse_collaboration_has_no_pi():
    inst, pi, known = op.parse_institution_pi("U. de Cuenca + U. Marburg")
    assert not known and pi == ""


def test_parse_trailing_person_plus_org_collapses_to_person():
    inst, pi, known = op.parse_institution_pi("UNAL / Jimenez + AGROSAVIA")
    assert known and pi == "Jimenez" and inst == "UNAL"


# -- Derived fields ---------------------------------------------------------

def test_priority_assignment():
    assert op._priority(2, True) == "P1"
    assert op._priority(2, False) == "P2"
    assert op._priority(3, True) == "P3"
    assert op._priority(3, False) == "P3"


def test_contact_route_branches():
    assert "consorcio" in op._contact_route("none", "Proprietary (request consortium)", "CO-EcoProMIS")
    amf = op._contact_route("AmeriFlux", "AmeriFlux registered; request PI", "CL-FJS")
    assert "CL-FJS" in amf and "<id>" not in amf


def test_build_contacts_rows_are_complete_and_sorted():
    rows = op.build_contacts()
    assert len(rows) == 32
    for r in rows:
        for field in op.CONTACT_FIELDS:
            assert field in r
    priorities = [r["priority"] for r in rows]
    assert priorities == sorted(priorities)


# -- Writers ----------------------------------------------------------------

def test_write_contacts_and_tracker(tmp_path, monkeypatch):
    contacts = tmp_path / "contacts.csv"
    tracker = tmp_path / "tracker.csv"
    monkeypatch.setattr(op, "CONTACTS_CSV", contacts)
    monkeypatch.setattr(op, "TRACKER_CSV", tracker)
    monkeypatch.setattr(op, "OUTPUTS_TABLES_DIR", tmp_path)

    rows = op.build_contacts()
    op.write_contacts(rows)
    assert op.write_tracker(rows) is True
    # Existing tracker is preserved unless forced.
    assert op.write_tracker(rows) is False
    assert op.write_tracker(rows, force=True) is True

    with tracker.open(encoding="utf-8") as fh:
        seeded = list(csv.DictReader(fh))
    assert len(seeded) == 32
    assert {r["status"] for r in seeded} == {"pendiente"}


def test_plan_markdown_mentions_worldclim_gap():
    md = op.build_plan_markdown(op.build_contacts())
    assert "WorldClim" in md and "host_not_allowed" in md
    assert "P1" in md and "Plantilla de correo" in md


def test_main_exit_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(op, "CONTACTS_CSV", tmp_path / "c.csv")
    monkeypatch.setattr(op, "TRACKER_CSV", tmp_path / "t.csv")
    monkeypatch.setattr(op, "PLAN_MD", tmp_path / "p.md")
    monkeypatch.setattr(op, "OUTPUTS_TABLES_DIR", tmp_path)
    monkeypatch.setattr(op, "RESEARCH_DIR", tmp_path)
    assert op.main([]) == 0
