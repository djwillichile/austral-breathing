"""Phase-1 open-data harvester for South American EC CO2-flux towers.

Reads the curated registry (``research/south_america_flux_towers.csv``), selects
the **open, archived** towers (availability tier 1) that measure CO2, and builds
a per-site **download plan** grouped by source network. Where a source exposes
anonymously-fetchable objects (ICOS Carbon Portal), it can fetch directly with
``--online``; the authenticated networks (AmeriFlux, ORNL DAAC) get explicit,
reproducible instructions instead of silent partial downloads.

Design notes
------------
* Honest about access: AmeriFlux BASE/FLUXNET and ORNL DAAC require free
  registration / a token, so this tool emits the exact commands/endpoints rather
  than pretending to download them unauthenticated. The repo's existing
  ``fluxnet-shuttle`` path remains the canonical AmeriFlux acquisition route.
* Offline-safe: with no network (or no ``--online``) it still writes a complete
  manifest, so it runs in restricted sandboxes and in CI.
* Output: ``outputs/tables/open_flux_harvest_manifest.csv`` plus a console plan.

Usage
-----
    python scripts_harvest_open_flux_data.py            # write manifest + plan
    python scripts_harvest_open_flux_data.py --online   # also fetch open ICOS objects
"""

from __future__ import annotations

import argparse
import csv

from pipeline_paths import DATA_DIR, OUTPUTS_TABLES_DIR
from pipeline_registry import open_co2_flux_towers

RAW_FLUX_DIR = DATA_DIR / "raw" / "open_flux"

# How each source network is acquired. ``how`` is shown to the user; ``auto``
# marks sources we can fetch without credentials when --online is set.
NETWORK_ACCESS = {
    "AmeriFlux": {
        "auto": False,
        "how": (
            "Free AmeriFlux account + accept data policy, then download via the "
            "AmeriFlux Data API / web (or the repo's fluxnet-shuttle path). "
            "Site page: https://ameriflux.lbl.gov/sites/siteinfo/{site_id}"
        ),
    },
    "FLUXNET2015": {
        "auto": False,
        "how": (
            "FLUXNET2015 release via fluxnet.org / OSTI DOI. "
            "Site DOI page: https://fluxnet.org/doi/FLUXNET2015/{site_id}"
        ),
    },
    "ICOS": {
        "auto": True,
        "how": "ICOS Carbon Portal (CC-BY); station page https://meta.icos-cp.eu/resources/stations/",
    },
    "LBA": {
        "auto": False,
        "how": (
            "ORNL DAAC (Earthdata login). LBA-ECO CD-32 compilation: "
            "https://daac.ornl.gov/LBA/guides/CD32_Brazil_Flux_Network.html"
        ),
    },
}


def build_plan() -> list[dict]:
    """One manifest row per open CO2 tower, annotated with its access method."""
    plan = []
    for tower in open_co2_flux_towers():
        network = tower.get("network", "")
        access = NETWORK_ACCESS.get(network, {"auto": False, "how": "See source_url."})
        plan.append(
            {
                "site_id": tower["site_id"],
                "country": tower["country"],
                "site_name": tower["site_name"],
                "network": network,
                "lat": tower["lat"],
                "lon": tower["lon"],
                "auto_fetchable": access["auto"],
                "access": access["how"].replace("{site_id}", tower["site_id"]),
                "source_url": tower.get("source_url", ""),
            }
        )
    return plan


def write_manifest(plan: list[dict]) -> None:
    OUTPUTS_TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUTS_TABLES_DIR / "open_flux_harvest_manifest.csv"
    fields = [
        "site_id",
        "country",
        "site_name",
        "network",
        "lat",
        "lon",
        "auto_fetchable",
        "access",
        "source_url",
    ]
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(plan)
    print(f"Wrote harvest manifest: {out} ({len(plan)} open CO2 towers)")


def fetch_auto(plan: list[dict]) -> None:
    """Fetch the anonymously-open sources (ICOS) using the respectful client."""
    from pipeline_http import RespectfulHttpClient

    auto = [p for p in plan if p["auto_fetchable"]]
    if not auto:
        print("No anonymously-fetchable sources in the current open set.")
        return
    RAW_FLUX_DIR.mkdir(parents=True, exist_ok=True)
    client = RespectfulHttpClient()
    for p in auto:
        result = client.fetch(p["source_url"])
        status = "ok" if result.status and 200 <= result.status < 300 else f"status={result.status}"
        if result.robots_blocked:
            status = "robots-blocked"
        print(f"  {p['site_id']} ({p['network']}): {status}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--online", action="store_true", help="Also fetch anonymously-open sources (ICOS)."
    )
    args = parser.parse_args()

    plan = build_plan()
    write_manifest(plan)

    by_network: dict[str, list[str]] = {}
    for p in plan:
        by_network.setdefault(p["network"], []).append(p["site_id"])

    print("\nOpen CO2 flux towers to harvest, by source network:")
    for network, ids in sorted(by_network.items()):
        access = NETWORK_ACCESS.get(network, {"how": "See source_url."})["how"]
        print(f"  [{network}] {len(ids)}: {', '.join(sorted(ids))}")
        print(f"      access: {access}")

    if args.online:
        print("\nFetching anonymously-open sources...")
        fetch_auto(plan)
    else:
        print(
            "\n(Run with --online from a network-enabled environment to fetch the "
            "anonymously-open sources; authenticated networks follow the printed access steps.)"
        )


if __name__ == "__main__":
    main()
