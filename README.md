# Eddy Covariance Stations in Chile and Patagonia

This repository assembles a **reproducible pipeline** for discovering, downloading, organizing, standardizing, and comparing eddy covariance station products from **Chile** and nearby southern South American sites with ecological or geographic relevance to **Patagonia**. The current implementation prioritizes officially distributed, programmatically accessible products and uses a scripted workflow centered on **AmeriFlux / FLUXNET data products** and the public **FLUXNET Shuttle** client rather than manual downloads or HTML scraping [1] [5].

This work has been prepared for **Instituto de Ciencias y Tecnología Ambiental ICTA ltda.**, with **Guillermo S. Fuentes-Jaque** as principal consultant. The repository is designed to remain suitable for future public release, while preserving the attribution and data-use requirements attached to the downloaded FLUXNET products [5].

| Project component | Current output |
| --- | --- |
| Station inventory | `stations_metadata.csv` |
| Download traceability log | `download_log.csv` |
| Standardized quality table | `stations_quality.csv` |
| Variable availability table | `variables_by_station.csv` |
| Interactive map | `outputs/maps/stations_map.html` |
| Consolidated overview table | `outputs/tables/station_overview.csv` |
| Reproducible Python scripts | `scripts_*.py` |

## Scientific motivation

Eddy covariance observations provide direct constraints on ecosystem-atmosphere exchanges of carbon, water, and energy, making them essential for regional carbon-balance studies, ecohydrological comparisons, model benchmarking, and synthesis across biomes. The FLUXNET processing framework and its regional networks have made such comparisons increasingly feasible by distributing harmonized products, standardized variables, and explicit metadata conventions [1] [3]. For southern South America, a curated and reproducible inventory is particularly useful because stations are sparse, ecosystems are highly heterogeneous, and access pathways may differ by network, product generation, or licensing requirements [1] [5].

The present repository therefore focuses not only on collecting station files, but also on documenting **how** they were discovered, **which** products were actually downloadable, **what** standardization choices were applied, and **where** attribution obligations arise. This emphasis is intended to support future scientific reuse, transparent auditing, and eventual integration into GitHub-based dissemination workflows.

| Regional rationale | Interpretation |
| --- | --- |
| Chilean sites | Core target of the project, including Chiloé and southern temperate ecosystems |
| Argentine comparator sites | Included when ecologically or geographically comparable to Patagonia |
| Programmatic access priority | Official APIs and documented tools are preferred over manual steps or scraping |
| Publication readiness | Outputs are organized to support a future GitHub repository and GitHub Pages site |

## Study area and current regional scope

The current validated inventory contains **6 stations** across **Chile** and **Argentina**, all distributed through **AmeriFlux FLUXNET products** and accessed through a reproducible scripted workflow based on `fluxnet-shuttle` [1]. The downloaded records span **2014 to 2024**, and the standardized daily products currently contain **11,689 observations** in aggregate across the six processed stations.

The geographic scope intentionally begins with the user-validated seed sites **CL-SDF** and **CL-SDP**, then expands to other Chilean stations and southern Argentine comparators already available through the same product family. At this stage, every station included in the active inventory is openly downloadable and represented by an unmodified original archive preserved under `data/raw/`.

| Site ID | Official name | Country | Regional scope | Ecosystem note | Years | Access | DOI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CL-SDF | Senda Darwin Forest | Chile | Chiloé Island, Northern Patagonia / temperate rainforest region | Old-growth North Patagonian rainforest | 2014–2021 | Open | [10](https://doi.org/10.17190/AMF/2469441) |
| CL-SDP | Senda Darwin Peatland | Chile | Chiloé Island, Northern Patagonia / peatland region | Peatland / wetland | 2014–2021 | Open | [11](https://doi.org/10.17190/AMF/2571108) |
| CL-ACF | Alerce Costero Forest | Chile | Alerce Costero, southern Chile | Temperate forest | 2018–2020 | Open | [9](https://doi.org/10.17190/AMF/2571129) |
| AR-TF1 | Rio Moat bog | Argentina | Tierra del Fuego / Southern Patagonia | Bog / wetland | 2016–2018 | Open | [7](https://doi.org/10.17190/AMF/1818370) |
| AR-TF2 | Rio Pipo bog | Argentina | Tierra del Fuego / Southern Patagonia | Bog / wetland | 2016–2018 | Open | [8](https://doi.org/10.17190/AMF/2571120) |
| AR-CCg | Carlos Casares grassland | Argentina | Regional comparator outside core Patagonia | Grassland | 2018–2024 | Open | [6](https://doi.org/10.17190/AMF/2469434) |

## Data sources, APIs, and tools

The operational priority of the repository follows a strict hierarchy: **official programmatic sources first**, then documented libraries or command-line clients, and only then any manual fallback if absolutely necessary. In the current implementation, the project relies primarily on the public **FLUXNET Shuttle** library, which is explicitly documented as a Python tool for discovering and downloading FLUXNET data from multiple hubs, including **AmeriFlux**, **ICOS**, and **TERN** [1]. In practice, the downloaded stations in this repository were all obtained from the AmeriFlux / FLUXNET product stream represented in the snapshot generated by the client.

The repository also keeps the **ICOS Carbon Portal** in scope for later expansion because ICOS documents quality-controlled ecosystem products and additional releases in FLUXNET-compatible formats, making it a natural extension pathway for future versions of this pipeline [2]. Although the current processed inventory is entirely AmeriFlux-based, the methodological design avoids hard-coding a single network and is intended to remain extensible to additional hubs.

| Source or tool | Role in this repository | Current use status | Notes |
| --- | --- | --- | --- |
| AmeriFlux / FLUXNET product archives | Authoritative downloaded station products | Active | All six current stations were downloaded from this product family |
| FLUXNET Shuttle | Programmatic discovery and download client | Active | Used for snapshot generation and reproducible site downloads [1] |
| ICOS Carbon Portal | Reference data hub for future extension | Referenced | Official ICOS data products include ecosystem archives and FLUXNET-format products [2] |
| Bundled FLUXNET license file | Operational source for attribution wording | Active | Used because it ships with each downloaded archive and was directly verifiable in-session [5] |
| AmeriFlux data policy page | Canonical policy reference | Referenced with caveat | The URL is official, but browser access during this session was blocked by Berkeley Lab WAF [4] |

## Workflow and methodology

The repository workflow is intentionally script-driven. It starts from station discovery, preserves the original downloaded archives, extracts only the required files for processing, standardizes a common set of flux and meteorological variables, computes quality indicators, and then builds an interactive regional map. This approach keeps the pipeline transparent and allows each phase to be rerun independently.

The standardization layer uses daily FLUXNET products and harmonizes the following core variables when present: **timestamp**, **NEE**, **GPP**, **LE**, **H**, **TA**, and **SW_IN**. Missing sentinels such as `-9999` are converted to `NaN`, quality-control columns are retained when available, and additional variables remain preserved in the raw station directories for future analyses. A documented fallback was necessary for **CL-SDF**, where `GPP_NT_VUT_REF` is absent at the daily time scale; in that case, the standardized `GPP` series is filled from `GPP_DT_VUT_REF`, and the method note is retained in the processed output.

| Workflow phase | Main script | Main output |
| --- | --- | --- |
| Build station tables | `scripts_build_station_tables.py` | `stations_metadata.csv`, initial logs and metadata tables |
| Download data | `scripts_download_fluxnet_data.py` | Original product archives and updated `download_log.csv` |
| Organize raw data | `scripts_organize_raw_downloads.py` | Station-level raw folders with ZIP, FLUXMET, BIF and BIFVARINFO files |
| Inspect variable schema | `scripts_inspect_flux_schema.py` | `research/flux_schema_summary.json` |
| Standardize and score | `scripts_standardize_and_compute_metrics.py` | `data/processed/*`, `stations_quality.csv`, `variables_by_station.csv` |
| Build map and summary | `scripts_build_map_and_summaries.py` | `outputs/maps/stations_map.html`, `outputs/tables/station_overview.csv` |

## Quality indicators and comparative logic

Each station is summarized using a compact but interpretable scoring system. The repository computes the temporal coverage window, the number of standardized observations, variable-specific valid-data percentages, and the share of acceptable QC values when QC flags are available. These components are then combined into a simple **utility score** intended for comparison and visualization rather than formal data certification.

The current classification results identify **4 stations as high utility** and **2 as medium utility**, with no station falling into the low class under the present rule set. The highest current utility score belongs to **CL-SDP** (`0.902`), while the lowest belongs to **AR-TF2** (`0.678`). These values should be interpreted as a project-internal comparative index, not as a substitute for station-specific expert judgment.

| Site ID | Temporal coverage (years) | Observations | Valid NEE (%) | Valid GPP (%) | Acceptable QC (%) | Utility score | Class |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| CL-SDP | 8 | 2922 | 99.66 | 99.66 | 82.20 | 0.902 | High |
| CL-SDF | 8 | 2922 | 94.32 | 94.32 | 78.78 | 0.886 | High |
| AR-CCg | 7 | 2557 | 85.80 | 85.80 | 74.14 | 0.837 | High |
| CL-ACF | 3 | 1096 | 98.63 | 98.63 | 93.05 | 0.804 | High |
| AR-TF1 | 3 | 1096 | 79.29 | 79.29 | 75.84 | 0.713 | Medium |
| AR-TF2 | 3 | 1096 | 75.91 | 75.91 | 66.84 | 0.678 | Medium |

## Interactive map

The interactive map is exported as a reusable HTML document at `outputs/maps/stations_map.html`. It shows station location, quality class, observation volume, and a popup summary with the site identifier, official name, country, ecosystem note, coverage years, variable availability, and utility score. The color scheme follows the project specification of **green for high**, **amber for medium**, and **red for low**, while marker size is scaled to the number of standardized observations.

Because the map is generated from the processed summary tables rather than hand-entered station metadata, it can be rebuilt automatically whenever the underlying standardized products or quality tables are updated. This design is meant to support later embedding in the GitHub Pages site without duplicating the processing logic.

| Map artifact | Path | Description |
| --- | --- | --- |
| Reusable HTML map | `outputs/maps/stations_map.html` | Interactive regional visualization for browser use |
| Consolidated map table | `outputs/tables/station_overview.csv` | Input table used to build the map |

## Repository structure

The repository is organized so that **raw**, **processed**, **metadata**, **analysis outputs**, **research notes**, and **web assets** remain clearly separated. This helps preserve provenance and reduces the risk of accidentally overwriting original downloads.

```text
.
├── data/
│   ├── raw/
│   │   ├── <SITE_ID>/
│   │   └── *.zip
│   ├── processed/
│   │   └── <SITE_ID>/<SITE_ID>_daily_standardized.csv
│   └── metadata/
│       ├── download_log.csv
│       ├── stations_metadata.csv
│       ├── stations_quality.csv
│       └── variables_by_station.csv
├── outputs/
│   ├── maps/
│   │   └── stations_map.html
│   └── tables/
│       ├── station_overview.csv
│       ├── stations_metadata.csv
│       ├── stations_quality.csv
│       └── variables_by_station.csv
├── research/
│   ├── fluxnet_shuttle_snapshot_*.csv
│   ├── flux_schema_summary.json
│   └── bifvarinfo_unit_hints.json
├── notebooks/
├── docs/
├── client/
├── scripts_build_station_tables.py
├── scripts_download_fluxnet_data.py
├── scripts_organize_raw_downloads.py
├── scripts_inspect_flux_schema.py
├── scripts_standardize_and_compute_metrics.py
├── scripts_build_map_and_summaries.py
├── stations_metadata.csv
├── stations_quality.csv
├── variables_by_station.csv
└── README.md
```

## How to reproduce the pipeline

The project is designed to be reproducible from a fresh Python environment with internet access and a working installation of `fluxnet-shuttle`. The download step assumes that the targeted products are legally accessible and that the user accepts the licensing terms attached to the downloaded FLUXNET archives [1] [5]. If a future source requires login, explicit license acceptance, or manual registration, that condition should be recorded in the download log and reflected in the README before redistribution.

A typical command-line reproduction sequence is shown below. The commands are intentionally explicit so they can later be mirrored in a Google Colab notebook or a CI-like workflow.

```bash
pip install -r requirements.txt
pip install git+https://github.com/fluxnet/shuttle.git
python scripts_discover_southern_cone_stations.py        # discover Southern-Cone catalog
python scripts_build_station_tables.py                   # target sites derived from the catalog
python scripts_loop_download_driver.py                   # idempotent, retrying download pass
python scripts_organize_raw_downloads.py
python scripts_inspect_flux_schema.py
python scripts_standardize_and_compute_metrics.py
python scripts_build_map_and_summaries.py
python scripts_export_web_data.py                        # emit JSON for the interactive web charts
```

## Expanded Southern-Cone discovery and aggressive acquisition

To grow the inventory beyond the original six sites, the pipeline now includes a
**station-discovery layer** and a **loop-driven download driver**, plus
**interactive web visualisations**:

- `scripts_discover_southern_cone_stations.py` queries official portals
  (AmeriFlux public site list, FLUXNET site pages, and `fluxnet-shuttle listall`),
  filters to the **Southern Cone** (country prefixes `CL/AR/UY/PY/BR` **and**
  latitude south of `-20°`, so tropical Brazilian sites are excluded), dedupes
  across networks, and writes a **snapshot-compatible** catalog into `research/`.
  Because every downstream script reads the newest snapshot, new stations flow
  through automatically. A `research/southern_cone_discovery_audit.csv` records
  every discovered site and why it was kept or dropped. Run `--dry-run` to use
  bundled fixtures with no network.
- **Respectful scraping**: HTML discovery goes through `pipeline_http.py`, which
  sets a descriptive User-Agent, honours `robots.txt`, rate-limits per host,
  retries with backoff (respecting `Retry-After`), and caches responses. Scraping
  is used **only for discovery/metadata**; actual data is always acquired through
  the official `fluxnet-shuttle` path, and CC-BY-4.0 attribution is preserved.
- `scripts_loop_download_driver.py` performs **one idempotent pass per
  invocation**: it skips stations whose data is already present, retries failed
  ones with exponential backoff persisted in `download_log.csv`, marks stations
  that hit the attempt ceiling as `exhausted`, and prints a `LOOP_STATUS:` line
  plus `logs/loop_status.txt`. It exits `0` when no retriable work remains. This
  is designed for the `/loop` skill — e.g. `/loop 10m python scripts_loop_download_driver.py`
  keeps ticking until everything is downloaded, then stops.
- `scripts_export_web_data.py` now also emits JSON into `client/public/data/`
  (`stations.json`, `stats.json`, `timeseries/<SITE>.json`) consumed by the
  React app's **Analysis** section: interactive per-variable time series,
  cross-station statistics/variability, an environmental-space scatter, biome
  coverage, and per-station ecological & geographic **representativeness**.

All file paths are resolved through `pipeline_paths.py` (honouring the
`EDDY_BASE_DIR` environment variable), so the pipeline runs from any checkout.
Offline logic tests live in `tests/` and run with `python -m pytest tests/`.

| Reproduction requirement | Practical note |
| --- | --- |
| Python environment | Python 3.11 or newer is recommended, matching FLUXNET Shuttle support [1] |
| Internet access | Required for discovery and download steps |
| Legal access to products | Must comply with the data-use terms packaged with the FLUXNET archive [5] |
| Original files preserved | ZIP archives remain in `data/raw/` and are also copied into station-level folders |
| Rebuild philosophy | Summary tables and map can be regenerated from the raw and processed folders |

## Data use, attribution, and citation obligations

The downloaded FLUXNET products used here are distributed under **CC-BY-4.0**, and the bundled license text explicitly requires attribution for every use, site-level citation, and a network-level acknowledgment statement [5]. The same bundled document also recommends citing the ONEFlux / FLUXNET processing paper by Pastorello et al. (2020) [3] and adding the AmeriFlux funding acknowledgment when AmeriFlux products are used [5].

> “The FLUXNET data product is shared under the CC-BY-4.0 license ... The CC-BY-4.0 license requires that attribution be given with every use.” [5]

> “Include the citation for each site's FLUXNET data product in your paper or project.” [5]

During this session, the official AmeriFlux data-policy webpage was referenced but direct browser access was blocked by a Berkeley Lab Cloudflare WAF page. For that reason, the operational attribution wording in this repository was taken from the license file included inside the downloaded archive, while the official AmeriFlux policy URL is still listed as the canonical policy reference [4] [5].

## Limitations

The present inventory is intentionally conservative. It includes only stations that were validated from official or product-linked sources and that could be downloaded reproducibly in the current session. This means the repository should be understood as a **verified working subset**, not yet a definitive census of every potentially relevant eddy covariance site in southern South America.

A second limitation is that the current processed inventory is entirely based on **AmeriFlux-distributed FLUXNET products**, even though the workflow is designed to be extensible to additional hubs such as ICOS [1] [2]. Future releases should test cross-network normalization more explicitly, especially where variable naming conventions, archive structure, QC semantics, or access procedures diverge.

A third limitation concerns attribution logistics. Site-specific citation metadata are present in the station inventory, but any formal publication or redistribution should still verify the most recent DOI and acknowledgment instructions at the time of submission. This is especially important because policy pages, portal interfaces, and archive versions may evolve over time [4] [5].

| Limitation | Consequence |
| --- | --- |
| Inventory is a validated subset | Additional relevant stations may be incorporated later |
| Current downloads come from one active network stream | Cross-network harmonization still needs broader testing |
| Daily products were used for standardization | Some variables or QC nuances may differ from sub-daily products |
| One official policy page was WAF-blocked in-session | Bundled license text was used as the directly verified attribution source |

## Potential applications

This repository can support regional screening of station suitability, comparative analyses of ecosystem coverage, preliminary carbon-cycle synthesis, educational demonstrations of eddy covariance workflows, and future integration into a public-facing project website. Because the outputs are already organized into reusable tables and an embeddable HTML map, the project is also well positioned for extension into GitHub Pages, Jupyter or Colab notebooks, and follow-up analyses centered on carbon, water, and energy flux comparisons.

The same framework can also serve as a starting point for a broader southern South America flux observatory index, especially if later versions incorporate additional official hubs, authenticated access flows, or more formal metadata harvesting from portal APIs. The emphasis on provenance, reproducibility, and explicit access logging is intended to make such extensions methodologically straightforward.

## References

[1]: https://github.com/fluxnet/shuttle "FLUXNET Shuttle Library"
[2]: https://www.icos-cp.eu/data-products "ICOS Main data products"
[3]: https://doi.org/10.1038/s41597-020-0534-3 "Pastorello et al. (2020) The FLUXNET2015 dataset and the ONEFlux processing pipeline for eddy covariance data"
[4]: https://ameriflux.lbl.gov/data/data-policy/ "AmeriFlux Data Policy"
[5]: data/raw/CL-SDF/DATA_POLICY_LICENSE_AND_INSTRUCTIONS.txt "FLUXNET data policy, license, and attribution instructions bundled with the downloaded CL-SDF FLUXNET archive"
[6]: https://doi.org/10.17190/AMF/2469434 "AmeriFlux FLUXNET-1F AR-CCg Carlos Casares grassland"
[7]: https://doi.org/10.17190/AMF/1818370 "AmeriFlux FLUXNET-1F AR-TF1 Rio Moat bog"
[8]: https://doi.org/10.17190/AMF/2571120 "AmeriFlux FLUXNET-1F AR-TF2 Rio Pipo bog"
[9]: https://doi.org/10.17190/AMF/2571129 "AmeriFlux FLUXNET-1F CL-ACF Alerce Costero Forest"
[10]: https://doi.org/10.17190/AMF/2469441 "AmeriFlux FLUXNET-1F CL-SDF Senda Darwin Forest"
[11]: https://doi.org/10.17190/AMF/2571108 "AmeriFlux FLUXNET-1F CL-SDP Senda Darwin Peatland"
