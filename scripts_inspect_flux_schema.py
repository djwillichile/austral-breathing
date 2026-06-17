from __future__ import annotations

from io import TextIOWrapper
from pathlib import Path
from zipfile import ZipFile
import csv
import json

from pipeline_paths import RAW_DIR, RESEARCH_DIR

OUTPUT_PATH = RESEARCH_DIR / 'flux_schema_summary.json'

TARGET_ZIPS = [
    RAW_DIR / 'AMF_CL-SDF_FLUXNET_2014-2021_v1.3_r1.zip',
    RAW_DIR / 'AMF_CL-SDP_FLUXNET_2014-2021_v1.3_r1.zip',
]

STANDARD_VARIABLE_HINTS = {
    'timestamp': ['TIMESTAMP', 'TIMESTAMP_START', 'TIMESTAMP_END'],
    'NEE': ['NEE', 'NEE_VUT_REF', 'NEE_CUT_REF'],
    'GPP': ['GPP', 'GPP_DT_VUT_REF', 'GPP_NT_VUT_REF'],
    'LE': ['LE', 'LE_F_MDS'],
    'H': ['H', 'H_F_MDS'],
    'TA': ['TA', 'TA_F_MDS'],
    'SW_IN': ['SW_IN', 'SW_IN_F_MDS'],
}


def pick_fluxmet_daily_member(names: list[str]) -> str:
    for name in names:
        if '_FLUXMET_DD_' in name and name.endswith('.csv'):
            return name
    raise FileNotFoundError('No FLUXMET daily CSV found inside ZIP file.')



def find_candidates(columns: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for standard_name, hints in STANDARD_VARIABLE_HINTS.items():
        matches = []
        for col in columns:
            if any(col == hint or col.startswith(f'{hint}_') for hint in hints):
                matches.append(col)
        result[standard_name] = matches
    return result



def inspect_zip(zip_path: Path) -> dict:
    with ZipFile(zip_path) as zf:
        member = pick_fluxmet_daily_member(zf.namelist())
        with zf.open(member) as fh:
            reader = csv.reader(TextIOWrapper(fh, encoding='utf-8'))
            header = next(reader)
            first_row = next(reader)

    summary = {
        'zip_file': zip_path.name,
        'site_id': zip_path.name.split('_')[1],
        'daily_fluxmet_file': member,
        'n_columns': len(header),
        'first_25_columns': header[:25],
        'last_25_columns': header[-25:],
        'standard_variable_candidates': find_candidates(header),
        'first_row_preview': dict(zip(header[:15], first_row[:15])),
    }
    return summary



def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    summaries = [inspect_zip(path) for path in TARGET_ZIPS if path.exists()]
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
