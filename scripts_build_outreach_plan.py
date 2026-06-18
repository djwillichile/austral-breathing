"""Phase-2 data-request outreach planner for South American EC CO2-flux towers.

Phase 1 inventoried 60 CO2-flux towers and harvested the **open** (tier-1) ones.
The remaining **restricted-access** towers — 25 tier-2 (published but not
archived) and 7 tier-3 (national / private) — can only be obtained by contacting
the operator or principal investigator. This module turns the curated registry
(``research/south_america_flux_towers.csv``) into the operational artifacts for
that outreach campaign:

    * ``outputs/tables/phase2_outreach_contacts.csv`` — one contact sheet per
      tower: parsed institution / PI, derived contact route, request scope and
      priority. Pure derived data; regenerated every run.
    * ``outputs/tables/phase2_outreach_tracker.csv`` — a follow-up tracker
      seeded with one ``pendiente`` row per tower (status, dates, response,
      agreement, owner, notes). **Created once and never overwritten** unless
      ``--force`` is given, so manual progress is preserved across regenerations.
    * ``research/phase2_outreach_plan.md`` — the human-facing plan: methodology,
      prioritisation, a bilingual (ES/EN) request-email template, and the
      prioritised per-tower table.

The ``institution_pi`` column is free-form (``"Institution / PI"``,
``"Institution"``, ``"unknown"``, collaborations, …). ``parse_institution_pi``
extracts a best-effort institution and PI name with a conservative heuristic and
flags ``pi_known``; the raw value is always preserved so nothing is lost.

Pure-stdlib and fully offline — runs in restricted sandboxes and in CI.

Usage
-----
    python scripts_build_outreach_plan.py            # contacts + plan (+ seed tracker if absent)
    python scripts_build_outreach_plan.py --force    # also reseed the tracker (discards manual edits)
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt

from pipeline_paths import OUTPUTS_TABLES_DIR, RESEARCH_DIR
from pipeline_registry import outreach_co2_flux_towers

CONTACTS_CSV = OUTPUTS_TABLES_DIR / "phase2_outreach_contacts.csv"
TRACKER_CSV = OUTPUTS_TABLES_DIR / "phase2_outreach_tracker.csv"
PLAN_MD = RESEARCH_DIR / "phase2_outreach_plan.md"

# Tokens that mark a free-form ``institution_pi`` segment as an *organisation*
# rather than a person, so it is not mistaken for a PI name. Matched as
# case-insensitive substrings.
INSTITUTION_TOKENS = (
    "universi", "instituto", "institut", "u. de", "u. ", "school", "laborator",
    "national lab", "corporation", "corporación", "embrapa", "ciat", "cenipalma",
    "agrosavia", "rothamsted", "agricompas", "conicet", "inta", "inpa", "inpe",
    "iiap", "inia", "unal", "pucp", "puc", "usb", "ivic", "epn", "epmaps",
    "fonag", "mpi", "bgc", "bayceer", "cirad", "inrae", "ecofog", "ufsm",
    "ufmt", "unic", "marburg", "penn state", "collaboration", "universities",
    "consortium", "lba", "ictua",
)

# Person-name hints that override an institution token when both are present
# (rare; the heuristic keeps the raw field regardless).


def _looks_like_person(segment: str) -> bool:
    seg = segment.strip().lower()
    if not seg or seg == "unknown":
        return False
    return not any(tok in seg for tok in INSTITUTION_TOKENS)


def parse_institution_pi(raw: str | None) -> tuple[str, str, bool]:
    """Best-effort split of a free-form ``institution_pi`` value.

    Returns ``(institution, pi_name, pi_known)``. The PI is taken from the last
    ``/``-delimited segment when it reads like a person (no organisation token);
    a trailing ``"PI + Org"`` segment is reduced to the person part. Everything
    is conservative: when in doubt, ``pi_known`` is ``False`` and ``pi_name`` is
    left empty rather than guessing.
    """
    raw = (raw or "").strip()
    if not raw or raw.lower() == "unknown":
        return "", "", False

    segments = [s.strip() for s in raw.split("/") if s.strip()]
    if not segments:
        return "", "", False

    last = segments[-1]
    # A trailing "Person + Organisation" collapses to the first person-like part.
    if "+" in last:
        for part in (p.strip() for p in last.split("+")):
            if _looks_like_person(part):
                pi = part
                institution = " / ".join(segments[:-1]) or raw
                return institution, pi, True
        # No person part in the last segment — treat whole thing as institution.
        return raw, "", False

    if _looks_like_person(last) and len(segments) >= 2:
        return " / ".join(segments[:-1]), last, True
    if _looks_like_person(last) and len(segments) == 1:
        # A lone person name with no institution context.
        return "", last, True
    return raw, "", False


def _contact_route(network: str, data_access: str, site_id: str) -> str:
    """Derive the recommended outreach channel from network + access note."""
    da = (data_access or "").lower()
    if "proprietary" in da or "consortium" in da:
        return "Solicitud formal al consorcio/empresa con acuerdo de uso de datos"
    if "operator" in da:
        return "Contacto al operador institucional que mantiene la torre"
    if network in ("AmeriFlux", "FLUXNET2015") and ("ameriflux registered" in da or "registered ameriflux" in da):
        return (f"AmeriFlux Team page del sitio (ameriflux.lbl.gov/sites/siteinfo/{site_id}) "
                "→ contacto del PI; cc datasupport@ameriflux.lbl.gov")
    return "Email al PI / autor de correspondencia vía institución (ver source_url)"


def _priority(tier: int, pi_known: bool) -> str:
    """P1 = tier-2 con PI identificado (más tratable); P2 = tier-2 sin PI;
    P3 = tier-3 (nacional/privado, requiere gestión institucional)."""
    if tier == 2 and pi_known:
        return "P1"
    if tier == 2:
        return "P2"
    return "P3"


def _request_scope(tower: dict) -> str:
    ys = tower.get("year_start")
    ye = tower.get("year_end")
    span = ""
    if ys:
        span = f" {ys}–{ye if ye else 'presente'}"
    return (f"NEE/GPP/Reco nivel-2 (half-hourly o diario){span}; metadatos BADM; "
            f"términos de co-autoría/cita según política del sitio")


def build_contacts() -> list[dict]:
    """One enriched contact row per restricted-access (tier 2/3) CO2 tower."""
    rows: list[dict] = []
    for t in outreach_co2_flux_towers():
        tier = t.get("availability_tier")
        institution, pi_name, pi_known = parse_institution_pi(t.get("institution_pi"))
        rows.append(
            {
                "site_id": t["site_id"],
                "country": t["country"],
                "site_name": t["site_name"],
                "biome": t.get("biome") or "",
                "network": t.get("network") or "none",
                "availability_tier": tier,
                "priority": _priority(tier, pi_known),
                "institution": institution,
                "pi_name": pi_name,
                "pi_known": "yes" if pi_known else "no",
                "institution_pi_raw": t.get("institution_pi") or "",
                "data_access": t.get("data_access") or "",
                "contact_route": _contact_route(t.get("network") or "", t.get("data_access") or "", t["site_id"]),
                "request_scope": _request_scope(t),
                "source_url": t.get("source_url") or "",
            }
        )
    # Deterministic order: priority, then country, then site_id.
    rows.sort(key=lambda r: (r["priority"], r["country"], r["site_id"]))
    return rows


CONTACT_FIELDS = [
    "site_id", "country", "site_name", "biome", "network", "availability_tier",
    "priority", "institution", "pi_name", "pi_known", "institution_pi_raw",
    "data_access", "contact_route", "request_scope", "source_url",
]

TRACKER_FIELDS = [
    "site_id", "country", "site_name", "priority", "pi_name", "contact_route",
    "status", "first_contacted", "last_contacted", "response_status",
    "data_shared", "agreement", "followup_due", "owner", "notes",
]

# Controlled vocabulary documented in the tracker / plan.
TRACKER_STATUS_VOCAB = (
    "pendiente", "contactado", "en_conversacion", "datos_comprometidos",
    "datos_recibidos", "rechazado", "sin_respuesta",
)


def write_contacts(rows: list[dict]) -> None:
    OUTPUTS_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with CONTACTS_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CONTACT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote contact sheet: {CONTACTS_CSV} ({len(rows)} tier-2/3 towers)")


def write_tracker(rows: list[dict], force: bool = False) -> bool:
    """Seed the follow-up tracker. Skips an existing file unless ``force`` so
    manual progress is never clobbered by a regeneration. Returns True if written."""
    OUTPUTS_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    if TRACKER_CSV.exists() and not force:
        print(f"Tracker exists, preserving manual edits: {TRACKER_CSV} (use --force to reseed)")
        return False
    with TRACKER_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=TRACKER_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "site_id": r["site_id"],
                    "country": r["country"],
                    "site_name": r["site_name"],
                    "priority": r["priority"],
                    "pi_name": r["pi_name"],
                    "contact_route": r["contact_route"],
                    "status": "pendiente",
                    "first_contacted": "",
                    "last_contacted": "",
                    "response_status": "",
                    "data_shared": "",
                    "agreement": "",
                    "followup_due": "",
                    "owner": "",
                    "notes": "",
                }
            )
    print(f"Seeded follow-up tracker: {TRACKER_CSV} ({len(rows)} rows, status=pendiente)")
    return True


EMAIL_TEMPLATE_ES = """\
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
"""

EMAIL_TEMPLATE_EN = """\
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
"""


def build_plan_markdown(rows: list[dict]) -> str:
    today = _dt.date.today().isoformat()
    n2 = sum(1 for r in rows if r["availability_tier"] == 2)
    n3 = sum(1 for r in rows if r["availability_tier"] == 3)
    by_prio = {p: sum(1 for r in rows if r["priority"] == p) for p in ("P1", "P2", "P3")}

    lines: list[str] = []
    lines.append("# Fase 2 — Plan de solicitud de datos (outreach a PIs)")
    lines.append("")
    lines.append(f"_Proyecto: Austral Breathing · generado: {today} · "
                 f"fuente: `research/south_america_flux_towers.csv`_")
    lines.append("")
    lines.append("> **Documento derivado.** Regenerar con "
                 "`python scripts_build_outreach_plan.py`. La tabla de contactos "
                 "(`outputs/tables/phase2_outreach_contacts.csv`) y este plan se "
                 "reescriben en cada corrida; el tracker "
                 "(`outputs/tables/phase2_outreach_tracker.csv`) se siembra una "
                 "sola vez y conserva el avance manual.")
    lines.append("")
    lines.append("## Alcance")
    lines.append("")
    lines.append(f"- **{len(rows)} torres** de acceso restringido que miden CO₂: "
                 f"**{n2} tier-2** (publicadas, no archivadas) + **{n3} tier-3** "
                 f"(nacional/privado).")
    lines.append(f"- Prioridades: **{by_prio['P1']} P1**, **{by_prio['P2']} P2**, "
                 f"**{by_prio['P3']} P3**.")
    lines.append("- Las torres tier-1 (abiertas/archivadas) NO entran aquí: se "
                 "obtienen con `scripts_harvest_open_flux_data.py`.")
    lines.append("")
    lines.append("## Priorización")
    lines.append("")
    lines.append("| Prioridad | Criterio | Racional |")
    lines.append("|---|---|---|")
    lines.append("| **P1** | tier-2 con PI identificado | Dato existe y publicado; "
                 "contacto directo → mayor probabilidad de respuesta. |")
    lines.append("| **P2** | tier-2 sin PI identificado | Hay que rastrear al "
                 "contacto (autor de correspondencia / página AmeriFlux). |")
    lines.append("| **P3** | tier-3 (nacional/privado) | Requiere gestión "
                 "institucional o acuerdo de uso de datos; ciclo más largo. |")
    lines.append("")
    lines.append("## Estados del tracker")
    lines.append("")
    lines.append("`" + "` · `".join(TRACKER_STATUS_VOCAB) + "`")
    lines.append("")
    lines.append("## Plantilla de correo (ES)")
    lines.append("")
    lines.append("```text")
    lines.append(EMAIL_TEMPLATE_ES.rstrip())
    lines.append("```")
    lines.append("")
    lines.append("Marcadores: `{site_id}`, `{site_name}`, `{biome}`, `{country}`, "
                 "`{pi_or_team}` (nombre del PI o «equipo del sitio»), "
                 "`{request_scope}` (columna del CSV de contactos).")
    lines.append("")
    lines.append("## Plantilla de correo (EN)")
    lines.append("")
    lines.append("```text")
    lines.append(EMAIL_TEMPLATE_EN.rstrip())
    lines.append("```")
    lines.append("")
    lines.append("## Torres a contactar (ordenadas por prioridad)")
    lines.append("")
    lines.append("| Prio | site_id | País | Sitio | Tier | Institución | PI | Ruta de contacto |")
    lines.append("|---|---|---|---|:--:|---|---|---|")
    for r in rows:
        pi = r["pi_name"] or "_(por identificar)_"
        inst = r["institution"] or "_(ver fuente)_"
        lines.append(
            f"| {r['priority']} | `{r['site_id']}` | {r['country']} | "
            f"{r['site_name']} | {r['availability_tier']} | {inst} | {pi} | "
            f"{r['contact_route']} |"
        )
    lines.append("")
    lines.append("## Nota: representatividad climática")
    lines.append("")
    lines.append("La representatividad climática real "
                 "(`client/public/data/representativeness_grid.json`) requiere los "
                 "rasters WorldClim 2.1 desde `geodata.ucdavis.edu`. Ese host está "
                 "bloqueado por egress en el entorno de desarrollo (HTTP 403 "
                 "`host_not_allowed`), por lo que el cálculo se delega al workflow "
                 "`.github/workflows/representativeness.yml`: corre en un runner de "
                 "Actions (internet abierto), descarga WorldClim (5m por defecto), "
                 "ejecuta el análisis continental "
                 "(`--region south-america --stations registry`) y commitea solo el "
                 "grid JSON (los `.tif` no se versionan). También puede correrse local "
                 "con egress habilitado o precargando `wc2.1_*_bio_*.tif` en "
                 "`data/climate/`.")
    lines.append("")
    return "\n".join(lines)


def write_plan(rows: list[dict]) -> None:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_MD.write_text(build_plan_markdown(rows), encoding="utf-8")
    print(f"Wrote outreach plan: {PLAN_MD}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="reseed the tracker even if it exists (discards manual edits)")
    args = parser.parse_args(argv)

    rows = build_contacts()
    write_contacts(rows)
    write_tracker(rows, force=args.force)
    write_plan(rows)

    by_prio = {p: sum(1 for r in rows if r["priority"] == p) for p in ("P1", "P2", "P3")}
    print(f"\nPhase-2 outreach set: {len(rows)} towers "
          f"(P1={by_prio['P1']}, P2={by_prio['P2']}, P3={by_prio['P3']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
