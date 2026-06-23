"""Environmental representativeness of the eddy-covariance network.

This is the *rigorous* representativeness analysis that complements the simple
nearest-neighbour "geographic reach" proxy already exported by
``scripts_export_web_data.py``.

Method (Hargrove/Hoffman-style network representativeness)
----------------------------------------------------------
1. Take a multivariate climate description of the Southern Cone on a regular
   grid (WorldClim 2.1 bioclimatic surfaces, cropped to the region).
2. Sample the same climate variables at every flux-tower location.
3. Standardise every climate variable to zero mean / unit variance using the
   *regional grid* statistics, so each axis of the environmental space is
   comparable.
4. For each grid cell, compute the Euclidean distance in standardised
   environmental space to the nearest station. Small distance => the network
   already samples conditions like that cell (well represented); large
   distance => an environmental gap the network does not cover.
5. Turn the dissimilarity surface into a 0..1 representativeness score and
   summarise per-station "representative area" (the territory for which each
   station is the closest environmental analogue, within a similarity
   threshold).

The numerical core (``standardize_columns``, ``nearest_env_distance``,
``representativeness_from_distance``, ``cell_area_km2`` ...) is pure NumPy and
unit-tested offline. The WorldClim loader is optional and only imported when
real rasters are present under ``data/climate/`` (requires ``rasterio``).

Network note
------------
Real WorldClim surfaces must be downloaded once from the official UC Davis
mirror (``https://geodata.ucdavis.edu/climate/worldclim/``). In sandboxes where
outbound hosts are blocked this download is skipped; run ``--demo`` to produce a
clearly-labelled SYNTHETIC climate field so the web visualisation and the full
pipeline can be exercised end to end. The synthetic field is *not* real climate
and every artifact it produces is tagged ``"synthetic": true``.

Usage
-----
    python scripts_representativeness_analysis.py            # use real rasters if present
    python scripts_representativeness_analysis.py --demo     # synthetic demo surface
    python scripts_representativeness_analysis.py --download  # fetch WorldClim (needs network)
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass

import numpy as np

from pipeline_paths import CLIENT_PUBLIC_DATA_DIR, DATA_DIR

# --------------------------------------------------------------------------
# Region + variable configuration
# --------------------------------------------------------------------------
# Named regions (lon/lat bounding boxes, degrees). "cono-sur" comfortably
# contains the original Southern-Cone stations (AR-CCg ~-35.9 down to Tierra del
# Fuego ~-55); "south-america" spans the continent for the regional inventory.
REGIONS = {
    "cono-sur": {"lon_min": -76.0, "lon_max": -52.0, "lat_min": -56.0, "lat_max": -30.0},
    "south-america": {"lon_min": -82.0, "lon_max": -34.0, "lat_min": -56.0, "lat_max": 13.0},
}

# Human-readable region names for the grid ``source`` provenance label.
REGION_LABELS = {
    "cono-sur": "the Southern Cone",
    "south-america": "South America",
}

# Default region (kept as a module global so the grid/sampling helpers can read
# it; ``main`` overrides it from --region).
REGION_BBOX = REGIONS["cono-sur"]

# WorldClim 2.1 bioclimatic variables used as the environmental axes. Mean and
# seasonality of both temperature and precipitation capture the dominant
# climate gradients of the region without over-weighting any single axis.
BIOCLIM_VARS = {
    "bio1": "Annual mean temperature",
    "bio4": "Temperature seasonality",
    "bio12": "Annual precipitation",
    "bio15": "Precipitation seasonality",
}

WORLDCLIM_BASE = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base/"
CLIMATE_DIR = DATA_DIR / "climate"

# A cell is "well represented" when an environmental analogue exists within this
# many standard deviations in the standardised climate space.
DEFAULT_THRESHOLD_SD = 1.0

EARTH_RADIUS_KM = 6371.0


# --------------------------------------------------------------------------
# Data container
# --------------------------------------------------------------------------
@dataclass
class ClimateGrid:
    """A regular lat/lon climate grid plus per-variable 2-D arrays.

    ``lats`` is north-to-south or south-to-north (we keep whatever order the
    source produces and carry it through consistently). ``data`` maps each
    variable name to a ``(n_lat, n_lon)`` array with ``np.nan`` over nodata
    (e.g. ocean)."""

    lats: np.ndarray
    lons: np.ndarray
    data: dict[str, np.ndarray]
    variables: list[str]
    synthetic: bool
    source: str

    @property
    def shape(self) -> tuple[int, int]:
        return (self.lats.size, self.lons.size)


# --------------------------------------------------------------------------
# Pure numerical core (unit-tested, no I/O)
# --------------------------------------------------------------------------
def standardize_columns(
    matrix: np.ndarray, mean: np.ndarray | None = None, std: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Z-score each column. Reuses provided ``mean``/``std`` when given so the
    grid transform can be applied identically to the station matrix."""
    matrix = np.asarray(matrix, dtype=float)
    if mean is None:
        mean = np.nanmean(matrix, axis=0)
    if std is None:
        std = np.nanstd(matrix, axis=0)
    safe_std = np.where(std == 0, 1.0, std)
    return (matrix - mean) / safe_std, mean, std


def nearest_env_distance(
    grid_points: np.ndarray, station_points: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """For each grid point return (distance, index) of the nearest station in
    standardised environmental space (Euclidean).

    ``grid_points`` is ``(n_grid, n_vars)``; ``station_points`` is
    ``(n_stations, n_vars)``."""
    grid_points = np.asarray(grid_points, dtype=float)
    station_points = np.asarray(station_points, dtype=float)
    # (n_grid, n_stations) pairwise distances via broadcasting.
    diff = grid_points[:, None, :] - station_points[None, :, :]
    dist = np.sqrt(np.sum(diff * diff, axis=2))
    nearest_idx = np.argmin(dist, axis=1)
    nearest_dist = dist[np.arange(dist.shape[0]), nearest_idx]
    return nearest_dist, nearest_idx


def representativeness_from_distance(
    dist: np.ndarray, scale: float | None = None
) -> np.ndarray:
    """Map environmental dissimilarity (>=0) to a 0..1 representativeness score
    with an exponential decay. ``scale`` defaults to the median distance, a
    robust characteristic length of the region's environmental spread."""
    dist = np.asarray(dist, dtype=float)
    if scale is None:
        positive = dist[dist > 0]
        scale = float(np.median(positive)) if positive.size else 1.0
    if scale <= 0:
        scale = 1.0
    return np.exp(-dist / scale)


def cell_area_km2(lat_deg: float, dlat_deg: float, dlon_deg: float) -> float:
    """Approximate the area of a regular grid cell centred at ``lat_deg``."""
    lat_rad = math.radians(lat_deg)
    half = math.radians(dlat_deg) / 2.0
    dlon_rad = math.radians(dlon_deg)
    return (
        EARTH_RADIUS_KM
        * EARTH_RADIUS_KM
        * dlon_rad
        * (math.sin(lat_rad + half) - math.sin(lat_rad - half))
    )


def coverage_fraction(dist: np.ndarray, weights: np.ndarray, threshold: float) -> float:
    """Area-weighted fraction of the region within ``threshold`` of a station."""
    dist = np.asarray(dist, dtype=float)
    weights = np.asarray(weights, dtype=float)
    total = float(np.sum(weights))
    if total <= 0:
        return 0.0
    return float(np.sum(weights[dist <= threshold]) / total)


# --------------------------------------------------------------------------
# Climate sources: real WorldClim rasters (optional) or synthetic demo field
# --------------------------------------------------------------------------
def load_worldclim_grid(resolution: str = "10m", region_label: str = "the Southern Cone") -> ClimateGrid | None:
    """Load WorldClim 2.1 bioclim GeoTIFFs cropped to ``REGION_BBOX``.

    Expects files like ``data/climate/wc2.1_<res>_bio_1.tif`` (the layout of the
    official ``wc2.1_<res>_bio.zip`` archive). Returns ``None`` if the rasters or
    ``rasterio`` are unavailable, so callers can degrade gracefully."""
    try:
        import rasterio
        from rasterio.windows import from_bounds
    except ImportError:
        return None

    band_files = {
        var: CLIMATE_DIR / f"wc2.1_{resolution}_bio_{var[3:]}.tif" for var in BIOCLIM_VARS
    }
    if not all(path.exists() for path in band_files.values()):
        return None

    data: dict[str, np.ndarray] = {}
    lats = lons = None
    for var, path in band_files.items():
        with rasterio.open(path) as src:
            window = from_bounds(
                REGION_BBOX["lon_min"],
                REGION_BBOX["lat_min"],
                REGION_BBOX["lon_max"],
                REGION_BBOX["lat_max"],
                transform=src.transform,
            )
            arr = src.read(1, window=window).astype(float)
            arr[arr == src.nodata] = np.nan
            data[var] = arr
            if lats is None:
                transform = src.window_transform(window)
                n_rows, n_cols = arr.shape
                lons = transform.c + (np.arange(n_cols) + 0.5) * transform.a
                lats = transform.f + (np.arange(n_rows) + 0.5) * transform.e
    return ClimateGrid(
        lats=np.asarray(lats),
        lons=np.asarray(lons),
        data=data,
        variables=list(BIOCLIM_VARS),
        synthetic=False,
        source=f"WorldClim 2.1 bioclim ({resolution}), cropped to {region_label}",
    )


def build_demo_climate_grid(step_deg: float = 0.5) -> ClimateGrid:
    """A SYNTHETIC, clearly-labelled climate field for end-to-end demonstration.

    The gradients are physically plausible for the Southern Cone (cooling and
    more seasonal southward, a wet Pacific/Andean west versus a dry Patagonian
    steppe east) but they are an analytic mock-up, NOT measured climate. Every
    artifact derived from it carries ``synthetic=True``."""
    lats = np.arange(REGION_BBOX["lat_max"], REGION_BBOX["lat_min"] - 1e-9, -step_deg)
    lons = np.arange(REGION_BBOX["lon_min"], REGION_BBOX["lon_max"] + 1e-9, step_deg)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # Annual mean temperature: warm in the north, cold toward Cape Horn.
    bio1 = 20.0 + 0.55 * (lat_grid + 30.0)
    # Temperature seasonality: rises southward and inland (away from the ocean).
    bio4 = 350.0 - 4.0 * (lat_grid + 30.0) + 6.0 * (lon_grid + 64.0)
    # Annual precipitation: a wet Pacific/Andean band (~lon -73) decaying east
    # into the dry Patagonian steppe.
    bio12 = 400.0 + 2200.0 * np.exp(-((lon_grid + 73.0) ** 2) / 9.0)
    bio12 = np.clip(bio12, 150.0, 3500.0)
    # Precipitation seasonality: stronger in the Mediterranean-ish north.
    bio15 = 55.0 + 1.2 * (lat_grid + 30.0)

    data = {"bio1": bio1, "bio4": bio4, "bio12": bio12, "bio15": bio15}
    return ClimateGrid(
        lats=lats,
        lons=lons,
        data=data,
        variables=list(BIOCLIM_VARS),
        synthetic=True,
        source="SYNTHETIC demonstration field (not measured climate)",
    )


# --------------------------------------------------------------------------
# Station sampling + analysis assembly
# --------------------------------------------------------------------------
def _nearest_index(values: np.ndarray, target: float) -> int:
    return int(np.argmin(np.abs(values - target)))


def sample_grid_at_stations(
    grid: ClimateGrid, stations: list[dict]
) -> tuple[np.ndarray, list[dict]]:
    """Return the climate matrix (n_stations, n_vars) sampled at each station
    (nearest cell), plus the stations that fall inside the grid."""
    rows: list[list[float]] = []
    kept: list[dict] = []
    for st in stations:
        if not (
            REGION_BBOX["lon_min"] <= st["lon"] <= REGION_BBOX["lon_max"]
            and REGION_BBOX["lat_min"] <= st["lat"] <= REGION_BBOX["lat_max"]
        ):
            continue
        i = _nearest_index(grid.lats, st["lat"])
        j = _nearest_index(grid.lons, st["lon"])
        row = [float(grid.data[var][i, j]) for var in grid.variables]
        if any(math.isnan(v) for v in row):
            continue
        rows.append(row)
        kept.append(st)
    return np.asarray(rows, dtype=float), kept


def analyse(
    grid: ClimateGrid, stations: list[dict], threshold_sd: float = DEFAULT_THRESHOLD_SD
) -> dict:
    """Run the full representativeness analysis and return a JSON-ready dict."""
    n_lat, n_lon = grid.shape
    dlat = abs(float(grid.lats[1] - grid.lats[0])) if n_lat > 1 else 1.0
    dlon = abs(float(grid.lons[1] - grid.lons[0])) if n_lon > 1 else 1.0

    # Flatten valid (land) cells into a feature matrix.
    stack = np.stack([grid.data[var] for var in grid.variables], axis=-1)  # (nlat,nlon,nvar)
    flat = stack.reshape(-1, len(grid.variables))
    valid = ~np.any(np.isnan(flat), axis=1)
    grid_matrix = flat[valid]

    station_matrix, kept = sample_grid_at_stations(grid, stations)
    if station_matrix.size == 0 or grid_matrix.size == 0:
        raise ValueError("No stations or no valid grid cells inside the region.")

    # Standardise on the grid statistics, apply the same transform to stations.
    grid_std, mean, std = standardize_columns(grid_matrix)
    station_std, _, _ = standardize_columns(station_matrix, mean=mean, std=std)

    dist, nearest_idx = nearest_env_distance(grid_std, station_std)
    rep = representativeness_from_distance(dist)

    # Area weights for the valid cells.
    lat_idx = (np.arange(n_lat * n_lon) // n_lon)[valid]
    cell_lats = grid.lats[lat_idx]
    areas = np.array([cell_area_km2(float(la), dlat, dlon) for la in cell_lats])

    coverage = coverage_fraction(dist, areas, threshold_sd)
    total_area = float(np.sum(areas))

    per_station = []
    for s_idx, st in enumerate(kept):
        assigned = nearest_idx == s_idx
        within = assigned & (dist <= threshold_sd)
        rep_area = float(np.sum(areas[within]))
        assigned_dist = dist[assigned]
        per_station.append(
            {
                "siteId": st["siteId"],
                "biome": st.get("ecosystemBiome") or st.get("biome") or "Unknown",
                "representativeAreaKm2": round(rep_area, 1),
                "representativeAreaPct": round(100.0 * rep_area / total_area, 2)
                if total_area
                else 0.0,
                "assignedAreaKm2": round(float(np.sum(areas[assigned])), 1),
                "medianDissimilarity": round(
                    float(np.median(assigned_dist)) if assigned_dist.size else 0.0, 3
                ),
            }
        )
    per_station.sort(key=lambda d: d["representativeAreaKm2"], reverse=True)

    grid_payload = _downsample_grid(grid, rep, valid)
    return {
        "method": (
            "Environmental representativeness: standardised multivariate climate "
            "distance from every regional grid cell to the nearest flux station "
            "(Hargrove/Hoffman-style network representativeness)."
        ),
        "source": grid.source,
        "synthetic": grid.synthetic,
        "variables": [{"id": v, "label": BIOCLIM_VARS.get(v, v)} for v in grid.variables],
        "bbox": REGION_BBOX,
        "resolutionDeg": round(dlat, 4),
        "thresholdSd": threshold_sd,
        "coverageFraction": round(coverage, 4),
        "regionAreaKm2": round(total_area, 1),
        "nStations": len(kept),
        "nValidCells": int(valid.sum()),
        "grid": grid_payload,
        "perStation": per_station,
    }


def _downsample_grid(
    grid: ClimateGrid, rep: np.ndarray, valid: np.ndarray, max_cells: int = 80
) -> dict:
    """Pack the representativeness surface into a compact web payload.

    Strides the grid down to at most ``max_cells`` per axis and emits a flat
    row-major array of rounded scores (``None`` over nodata cells)."""
    n_lat, n_lon = grid.shape
    full = np.full(n_lat * n_lon, np.nan)
    full[valid] = rep
    full = full.reshape(n_lat, n_lon)

    lat_stride = max(1, math.ceil(n_lat / max_cells))
    lon_stride = max(1, math.ceil(n_lon / max_cells))
    sub = full[::lat_stride, ::lon_stride]
    sub_lats = grid.lats[::lat_stride]
    sub_lons = grid.lons[::lon_stride]

    flat = [None if math.isnan(v) else round(float(v), 4) for v in sub.ravel()]
    return {
        "latStart": round(float(sub_lats[0]), 4),
        "lonStart": round(float(sub_lons[0]), 4),
        "dLat": round(float(sub_lats[1] - sub_lats[0]), 4) if sub_lats.size > 1 else 0.0,
        "dLon": round(float(sub_lons[1] - sub_lons[0]), 4) if sub_lons.size > 1 else 0.0,
        "nLat": int(sub.shape[0]),
        "nLon": int(sub.shape[1]),
        "rep": flat,
    }


def load_stations() -> list[dict]:
    """Read station coordinates/biomes from the exported web payload."""
    path = CLIENT_PUBLIC_DATA_DIR / "stations.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["stations"]


def load_stations_from_registry() -> list[dict]:
    """CO2 flux towers with coordinates from the South American registry,
    normalised to the keys the analysis expects (siteId/lat/lon/ecosystemBiome)."""
    from pipeline_registry import located_co2_flux_towers

    stations = []
    for t in located_co2_flux_towers():
        stations.append(
            {
                "siteId": t["site_id"],
                "lat": t["lat"],
                "lon": t["lon"],
                "ecosystemBiome": t.get("biome") or "Unknown",
            }
        )
    return stations


def download_worldclim(resolution: str = "10m") -> None:
    """Document + attempt the one-time WorldClim download (needs network).

    Kept deliberately simple and explicit so it can be run wherever outbound
    access to the UC Davis mirror is permitted."""
    import io
    import zipfile

    import requests

    CLIMATE_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{WORLDCLIM_BASE}wc2.1_{resolution}_bio.zip"
    print(f"Downloading {url} ...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(CLIMATE_DIR)
    print(f"Extracted WorldClim bioclim rasters to {CLIMATE_DIR}")


def main() -> None:
    global REGION_BBOX

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use a synthetic (clearly-labelled) climate field instead of real rasters.",
    )
    parser.add_argument(
        "--download", action="store_true", help="Fetch WorldClim rasters first (needs network)."
    )
    parser.add_argument("--resolution", default="10m", help="WorldClim resolution (e.g. 10m, 5m).")
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD_SD, help="Similarity threshold (SD)."
    )
    parser.add_argument(
        "--region",
        choices=sorted(REGIONS),
        default="cono-sur",
        help="Analysis bounding box (default: cono-sur).",
    )
    parser.add_argument(
        "--stations",
        choices=["web", "registry"],
        default="web",
        help="Station source: 'web' (stations.json) or 'registry' (South American CO2 towers).",
    )
    args = parser.parse_args()

    REGION_BBOX = REGIONS[args.region]

    if args.download:
        download_worldclim(args.resolution)

    grid = load_worldclim_grid(args.resolution, REGION_LABELS.get(args.region, args.region))
    if grid is None and args.demo:
        grid = build_demo_climate_grid()
        if args.region != "cono-sur":
            print(
                "Note: the --demo synthetic field is tuned for the Southern Cone; "
                "for continental scope use real WorldClim rasters (--download)."
            )
    if grid is None:
        print(
            "No WorldClim rasters found under data/climate/ and --demo not set.\n"
            "  • To use real climate: download once with --download (needs outbound\n"
            f"    access to {WORLDCLIM_BASE}) or place wc2.1_<res>_bio_*.tif there.\n"
            "  • To preview the visualisation now: re-run with --demo (synthetic field).\n"
            "No representativeness_grid.json was written."
        )
        return

    stations = load_stations_from_registry() if args.stations == "registry" else load_stations()
    result = analyse(grid, stations, threshold_sd=args.threshold)

    CLIENT_PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = CLIENT_PUBLIC_DATA_DIR / "representativeness_grid.json"
    out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    tag = " (SYNTHETIC demo)" if result["synthetic"] else ""
    print(
        f"Wrote {out}{tag}: coverage={result['coverageFraction']:.1%} of the region "
        f"within {args.threshold} SD, {result['nStations']} stations, "
        f"{result['nValidCells']} grid cells."
    )


if __name__ == "__main__":
    main()
