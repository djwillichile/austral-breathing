# Fase 2 — Plataformas y cuentas de acceso a datos

_Proyecto: Austral Breathing · guía operativa de credenciales para acceder a los
datos de **torres de flujo** (`research/south_america_flux_towers.csv`) y
**programas de stock de carbono** (`research/south_america_carbon_stock_programs.csv`)._

Este documento responde a una pregunta práctica de la Fase 2: **¿qué cuentas hay
que crear para obtener los datos?** El acceso se reparte entre varias
plataformas, cada una con su propio tipo de credencial. La buena noticia: en la
práctica bastan **2 cuentas imprescindibles** (ambas gratuitas) para destrabar la
mayor parte, más unas pocas recomendadas. Todo el resto es descarga abierta o
gestión por correo (el outreach a PIs, cubierto por `phase2_outreach_plan.md`).

---

## Resumen ejecutivo — cuentas a crear

| # | Cuenta | Costo | Qué destraba | Registro |
|:--:|---|---|---|---|
| 1 | **AmeriFlux** | Gratis | 36 torres (tier-1 abiertas + tier-2 registradas) | <https://ameriflux.lbl.gov> → *Sign Up*; aceptar la *Data Policy* |
| 2 | **NASA Earthdata Login** | Gratis | 8 torres LBA (ORNL DAAC) **+** stock GEDI L4A y LiDAR Brasil | <https://urs.earthdata.nasa.gov/users/new> |
| 3 | **ForestPlots.net** | Gratis (con solicitud) | Biomasa de plots amazónicos: RAINFOR, GEM | <https://forestplots.net> → *Register*, luego solicitar acceso al PI |
| 4 | **ICOS Carbon Portal** | Gratis (registro ligero) | 1 torre abierta CC-BY (GF-Guy, Guyaflux) | <https://cpauth.icos-cp.eu> |
| 5 | **ATTO data portal** | Gratis (registro) | 1 torre (BR-ATTO) | <https://www.attoproject.org> → *Data* |

> **Una sola cuenta de NASA Earthdata** sirve a la vez para las torres LBA y para
> los productos de stock alojados en ORNL DAAC (GEDI, LiDAR Brasil): es la
> credencial de mejor relación cobertura/esfuerzo después de AmeriFlux.

---

## A. Torres de flujo (60 torres CO₂) por vía de acceso

| Plataforma | N.º torres | Credencial | Licencia / uso |
|---|:--:|---|---|
| **AmeriFlux** | 36 | Cuenta gratuita + aceptar *Data Policy* | AmeriFlux Data Policy; cita por sitio (DOI). Productos FLUXNET con **CC-BY-4.0** |
| **Contacto directo al PI** | 14 | Sin cuenta — correo al PI/operador | Acuerdo bilateral; co-autoría/cita según el PI (ver tracker) |
| **NASA Earthdata (ORNL DAAC)** | 8 | Earthdata Login gratuito | Datos LBA-ECO abiertos; citar dataset ORNL DAAC |
| **ICOS Carbon Portal** | 1 | Registro ligero | **CC-BY-4.0** |
| **ATTO portal** | 1 | Registro/solicitud | Términos del proyecto ATTO |

Notas:
- Las **14 «contacto directo al PI»** son torres tier-2/3 sin plataforma de
  descarga: su gestión es exactamente el outreach por correo de la Fase 2
  (`phase2_outreach_plan.md` + `phase2_outreach_tracker.csv`). **No requieren
  cuenta**, requieren gestión.
- La adquisición programática de AmeriFlux sigue la vía oficial `fluxnet-shuttle`
  / Data API; la cuenta es el único prerrequisito.

## B. Programas de stock de carbono (24 programas) por vía de acceso

| Plataforma / vía | N.º prog. | Credencial | Licencia / uso |
|---|:--:|---|---|
| **Portales nacionales / abiertos** | 11 | Normalmente sin cuenta (datos agregados); plots crudos por solicitud | Según portal (SNIF/BR, SNIFFS/PE, IDEAM-SIAC/CO, ENF/EC, INFONA/PY, PPBio…) |
| **Papers / acceso abierto** | 4 | Sin cuenta | Según revista (a menudo OA/CC-BY) |
| **ForestPlots.net** | 2–3 | Registro + solicitud al PI | **Normas de co-autoría** (RAINFOR/GEM); citar plots |
| **NASA Earthdata (ORNL DAAC)** | 2 | Earthdata Login | Abierto; citar dataset (GEDI L4A, LiDAR Brasil) |
| **ISRIC / CIRAD Dataverse** | 2 | Abierto (sin cuenta) | CC-BY (SoilGrids; Guyafor DOI) |
| **Consorcio (TmFO)** | 1 | Acceso gestionado por consorcio | Acuerdo de consorcio |

Notas:
- **ForestPlots.net** es la pieza más sensible: el dato existe pero su uso
  conlleva **co-autoría** con los responsables de los plots (RAINFOR, GEM). Hay
  que registrarse y solicitar acceso por proyecto, no descargar sin más.
- Los **portales nacionales** suelen ofrecer mapas/agregados abiertos; el dato de
  parcela crudo puede requerir una **solicitud formal** a la institución (INPE/SFB,
  SERFOR, IDEAM, MAE, INFONA, etc.).
- Abiertos sin fricción: **SoilGrids/ISRIC**, **SISLAC (FAO)**, **SISINTA (INTA)**,
  **mapa SOC Embrapa**, **CIRAD Dataverse (Guyafor)**.

---

## C. Plan de acción sugerido

1. **Crear cuenta AmeriFlux** y aceptar la Data Policy → habilita 36 torres vía
   `fluxnet-shuttle` / Data API. *(Mayor retorno inmediato.)*
2. **Crear cuenta NASA Earthdata** → habilita 8 torres LBA + GEDI L4A + LiDAR
   Brasil con una sola credencial.
3. **Registrarse en ForestPlots.net** e iniciar la solicitud de acceso para
   RAINFOR/GEM (asumiendo el compromiso de **co-autoría**).
4. **Registro ligero en ICOS** (CC-BY) y **ATTO** (1 torre cada uno) cuando se
   trabajen esos sitios.
5. **Sin cuenta**: descargar directamente los portales abiertos de suelo
   (ISRIC/SISLAC/SISINTA/Embrapa) y CIRAD Dataverse.
6. **Por correo (sin cuenta)**: las 14 torres «contacto al PI» y los stocks
   nacionales con dato crudo restringido → gestionar con el tracker de outreach.

## D. Obligaciones de atribución (resumen)

- **AmeriFlux / FLUXNET**: aceptar Data Policy; **cita por sitio** (DOI del sitio)
  y reconocimiento del PI; productos FLUXNET bajo **CC-BY-4.0**.
- **ICOS**: **CC-BY-4.0**, citar el producto/estación.
- **ORNL DAAC (LBA, GEDI, LiDAR Brasil)**: abiertos con Earthdata Login; **citar el
  dataset**.
- **ForestPlots.net / RAINFOR / GEM**: **co-autoría** y citación de plots según las
  normas de la red — no es solo «citar», implica involucrar a los responsables.
- **Portales nacionales**: respetar términos de cada portal y, para dato crudo,
  los acuerdos de la institución.

---

_Las URL de plataforma provienen de `source_url` en los dos CSV del registro; las
de registro de cuenta corresponden a las páginas oficiales de cada plataforma.
Todas las cuentas listadas son **gratuitas**. Conviene confirmar el enlace de
alta vigente al momento de registrarse._
