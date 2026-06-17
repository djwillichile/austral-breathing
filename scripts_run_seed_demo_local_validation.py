from __future__ import annotations

import json

import folium
import numpy as np
import pandas as pd
from folium.plugins import Fullscreen

from pipeline_paths import BASE_DIR, RAW_DIR

VALIDATION_DIR = BASE_DIR / "outputs" / "seed_demo_local_validation"
VALIDATION_TABLES_DIR = VALIDATION_DIR / "tables"
VALIDATION_MAPS_DIR = VALIDATION_DIR / "maps"
VALIDATION_PROCESSED_DIR = VALIDATION_DIR / "processed"
VALIDATION_RESEARCH_DIR = VALIDATION_DIR / "research"

for directory in [VALIDATION_DIR, VALIDATION_TABLES_DIR, VALIDATION_MAPS_DIR, VALIDATION_PROCESSED_DIR, VALIDATION_RESEARCH_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

TARGET_SITES = ["CL-SDF", "CL-SDP"]
MISSING_SENTINELS = [-9999, -9999.0, -6999, -6999.0]
CORE_MAPPING = {
    "TIMESTAMP": "timestamp",
    "NEE_VUT_REF": "NEE",
    "NEE_VUT_REF_QC": "NEE_QC",
    "GPP_NT_VUT_REF": "GPP",
    "GPP_DT_VUT_REF": "GPP_DT_VUT_REF",
    "LE_F_MDS": "LE",
    "LE_F_MDS_QC": "LE_QC",
    "H_F_MDS": "H",
    "H_F_MDS_QC": "H_QC",
    "TA_F_MDS": "TA",
    "TA_F_MDS_QC": "TA_QC",
    "SW_IN_F_MDS": "SW_IN",
    "SW_IN_F_MDS_QC": "SW_IN_QC",
}
CORE_VARIABLES = ["NEE", "GPP", "LE", "H", "TA", "SW_IN"]
QC_COLUMNS = ["NEE_QC", "LE_QC", "H_QC", "TA_QC", "SW_IN_QC"]


def parse_timestamp(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    mode_len = int(text.str.len().mode().iloc[0])
    if mode_len == 8:
        return pd.to_datetime(text, format="%Y%m%d", errors="coerce")
    if mode_len == 12:
        return pd.to_datetime(text, format="%Y%m%d%H%M", errors="coerce")
    return pd.to_datetime(text, errors="coerce")


def summarize_bifvarinfo(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {"variables_with_metadata": [], "unit_hints": {}, "notes": "No BIFVARINFO file available."}

    last_error = None
    bif = None
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            bif = pd.read_csv(path, encoding=encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

    if bif is None:
        return {
            "variables_with_metadata": [],
            "unit_hints": {},
            "notes": f"BIFVARINFO could not be parsed due to encoding issues: {last_error}",
        }

    variables = sorted(set(bif["VARIABLE"].dropna().astype(str))) if "VARIABLE" in bif.columns else []
    unit_hints = {}
    candidate_value_cols = [c for c in bif.columns if str(c).upper() in {"DATAVALUE", "VALUE", "VARIABLE_VALUE"}]
    value_col = candidate_value_cols[0] if candidate_value_cols else None
    if "VARIABLE" in bif.columns and value_col is not None:
        mask = bif["VARIABLE"].astype(str).str.contains("UNIT|UNITS", case=False, na=False)
        units_df = bif.loc[mask, ["VARIABLE", value_col]].copy()
        for _, row in units_df.iterrows():
            key = str(row["VARIABLE"])
            unit_hints.setdefault(key, [])
            val = str(row[value_col])
            if val not in unit_hints[key]:
                unit_hints[key].append(val)

    return {
        "variables_with_metadata": variables,
        "unit_hints": unit_hints,
        "notes": "Unit hints extracted from BIFVARINFO where available.",
    }


def classify_quality(score: float) -> str:
    if pd.isna(score):
        return "unknown"
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def summarize_station(site_id: str, df: pd.DataFrame, original_columns: list[str], bifvarinfo_summary: dict) -> dict:
    metrics = {
        "site_id": site_id,
        "year_start": int(df["timestamp"].dt.year.min()) if df["timestamp"].notna().any() else pd.NA,
        "year_end": int(df["timestamp"].dt.year.max()) if df["timestamp"].notna().any() else pd.NA,
        "total_observations": int(len(df)),
        "variables_present": ", ".join([v for v in CORE_VARIABLES if v in df.columns]),
        "variables_available_count": int(sum(v in df.columns for v in CORE_VARIABLES)),
        "original_variable_count": int(len(original_columns)),
        "standardized_variable_count": int(sum(c in df.columns for c in ["timestamp"] + CORE_VARIABLES + QC_COLUMNS)),
        "additional_variables_detected": ", ".join(sorted([c for c in original_columns if c not in CORE_MAPPING])),
        "unit_notes": json.dumps(bifvarinfo_summary.get("unit_hints", {}), ensure_ascii=False),
    }

    completeness_values = []
    qc_values = []

    for var in CORE_VARIABLES:
        pct = float(df[var].notna().mean() * 100) if var in df.columns else np.nan
        metrics[f"valid_{var.lower()}_pct"] = round(pct, 2) if not np.isnan(pct) else pd.NA
        if not np.isnan(pct):
            completeness_values.append(pct / 100.0)

    qc_map = {
        "NEE_QC": "acceptable_nee_qc_pct",
        "LE_QC": "acceptable_le_qc_pct",
        "H_QC": "acceptable_h_qc_pct",
        "TA_QC": "acceptable_ta_qc_pct",
        "SW_IN_QC": "acceptable_sw_in_qc_pct",
    }
    for qc_col, metric_name in qc_map.items():
        if qc_col in df.columns:
            pct = float(df[qc_col].ge(0.5).mean() * 100)
            metrics[metric_name] = round(pct, 2)
            qc_values.append(pct / 100.0)
        else:
            metrics[metric_name] = pd.NA

    acceptable_qc_pct = round(float(np.mean(qc_values) * 100), 2) if qc_values else pd.NA
    metrics["acceptable_qc_pct"] = acceptable_qc_pct

    temporal_score = 0.0
    if pd.notna(metrics["year_start"]) and pd.notna(metrics["year_end"]):
        temporal_score = min((int(metrics["year_end"]) - int(metrics["year_start"]) + 1) / 10.0, 1.0)

    completeness_score = float(np.mean(completeness_values)) if completeness_values else np.nan
    qc_score = float(np.mean(qc_values)) if qc_values else np.nan
    variable_score = metrics["variables_available_count"] / len(CORE_VARIABLES)

    components = [temporal_score, completeness_score, variable_score]
    if not np.isnan(qc_score):
        components.append(qc_score)
    utility_score = float(np.nanmean(components)) if components else np.nan

    metrics["temporal_coverage_years"] = (
        int(metrics["year_end"] - metrics["year_start"] + 1)
        if pd.notna(metrics["year_start"]) and pd.notna(metrics["year_end"])
        else pd.NA
    )
    metrics["utility_score"] = round(utility_score, 3) if not np.isnan(utility_score) else pd.NA
    metrics["quality_class"] = classify_quality(utility_score)
    metrics["notes"] = (
        "Daily FLUXMET standardized from FLUXNET product. Missing sentinels converted to NaN. "
        "QC acceptable threshold set to >= 0.5 for available QC variables."
    )
    return metrics


def read_station_inputs(site_id: str) -> tuple[pd.DataFrame, dict, dict]:
    station_dir = RAW_DIR / site_id
    flux_file = next(station_dir.glob("*_FLUXMET_DD_*.csv"))
    bifvarinfo_files = list(station_dir.glob("*_BIFVARINFO_DD_*.csv"))
    bifvarinfo_path = bifvarinfo_files[0] if bifvarinfo_files else None

    df = pd.read_csv(flux_file)
    original_columns = list(df.columns)
    selected = [col for col in CORE_MAPPING if col in df.columns]
    out = df[selected].copy().rename(columns={col: CORE_MAPPING[col] for col in selected})

    for col in out.columns:
        if col != "timestamp":
            out[col] = pd.to_numeric(out[col], errors="coerce")
            out[col] = out[col].replace(MISSING_SENTINELS, np.nan)

    gpp_note = "Primary standardized GPP column uses the available GPP reference variable."
    if "GPP" in out.columns and "GPP_DT_VUT_REF" in out.columns:
        out["GPP"] = out["GPP"].where(out["GPP"].notna(), out["GPP_DT_VUT_REF"])
        if out["GPP"].notna().any() and out["GPP_DT_VUT_REF"].notna().any():
            gpp_note = "Standardized GPP prioritizes GPP_NT_VUT_REF and fills missing values with GPP_DT_VUT_REF when needed."
        else:
            gpp_note = "Standardized GPP uses GPP_DT_VUT_REF because GPP_NT_VUT_REF is unavailable for this station/time scale."

    out["timestamp"] = parse_timestamp(out["timestamp"])
    out["site_id"] = site_id
    out = out[["site_id", "timestamp"] + [c for c in out.columns if c not in {"site_id", "timestamp"}]]
    out["GPP_method_note"] = gpp_note

    bifvarinfo_summary = summarize_bifvarinfo(bifvarinfo_path)
    station_summary = summarize_station(site_id, out, original_columns, bifvarinfo_summary)
    return out, station_summary, bifvarinfo_summary


def quality_color(quality_class: str) -> str:
    palette = {"high": "#2F6B3B", "medium": "#C78C1B", "low": "#A43A2A"}
    return palette.get(str(quality_class).lower(), "#5E6A71")


def marker_radius(total_observations: float, min_obs: float, max_obs: float) -> float:
    if pd.isna(total_observations):
        return 6.0
    if max_obs == min_obs:
        return 8.0
    scaled = 6 + 10 * ((float(total_observations) - min_obs) / (max_obs - min_obs))
    return round(max(6.0, min(16.0, scaled)), 2)


def build_popup(row: pd.Series) -> str:
    return f"""
    <div style='width: 320px; font-family: Georgia, serif; color: #1f2937;'>
      <h4 style='margin: 0 0 8px 0; font-size: 16px; color: #16322f;'>{row['site_id']} — {row['site_name']}</h4>
      <table style='width:100%; border-collapse: collapse; font-size: 12px;'>
        <tr><td style='padding: 3px 6px;'><b>Country</b></td><td style='padding: 3px 6px;'>{row['country']}</td></tr>
        <tr><td style='padding: 3px 6px;'><b>Ecosystem</b></td><td style='padding: 3px 6px;'>{row['ecosystem_biome']}</td></tr>
        <tr><td style='padding: 3px 6px;'><b>Years</b></td><td style='padding: 3px 6px;'>{int(row['year_start'])}–{int(row['year_end'])}</td></tr>
        <tr><td style='padding: 3px 6px;'><b>Observations</b></td><td style='padding: 3px 6px;'>{int(row['total_observations'])}</td></tr>
        <tr><td style='padding: 3px 6px;'><b>Variables</b></td><td style='padding: 3px 6px;'>{row['variables_present']}</td></tr>
        <tr><td style='padding: 3px 6px;'><b>Utility score</b></td><td style='padding: 3px 6px;'>{row['utility_score']}</td></tr>
        <tr><td style='padding: 3px 6px;'><b>Quality class</b></td><td style='padding: 3px 6px; text-transform: capitalize;'>{row['quality_class']}</td></tr>
      </table>
    </div>
    """


def add_legend(fmap: folium.Map) -> None:
    legend_html = """
    <div style="
        position: fixed;
        bottom: 24px;
        left: 24px;
        z-index: 9999;
        background: rgba(249, 247, 241, 0.95);
        border: 1px solid rgba(22, 50, 47, 0.18);
        box-shadow: 0 12px 24px rgba(0,0,0,0.12);
        border-radius: 12px;
        padding: 14px 16px;
        min-width: 220px;
        font-family: Georgia, serif;
        color: #16322f;">
      <div style="font-size: 14px; font-weight: bold; margin-bottom: 8px;">Station quality</div>
      <div style="font-size: 12px; margin-bottom: 6px;"><span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#2F6B3B; margin-right:8px;"></span>High</div>
      <div style="font-size: 12px; margin-bottom: 6px;"><span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#C78C1B; margin-right:8px;"></span>Medium</div>
      <div style="font-size: 12px; margin-bottom: 10px;"><span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#A43A2A; margin-right:8px;"></span>Low</div>
      <div style="font-size: 12px; line-height: 1.4;">Marker size is proportional to the number of observations in the standardized daily dataset.</div>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(legend_html))


metadata = pd.read_csv(BASE_DIR / "stations_metadata.csv")
seed_metadata = metadata[metadata["site_id"].isin(TARGET_SITES)].copy().sort_values("site_id").reset_index(drop=True)
seed_metadata.to_csv(VALIDATION_TABLES_DIR / "stations_metadata_seed_demo.csv", index=False)

station_frames = {}
station_summaries = []
bifvarinfo_summaries = {}
for site_id in TARGET_SITES:
    standardized_df, summary, bif_summary = read_station_inputs(site_id)
    station_frames[site_id] = standardized_df
    station_summaries.append(summary)
    bifvarinfo_summaries[site_id] = bif_summary
    site_dir = VALIDATION_PROCESSED_DIR / site_id
    site_dir.mkdir(parents=True, exist_ok=True)
    standardized_df.to_csv(site_dir / f"{site_id}_daily_standardized.csv", index=False)

quality_df = pd.DataFrame(station_summaries)
quality_df = quality_df.merge(seed_metadata[["site_id", "site_name", "country"]], on="site_id", how="left")
quality_df = quality_df[[
    "site_id", "site_name", "country", "year_start", "year_end", "temporal_coverage_years",
    "total_observations", "valid_nee_pct", "valid_gpp_pct", "valid_le_pct", "valid_h_pct",
    "valid_ta_pct", "valid_sw_in_pct", "acceptable_qc_pct", "acceptable_nee_qc_pct",
    "acceptable_le_qc_pct", "acceptable_h_qc_pct", "acceptable_ta_qc_pct",
    "acceptable_sw_in_qc_pct", "variables_available_count", "utility_score", "quality_class",
    "original_variable_count", "standardized_variable_count", "variables_present",
    "additional_variables_detected", "unit_notes", "notes",
]].sort_values("site_id").reset_index(drop=True)
quality_df.to_csv(VALIDATION_TABLES_DIR / "stations_quality_seed_demo.csv", index=False)

variables_df = pd.DataFrame([
    {
        "site_id": row["site_id"],
        "site_name": seed_metadata.loc[seed_metadata["site_id"] == row["site_id"], "site_name"].iloc[0],
        "variables_present": row["variables_present"],
        "standardized_core_variables_present": row["variables_present"],
        "source_file": f"data/raw/{row['site_id']}",
        "notes": "Standardized from daily FLUXMET product. Additional variables preserved in original raw files.",
    }
    for row in station_summaries
]).sort_values("site_id").reset_index(drop=True)
variables_df.to_csv(VALIDATION_TABLES_DIR / "variables_by_station_seed_demo.csv", index=False)

merged = seed_metadata.merge(quality_df, on=["site_id", "site_name", "country"], how="left")
merged = merged.merge(variables_df[["site_id", "variables_present"]], on="site_id", how="left", suffixes=("", "_variables"))
if "variables_present_variables" in merged.columns:
    merged["variables_present"] = merged["variables_present"].fillna(merged["variables_present_variables"])
    merged = merged.drop(columns=["variables_present_variables"])

merged["quality_color"] = merged["quality_class"].map(quality_color)
min_obs = float(merged["total_observations"].min())
max_obs = float(merged["total_observations"].max())
merged["marker_radius"] = merged["total_observations"].apply(lambda x: marker_radius(x, min_obs, max_obs))
merged = merged.sort_values("site_id").reset_index(drop=True)
merged.to_csv(VALIDATION_TABLES_DIR / "station_overview_seed_demo.csv", index=False)

center_lat = merged["location_lat"].mean()
center_lon = merged["location_long"].mean()
fmap = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="CartoDB positron", control_scale=True)
Fullscreen(position="topright").add_to(fmap)

for _, row in merged.iterrows():
    folium.CircleMarker(
        location=[row["location_lat"], row["location_long"]],
        radius=row["marker_radius"],
        color=row["quality_color"],
        weight=1.5,
        fill=True,
        fill_color=row["quality_color"],
        fill_opacity=0.82,
        popup=folium.Popup(build_popup(row), max_width=360),
        tooltip=f"{row['site_id']} | {row['site_name']}",
    ).add_to(fmap)

add_legend(fmap)
map_path = VALIDATION_MAPS_DIR / "stations_map_seed_demo.html"
fmap.save(str(map_path))

summary_payload = {
    "sites_validated": TARGET_SITES,
    "n_sites": int(len(merged)),
    "total_observations_by_site": {row["site_id"]: int(row["total_observations"]) for _, row in merged.iterrows()},
    "utility_score_by_site": {row["site_id"]: float(row["utility_score"]) for _, row in merged.iterrows()},
    "quality_class_by_site": {row["site_id"]: row["quality_class"] for _, row in merged.iterrows()},
    "files": {
        "stations_metadata": str((VALIDATION_TABLES_DIR / "stations_metadata_seed_demo.csv").resolve()),
        "variables_by_station": str((VALIDATION_TABLES_DIR / "variables_by_station_seed_demo.csv").resolve()),
        "stations_quality": str((VALIDATION_TABLES_DIR / "stations_quality_seed_demo.csv").resolve()),
        "station_overview": str((VALIDATION_TABLES_DIR / "station_overview_seed_demo.csv").resolve()),
        "map": str(map_path.resolve()),
    },
}

with open(VALIDATION_RESEARCH_DIR / "seed_demo_validation_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary_payload, f, indent=2, ensure_ascii=False)
with open(VALIDATION_RESEARCH_DIR / "bifvarinfo_unit_hints_seed_demo.json", "w", encoding="utf-8") as f:
    json.dump(bifvarinfo_summaries, f, indent=2, ensure_ascii=False)

assert len(merged) == 2, "La validación local debe contener exactamente CL-SDF y CL-SDP."
assert set(merged["site_id"]) == set(TARGET_SITES), "La validación local no contiene ambas estaciones semilla."
assert merged["utility_score"].notna().all(), "Cada estación debe tener utility_score calculado."
assert map_path.exists(), "No se generó el mapa HTML de validación local."

print(json.dumps(summary_payload, indent=2, ensure_ascii=False))
