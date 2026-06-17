from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import shutil

from pipeline_paths import RAW_DIR


def discover_target_zips() -> dict[str, Path]:
    """Discover ``<SITE_ID> -> product ZIP`` pairs by scanning ``data/raw/``.

    Catalog-driven (no hardcoded filenames): any ``*.zip`` placed directly in
    ``RAW_DIR`` whose name contains a FLUXNET site code is mapped to that site.
    """
    import re

    site_code = re.compile(r'_([A-Z]{2}-[A-Za-z0-9]{2,})_')
    targets: dict[str, Path] = {}
    for zip_path in sorted(RAW_DIR.glob('*.zip')):
        match = site_code.search(zip_path.name)
        if match:
            # Prefer the first/most-complete archive per site.
            targets.setdefault(match.group(1), zip_path)
    return targets


def pick_member(names: list[str], token: str) -> str:
    for name in names:
        if token in name and name.endswith('.csv'):
            return name
    raise FileNotFoundError(f'No member matching {token} was found inside ZIP archive.')



def ensure_original_copy(site_id: str, zip_path: Path) -> Path:
    site_raw_dir = RAW_DIR / site_id
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    destination = site_raw_dir / zip_path.name
    if not destination.exists():
        shutil.copy2(zip_path, destination)
    return destination



def extract_selected_members(zip_copy_path: Path, site_id: str) -> None:
    site_raw_dir = RAW_DIR / site_id
    with ZipFile(zip_copy_path) as zf:
        names = zf.namelist()
        selected = [
            pick_member(names, '_FLUXMET_DD_'),
            pick_member(names, '_BIF_'),
            pick_member(names, '_BIFVARINFO_DD_'),
        ]
        text_members = [name for name in names if name in {'README.txt', 'DATA_POLICY_LICENSE_AND_INSTRUCTIONS.txt'}]
        selected.extend(text_members)
        for member in selected:
            output_path = site_raw_dir / Path(member).name
            if not output_path.exists():
                with zf.open(member) as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())



def main() -> None:
    for site_id, zip_path in discover_target_zips().items():
        if not zip_path.exists():
            continue
        zip_copy = ensure_original_copy(site_id, zip_path)
        extract_selected_members(zip_copy, site_id)


if __name__ == '__main__':
    main()
