from __future__ import annotations

from pathlib import Path
import json
import re
import pandas as pd
import numpy as np

from pipeline_paths import (
    BASE_DIR,
    RAW_DIR,
    PROCESSED_DIR,
    METADATA_DIR,
    OUTPUTS_TABLES_DIR,
    RESEARCH_DIR,
)

CORE_MAPPING = {
    'TIMESTAMP': 'timestamp',
    'NEE_VUT_REF': 'NEE',
    'NEE_VUT_REF_QC': 'NEE_QC',
    'GPP_NT_VUT_REF': 'GPP',
    'GPP_DT_VUT_REF': 'GPP_DT_VUT_REF',
    'LE_F_MDS': 'LE',
    'LE_F_MDS_QC': 'LE_QC',
    'H_F_MDS': 'H',
    'H_F_MDS_QC': 'H_QC',
    'TA_F_MDS': 'TA',
    'TA_F_MDS_QC': 'TA_QC',
    'SW_IN_F_MDS': 'SW_IN',
    'SW_IN_F_MDS_QC': 'SW_IN_QC',
}

CORE_VARIABLES = ['NEE', 'GPP', 'LE', 'H', 'TA', 'SW_IN']
QC_COLUMNS = ['NEE_QC', 'LE_QC', 'H_QC', 'TA_QC', 'SW_IN_QC']
MISSING_SENTINELS = [-9999, -9999.0, -6999, -6999.0]


def parse_timestamp(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    if text.str.len().mode().iloc[0] == 8:
        return pd.to_datetime(text, format='%Y%m%d', errors='coerce')
    if text.str.len().mode().iloc[0] == 12:
        return pd.to_datetime(text, format='%Y%m%d%H%M', errors='coerce')
    return pd.to_datetime(text, errors='coerce')



def discover_station_files() -> dict[str, dict[str, Path]]:
    stations: dict[str, dict[str, Path]] = {}
    for station_dir in sorted(RAW_DIR.iterdir()):
        if not station_dir.is_dir():
            continue
        flux_files = list(station_dir.glob('*_FLUXMET_DD_*.csv'))
        bif_files = list(station_dir.glob('*_BIF_*.csv'))
        bifvarinfo_files = list(station_dir.glob('*_BIFVARINFO_DD_*.csv'))
        if not flux_files:
            continue
        stations[station_dir.name] = {
            'fluxmet_dd': flux_files[0],
            'bif': bif_files[0] if bif_files else None,
            'bifvarinfo': bifvarinfo_files[0] if bifvarinfo_files else None,
        }
    return stations



def read_and_standardize_station(site_id: str, file_info: dict[str, Path]) -> tuple[pd.DataFrame, dict, dict]:
    df = pd.read_csv(file_info['fluxmet_dd'])
    original_columns = list(df.columns)

    selected = [col for col in CORE_MAPPING if col in df.columns]
    out = df[selected].copy()
    out = out.rename(columns={col: CORE_MAPPING[col] for col in selected})

    for col in out.columns:
        if col != 'timestamp':
            out[col] = pd.to_numeric(out[col], errors='coerce')
            out[col] = out[col].replace(MISSING_SENTINELS, np.nan)

    gpp_note = 'Primary standardized GPP column uses the available GPP reference variable.'
    if 'GPP' in out.columns and 'GPP_DT_VUT_REF' in out.columns:
        out['GPP'] = out['GPP'].where(out['GPP'].notna(), out['GPP_DT_VUT_REF'])
        if out['GPP'].notna().any() and out['GPP_DT_VUT_REF'].notna().any():
            gpp_note = 'Standardized GPP prioritizes GPP_NT_VUT_REF and fills missing values with GPP_DT_VUT_REF when needed.'
        else:
            gpp_note = 'Standardized GPP uses GPP_DT_VUT_REF because GPP_NT_VUT_REF is unavailable for this station/time scale.'

    out['timestamp'] = parse_timestamp(out['timestamp'])
    out['site_id'] = site_id
    out = out[['site_id', 'timestamp'] + [c for c in out.columns if c not in {'site_id', 'timestamp'}]]
    out['GPP_method_note'] = gpp_note

    bifvarinfo_summary = summarize_bifvarinfo(file_info.get('bifvarinfo'))
    station_summary = summarize_station(site_id, out, original_columns, bifvarinfo_summary)
    return out, station_summary, bifvarinfo_summary



def summarize_bifvarinfo(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {'variables_with_metadata': [], 'unit_hints': {}, 'notes': 'No BIFVARINFO file available.'}

    last_error = None
    bif = None
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            bif = pd.read_csv(path, encoding=encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if bif is None:
        return {
            'variables_with_metadata': [],
            'unit_hints': {},
            'notes': f'BIFVARINFO could not be parsed due to encoding issues: {last_error}'
        }

    variables = sorted(set(bif['VARIABLE'].dropna().astype(str))) if 'VARIABLE' in bif.columns else []
    unit_hints: dict[str, list[str]] = {}
    candidate_value_cols = [c for c in bif.columns if str(c).upper() in {'DATAVALUE', 'VALUE', 'VARIABLE_VALUE'}]
    value_col = candidate_value_cols[0] if candidate_value_cols else None
    if 'VARIABLE' in bif.columns and value_col is not None:
        mask = bif['VARIABLE'].astype(str).str.contains('UNIT|UNITS', case=False, na=False)
        units_df = bif.loc[mask, ['VARIABLE', value_col]].copy()
        for _, row in units_df.iterrows():
            key = str(row['VARIABLE'])
            unit_hints.setdefault(key, [])
            val = str(row[value_col])
            if val not in unit_hints[key]:
                unit_hints[key].append(val)

    return {
        'variables_with_metadata': variables,
        'unit_hints': unit_hints,
        'notes': 'Unit hints extracted from BIFVARINFO where available; detailed semantic parsing may still require manual review.'
    }



def classify_quality(score: float) -> str:
    if pd.isna(score):
        return 'unknown'
    if score >= 0.75:
        return 'high'
    if score >= 0.5:
        return 'medium'
    return 'low'



def summarize_station(site_id: str, df: pd.DataFrame, original_columns: list[str], bifvarinfo_summary: dict) -> dict:
    metrics: dict[str, object] = {
        'site_id': site_id,
        'year_start': int(df['timestamp'].dt.year.min()) if df['timestamp'].notna().any() else pd.NA,
        'year_end': int(df['timestamp'].dt.year.max()) if df['timestamp'].notna().any() else pd.NA,
        'total_observations': int(len(df)),
        'variables_present': ', '.join([v for v in CORE_VARIABLES if v in df.columns]),
        'variables_available_count': int(sum(v in df.columns for v in CORE_VARIABLES)),
        'original_variable_count': int(len(original_columns)),
        'standardized_variable_count': int(sum(c in df.columns for c in ['timestamp'] + CORE_VARIABLES + QC_COLUMNS)),
        'additional_variables_detected': ', '.join(sorted([c for c in original_columns if c not in CORE_MAPPING])),
        'unit_notes': json.dumps(bifvarinfo_summary.get('unit_hints', {}), ensure_ascii=False),
    }

    completeness_values = []
    qc_values = []

    for var in CORE_VARIABLES:
        pct = float(df[var].notna().mean() * 100) if var in df.columns else np.nan
        metrics[f'valid_{var.lower()}_pct'] = round(pct, 2) if not np.isnan(pct) else pd.NA
        if not np.isnan(pct):
            completeness_values.append(pct / 100.0)

    qc_map = {
        'NEE_QC': 'acceptable_nee_qc_pct',
        'LE_QC': 'acceptable_le_qc_pct',
        'H_QC': 'acceptable_h_qc_pct',
        'TA_QC': 'acceptable_ta_qc_pct',
        'SW_IN_QC': 'acceptable_sw_in_qc_pct',
    }
    for qc_col, metric_name in qc_map.items():
        if qc_col in df.columns:
            pct = float(df[qc_col].ge(0.5).mean() * 100)
            metrics[metric_name] = round(pct, 2)
            qc_values.append(pct / 100.0)
        else:
            metrics[metric_name] = pd.NA

    if qc_values:
        acceptable_qc_pct = round(float(np.mean(qc_values) * 100), 2)
    else:
        acceptable_qc_pct = pd.NA
    metrics['acceptable_qc_pct'] = acceptable_qc_pct

    temporal_score = 0.0
    if pd.notna(metrics['year_start']) and pd.notna(metrics['year_end']):
        temporal_score = min((int(metrics['year_end']) - int(metrics['year_start']) + 1) / 10.0, 1.0)

    completeness_score = float(np.mean(completeness_values)) if completeness_values else np.nan
    qc_score = float(np.mean(qc_values)) if qc_values else np.nan
    variable_score = metrics['variables_available_count'] / len(CORE_VARIABLES)

    components = [temporal_score, completeness_score, variable_score]
    if not np.isnan(qc_score):
        components.append(qc_score)
    utility_score = float(np.nanmean(components)) if components else np.nan

    metrics['temporal_coverage_years'] = int(metrics['year_end'] - metrics['year_start'] + 1) if pd.notna(metrics['year_start']) and pd.notna(metrics['year_end']) else pd.NA
    metrics['utility_score'] = round(utility_score, 3) if not np.isnan(utility_score) else pd.NA
    metrics['quality_class'] = classify_quality(utility_score)
    metrics['notes'] = 'Daily FLUXMET standardized from FLUXNET product. Missing sentinels converted to NaN. QC acceptable threshold set to >= 0.5 for available QC variables.'
    return metrics



def update_variables_table(station_summaries: list[dict]) -> pd.DataFrame:
    rows = []
    for s in station_summaries:
        rows.append({
            'site_id': s['site_id'],
            'site_name': pd.NA,
            'variables_present': s['variables_present'],
            'standardized_core_variables_present': s['variables_present'],
            'source_file': f"data/raw/{s['site_id']}",
            'notes': 'Standardized from daily FLUXMET product. Additional variables preserved in original raw files.'
        })
    out = pd.DataFrame(rows)
    meta = pd.read_csv(BASE_DIR / 'stations_metadata.csv')[['site_id', 'site_name']]
    out = out.drop(columns=['site_name']).merge(meta, on='site_id', how='left')
    return out[['site_id', 'site_name', 'variables_present', 'standardized_core_variables_present', 'source_file', 'notes']].sort_values('site_id')



def update_quality_table(station_summaries: list[dict]) -> pd.DataFrame:
    quality = pd.DataFrame(station_summaries)
    meta = pd.read_csv(BASE_DIR / 'stations_metadata.csv')[['site_id', 'site_name', 'country']]
    quality = quality.merge(meta, on='site_id', how='left')
    ordered_cols = [
        'site_id', 'site_name', 'country', 'year_start', 'year_end', 'temporal_coverage_years',
        'total_observations', 'valid_nee_pct', 'valid_gpp_pct', 'valid_le_pct', 'valid_h_pct',
        'valid_ta_pct', 'valid_sw_in_pct', 'acceptable_qc_pct', 'acceptable_nee_qc_pct',
        'acceptable_le_qc_pct', 'acceptable_h_qc_pct', 'acceptable_ta_qc_pct',
        'acceptable_sw_in_qc_pct', 'variables_available_count', 'utility_score', 'quality_class',
        'original_variable_count', 'standardized_variable_count', 'variables_present',
        'additional_variables_detected', 'unit_notes', 'notes'
    ]
    return quality[ordered_cols].sort_values('site_id')



def save_outputs(station_frames: dict[str, pd.DataFrame], station_summaries: list[dict], bifvarinfo_summaries: dict[str, dict]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    for site_id, df in station_frames.items():
        site_dir = PROCESSED_DIR / site_id
        site_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(site_dir / f'{site_id}_daily_standardized.csv', index=False)

    variables_df = update_variables_table(station_summaries)
    quality_df = update_quality_table(station_summaries)

    variables_df.to_csv(BASE_DIR / 'variables_by_station.csv', index=False)
    quality_df.to_csv(BASE_DIR / 'stations_quality.csv', index=False)
    variables_df.to_csv(METADATA_DIR / 'variables_by_station.csv', index=False)
    quality_df.to_csv(METADATA_DIR / 'stations_quality.csv', index=False)
    variables_df.to_csv(OUTPUTS_TABLES_DIR / 'variables_by_station.csv', index=False)
    quality_df.to_csv(OUTPUTS_TABLES_DIR / 'stations_quality.csv', index=False)

    with open(RESEARCH_DIR / 'bifvarinfo_unit_hints.json', 'w', encoding='utf-8') as f:
        json.dump(bifvarinfo_summaries, f, indent=2, ensure_ascii=False)



def main() -> None:
    station_files = discover_station_files()
    station_frames: dict[str, pd.DataFrame] = {}
    station_summaries: list[dict] = []
    bifvarinfo_summaries: dict[str, dict] = {}

    for site_id, info in station_files.items():
        standardized_df, summary, bifvarinfo_summary = read_and_standardize_station(site_id, info)
        station_frames[site_id] = standardized_df
        station_summaries.append(summary)
        bifvarinfo_summaries[site_id] = bifvarinfo_summary

    save_outputs(station_frames, station_summaries, bifvarinfo_summaries)


if __name__ == '__main__':
    main()
