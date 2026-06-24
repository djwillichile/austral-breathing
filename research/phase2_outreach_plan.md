# Fase 2 — Plan de solicitud de datos (outreach a PIs)

_Proyecto: Austral Breathing · generado: 2026-06-18 · fuente: `research/south_america_flux_towers.csv`_

> **Documento derivado.** Regenerar con `python scripts_build_outreach_plan.py`. La tabla de contactos (`outputs/tables/phase2_outreach_contacts.csv`) y este plan se reescriben en cada corrida; el tracker (`outputs/tables/phase2_outreach_tracker.csv`) se siembra una sola vez y conserva el avance manual.

## Alcance

- **32 torres** de acceso restringido que miden CO₂: **25 tier-2** (publicadas, no archivadas) + **7 tier-3** (nacional/privado).
- Prioridades: **19 P1**, **6 P2**, **7 P3**.
- Las torres tier-1 (abiertas/archivadas) NO entran aquí: se obtienen con `scripts_harvest_open_flux_data.py`.

## Priorización

| Prioridad | Criterio | Racional |
|---|---|---|
| **P1** | tier-2 con PI identificado | Dato existe y publicado; contacto directo → mayor probabilidad de respuesta. |
| **P2** | tier-2 sin PI identificado | Hay que rastrear al contacto (autor de correspondencia / página AmeriFlux). |
| **P3** | tier-3 (nacional/privado) | Requiere gestión institucional o acuerdo de uso de datos; ciclo más largo. |

## Estados del tracker

`pendiente` · `contactado` · `en_conversacion` · `datos_comprometidos` · `datos_recibidos` · `rechazado` · `sin_respuesta`

## Plantilla de correo (ES)

```text
Asunto: Solicitud de datos de flujo de CO₂ — torre {site_id} ({site_name})

Estimado/a {pi_or_team}:

Le escribo desde el Instituto de Ciencias y Tecnología Ambiental (ICTA Ltda.),
en el marco del proyecto *Austral Breathing — Atlas de Carbono de Sudamérica*,
un inventario reproducible de infraestructura de observación de carbono (torres
de covarianza de remolinos y programas de stock) en Sudamérica.

Identificamos su torre **{site_name}** ({site_id}, {biome}, {country}) como un
sitio clave para cerrar las brechas de representatividad climática del
continente. Quisiéramos consultar la posibilidad de acceder a:

    {request_scope}

Respetaremos íntegramente sus condiciones de uso, licenciamiento, cita por sitio
y normas de co-autoría. Con gusto compartimos el protocolo de estandarización del
proyecto y coordinamos la forma de reconocimiento que usted prefiera.

Agradezco de antemano su tiempo y quedo atento/a a su respuesta.

Cordialmente,
Guillermo S. Fuentes-Jaque — Consultor principal, ICTA Ltda.
```

Marcadores: `{site_id}`, `{site_name}`, `{biome}`, `{country}`, `{pi_or_team}` (nombre del PI o «equipo del sitio»), `{request_scope}` (columna del CSV de contactos).

## Plantilla de correo (EN)

```text
Subject: Request for CO₂ flux data — {site_id} ({site_name}) tower

Dear {pi_or_team},

I am writing from the Institute of Environmental Science and Technology
(ICTA Ltda.), as part of *Austral Breathing — A Carbon Atlas of South America*,
a reproducible inventory of carbon-observation infrastructure (eddy-covariance
towers and carbon-stock programs) across South America.

We identified your **{site_name}** tower ({site_id}, {biome}, {country}) as a key
site for closing the continent's climate-representativeness gaps. We would like to
ask about the possibility of accessing:

    {request_scope}

We will fully respect your data-use terms, licensing, per-site citation and
co-authorship norms. We are happy to share the project's standardisation protocol
and to arrange whatever form of acknowledgement you prefer.

Thank you for your time; I look forward to your reply.

Best regards,
Guillermo S. Fuentes-Jaque — Principal consultant, ICTA Ltda.
```

## Torres a contactar (ordenadas por prioridad)

| Prio | site_id | País | Sitio | Tier | Institución | PI | Ruta de contacto |
|---|---|---|---|:--:|---|---|---|
| P1 | `BR-BNT` | Brazil | BIONTE Manaus terra-firme forest | 2 | Lawrence Berkeley National Laboratory | Negron-Juarez Robinson | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-BNT) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-CMT` | Brazil | Capuaba farm cropland (Mato Grosso) | 2 | University of British Columbia | Mark Johnson | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-CMT) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-CUP` | Brazil | Cupari, Tapajos National Forest | 2 | University of Arizona | Scott Saleska | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-CUP) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-Cui` | Brazil | Braganca Amazonian mangrove | 2 | LBA | Isabel Vitorino | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-Cui) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-IAB` | Brazil | Instituto Arruda Botelho wooded cerrado | 2 | São Carlos School of Engineering, University of São Paulo | Edson Wendland | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-IAB) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-Moj` | Brazil | Moju oil-palm plantation (PA) | 2 | Brazilian Agricultural Research Corporation (Embrapa Eastern Amazon) | Alessandro Araujo | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-Moj) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-PRS` | Brazil | Paraiso do Sul cropland | 2 | Universidade Federal de Santa Maria (UFSM) | Débora Roberti | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-PRS) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-SGC` | Brazil | Sao Gabriel da Cachoeira (Pico da Neblina) | 2 | Brazilian Agricultural Research Corporation (Embrapa Eastern Amazon) | Alessandro Araujo | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-SGC) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-SM2` | Brazil | Pedras Altas grassland | 2 | Universidade Federal de Santa Maria | Debora Regina Roberti | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-SM2) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-SM3` | Brazil | Santa Maria grassland | 2 | Universidade Federal de Santa Maria | Debora Regina Roberti | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-SM3) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `BR-SP1` | Brazil | Southern Pantanal Wetland | 2 | Universidade Federal de Mato Grosso do Sul | Thiago Rangel Rodrigues | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/BR-SP1) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `CL-FJS` | Chile | Fray Jorge shrubland | 2 | University of La Serena | Alejandra Troncoso | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/CL-FJS) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `CL-OPP` | Chile | Omora Park Peatland (Cape Horn) | 2 | University of Chile | Jorge Perez-Quezada | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/CL-OPP) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `CL-Poqui` | Chile | Cerro Poqui (Nothofagus mediterranean) | 2 | U. de Chile | Perez-Quezada | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P1 | `CO-Carimagua` | Colombia | Carimagua/Taluma Orinoco savanna | 2 | UNAL | Jimenez | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P1 | `CO-GV2` | Colombia | Guatavita Station 2 | 2 | Pontificia Universidad Javeriana | Juan C. Benavides | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/CO-GV2) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `EC-Zhu` | Ecuador | Zhurucay paramo | 2 | U. de Cuenca | Carrillo-Rojas-Crespo | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P1 | `PE-IGP` | Peru | Huancayo Geophysical Observatory (IGP) | 2 | Instituto Geofísico del Perú | Jose Flores-Rojas | AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/PE-IGP) → contacto del PI; cc datasupport@ameriflux.lbl.gov |
| P1 | `PE-TNR` | Peru | Tambopata ECOTOWER | 2 | PUCP | Cosio | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P2 | `AR-RioMayo` | Argentina | Rio Mayo Patagonian steppe | 2 | INTA Rio Mayo | _(por identificar)_ | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P2 | `BR-ATTO` | Brazil | Amazon Tall Tower Observatory | 2 | INPA + MPI-BGC | _(por identificar)_ | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P2 | `CO-Potato` | Colombia | Subachoque high-Andean potato | 2 | UNAL | _(por identificar)_ | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P2 | `EC-Laipuna` | Ecuador | Laipuna dry forest | 2 | U. Marburg + Ecuadorian universities | _(por identificar)_ | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P2 | `EC-SanFrancisco` | Ecuador | RBSF / ECSF montane cloud forest | 2 | U. de Cuenca + U. Marburg | _(por identificar)_ | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P2 | `GF-Nouragues` | French Guiana | Nouragues (Nourflux) | 2 | INRAE / EcoFoG | _(por identificar)_ | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P3 | `CL-AcaciaSav` | Chile | Central Chile Acacia caven savanna | 3 | U. de Chile | Perez-Quezada | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P3 | `CO-Cenipalma` | Colombia | Cenipalma/CIAT oil palm | 3 | Cenipalma + CIAT | _(por identificar)_ | Solicitud formal al consorcio/empresa con acuerdo de uso de datos |
| P3 | `CO-EcoProMIS` | Colombia | EcoProMIS rice & oil-palm towers (x4) | 3 | Rothamsted + Agricompas + CIAT | _(por identificar)_ | Solicitud formal al consorcio/empresa con acuerdo de uso de datos |
| P3 | `EC-Antisana` | Ecuador | Antisana FTEC | 3 | EPN + EPMAPS/FONAG | _(por identificar)_ | Contacto al operador institucional que mantiene la torre |
| P3 | `PE-AMG` | Peru | Los Amigos (CICRA) | 3 | PUCP | _(por identificar)_ | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P3 | `PE-BRE` | Peru | El Breo | 3 | PUCP | _(por identificar)_ | Email al PI / autor de correspondencia vía institución (ver source_url) |
| P3 | `PE-PAN` | Peru | Panguana | 3 | PUCP / BayCEER | _(por identificar)_ | Email al PI / autor de correspondencia vía institución (ver source_url) |

## Nota: representatividad climática

La representatividad climática real (`client/public/data/representativeness_grid.json`) requiere los rasters WorldClim 2.1 desde `geodata.ucdavis.edu`. Ese host está bloqueado por egress en el entorno de desarrollo (HTTP 403 `host_not_allowed`), por lo que el cálculo se delega al workflow `.github/workflows/representativeness.yml`: corre en un runner de Actions (internet abierto), descarga WorldClim (5m por defecto), ejecuta el análisis continental (`--region south-america --stations registry`) y commitea solo el grid JSON (los `.tif` no se versionan). También puede correrse local con egress habilitado o precargando `wc2.1_*_bio_*.tif` en `data/climate/`.
