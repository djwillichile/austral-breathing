"""Offline tests for the South American registry, harvester, and web export."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pipeline_registry as reg  # noqa: E402
import scripts_build_registry_web_data as web  # noqa: E402
import scripts_harvest_open_flux_data as harvest  # noqa: E402
import scripts_representativeness_analysis as rep  # noqa: E402


def test_flux_registry_loads_and_types():
    towers = reg.load_flux_towers()
    assert len(towers) > 20
    # Known anchor site present and well-typed.
    sdf = next(t for t in towers if t["site_id"] == "CL-SDF")
    assert isinstance(sdf["lat"], float) and isinstance(sdf["lon"], float)
    assert sdf["measures_co2"] == "yes"
    assert sdf["availability_tier"] == 1


def test_unknown_coordinates_resolve_to_none():
    towers = {t["site_id"]: t for t in reg.load_flux_towers()}
    # EcoProMIS has no public coordinates -> None, but still a CO2 tower.
    eco = towers["CO-EcoProMIS"]
    assert eco["lat"] is None and eco["lon"] is None
    assert eco["measures_co2"] == "yes"


def test_open_subset_is_tier1_co2_only():
    for t in reg.open_co2_flux_towers():
        assert t["availability_tier"] == 1
        assert t["measures_co2"] == "yes"


def test_located_subset_has_coordinates():
    located = reg.located_co2_flux_towers()
    assert all(t["lat"] is not None and t["lon"] is not None for t in located)
    assert all(t["measures_co2"] == "yes" for t in located)
    # The ET-only Uruguay tower must be excluded (measures_co2 == "no").
    assert "UY-Estanzuela" not in {t["site_id"] for t in located}


def test_stock_registry_loads():
    programs = reg.load_stock_programs()
    names = {p["program"] for p in programs}
    assert "RAINFOR" in names and "SISLAC" in names
    assert all(isinstance(p["availability_tier"], int) for p in programs)


def test_harvest_plan_groups_by_network():
    plan = harvest.build_plan()
    assert plan, "expected at least one open tower"
    networks = {p["network"] for p in plan}
    assert "AmeriFlux" in networks
    # Every open tower is tier-1 CO2; ICOS is the auto-fetchable one.
    assert any(p["auto_fetchable"] for p in plan if p["network"] == "ICOS")
    assert all(isinstance(p["site_id"], str) for p in plan)


def test_web_export_payload_shape():
    flux = web._flux_payload()
    stock = web._stock_payload()
    counts = web._counts(flux)
    assert counts["fluxTowersCo2"] >= counts["fluxTowersOpen"] > 0
    assert sum(counts["byCountry"].values()) == counts["fluxTowersCo2"]
    assert len(stock) > 10


def test_representativeness_registry_stations_match_located():
    stations = rep.load_stations_from_registry()
    assert {s["siteId"] for s in stations} == {
        t["site_id"] for t in reg.located_co2_flux_towers()
    }
    assert all({"siteId", "lat", "lon", "ecosystemBiome"} <= set(s) for s in stations)


def test_regions_are_well_formed():
    for name, bbox in rep.REGIONS.items():
        assert bbox["lon_min"] < bbox["lon_max"]
        assert bbox["lat_min"] < bbox["lat_max"]
    # South America must extend north of the Southern Cone box.
    assert rep.REGIONS["south-america"]["lat_max"] > rep.REGIONS["cono-sur"]["lat_max"]
