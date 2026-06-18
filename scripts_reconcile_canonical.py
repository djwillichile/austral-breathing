#!/usr/bin/env python3
"""Reconcile the South American flux-tower registry against the canonical
AmeriFlux metadata fetched by the GitHub Actions runner into research/_canonical/
(ameriflux_site_display.json, avail_site_availability.json, siteinfo/*.html).

What it does, deterministically and idempotently:
  1. Loads the 17-column registry CSV, preserving the leading comment block.
  2. For rows whose code (case-insensitive, after a few known renames) matches
     an AmeriFlux South American site, overwrites lat/lon with the canonical
     value, marks ``coord_note=verified`` and fills blank ``igbp`` /
     ``year_start`` / ``year_end`` from the canonical record.
  3. Applies three code renames where the registry used a non-canonical id:
        BR-FNS -> BR-Ji1   (Fazenda Nossa Senhora)
        BR-Ji2 -> BR-Ji3   (Reserva Biologica do Jaru)
        BR-CAX -> BR-Cax   (Caxiuana micromet tower)
  4. Appends AmeriFlux SA sites that are absent from the registry as new
     ``measures_co2=yes`` rows (AmeriFlux towers measure CO2 by design).
  5. Enriches the appended sites (+ BR-CST) from the data-availability snapshot
     (open BASE/FLUXNET product -> availability_tier=1) and from the per-site
     siteinfo HTML (PI name + institution).

Run from repo root:  python3 scripts_reconcile_canonical.py
"""
from __future__ import annotations
import csv, io, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(ROOT, "research", "south_america_flux_towers.csv")
CANON = os.path.join(ROOT, "research", "_canonical")
AMF = os.path.join(CANON, "ameriflux_site_display.json")
AVAIL = os.path.join(CANON, "avail_site_availability.json")
SITEINFO = os.path.join(CANON, "siteinfo")

COLS = ["site_id","country","site_name","lat","lon","biome","igbp","network",
        "year_start","year_end","measures_co2","availability_tier","data_access",
        "institution_pi","confidence","coord_note","source_url"]

SA_PREFIX = ("AR-","BR-","CL-","PE-","EC-","CO-","VE-","BO-","UY-","PY-","GF-","SR-","GY-")

# registry code -> canonical AmeriFlux code
RENAMES = {"BR-FNS": "BR-Ji1", "BR-JI2": "BR-Ji3", "BR-CAX": "BR-Cax"}

IGBP_BIOME = {
    "EBF": "Evergreen Broadleaf Forest", "DBF": "Deciduous Broadleaf Forest",
    "ENF": "Evergreen Needleleaf Forest", "CRO": "Cropland", "GRA": "Grassland",
    "WET": "Wetland", "WSA": "Woody savanna", "SAV": "Savanna",
    "OSH": "Open shrubland", "CSH": "Closed shrubland",
    "CVM": "Cropland / natural-vegetation mosaic", "MF": "Mixed forest",
}

# Curated human-readable names / biomes for the new sites (override the very
# long AmeriFlux SITE_NAME strings where helpful). Keyed by canonical code.
NEW_META = {
    "BR-BNT": ("BIONTE Manaus terra-firme forest", "Evergreen Broadleaf Forest"),
    "BR-CMT": ("Capuaba farm cropland (Mato Grosso)", "Cropland"),
    "BR-CUP": ("Cupari, Tapajos National Forest", "Deciduous Broadleaf Forest"),
    "BR-Cui": ("Braganca Amazonian mangrove", "Mangrove wetland"),
    "BR-IAB": ("Instituto Arruda Botelho wooded cerrado", "Woody savanna (cerrado)"),
    "BR-ITA": ("MataFLUX tree-restoration planting", "Restoration broadleaf forest"),
    "BR-Ma3": ("Manaus ZF3 Colosso farm", "Cropland / natural mosaic"),
    "BR-Moj": ("Moju oil-palm plantation (PA)", "Oil-palm plantation"),
    "BR-PRS": ("Paraiso do Sul cropland", "Cropland"),
    "BR-SGC": ("Sao Gabriel da Cachoeira (Pico da Neblina)", "Evergreen Broadleaf Forest"),
    "BR-SM1": ("Cachoeira do Sul rice paddy", "Cropland (rice)"),
    "BR-SM2": ("Pedras Altas grassland", "Grassland"),
    "BR-SM3": ("Santa Maria grassland", "Grassland"),
    "BR-SP1": ("Southern Pantanal Wetland", "Wetland / flooded savanna"),
    "BR-Xpw": ("XomanoFlux northern Pantanal", "Grassland / wetland"),
    "CL-FJS": ("Fray Jorge shrubland", "Open shrubland (semi-arid)"),
    "CL-OPP": ("Omora Park Peatland (Cape Horn)", "Wetland (sub-Antarctic peatland)"),
    "CO-GV2": ("Guatavita Station 2", "Wetland (high-Andean)"),
    "PE-IGP": ("Huancayo Geophysical Observatory (IGP)", "Grassland (high-Andean)"),
}
# canonical codes that correspond to EXISTING registry rows (renames) and so
# must NOT be appended as new rows.
RENAME_TARGETS = set(RENAMES.values())
# rows eligible for availability/PI enrichment (curated rows are left untouched).
ENRICH_TARGETS = set(NEW_META) | {"BR-CST"}


def load_amf():
    data = json.load(open(AMF, encoding="utf-8"))
    out = {}
    for s in data:
        sid = str(s.get("SITE_ID", ""))
        if sid.startswith(SA_PREFIX):
            loc = s.get("GRP_LOCATION", {}) or {}
            out[sid] = {
                "lat": loc.get("LOCATION_LAT", ""),
                "lon": loc.get("LOCATION_LONG", ""),
                "igbp": s.get("IGBP", "") or "",
                "y0": s.get("TOWER_BEGAN", "") or "",
                "y1": s.get("TOWER_END", "") or "",
                "url": s.get("URL_AMERIFLUX", "") or "",
                "country": s.get("COUNTRY", "") or "",
            }
    return out


def load_open_sets():
    """Return (open_codes, flux_codes) from the AmeriFlux data-availability
    snapshot. A site is 'open' if it exposes a downloadable BASE-BADM product
    (CC-BY-4.0 or LEGACY policy) or a FLUXNET product."""
    open_codes, flux_codes = set(), set()
    if not os.path.exists(AVAIL):
        return open_codes, flux_codes
    av = json.load(open(AVAIL, encoding="utf-8"))

    def codes(section):
        out = set()
        sec = av.get(section, {})
        lists = sec.values() if isinstance(sec, dict) else [sec]
        for lst in lists:
            for it in lst or []:
                out.add(it[0] if isinstance(it, list) else it)
        return out

    flux_codes = codes("FLUXNET")
    open_codes = codes("BASE-BADM") | flux_codes
    return open_codes, flux_codes


def parse_pi(codes):
    """Extract '(name, institution)' for each code from its committed AmeriFlux
    siteinfo HTML snapshot (mailto anchor + email stripped)."""
    out = {}
    for sid in codes:
        p = os.path.join(SITEINFO, f"{sid}.html")
        if not os.path.exists(p):
            continue
        html = open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r'class="team"><td>PI:\s*</td><td>(.*?)</td>', html, re.S)
        if not m:
            continue
        raw = re.sub(r"<[^>]+>", "", m.group(1))      # drop the mailto anchor
        raw = re.sub(r"\S+@\S+", "", raw)             # drop the email address
        raw = re.sub(r"\s+", " ", raw).strip(" -")
        if " - " in raw:
            name, inst = (x.strip() for x in raw.rsplit(" - ", 1))
        else:
            name, inst = raw.strip(), ""
        if name:
            out[sid] = (name, inst)
    return out


def main():
    amf = load_amf()
    amf_upper = {k.upper(): k for k in amf}

    # read file, split comment header from data
    header_lines, data_lines = [], []
    with open(CSV, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("site_id,"):
                header_lines.append(line.rstrip("\n"))
            elif line.strip():
                data_lines.append(line.rstrip("\n"))

    rows = list(csv.DictReader(data_lines, fieldnames=COLS))

    present_upper = set()
    n_coord, n_fill, n_rename = 0, 0, 0
    for r in rows:
        sid = r["site_id"]
        canon = RENAMES.get(sid.upper())
        if canon:
            r["site_id"] = canon
            sid = canon
            n_rename += 1
        present_upper.add(sid.upper())
        key = amf_upper.get(sid.upper())
        if not key:
            continue
        a = amf[key]
        # normalise code casing to canonical
        r["site_id"] = key
        if a["lat"] and a["lon"]:
            r["lat"], r["lon"] = a["lat"], a["lon"]
            if r["coord_note"] != "verified":
                n_coord += 1
            r["coord_note"] = "verified"
        if not r["igbp"] and a["igbp"]:
            r["igbp"] = a["igbp"]; n_fill += 1
        if not r["year_start"] and a["y0"]:
            r["year_start"] = a["y0"]
        if not r["year_end"] and a["y1"]:
            r["year_end"] = a["y1"]

    # append new sites
    n_new = 0
    for sid, a in sorted(amf.items()):
        if sid.upper() in present_upper or sid in RENAME_TARGETS:
            continue
        name, biome = NEW_META.get(sid, (sid, IGBP_BIOME.get(a["igbp"], "")))
        rows.append({
            "site_id": sid, "country": a["country"], "site_name": name,
            "lat": a["lat"], "lon": a["lon"], "biome": biome, "igbp": a["igbp"],
            "network": "AmeriFlux", "year_start": a["y0"], "year_end": a["y1"],
            "measures_co2": "yes", "availability_tier": "2",
            "data_access": "AmeriFlux registered; per-site BASE availability to verify",
            "institution_pi": "see AmeriFlux site page", "confidence": "high",
            "coord_note": "verified", "source_url": a["url"],
        })
        present_upper.add(sid.upper())
        n_new += 1

    # enrichment: data availability (tier/access) + PI metadata, from canonical
    # snapshots. Targeted to ENRICH_TARGETS so curated rows are not clobbered.
    open_codes, flux_codes = load_open_sets()
    pi_map = parse_pi(set(NEW_META))
    n_pi, n_open, n_closed = 0, 0, 0
    for r in rows:
        sid = r["site_id"]
        if sid in pi_map:
            name, inst = pi_map[sid]
            r["institution_pi"] = f"{inst} / {name}" if inst else name
            n_pi += 1
        if sid in ENRICH_TARGETS:
            if sid in open_codes:
                r["availability_tier"] = "1"
                r["data_access"] = ("AmeriFlux BASE + FLUXNET (CC-BY-4.0)"
                                    if sid in flux_codes else
                                    "AmeriFlux BASE (CC-BY-4.0)")
                n_open += 1
            else:
                r["data_access"] = ("AmeriFlux registered; no open BASE/FLUXNET "
                                    "product yet (request PI)")
                n_closed += 1

    # write back
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n")
    for r in rows:
        w.writerow(r)
    with open(CSV, "w", encoding="utf-8") as f:
        f.write("\n".join(header_lines) + "\n" + buf.getvalue())

    print(f"renames applied      : {n_rename}")
    print(f"coords -> verified   : {n_coord}")
    print(f"blank igbp/years fill: {n_fill}")
    print(f"new sites appended   : {n_new}")
    print(f"PI enriched          : {n_pi}")
    print(f"upgraded to open(T1) : {n_open}")
    print(f"kept closed (T2)     : {n_closed}")
    print(f"total rows           : {len(rows)}")


if __name__ == "__main__":
    main()
