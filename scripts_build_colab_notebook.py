import json
from textwrap import dedent

from pipeline_paths import BASE_DIR

NOTEBOOKS_DIR = BASE_DIR / "notebooks"
NOTEBOOK_PATH = NOTEBOOKS_DIR / "eddy_covariance_pipeline_colab.ipynb"


def lines(text: str) -> list[str]:
    text = dedent(text).strip("\n")
    if not text:
        return []
    return [line + "\n" for line in text.split("\n")]


def md_cell(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": lines(text),
    }


def code_cell(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines(text),
    }


cells = [
    md_cell(
        """
        # Google Colab reproducible demo: Eddy covariance pipeline for Chile and Patagonia

        Este notebook implementa una **demostración mínima funcional de extremo a extremo** del pipeline del proyecto usando como semillas validadas:

        - **CL-SDF** = Senda Darwin Forest
        - **CL-SDP** = Senda Darwin Peatland

        Sigue la prioridad solicitada en el encargo:

        1. **APIs y fuentes oficiales** cuando existan.
        2. **Librerías Python/R** documentadas.
        3. **Herramientas programáticas** como `fluxnet-shuttle`.

        El notebook evita scraping HTML y documenta explícitamente las limitaciones de acceso cuando la descarga automática falla por licencia, autenticación o restricciones del proveedor.

        ## Productos generados

        - `stations_metadata.csv`
        - `download_log.csv`
        - `variables_by_station.csv`
        - `stations_quality.csv`
        - `station_overview.csv`
        - `outputs/maps/stations_map.html`
        - archivos normalizados por estación en `data/processed/<site_id>/`
        """
    ),
    code_cell(
        '''
        # 1. Setup general del proyecto
        from __future__ import annotations

        import csv
        import io
        import json
        import os
        import shutil
        import subprocess
        import sys
        from io import TextIOWrapper
        from pathlib import Path
        from zipfile import ZipFile

        import folium
        from folium.plugins import Fullscreen
        from IPython.display import FileLink, display
        import numpy as np
        import pandas as pd

        PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/content/eddy_covariance_chile_patagonia_colab"))
        RAW_DIR = PROJECT_ROOT / "data" / "raw"
        PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
        METADATA_DIR = PROJECT_ROOT / "data" / "metadata"
        OUTPUTS_MAPS_DIR = PROJECT_ROOT / "outputs" / "maps"
        OUTPUTS_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
        RESEARCH_DIR = PROJECT_ROOT / "research"
        NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
        LOGS_DIR = PROJECT_ROOT / "logs"

        for directory in [
            PROJECT_ROOT,
            RAW_DIR,
            PROCESSED_DIR,
            METADATA_DIR,
            OUTPUTS_MAPS_DIR,
            OUTPUTS_TABLES_DIR,
            RESEARCH_DIR,
            NOTEBOOKS_DIR,
            LOGS_DIR,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        TARGET_SITES = ["CL-SDF", "CL-SDP"]

        SITE_CONTEXT = {
            "CL-SDF": {
                "country": "Chile",
                "regional_scope": "Chiloé Island, Northern Patagonia / temperate rainforest region",
                "ecosystem_note": "Old-growth North Patagonian rainforest",
                "access_type": "open",
                "access_method": "fluxnet-shuttle + AmeriFlux/FLUXNET product link",
            },
            "CL-SDP": {
                "country": "Chile",
                "regional_scope": "Chiloé Island, Northern Patagonia / peatland region",
                "ecosystem_note": "Peatland / wetland",
                "access_type": "open",
                "access_method": "fluxnet-shuttle + AmeriFlux/FLUXNET product link",
            },
        }

        IGBP_TO_BIOME = {
            "EBF": "Evergreen Broadleaf Forest",
            "ENF": "Evergreen Needleleaf Forest",
            "WET": "Wetland",
            "GRA": "Grassland",
        }

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
        MISSING_SENTINELS = [-9999, -9999.0, -6999, -6999.0]

        print(f"PROJECT_ROOT = {PROJECT_ROOT}")
        print(f"TARGET_SITES = {TARGET_SITES}")
        '''
    ),
    md_cell(
        """
        ## 2. Instalación condicional de dependencias

        Esta celda evita reinstalar paquetes si ya existen. En particular, intenta instalar `fluxnet-shuttle` solo cuando el comando no está disponible en el entorno.
        """
    ),
    code_cell(
        '''
        def ensure_python_package(import_name: str, pip_spec: str | None = None) -> None:
            try:
                __import__(import_name)
            except ImportError:
                spec = pip_spec or import_name
                print(f"Instalando dependencia Python: {spec}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", spec])

        def ensure_command(command_name: str, pip_spec: str | None = None) -> None:
            if shutil.which(command_name):
                print(f"Comando ya disponible: {command_name}")
                return
            if pip_spec is None:
                raise RuntimeError(f"No se encontró el comando requerido: {command_name}")
            print(f"Instalando comando faltante: {command_name}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pip_spec])
            if not shutil.which(command_name):
                raise RuntimeError(f"La instalación terminó, pero el comando sigue sin estar disponible: {command_name}")

        ensure_python_package("pandas")
        ensure_python_package("numpy")
        ensure_python_package("folium")
        ensure_command("fluxnet-shuttle", "git+https://github.com/fluxnet/shuttle.git")

        print("Dependencias listas.")
        '''
    ),
    md_cell(
        """
        ## 3. Descubrimiento de estaciones

        El notebook consulta `fluxnet-shuttle listall`, guarda un snapshot reproducible del inventario y construye una tabla de metadatos para **CL-SDF** y **CL-SDP**.
        """
    ),
    code_cell(
        '''
        def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if check and result.returncode != 0:
                print(result.stdout)
                print(result.stderr)
                raise RuntimeError(f"El comando falló ({result.returncode}): {' '.join(cmd)}")
            return result

        def write_csv_to_project_locations(df: pd.DataFrame, filename: str) -> None:
            df.to_csv(PROJECT_ROOT / filename, index=False)
            df.to_csv(METADATA_DIR / filename, index=False)
            df.to_csv(OUTPUTS_TABLES_DIR / filename, index=False)

        def discover_fluxnet_snapshot() -> tuple[pd.DataFrame, Path]:
            result = run_command(["fluxnet-shuttle", "listall"], check=True)
            snapshot_text = result.stdout.strip()
            if not snapshot_text:
                raise RuntimeError("fluxnet-shuttle listall no devolvió contenido utilizable.")
            snapshot_path = RESEARCH_DIR / "fluxnet_shuttle_snapshot_full.csv"
            snapshot_path.write_text(snapshot_text + "\n", encoding="utf-8")
            snapshot_df = pd.read_csv(io.StringIO(snapshot_text))
            return snapshot_df, snapshot_path

        def build_station_metadata(snapshot_df: pd.DataFrame) -> pd.DataFrame:
            filtered = snapshot_df[snapshot_df["site_id"].isin(TARGET_SITES)].copy()
            missing_sites = sorted(set(TARGET_SITES) - set(filtered["site_id"].unique()))
            if missing_sites:
                raise AssertionError(f"No fue posible encontrar las estaciones esperadas en el inventario: {missing_sites}")

            filtered["country"] = filtered["site_id"].map(lambda s: SITE_CONTEXT[s]["country"])
            filtered["regional_scope"] = filtered["site_id"].map(lambda s: SITE_CONTEXT[s]["regional_scope"])
            filtered["ecosystem_biome"] = filtered["igbp"].map(IGBP_TO_BIOME).fillna(filtered["igbp"])
            filtered["ecosystem_note"] = filtered["site_id"].map(lambda s: SITE_CONTEXT[s]["ecosystem_note"])
            filtered["temporal_period_available"] = filtered["first_year"].astype("Int64").astype(str) + "-" + filtered["last_year"].astype("Int64").astype(str)
            filtered["download_availability"] = filtered["download_link"].notna().map({True: "available", False: "unknown"})
            filtered["access_type"] = filtered["site_id"].map(lambda s: SITE_CONTEXT[s]["access_type"])
            filtered["access_method"] = filtered["site_id"].map(lambda s: SITE_CONTEXT[s]["access_method"])
            filtered["official_validation_source"] = filtered["product_citation"].fillna("AmeriFlux / FLUXNET metadata via fluxnet-shuttle")

            ordered_cols = [
                "site_id", "site_name", "country", "regional_scope", "location_lat", "location_long",
                "igbp", "ecosystem_biome", "ecosystem_note", "network", "first_year", "last_year",
                "temporal_period_available", "download_availability", "access_type", "access_method",
                "download_link", "fluxnet_product_name", "product_id", "oneflux_code_version",
                "official_validation_source",
            ]
            return filtered[ordered_cols].sort_values("site_id").reset_index(drop=True)

        snapshot_df, snapshot_path = discover_fluxnet_snapshot()
        stations_metadata = build_station_metadata(snapshot_df)
        write_csv_to_project_locations(stations_metadata, "stations_metadata.csv")

        stations_metadata[["site_id", "site_name", "country", "network", "first_year", "last_year", "fluxnet_product_name"]].to_csv(
            RESEARCH_DIR / "fluxnet_shuttle_snapshot_seed_sites.csv", index=False
        )

        print(f"Snapshot guardado en: {snapshot_path}")
        display(stations_metadata)
        '''
    ),
    md_cell(
        """
        ## 4. Descarga reproducible de datos

        Se intenta la descarga no interactiva usando `fluxnet-shuttle download`. Si falla por licencia, autenticación o restricciones del proveedor, el notebook deja la traza correspondiente en `download_log.csv`.
        """
    ),
    code_cell(
        '''
        def locate_existing_zip(product_name: str, site_id: str) -> Path | None:
            candidate_paths = [
                RAW_DIR / product_name,
                RAW_DIR / site_id / product_name,
                PROJECT_ROOT / product_name,
                Path("/content") / product_name,
            ]
            for path in candidate_paths:
                if path.exists():
                    return path
            return None

        def build_initial_download_log(metadata_df: pd.DataFrame) -> pd.DataFrame:
            log = metadata_df[["site_id", "site_name", "network", "download_link", "access_type", "access_method"]].copy()
            log["download_status"] = "pending"
            log["failure_reason"] = ""
            log["notes"] = "Initial log created from fluxnet-shuttle snapshot."
            return log[[
                "site_id", "site_name", "network", "access_type", "access_method",
                "download_status", "failure_reason", "download_link", "notes"
            ]]

        def attempt_download(metadata_df: pd.DataFrame, snapshot_csv: Path) -> pd.DataFrame:
            download_log = build_initial_download_log(metadata_df)
            products = dict(zip(metadata_df["site_id"], metadata_df["fluxnet_product_name"]))
            already_available = []
            missing_sites = []

            for site_id, product_name in products.items():
                if locate_existing_zip(product_name, site_id) is not None:
                    already_available.append(site_id)
                else:
                    missing_sites.append(site_id)

            stdout = ""
            stderr = ""
            return_code = None

            if missing_sites:
                cmd = [
                    "fluxnet-shuttle", "download",
                    "-f", str(snapshot_csv),
                    "-s", *missing_sites,
                    "-o", str(RAW_DIR),
                    "--quiet",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                return_code = result.returncode
            else:
                stdout = "No download required; files were already present."
                return_code = 0

            for site_id, product_name in products.items():
                zip_path = locate_existing_zip(product_name, site_id)
                if zip_path is not None:
                    status = "success"
                    failure_reason = ""
                    notes = "Downloaded automatically with fluxnet-shuttle or found pre-existing in the Colab workspace."
                else:
                    status = "restricted_or_failed"
                    failure_reason = "File not found after automated download attempt."
                    notes = "Review logs; this usually indicates license acceptance, authentication, network restriction, or manual-upload requirement."

                download_log.loc[download_log["site_id"] == site_id, "download_status"] = status
                download_log.loc[download_log["site_id"] == site_id, "failure_reason"] = failure_reason
                download_log.loc[download_log["site_id"] == site_id, "notes"] = notes

            write_csv_to_project_locations(download_log, "download_log.csv")
            (LOGS_DIR / "download_stdout.log").write_text(stdout, encoding="utf-8")
            (LOGS_DIR / "download_stderr.log").write_text(stderr, encoding="utf-8")
            (LOGS_DIR / "download_summary.txt").write_text(
                "\n".join([
                    f"requested_sites={','.join(TARGET_SITES)}",
                    f"already_available={','.join(already_available) if already_available else 'none'}",
                    f"attempted_download={','.join(missing_sites) if missing_sites else 'none'}",
                    f"return_code={return_code}",
                ]) + "\n",
                encoding="utf-8",
            )
            return download_log

        download_log = attempt_download(stations_metadata, snapshot_path)
        display(download_log)
        '''
    ),
    md_cell(
        """
        ## 5. Carga manual opcional de archivos ZIP

        Si una estación queda como `restricted_or_failed`, puedes subir manualmente los ZIP originales al entorno de Colab. Deja `ENABLE_MANUAL_UPLOAD = False` si no lo necesitas.
        """
    ),
    code_cell(
        '''
        ENABLE_MANUAL_UPLOAD = False

        if ENABLE_MANUAL_UPLOAD:
            try:
                from google.colab import files
            except ImportError:
                raise RuntimeError("La carga manual está pensada para ejecutarse dentro de Google Colab.")

            uploaded = files.upload()
            for filename, content in uploaded.items():
                destination = RAW_DIR / filename
                with open(destination, "wb") as f:
                    f.write(content)
            print("Archivos subidos:", sorted(p.name for p in RAW_DIR.glob("*.zip")))
        else:
            print("Carga manual deshabilitada. Continúa si la descarga automática ya fue exitosa o si los ZIP ya existen en el entorno.")
        '''
    ),
    md_cell(
        """
        ## 6. Organización de archivos originales y extracción selectiva

        Se conserva una copia original del ZIP por estación y se extraen los insumos mínimos necesarios para la validación:

        - `*_FLUXMET_DD_*.csv`
        - `*_BIF_*.csv`
        - `*_BIFVARINFO_DD_*.csv`
        - licencia / instrucciones de uso si existen
        """
    ),
    code_cell(
        '''
        def pick_member(names: list[str], token: str) -> str:
            for name in names:
                if token in name and name.endswith(".csv"):
                    return name
            raise FileNotFoundError(f"No se encontró un miembro con el patrón {token} dentro del ZIP.")

        def ensure_original_copy(site_id: str, zip_path: Path) -> Path:
            site_raw_dir = RAW_DIR / site_id
            site_raw_dir.mkdir(parents=True, exist_ok=True)
            destination = site_raw_dir / zip_path.name
            if zip_path.resolve() != destination.resolve():
                shutil.copy2(zip_path, destination)
            return destination

        def extract_selected_members(zip_copy_path: Path, site_id: str) -> None:
            site_raw_dir = RAW_DIR / site_id
            with ZipFile(zip_copy_path) as zf:
                names = zf.namelist()
                selected = [
                    pick_member(names, "_FLUXMET_DD_"),
                    pick_member(names, "_BIF_"),
                    pick_member(names, "_BIFVARINFO_DD_"),
                ]
                text_members = [name for name in names if name in {"README.txt", "DATA_POLICY_LICENSE_AND_INSTRUCTIONS.txt"}]
                selected.extend(text_members)
                for member in selected:
                    output_path = site_raw_dir / Path(member).name
                    if not output_path.exists():
                        with zf.open(member) as src, open(output_path, "wb") as dst:
                            dst.write(src.read())

        extracted_inventory = []
        for row in stations_metadata.itertuples(index=False):
            zip_path = locate_existing_zip(row.fluxnet_product_name, row.site_id)
            if zip_path is None:
                raise RuntimeError(
                    f"No se encontró el ZIP para {row.site_id}. Revisa download_log.csv o habilita la carga manual en la celda anterior."
                )
            zip_copy = ensure_original_copy(row.site_id, zip_path)
            extract_selected_members(zip_copy, row.site_id)
            extracted_inventory.append({
                "site_id": row.site_id,
                "zip_file": zip_copy.name,
                "site_raw_dir": str((RAW_DIR / row.site_id).resolve()),
            })

        extracted_inventory_df = pd.DataFrame(extracted_inventory)
        extracted_inventory_df.to_csv(RESEARCH_DIR / "raw_seed_inventory.csv", index=False)
        display(extracted_inventory_df)
        '''
    ),
    md_cell(
        """
        ## 7. Validación intermedia del esquema

        Antes de normalizar, inspeccionamos los archivos diarios de CL-SDF y CL-SDP para confirmar que el pipeline realmente está leyendo productos FLUXNET con las variables núcleo esperadas.
        """
    ),
    code_cell(
        '''
        STANDARD_VARIABLE_HINTS = {
            "timestamp": ["TIMESTAMP"],
            "NEE": ["NEE_VUT_REF", "NEE_CUT_REF", "FC", "FC_F_MDS"],
            "GPP": ["GPP_NT_VUT_REF", "GPP_DT_VUT_REF"],
            "LE": ["LE_F_MDS", "LE"],
            "H": ["H_F_MDS", "H"],
            "TA": ["TA_F_MDS", "TA"],
            "SW_IN": ["SW_IN_F_MDS", "SW_IN"],
        }

        def summarize_flux_schema(site_id: str) -> dict:
            site_dir = RAW_DIR / site_id
            flux_file = next(site_dir.glob("*_FLUXMET_DD_*.csv"))
            with open(flux_file, "rb") as fh:
                reader = csv.reader(TextIOWrapper(fh, encoding="utf-8", errors="replace"))
                header = next(reader)
                first_row = next(reader)
            candidates = {
                variable: [col for col in header if any(token in col for token in tokens)]
                for variable, tokens in STANDARD_VARIABLE_HINTS.items()
            }
            return {
                "site_id": site_id,
                "flux_file": flux_file.name,
                "n_columns": len(header),
                "first_25_columns": header[:25],
                "last_25_columns": header[-25:],
                "candidate_columns": candidates,
                "first_row_preview": first_row[:12],
            }

        schema_summary = {site_id: summarize_flux_schema(site_id) for site_id in TARGET_SITES}
        with open(RESEARCH_DIR / "flux_schema_summary_seed_sites.json", "w", encoding="utf-8") as f:
            json.dump(schema_summary, f, indent=2, ensure_ascii=False)

        for site_id, summary in schema_summary.items():
            print(f"\n===== {site_id} =====")
            print("Archivo:", summary["flux_file"])
            print("Columnas candidatas:")
            for key, value in summary["candidate_columns"].items():
                print(f"  - {key}: {value}")
        '''
    ),
    md_cell(
        """
        ## 8. Lectura, normalización y cálculo de indicadores

        Se armonizan las variables mínimas solicitadas, se convierten sentinelas de missing a `NaN`, se conservan columnas de calidad cuando existen y se calcula un indicador sintético simple de utilidad/calidad por estación.
        """
    ),
    code_cell(
        '''
        def parse_timestamp(series: pd.Series) -> pd.Series:
            text = series.astype(str).str.strip()
            if text.str.len().mode().iloc[0] == 8:
                return pd.to_datetime(text, format="%Y%m%d", errors="coerce")
            if text.str.len().mode().iloc[0] == 12:
                return pd.to_datetime(text, format="%Y%m%d%H%M", errors="coerce")
            return pd.to_datetime(text, errors="coerce")

        def discover_station_files() -> dict[str, dict[str, Path | None]]:
            stations = {}
            for site_id in TARGET_SITES:
                station_dir = RAW_DIR / site_id
                flux_files = list(station_dir.glob("*_FLUXMET_DD_*.csv"))
                bif_files = list(station_dir.glob("*_BIF_*.csv"))
                bifvarinfo_files = list(station_dir.glob("*_BIFVARINFO_DD_*.csv"))
                if not flux_files:
                    raise FileNotFoundError(f"No se encontró un archivo *_FLUXMET_DD_* para {site_id}")
                stations[site_id] = {
                    "fluxmet_dd": flux_files[0],
                    "bif": bif_files[0] if bif_files else None,
                    "bifvarinfo": bifvarinfo_files[0] if bifvarinfo_files else None,
                }
            return stations

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
                "notes": "Unit hints extracted from BIFVARINFO where available; detailed semantic parsing may still require manual review.",
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

        def read_and_standardize_station(site_id: str, file_info: dict[str, Path | None]) -> tuple[pd.DataFrame, dict, dict]:
            df = pd.read_csv(file_info["fluxmet_dd"])
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

            bifvarinfo_summary = summarize_bifvarinfo(file_info.get("bifvarinfo"))
            station_summary = summarize_station(site_id, out, original_columns, bifvarinfo_summary)
            return out, station_summary, bifvarinfo_summary

        def update_variables_table(station_summaries: list[dict]) -> pd.DataFrame:
            rows = []
            for summary in station_summaries:
                rows.append({
                    "site_id": summary["site_id"],
                    "site_name": pd.NA,
                    "variables_present": summary["variables_present"],
                    "standardized_core_variables_present": summary["variables_present"],
                    "source_file": f"data/raw/{summary['site_id']}",
                    "notes": "Standardized from daily FLUXMET product. Additional variables preserved in original raw files.",
                })
            out = pd.DataFrame(rows)
            meta = pd.read_csv(PROJECT_ROOT / "stations_metadata.csv")[["site_id", "site_name"]]
            out = out.drop(columns=["site_name"]).merge(meta, on="site_id", how="left")
            return out[["site_id", "site_name", "variables_present", "standardized_core_variables_present", "source_file", "notes"]].sort_values("site_id")

        def update_quality_table(station_summaries: list[dict]) -> pd.DataFrame:
            quality = pd.DataFrame(station_summaries)
            meta = pd.read_csv(PROJECT_ROOT / "stations_metadata.csv")[["site_id", "site_name", "country"]]
            quality = quality.merge(meta, on="site_id", how="left")
            ordered_cols = [
                "site_id", "site_name", "country", "year_start", "year_end", "temporal_coverage_years",
                "total_observations", "valid_nee_pct", "valid_gpp_pct", "valid_le_pct", "valid_h_pct",
                "valid_ta_pct", "valid_sw_in_pct", "acceptable_qc_pct", "acceptable_nee_qc_pct",
                "acceptable_le_qc_pct", "acceptable_h_qc_pct", "acceptable_ta_qc_pct",
                "acceptable_sw_in_qc_pct", "variables_available_count", "utility_score", "quality_class",
                "original_variable_count", "standardized_variable_count", "variables_present",
                "additional_variables_detected", "unit_notes", "notes",
            ]
            return quality[ordered_cols].sort_values("site_id")

        station_files = discover_station_files()
        station_frames = {}
        station_summaries = []
        bifvarinfo_summaries = {}

        for site_id, info in station_files.items():
            standardized_df, summary, bif_summary = read_and_standardize_station(site_id, info)
            station_frames[site_id] = standardized_df
            station_summaries.append(summary)
            bifvarinfo_summaries[site_id] = bif_summary

        for site_id, df in station_frames.items():
            site_dir = PROCESSED_DIR / site_id
            site_dir.mkdir(parents=True, exist_ok=True)
            df.to_csv(site_dir / f"{site_id}_daily_standardized.csv", index=False)

        variables_df = update_variables_table(station_summaries)
        quality_df = update_quality_table(station_summaries)

        write_csv_to_project_locations(variables_df, "variables_by_station.csv")
        write_csv_to_project_locations(quality_df, "stations_quality.csv")
        with open(RESEARCH_DIR / "bifvarinfo_unit_hints.json", "w", encoding="utf-8") as f:
            json.dump(bifvarinfo_summaries, f, indent=2, ensure_ascii=False)

        assert len(quality_df) == 2, "La tabla de calidad debe contener exactamente CL-SDF y CL-SDP en esta demostración mínima."
        assert set(quality_df["site_id"]) == set(TARGET_SITES), "La tabla de calidad no contiene ambas estaciones semilla."

        display(quality_df[[
            "site_id", "year_start", "year_end", "total_observations",
            "valid_nee_pct", "valid_gpp_pct", "acceptable_qc_pct",
            "utility_score", "quality_class"
        ]])
        '''
    ),
    md_cell(
        """
        ## 9. Tabla consolidada y mapa interactivo HTML

        El mapa utiliza colores por clase de calidad/utilidad y tamaño de marcador proporcional al número de observaciones diarias estandarizadas.
        """
    ),
    code_cell(
        '''
        def quality_color(quality_class: str) -> str:
            palette = {
                "high": "#2F6B3B",
                "medium": "#C78C1B",
                "low": "#A43A2A",
            }
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

        metadata = pd.read_csv(PROJECT_ROOT / "stations_metadata.csv")
        quality = pd.read_csv(PROJECT_ROOT / "stations_quality.csv")
        variables = pd.read_csv(PROJECT_ROOT / "variables_by_station.csv")

        merged = metadata.merge(quality, on=["site_id", "site_name", "country"], how="left")
        merged = merged.merge(variables[["site_id", "variables_present"]], on="site_id", how="left", suffixes=("", "_variables"))
        if "variables_present_variables" in merged.columns:
            merged["variables_present"] = merged["variables_present"].fillna(merged["variables_present_variables"])
            merged = merged.drop(columns=["variables_present_variables"])

        merged["quality_color"] = merged["quality_class"].map(quality_color)
        min_obs = float(merged["total_observations"].min())
        max_obs = float(merged["total_observations"].max())
        merged["marker_radius"] = merged["total_observations"].apply(lambda x: marker_radius(x, min_obs, max_obs))
        merged = merged.sort_values(["country", "site_id"]).reset_index(drop=True)
        merged.to_csv(OUTPUTS_TABLES_DIR / "station_overview.csv", index=False)

        center_lat = merged["location_lat"].mean()
        center_lon = merged["location_long"].mean()
        fmap = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="CartoDB positron", control_scale=True)

        title_html = """
        <div style="position: fixed; top: 18px; left: 50%; transform: translateX(-50%); z-index: 9999; background: rgba(22,50,47,0.88); color: #f7f3ea; padding: 12px 18px; border-radius: 14px; box-shadow: 0 12px 28px rgba(0,0,0,0.18); font-family: Georgia, serif;">
          <div style="font-size: 16px; font-weight: bold;">Seed-site validation map: Chilean eddy covariance stations</div>
          <div style="font-size: 12px; opacity: 0.9; margin-top: 4px;">CL-SDF and CL-SDP processed end-to-end from the reproducible Colab workflow</div>
        </div>
        """
        fmap.get_root().html.add_child(folium.Element(title_html))
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
        map_path = OUTPUTS_MAPS_DIR / "stations_map.html"
        fmap.save(str(map_path))
        display(merged[["site_id", "site_name", "total_observations", "utility_score", "quality_class"]])
        fmap
        '''
    ),
    md_cell(
        """
        ## 10. Validación final y exportación de outputs

        Esta celda ejecuta comprobaciones mínimas para demostrar que el pipeline se completó de extremo a extremo con las dos estaciones semilla.
        """
    ),
    code_cell(
        '''
        final_checks = {
            "stations_metadata_exists": (PROJECT_ROOT / "stations_metadata.csv").exists(),
            "download_log_exists": (PROJECT_ROOT / "download_log.csv").exists(),
            "variables_by_station_exists": (PROJECT_ROOT / "variables_by_station.csv").exists(),
            "stations_quality_exists": (PROJECT_ROOT / "stations_quality.csv").exists(),
            "station_overview_exists": (OUTPUTS_TABLES_DIR / "station_overview.csv").exists(),
            "map_exists": (OUTPUTS_MAPS_DIR / "stations_map.html").exists(),
            "standardized_cl_sdf_exists": (PROCESSED_DIR / "CL-SDF" / "CL-SDF_daily_standardized.csv").exists(),
            "standardized_cl_sdp_exists": (PROCESSED_DIR / "CL-SDP" / "CL-SDP_daily_standardized.csv").exists(),
        }

        for key, value in final_checks.items():
            assert value, f"Fallo en validación final: {key}"

        station_overview = pd.read_csv(OUTPUTS_TABLES_DIR / "station_overview.csv")
        assert len(station_overview) == 2, "station_overview.csv debe contener exactamente dos estaciones en esta demostración mínima."
        assert set(station_overview["site_id"]) == set(TARGET_SITES), "station_overview.csv no contiene exactamente CL-SDF y CL-SDP."
        assert station_overview["utility_score"].notna().all(), "Cada estación debe tener utility_score calculado."

        bundle_base = PROJECT_ROOT / "outputs" / "colab_seed_demo_outputs"
        bundle_path = shutil.make_archive(str(bundle_base), "zip", root_dir=PROJECT_ROOT / "outputs")

        print("Validación final completada correctamente.")
        print("Bundle de salida:", bundle_path)
        display(FileLink(bundle_path))
        display(FileLink(OUTPUTS_MAPS_DIR / "stations_map.html"))
        display(FileLink(OUTPUTS_TABLES_DIR / "station_overview.csv"))
        '''
    ),
    md_cell(
        """
        ## 11. Limitaciones y notas de reproducibilidad

        > Esta demostración mínima valida el flujo completo con **CL-SDF** y **CL-SDP**, pero el mismo patrón puede ampliarse a otras estaciones chilenas y comparadores patagónicos cambiando `TARGET_SITES`.

        Consideraciones importantes:

        - La disponibilidad efectiva de descarga depende del estado del proveedor y de sus condiciones de acceso.
        - Si una red exige aceptación de licencia, registro o autenticación, el notebook **no intenta eludirla**.
        - El notebook deja trazabilidad en `download_log.csv` para distinguir entre éxito, restricción y fallo operativo.
        - Las unidades y metadatos adicionales se resumen desde `BIFVARINFO`, pero su interpretación semántica detallada aún puede requerir revisión manual.
        - El umbral de calidad usado aquí para variables QC disponibles es **>= 0.5**, replicando la lógica del pipeline del repositorio.
        """
    ),
]

notebook = {
    "cells": cells,
    "metadata": {
        "colab": {
            "name": NOTEBOOK_PATH.name,
            "provenance": [],
            "toc_visible": True,
        },
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.11",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)
NOTEBOOK_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Notebook written to {NOTEBOOK_PATH}")
