from __future__ import annotations

import pandas as pd

from pipeline_paths import (
    BASE_DIR,
    METADATA_DIR,
    OUTPUTS_TABLES_DIR,
    latest_snapshot,
)
from scripts_discover_southern_cone_stations import is_southern_cone

ACCESS_METHOD = 'fluxnet-shuttle + AmeriFlux/FLUXNET product link'

PREFIX_TO_COUNTRY = {
    'CL': 'Chile',
    'AR': 'Argentina',
    'UY': 'Uruguay',
    'PY': 'Paraguay',
    'BR': 'Brazil',
}

# Hand-written editorial notes for the originally curated six stations.
# These take precedence over the IGBP-derived defaults for those sites; every
# other (newly discovered) station gets an auto-generated entry.
CURATED_NOTES = {
    'CL-SDF': {
        'region_scope': 'Chiloé Island, Northern Patagonia / temperate rainforest region',
        'ecosystem_note': 'Old-growth North Patagonian rainforest',
    },
    'CL-SDP': {
        'region_scope': 'Chiloé Island, Northern Patagonia / peatland region',
        'ecosystem_note': 'Peatland / wetland',
    },
    'CL-ACF': {
        'region_scope': 'Alerce Costero, southern Chile',
        'ecosystem_note': 'Temperate forest',
    },
    'AR-TF1': {
        'region_scope': 'Tierra del Fuego / Southern Patagonia',
        'ecosystem_note': 'Bog / wetland',
    },
    'AR-TF2': {
        'region_scope': 'Tierra del Fuego / Southern Patagonia',
        'ecosystem_note': 'Bog / wetland',
    },
    'AR-CCg': {
        'region_scope': 'Argentina, included as regional comparator outside core Patagonia',
        'ecosystem_note': 'Grassland',
    },
}

IGBP_TO_BIOME = {
    'EBF': 'Evergreen Broadleaf Forest',
    'ENF': 'Evergreen Needleleaf Forest',
    'DBF': 'Deciduous Broadleaf Forest',
    'MF': 'Mixed Forest',
    'WET': 'Wetland',
    'GRA': 'Grassland',
    'SAV': 'Savanna',
    'WSA': 'Woody Savanna',
    'OSH': 'Open Shrubland',
    'CSH': 'Closed Shrubland',
    'CRO': 'Cropland',
}


def load_snapshot() -> pd.DataFrame:
    return pd.read_csv(latest_snapshot())


def build_target_sites(df: pd.DataFrame) -> dict[str, dict]:
    """Generate the target-site mapping from the catalog (no hardcoding).

    Country is derived from the site_id prefix; region_scope / ecosystem_note
    default from the IGBP biome and are overridden by ``CURATED_NOTES`` for the
    original six stations so their editorial text is preserved verbatim.
    """
    targets: dict[str, dict] = {}
    for _, row in df.iterrows():
        site_id = row['site_id']
        if not is_southern_cone(site_id, row.get('location_lat')):
            continue
        prefix = str(site_id).split('-', 1)[0].upper()
        country = PREFIX_TO_COUNTRY.get(prefix, 'Unknown')
        biome = IGBP_TO_BIOME.get(str(row.get('igbp', '')).strip(), str(row.get('igbp', '')))
        curated = CURATED_NOTES.get(site_id, {})
        targets[site_id] = {
            'country': country,
            'region_scope': curated.get('region_scope', f'{country} — Southern Cone ({biome})'),
            'ecosystem_note': curated.get('ecosystem_note', biome or 'Unspecified ecosystem'),
            'access_type': 'open',
            'access_method': ACCESS_METHOD,
        }
    return targets



def build_station_metadata(df: pd.DataFrame) -> pd.DataFrame:
    target_sites = build_target_sites(df)
    df = df[df['site_id'].isin(target_sites.keys())].copy()
    df['country'] = df['site_id'].map(lambda s: target_sites[s]['country'])
    df['regional_scope'] = df['site_id'].map(lambda s: target_sites[s]['region_scope'])
    df['ecosystem_biome'] = df['igbp'].map(IGBP_TO_BIOME).fillna(df['igbp'])
    df['ecosystem_note'] = df['site_id'].map(lambda s: target_sites[s]['ecosystem_note'])
    df['temporal_period_available'] = df['first_year'].astype('Int64').astype(str) + '-' + df['last_year'].astype('Int64').astype(str)
    df['download_availability'] = df['download_link'].notna().map({True: 'available', False: 'unknown'})
    df['access_type'] = df['site_id'].map(lambda s: target_sites[s]['access_type'])
    df['access_method'] = df['site_id'].map(lambda s: target_sites[s]['access_method'])
    df['official_validation_source'] = df['product_citation'].fillna('AmeriFlux / FLUXNET metadata via fluxnet-shuttle')

    cols = [
        'site_id', 'site_name', 'country', 'regional_scope', 'location_lat', 'location_long',
        'igbp', 'ecosystem_biome', 'ecosystem_note', 'network', 'first_year', 'last_year',
        'temporal_period_available', 'download_availability', 'access_type', 'access_method',
        'download_link', 'fluxnet_product_name', 'product_id', 'oneflux_code_version',
        'official_validation_source'
    ]
    return df[cols].sort_values(['country', 'site_id']).reset_index(drop=True)



def build_download_log(stations: pd.DataFrame) -> pd.DataFrame:
    log = stations[[
        'site_id', 'site_name', 'network', 'download_link', 'access_type', 'access_method'
    ]].copy()
    log['download_status'] = 'pending'
    log['failure_reason'] = ''
    log['notes'] = 'Initial log created from fluxnet-shuttle snapshot.'
    return log[[
        'site_id', 'site_name', 'network', 'access_type', 'access_method',
        'download_status', 'failure_reason', 'download_link', 'notes'
    ]]



def build_variables_placeholder(stations: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for site_id, site_name in stations[['site_id', 'site_name']].itertuples(index=False):
        rows.append({
            'site_id': site_id,
            'site_name': site_name,
            'variables_present': '',
            'standardized_core_variables_present': '',
            'source_file': '',
            'notes': 'To be populated after file download and variable harmonization.'
        })
    return pd.DataFrame(rows)



def build_quality_placeholder(stations: pd.DataFrame) -> pd.DataFrame:
    quality = stations[[
        'site_id', 'site_name', 'country', 'first_year', 'last_year'
    ]].copy()
    quality['total_observations'] = pd.NA
    quality['temporal_coverage_years'] = (quality['last_year'] - quality['first_year'] + 1).astype('Int64')
    quality['valid_nee_pct'] = pd.NA
    quality['valid_gpp_pct'] = pd.NA
    quality['valid_le_pct'] = pd.NA
    quality['valid_h_pct'] = pd.NA
    quality['valid_ta_pct'] = pd.NA
    quality['valid_sw_in_pct'] = pd.NA
    quality['acceptable_qc_pct'] = pd.NA
    quality['variables_available_count'] = pd.NA
    quality['utility_score'] = pd.NA
    quality['quality_class'] = 'pending'
    quality['notes'] = 'Template created before data download and harmonization.'
    return quality



def main() -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_TABLES_DIR.mkdir(parents=True, exist_ok=True)

    snapshot = load_snapshot()
    stations = build_station_metadata(snapshot)
    download_log = build_download_log(stations)
    variables = build_variables_placeholder(stations)
    quality = build_quality_placeholder(stations)

    stations.to_csv(BASE_DIR / 'stations_metadata.csv', index=False)
    download_log.to_csv(BASE_DIR / 'download_log.csv', index=False)
    variables.to_csv(BASE_DIR / 'variables_by_station.csv', index=False)
    quality.to_csv(BASE_DIR / 'stations_quality.csv', index=False)

    stations.to_csv(METADATA_DIR / 'stations_metadata.csv', index=False)
    download_log.to_csv(METADATA_DIR / 'download_log.csv', index=False)
    variables.to_csv(METADATA_DIR / 'variables_by_station.csv', index=False)
    quality.to_csv(METADATA_DIR / 'stations_quality.csv', index=False)

    stations.to_csv(OUTPUTS_TABLES_DIR / 'stations_metadata.csv', index=False)
    download_log.to_csv(OUTPUTS_TABLES_DIR / 'download_log.csv', index=False)
    variables.to_csv(OUTPUTS_TABLES_DIR / 'variables_by_station.csv', index=False)
    quality.to_csv(OUTPUTS_TABLES_DIR / 'stations_quality.csv', index=False)

    summary = pd.DataFrame([
        {'metric': 'n_stations', 'value': len(stations)},
        {'metric': 'n_chile', 'value': int((stations['country'] == 'Chile').sum())},
        {'metric': 'n_argentina', 'value': int((stations['country'] == 'Argentina').sum())},
        {'metric': 'source', 'value': 'AmeriFlux/FLUXNET metadata via fluxnet-shuttle'},
    ])
    summary.to_csv(OUTPUTS_TABLES_DIR / 'metadata_summary.csv', index=False)


if __name__ == '__main__':
    main()
