"""Offline tests for the environmental representativeness core.

All tests use small synthetic arrays or the labelled demo grid; none require
network access or real WorldClim rasters."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts_representativeness_analysis as rep  # noqa: E402


def test_standardize_columns_zero_mean_unit_variance():
    m = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]])
    std, mean, sd = rep.standardize_columns(m)
    assert np.allclose(std.mean(axis=0), 0.0, atol=1e-9)
    assert np.allclose(std.std(axis=0), 1.0, atol=1e-9)
    assert np.allclose(mean, [2.0, 20.0])
    # Reusing the transform reproduces the same standardisation.
    std2, _, _ = rep.standardize_columns(m, mean=mean, std=sd)
    assert np.allclose(std, std2)


def test_standardize_handles_constant_column():
    m = np.array([[5.0, 1.0], [5.0, 2.0], [5.0, 3.0]])
    std, _, _ = rep.standardize_columns(m)
    assert np.all(np.isfinite(std))  # zero-variance column must not divide by zero


def test_nearest_env_distance_zero_at_station():
    stations = np.array([[0.0, 0.0], [3.0, 4.0]])
    grid = np.array([[0.0, 0.0], [3.0, 4.0], [0.0, 1.0]])
    dist, idx = rep.nearest_env_distance(grid, stations)
    assert dist[0] == pytest.approx(0.0)
    assert dist[1] == pytest.approx(0.0)
    assert dist[2] == pytest.approx(1.0)
    assert list(idx) == [0, 1, 0]


def test_representativeness_in_unit_interval_and_max_at_station():
    dist = np.array([0.0, 1.0, 5.0, 20.0])
    r = rep.representativeness_from_distance(dist, scale=2.0)
    assert r[0] == pytest.approx(1.0)
    assert np.all((r >= 0) & (r <= 1))
    assert np.all(np.diff(r) < 0)  # strictly decreasing with dissimilarity


def test_coverage_fraction_monotone_in_threshold():
    dist = np.array([0.2, 0.8, 1.5, 3.0])
    w = np.ones_like(dist)
    low = rep.coverage_fraction(dist, w, 1.0)
    high = rep.coverage_fraction(dist, w, 2.0)
    assert low == pytest.approx(0.5)
    assert high == pytest.approx(0.75)
    assert high >= low


def test_cell_area_positive_and_shrinks_toward_pole():
    eq = rep.cell_area_km2(0.0, 0.5, 0.5)
    south = rep.cell_area_km2(-55.0, 0.5, 0.5)
    assert eq > 0 and south > 0
    assert south < eq  # cells get smaller toward the pole


def test_demo_grid_shape_and_synthetic_flag():
    grid = rep.build_demo_climate_grid(step_deg=1.0)
    assert grid.synthetic is True
    assert set(grid.variables) == set(rep.BIOCLIM_VARS)
    for var in grid.variables:
        assert grid.data[var].shape == grid.shape
        assert np.all(np.isfinite(grid.data[var]))


def test_analyse_end_to_end_on_demo_grid():
    grid = rep.build_demo_climate_grid(step_deg=1.0)
    stations = [
        {"siteId": "CL-SDP", "lat": -41.879, "lon": -73.666, "ecosystemBiome": "Wetland"},
        {"siteId": "AR-CCg", "lat": -35.924, "lon": -61.186, "ecosystemBiome": "Grassland"},
        {"siteId": "AR-TF1", "lat": -54.973, "lon": -66.734, "ecosystemBiome": "Wetland"},
    ]
    result = rep.analyse(grid, stations, threshold_sd=1.0)

    assert result["synthetic"] is True
    assert result["nStations"] == 3
    assert 0.0 <= result["coverageFraction"] <= 1.0
    # Per-station representative areas never exceed the region and sum sanely.
    total = result["regionAreaKm2"]
    assert total > 0
    assert sum(p["representativeAreaKm2"] for p in result["perStation"]) <= total + 1.0
    # The payload must be JSON-serialisable for the web.
    json.dumps(result)
    g = result["grid"]
    assert g["nLat"] * g["nLon"] == len(g["rep"])


def test_stations_outside_region_are_dropped():
    grid = rep.build_demo_climate_grid(step_deg=1.0)
    stations = [
        {"siteId": "IN", "lat": -41.0, "lon": -73.0, "ecosystemBiome": "Wetland"},
        {"siteId": "OUT", "lat": 10.0, "lon": 10.0, "ecosystemBiome": "Tropical"},
    ]
    matrix, kept = rep.sample_grid_at_stations(grid, stations)
    assert [s["siteId"] for s in kept] == ["IN"]
    assert matrix.shape == (1, len(grid.variables))
