"""Export the South American carbon-observation registries for the web.

Reads the curated CSV registries and emits
``client/public/data/regional_inventory.json`` consumed by the React app's
"Regional inventory" tab: the EC CO2 flux towers and the carbon-stock programs,
plus summary counts by country, availability tier, and measurement type.
"""

from __future__ import annotations

import json

from pipeline_paths import CLIENT_PUBLIC_DATA_DIR
from pipeline_registry import load_flux_towers, load_stock_programs

# Countries with no confirmed open/published EC CO2 tower (documented gaps).
FLUX_GAP_COUNTRIES = ["Bolivia", "Paraguay", "Guyana", "Suriname"]


def _flux_payload() -> list[dict]:
    towers = []
    for t in load_flux_towers():
        towers.append(
            {
                "siteId": t["site_id"],
                "country": t["country"],
                "siteName": t["site_name"],
                "lat": t["lat"],
                "lon": t["lon"],
                "biome": t.get("biome") or "Unknown",
                "network": t.get("network") or "none",
                "yearStart": t["year_start"],
                "yearEnd": t["year_end"],
                "measuresCo2": t.get("measures_co2"),
                "tier": t["availability_tier"],
                "dataAccess": t.get("data_access"),
                "institution": t.get("institution_pi"),
                "confidence": t.get("confidence"),
                "sourceUrl": t.get("source_url"),
            }
        )
    return towers


def _stock_payload() -> list[dict]:
    return [
        {
            "program": p["program"],
            "stockType": p.get("stock_type"),
            "countries": p.get("countries"),
            "measures": p.get("measures"),
            "institution": p.get("institution"),
            "tier": p["availability_tier"],
            "dataAccess": p.get("data_access"),
            "confidence": p.get("confidence"),
            "sourceUrl": p.get("source_url"),
        }
        for p in load_stock_programs()
    ]


def _counts(flux: list[dict]) -> dict:
    co2 = [f for f in flux if f["measuresCo2"] == "yes"]
    by_country: dict[str, int] = {}
    for f in co2:
        by_country[f["country"]] = by_country.get(f["country"], 0) + 1
    by_tier = {str(t): len([f for f in co2 if f["tier"] == t]) for t in (1, 2, 3)}
    return {
        "fluxTowersCo2": len(co2),
        "fluxTowersOpen": len([f for f in co2 if f["tier"] == 1]),
        "byCountry": dict(sorted(by_country.items(), key=lambda kv: -kv[1])),
        "byTier": by_tier,
    }


def main() -> None:
    flux = _flux_payload()
    stock = _stock_payload()
    payload = {
        "fluxTowers": flux,
        "stockPrograms": stock,
        "fluxGapCountries": FLUX_GAP_COUNTRIES,
        "summary": {
            **_counts(flux),
            "stockPrograms": len(stock),
        },
    }
    CLIENT_PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = CLIENT_PUBLIC_DATA_DIR / "regional_inventory.json"
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    s = payload["summary"]
    print(
        f"Wrote {out}: {s['fluxTowersCo2']} CO2 flux towers "
        f"({s['fluxTowersOpen']} open), {s['stockPrograms']} stock programs."
    )


if __name__ == "__main__":
    main()
