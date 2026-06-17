from __future__ import annotations

import json
import math

import pandas as pd

from pipeline_paths import (
    BASE_DIR as ROOT,
    CLIENT_PUBLIC_DATA_DIR,
    OUTPUTS_TABLES_DIR,
    PROCESSED_DIR,
)

SRC = OUTPUTS_TABLES_DIR / 'station_overview.csv'
DST = ROOT / 'client' / 'src' / 'lib' / 'stationsData.ts'

# Core flux/meteorology variables exposed in the interactive charts.
TIMESERIES_VARS = ['NEE', 'GPP', 'LE', 'H', 'TA', 'SW_IN']


def _to_native(value):
    if pd.isna(value):
        return None
    if hasattr(value, 'item'):
        try:
            return value.item()
        except Exception:
            return value
    return value


def main() -> None:
    df = pd.read_csv(SRC)

    stations = []
    for _, row in df.sort_values(['utility_score', 'site_id'], ascending=[False, True]).iterrows():
        stations.append(
            {
                'siteId': _to_native(row['site_id']),
                'siteName': _to_native(row['site_name']),
                'country': _to_native(row['country']),
                'regionalScope': _to_native(row['regional_scope']),
                'ecosystem': _to_native(row['ecosystem_note']),
                'network': _to_native(row['network']),
                'lat': float(row['location_lat']),
                'lon': float(row['location_long']),
                'yearStart': int(row['year_start']),
                'yearEnd': int(row['year_end']),
                'coverageYears': int(row['temporal_coverage_years']),
                'observations': int(row['total_observations']),
                'validNeePct': float(row['valid_nee_pct']),
                'validGppPct': float(row['valid_gpp_pct']),
                'validLePct': float(row['valid_le_pct']),
                'validHPct': float(row['valid_h_pct']),
                'validTaPct': float(row['valid_ta_pct']),
                'validSwInPct': float(row['valid_sw_in_pct']),
                'acceptableQcPct': float(row['acceptable_qc_pct']),
                'variablesAvailableCount': int(row['variables_available_count']),
                'utilityScore': float(row['utility_score']),
                'qualityClass': _to_native(row['quality_class']),
                'qualityColor': _to_native(row['quality_color']),
                'markerRadius': float(row['marker_radius']),
                'variablesPresent': [part.strip() for part in str(row['variables_present']).split(',') if part.strip()],
                'productId': _to_native(row['product_id']),
                'notes': _to_native(row['notes']),
            }
        )

    stats = {
        'stationCount': len(stations),
        'countryCount': int(df['country'].nunique()),
        'networkCount': int(df['network'].nunique()),
        'yearMin': int(df['year_start'].min()),
        'yearMax': int(df['year_end'].max()),
        'observationSum': int(df['total_observations'].sum()),
        'highQualityCount': int((df['quality_class'] == 'high').sum()),
        'mediumQualityCount': int((df['quality_class'] == 'medium').sum()),
        'lowQualityCount': int((df['quality_class'] == 'low').sum()),
        'meanUtilityScore': round(float(df['utility_score'].mean()), 3),
        'topSiteId': str(df.sort_values('utility_score', ascending=False).iloc[0]['site_id']),
    }

    module_text = (
        '// Design reminder: regional scientific editorialism with cartographic modernism.\n'
        '// Keep data presentation traceable, elegant, and publication-oriented.\n\n'
        'export type StationRecord = {\n'
        '  siteId: string;\n'
        '  siteName: string;\n'
        '  country: string;\n'
        '  regionalScope: string;\n'
        '  ecosystem: string;\n'
        '  network: string;\n'
        '  lat: number;\n'
        '  lon: number;\n'
        '  yearStart: number;\n'
        '  yearEnd: number;\n'
        '  coverageYears: number;\n'
        '  observations: number;\n'
        '  validNeePct: number;\n'
        '  validGppPct: number;\n'
        '  validLePct: number;\n'
        '  validHPct: number;\n'
        '  validTaPct: number;\n'
        '  validSwInPct: number;\n'
        '  acceptableQcPct: number;\n'
        '  variablesAvailableCount: number;\n'
        '  utilityScore: number;\n'
        '  qualityClass: string;\n'
        '  qualityColor: string;\n'
        '  markerRadius: number;\n'
        '  variablesPresent: string[];\n'
        '  productId: string;\n'
        '  notes: string;\n'
        '};\n\n'
        'export type ProjectStats = {\n'
        '  stationCount: number;\n'
        '  countryCount: number;\n'
        '  networkCount: number;\n'
        '  yearMin: number;\n'
        '  yearMax: number;\n'
        '  observationSum: number;\n'
        '  highQualityCount: number;\n'
        '  mediumQualityCount: number;\n'
        '  lowQualityCount: number;\n'
        '  meanUtilityScore: number;\n'
        '  topSiteId: string;\n'
        '};\n\n'
        f'export const stationData: StationRecord[] = {json.dumps(stations, ensure_ascii=False, indent=2)} as StationRecord[];\n\n'
        f'export const projectStats: ProjectStats = {json.dumps(stats, ensure_ascii=False, indent=2)} as ProjectStats;\n'
    )

    DST.write_text(module_text + '\n', encoding='utf-8')
    print(f'Wrote {DST}')

    export_json(df)


# --------------------------------------------------------------------------
# JSON export for the interactive web visualisations
# --------------------------------------------------------------------------
def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _quantiles(series: pd.Series) -> dict:
    clean = series.dropna()
    if clean.empty:
        return {k: None for k in ['n', 'mean', 'sd', 'min', 'p5', 'p25', 'median', 'p75', 'p95', 'max']}
    return {
        'n': int(clean.shape[0]),
        'mean': round(float(clean.mean()), 4),
        'sd': round(float(clean.std()), 4),
        'min': round(float(clean.min()), 4),
        'p5': round(float(clean.quantile(0.05)), 4),
        'p25': round(float(clean.quantile(0.25)), 4),
        'median': round(float(clean.median()), 4),
        'p75': round(float(clean.quantile(0.75)), 4),
        'p95': round(float(clean.quantile(0.95)), 4),
        'max': round(float(clean.max()), 4),
    }


def load_timeseries(site_id: str) -> pd.DataFrame | None:
    path = PROCESSED_DIR / site_id / f'{site_id}_daily_standardized.csv'
    if not path.exists():
        return None
    ts = pd.read_csv(path)
    ts['timestamp'] = pd.to_datetime(ts['timestamp'], errors='coerce')
    return ts


def build_geographic_reach(df: pd.DataFrame) -> dict[str, dict]:
    """Nearest-neighbour distance and an indicative representativeness radius.

    The 'reach' is half the distance to the nearest station (a simple, honest
    proxy for the geographic extent each station stands for, without external
    climate rasters)."""
    coords = [(r['site_id'], float(r['location_lat']), float(r['location_long'])) for _, r in df.iterrows()]
    reach = {}
    for site_id, lat, lon in coords:
        nearest_km = None
        nearest_id = None
        for other_id, olat, olon in coords:
            if other_id == site_id:
                continue
            d = _haversine_km(lat, lon, olat, olon)
            if nearest_km is None or d < nearest_km:
                nearest_km, nearest_id = d, other_id
        reach[site_id] = {
            'nearestNeighborId': nearest_id,
            'nearestNeighborKm': round(nearest_km, 1) if nearest_km is not None else None,
            'reachRadiusKm': round(nearest_km / 2, 1) if nearest_km is not None else None,
        }
    return reach


def build_representativeness(df: pd.DataFrame) -> dict:
    """Per-station biome representation + Southern-Cone biome coverage."""
    biome_counts = df['ecosystem_biome'].fillna('Unknown').value_counts().to_dict()
    reach = build_geographic_reach(df)
    per_station = []
    for _, row in df.iterrows():
        biome = row.get('ecosystem_biome') or 'Unknown'
        n_sharing = int(biome_counts.get(biome, 1))
        per_station.append({
            'siteId': row['site_id'],
            'biome': biome,
            'igbp': row.get('igbp'),
            'stationsSharingBiome': n_sharing,
            'soleRepresentative': n_sharing == 1,
            'lat': float(row['location_lat']),
            'lon': float(row['location_long']),
            **reach.get(row['site_id'], {}),
        })
    return {
        'biomeCoverage': [{'biome': b, 'stationCount': int(c)} for b, c in biome_counts.items()],
        'perStation': per_station,
    }


def build_stats(df: pd.DataFrame) -> dict:
    """Per-station, per-variable distribution statistics and monthly climatology."""
    per_station = []
    for site_id in df['site_id']:
        ts = load_timeseries(site_id)
        if ts is None:
            continue
        variables = {}
        monthly = {}
        for var in TIMESERIES_VARS:
            if var in ts.columns:
                variables[var] = _quantiles(ts[var])
                clim = ts.assign(month=ts['timestamp'].dt.month).groupby('month')[var].mean()
                monthly[var] = [
                    None if pd.isna(clim.get(m)) else round(float(clim.get(m)), 4)
                    for m in range(1, 13)
                ]
        per_station.append({'siteId': site_id, 'variables': variables, 'monthlyClimatology': monthly})
    return {'variables': TIMESERIES_VARS, 'perStation': per_station}


def export_json(df: pd.DataFrame) -> None:
    CLIENT_PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts_dir = CLIENT_PUBLIC_DATA_DIR / 'timeseries'
    ts_dir.mkdir(parents=True, exist_ok=True)

    # stations.json (metadata + quality + representativeness).
    # Built directly from the overview frame.
    stations = []
    for _, row in df.sort_values(['utility_score', 'site_id'], ascending=[False, True]).iterrows():
        stations.append({
            'siteId': _to_native(row['site_id']),
            'siteName': _to_native(row['site_name']),
            'country': _to_native(row['country']),
            'regionalScope': _to_native(row['regional_scope']),
            'ecosystem': _to_native(row['ecosystem_note']),
            'ecosystemBiome': _to_native(row['ecosystem_biome']),
            'igbp': _to_native(row['igbp']),
            'network': _to_native(row['network']),
            'lat': float(row['location_lat']),
            'lon': float(row['location_long']),
            'yearStart': int(row['year_start']),
            'yearEnd': int(row['year_end']),
            'coverageYears': int(row['temporal_coverage_years']),
            'observations': int(row['total_observations']),
            'utilityScore': float(row['utility_score']),
            'qualityClass': _to_native(row['quality_class']),
            'qualityColor': _to_native(row['quality_color']),
            'markerRadius': float(row['marker_radius']),
            'validPct': {
                'NEE': float(row['valid_nee_pct']),
                'GPP': float(row['valid_gpp_pct']),
                'LE': float(row['valid_le_pct']),
                'H': float(row['valid_h_pct']),
                'TA': float(row['valid_ta_pct']),
                'SW_IN': float(row['valid_sw_in_pct']),
            },
            'acceptableQcPct': float(row['acceptable_qc_pct']),
            'variablesAvailableCount': int(row['variables_available_count']),
        })
    stations_payload = {'stations': stations, 'representativeness': build_representativeness(df)}
    (CLIENT_PUBLIC_DATA_DIR / 'stations.json').write_text(
        json.dumps(stations_payload, ensure_ascii=False), encoding='utf-8'
    )

    # stats.json (distribution + variability + monthly climatology)
    (CLIENT_PUBLIC_DATA_DIR / 'stats.json').write_text(
        json.dumps(build_stats(df), ensure_ascii=False), encoding='utf-8'
    )

    # timeseries/<SITE>.json (daily series for the interactive line charts)
    for site_id in df['site_id']:
        ts = load_timeseries(site_id)
        if ts is None:
            continue
        records = []
        for _, r in ts.iterrows():
            rec = {'t': r['timestamp'].strftime('%Y-%m-%d') if pd.notna(r['timestamp']) else None}
            for var in TIMESERIES_VARS:
                if var in ts.columns:
                    val = r[var]
                    rec[var] = None if pd.isna(val) else round(float(val), 4)
            records.append(rec)
        (ts_dir / f'{site_id}.json').write_text(
            json.dumps({'siteId': site_id, 'variables': TIMESERIES_VARS, 'daily': records}, ensure_ascii=False),
            encoding='utf-8',
        )

    print(f'Wrote JSON visualisation data to {CLIENT_PUBLIC_DATA_DIR}')


if __name__ == '__main__':
    main()
