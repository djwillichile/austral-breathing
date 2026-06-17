from __future__ import annotations

import argparse
import subprocess
import pandas as pd

from pipeline_paths import (
    BASE_DIR,
    RAW_DIR,
    DOWNLOAD_LOG_PATH,
    METADATA_DIR,
    OUTPUTS_TABLES_DIR,
    latest_snapshot,
)

METADATA_DOWNLOAD_LOG_PATH = METADATA_DIR / 'download_log.csv'
OUTPUTS_DOWNLOAD_LOG_PATH = OUTPUTS_TABLES_DIR / 'download_log.csv'


def default_sites() -> list[str]:
    """Southern-Cone target sites derived from the latest catalog snapshot.

    Falls back to the original six if the catalog cannot be read."""
    fallback = ['CL-SDF', 'CL-SDP', 'CL-ACF', 'AR-TF1', 'AR-TF2', 'AR-CCg']
    try:
        from scripts_discover_southern_cone_stations import is_southern_cone
        snapshot = pd.read_csv(latest_snapshot())
        sites = [
            row['site_id']
            for _, row in snapshot.iterrows()
            if is_southern_cone(row['site_id'], row.get('location_lat'))
        ]
        return sites or fallback
    except Exception:
        return fallback


DEFAULT_SITES = default_sites()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Download FLUXNET datasets reproducibly with fluxnet-shuttle and update download logs.'
    )
    parser.add_argument('--sites', nargs='*', default=DEFAULT_SITES, help='Site IDs to download.')
    return parser.parse_args()



def expected_products(snapshot_file: Path, sites: list[str]) -> dict[str, str]:
    snapshot = pd.read_csv(snapshot_file)
    snapshot = snapshot[snapshot['site_id'].isin(sites)].copy()
    return dict(zip(snapshot['site_id'], snapshot['fluxnet_product_name']))



def existing_sites(product_names: dict[str, str]) -> list[str]:
    available = []
    for site_id, product_name in product_names.items():
        if (RAW_DIR / product_name).exists():
            available.append(site_id)
    return available



def run_download(snapshot_file: Path, sites_to_download: list[str]) -> subprocess.CompletedProcess[str] | None:
    if not sites_to_download:
        return None
    cmd = [
        'fluxnet-shuttle', 'download',
        '-f', str(snapshot_file),
        '-s', *sites_to_download,
        '-o', str(RAW_DIR),
        '--quiet',
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)



def update_download_log(product_names: dict[str, str], stdout: str, stderr: str) -> pd.DataFrame:
    log_df = pd.read_csv(DOWNLOAD_LOG_PATH)

    for site_id, product_name in product_names.items():
        zip_path = RAW_DIR / product_name
        if zip_path.exists():
            status = 'success'
            failure_reason = ''
            notes = 'Downloaded with fluxnet-shuttle in non-interactive mode.'
        else:
            status = 'failed'
            failure_reason = 'File not found after fluxnet-shuttle execution.'
            notes = 'Review stdout/stderr captured by scripts_download_fluxnet_data.py.'

        log_df.loc[log_df['site_id'] == site_id, 'download_status'] = status
        log_df.loc[log_df['site_id'] == site_id, 'failure_reason'] = failure_reason
        log_df.loc[log_df['site_id'] == site_id, 'notes'] = notes

    log_df.to_csv(DOWNLOAD_LOG_PATH, index=False)
    log_df.to_csv(METADATA_DOWNLOAD_LOG_PATH, index=False)
    log_df.to_csv(OUTPUTS_DOWNLOAD_LOG_PATH, index=False)

    logs_dir = BASE_DIR / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'download_stdout.log').write_text(stdout or '', encoding='utf-8')
    (logs_dir / 'download_stderr.log').write_text(stderr or '', encoding='utf-8')
    return log_df



def main() -> None:
    args = parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = latest_snapshot()
    products = expected_products(snapshot_file, args.sites)
    already_available = set(existing_sites(products))
    sites_to_download = [site for site in args.sites if site not in already_available]

    result = run_download(snapshot_file, sites_to_download)
    stdout = '' if result is None else result.stdout
    stderr = '' if result is None else result.stderr

    update_download_log(products, stdout, stderr)

    summary_lines = [
        f'Snapshot file: {snapshot_file.name}',
        f'Requested sites: {", ".join(args.sites)}',
        f'Already available before run: {", ".join(sorted(already_available)) if already_available else "none"}',
        f'Sites downloaded in this run: {", ".join(sites_to_download) if sites_to_download else "none"}',
        f'Return code: {"skipped" if result is None else result.returncode}',
    ]
    (BASE_DIR / 'logs' / 'download_summary.txt').write_text('\n'.join(summary_lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
