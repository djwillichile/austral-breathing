import json

from pipeline_paths import BASE_DIR

NOTEBOOK_PATH = BASE_DIR / "notebooks" / "eddy_covariance_pipeline_colab.ipynb"

if not NOTEBOOK_PATH.exists():
    raise SystemExit(f"Notebook not found: {NOTEBOOK_PATH}")

nb = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
cells = nb.get("cells", [])
all_text = "\n".join("".join(cell.get("source", [])) for cell in cells)

required_snippets = {
    "cl_sdf": "CL-SDF",
    "cl_sdp": "CL-SDP",
    "fluxnet_shuttle": "fluxnet-shuttle",
    "download_log": "download_log.csv",
    "stations_quality": "stations_quality.csv",
    "station_overview": "station_overview.csv",
    "map_html": "stations_map.html",
    "manual_upload_toggle": "ENABLE_MANUAL_UPLOAD = False",
    "utility_score": "utility_score",
}

missing = [name for name, snippet in required_snippets.items() if snippet not in all_text]
if missing:
    raise SystemExit(f"Notebook validation failed; missing snippets: {missing}")

markdown_cells = sum(1 for cell in cells if cell.get("cell_type") == "markdown")
code_cells = sum(1 for cell in cells if cell.get("cell_type") == "code")

if markdown_cells < 5 or code_cells < 5:
    raise SystemExit(
        f"Notebook validation failed; insufficient structure: markdown_cells={markdown_cells}, code_cells={code_cells}"
    )

print("Notebook validation passed.")
print(f"Path: {NOTEBOOK_PATH}")
print(f"Cells: total={len(cells)}, markdown={markdown_cells}, code={code_cells}")
print("Included seed sites: CL-SDF, CL-SDP")
print("Includes download, normalization, quality metrics, station overview, and interactive map steps.")
