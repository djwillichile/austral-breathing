"""Shared path resolution for the eddy-covariance pipeline.

Single source of truth for the repository base directory and all derived
directories. Replaces the previously hardcoded ``/home/ubuntu/...`` paths so
the pipeline runs from any checkout.

Resolution order for the base directory:
    1. ``EDDY_BASE_DIR`` environment variable, if set.
    2. The directory containing this file (the repo root, since the
       ``scripts_*.py`` modules live at the top level alongside it).
"""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_base_dir() -> Path:
    env = os.environ.get("EDDY_BASE_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent


BASE_DIR = _resolve_base_dir()

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
RESEARCH_DIR = BASE_DIR / "research"
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_TABLES_DIR = OUTPUTS_DIR / "tables"
OUTPUTS_MAPS_DIR = OUTPUTS_DIR / "maps"
LOGS_DIR = BASE_DIR / "logs"
CLIENT_PUBLIC_DATA_DIR = BASE_DIR / "client" / "public" / "data"

DOWNLOAD_LOG_PATH = BASE_DIR / "download_log.csv"

SNAPSHOT_GLOB = "fluxnet_shuttle_snapshot_*.csv"


def latest_snapshot() -> Path:
    """Return the newest fluxnet-shuttle snapshot CSV in ``research/``.

    Snapshots are timestamped, so the lexicographically last file is the most
    recent. Discovery writes a newer-timestamped catalog here, which makes the
    whole pipeline pick up new stations with no downstream changes.
    """
    files = sorted(RESEARCH_DIR.glob(SNAPSHOT_GLOB))
    if not files:
        raise FileNotFoundError(
            f"No fluxnet-shuttle snapshot ({SNAPSHOT_GLOB}) found in {RESEARCH_DIR}."
        )
    return files[-1]


def catalog_path(timestamp: str) -> Path:
    """Path for a new snapshot-compatible catalog with the given UTC timestamp."""
    return RESEARCH_DIR / f"fluxnet_shuttle_snapshot_{timestamp}.csv"


def ensure_dirs() -> None:
    """Create the standard output directories if they do not yet exist."""
    for directory in (
        RAW_DIR,
        PROCESSED_DIR,
        METADATA_DIR,
        RESEARCH_DIR,
        OUTPUTS_TABLES_DIR,
        OUTPUTS_MAPS_DIR,
        LOGS_DIR,
        CLIENT_PUBLIC_DATA_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
