from __future__ import annotations

import math
import pandas as pd
import folium
from folium.plugins import Fullscreen

from pipeline_paths import BASE_DIR, OUTPUTS_MAPS_DIR, OUTPUTS_TABLES_DIR


def quality_color(quality_class: str) -> str:
    palette = {
        'high': '#2F6B3B',
        'medium': '#C78C1B',
        'low': '#A43A2A',
    }
    return palette.get(str(quality_class).lower(), '#5E6A71')



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



def main() -> None:
    OUTPUTS_MAPS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_TABLES_DIR.mkdir(parents=True, exist_ok=True)

    metadata = pd.read_csv(BASE_DIR / 'stations_metadata.csv')
    quality = pd.read_csv(BASE_DIR / 'stations_quality.csv')
    variables = pd.read_csv(BASE_DIR / 'variables_by_station.csv')

    merged = metadata.merge(quality, on=['site_id', 'site_name', 'country'], how='left')
    merged = merged.merge(variables[['site_id', 'variables_present']], on='site_id', how='left', suffixes=('', '_variables'))
    if 'variables_present_variables' in merged.columns:
        merged['variables_present'] = merged['variables_present'].fillna(merged['variables_present_variables'])
        merged = merged.drop(columns=['variables_present_variables'])

    merged['quality_color'] = merged['quality_class'].map(quality_color)
    min_obs = float(merged['total_observations'].min())
    max_obs = float(merged['total_observations'].max())
    merged['marker_radius'] = merged['total_observations'].apply(lambda x: marker_radius(x, min_obs, max_obs))

    merged = merged.sort_values(['country', 'site_id']).reset_index(drop=True)
    merged.to_csv(OUTPUTS_TABLES_DIR / 'station_overview.csv', index=False)

    center_lat = merged['location_lat'].mean()
    center_lon = merged['location_long'].mean()
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles='CartoDB positron',
        control_scale=True,
    )

    title_html = """
    <div style="position: fixed; top: 18px; left: 50%; transform: translateX(-50%); z-index: 9999; background: rgba(22,50,47,0.88); color: #f7f3ea; padding: 12px 18px; border-radius: 14px; box-shadow: 0 12px 28px rgba(0,0,0,0.18); font-family: Georgia, serif;">
      <div style="font-size: 16px; font-weight: bold;">Eddy covariance stations in Chile and nearby Patagonia</div>
      <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">Validated and processed from AmeriFlux/FLUXNET products with a reproducible Python pipeline</div>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(title_html))
    Fullscreen(position='topright').add_to(fmap)

    for _, row in merged.iterrows():
        folium.CircleMarker(
            location=[row['location_lat'], row['location_long']],
            radius=row['marker_radius'],
            color=row['quality_color'],
            weight=1.5,
            fill=True,
            fill_color=row['quality_color'],
            fill_opacity=0.82,
            popup=folium.Popup(build_popup(row), max_width=360),
            tooltip=f"{row['site_id']} | {row['site_name']}",
        ).add_to(fmap)

    add_legend(fmap)
    fmap.save(str(OUTPUTS_MAPS_DIR / 'stations_map.html'))


if __name__ == '__main__':
    main()
