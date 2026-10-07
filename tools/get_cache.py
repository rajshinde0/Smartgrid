"""Download the derived parquet cache from this repo's GitHub Release.

    python tools/get_cache.py --dashboard   # 39 MB, what the dashboard needs
    python tools/get_cache.py --full        # 338 MB, lets Phases 2-8 skip ingest
    python tools/get_cache.py --list        # show what the release holds

Why this script exists
----------------------
`Dataset/` holds 1.6 GB of raw meter readings and `data/` holds the parquet
built from it. Neither is committed -- five raw files exceed GitHub's hard
100 MB per-file limit, and more importantly data does not belong in a source
tree. `tools/get_data.py` solves that for the *raw* data by fetching it from
figshare.

This script does the same for the *derived* data, which figshare does not host
because we produced it. GitHub Release assets are the right home: they allow up
to 2 GB per file, they are versioned by tag, and nothing data-shaped enters the
repository tree. `tools/check_no_data.py` still passes.

Two assets, because two jobs:

    dashboard-parquet.zip   the seven scored per-building tables the Streamlit
                            app reads. Small, and all it needs.
    processed-cache.zip     the full Phase 1 output. Lets a fresh machine run
                            Phases 2-8 without first ingesting 1.6 GB.

A snapshot, not a source of truth
---------------------------------
These assets are built from one verified pipeline run. If the pipeline is
re-run and the numbers move, the assets are stale until they are re-uploaded.
So every fetch prints the release tag it pulled from -- if that tag is older
than your last run, you are looking at old data.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"

REPO = "rajshinde0/Smartgrid"
API = f"https://api.github.com/repos/{REPO}/releases/tags"
RELEASE_TAG = "data-v1"

DASHBOARD_ASSET = "dashboard-parquet.zip"
FULL_ASSET = "processed-cache.zip"

TIMEOUT = 120
RELEASE_PAGE = f"https://github.com/{REPO}/releases/tag/{RELEASE_TAG}"


def release_info(tag: str = RELEASE_TAG) -> dict:
    """Ask the GitHub API what this release holds.

    Raises SystemExit with a readable message rather than a traceback: this is
    the first thing that runs on a fresh machine, and "HTTP Error 404" alone
    does not tell anyone what to do about it.
    """
    try:
        with urllib.request.urlopen(f"{API}/{tag}", timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            sys.exit(
                f"ERROR: no release tagged '{tag}' on {REPO}.\n"
                f"       Check {RELEASE_PAGE}\n"
                "       If the release has not been created yet, build the\n"
                "       cache locally instead:\n"
                "         python tools/get_data.py\n"
                "         python tools/build_and_run.py 01_data_prep"
            )
        sys.exit(f"ERROR: GitHub API returned HTTP {exc.code} for {tag}.")
    except urllib.error.URLError as exc:
        sys.exit(
            f"ERROR: could not reach the GitHub API ({exc.reason}).\n"
            f"       Download the asset by hand from {RELEASE_PAGE}\n"
            f"       and unzip it into data/processed/."
        )


def download(url: str, destination: Path) -> None:
    """Download with a progress line, into a .part file first."""
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        with open(partial, "wb") as handle:
            while chunk := response.read(1 << 20):
                handle.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r    {done / 1048576:8.1f} / {total / 1048576:.1f} MB "
                          f"({100 * done / total:5.1f}%)", end="", flush=True)
                else:
                    print(f"\r    {done / 1048576:8.1f} MB", end="", flush=True)
    print()
    partial.replace(destination)


def unzip_into_processed(archive: Path) -> int:
    """Unzip into data/processed/, flattening one wrapping folder if present.

    Returns the number of parquet files placed. Existing files are overwritten:
    unlike the raw dataset, this cache is ours and a newer copy always wins.
    """
    if not zipfile.is_zipfile(archive):
        sys.exit(f"ERROR: {archive.name} is not a zip archive; refusing to unpack it.")

    staging = PROCESSED_DIR / f"_staging_{archive.stem}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    with zipfile.ZipFile(archive) as zf:
        zf.extractall(staging)

    entries = [p for p in staging.iterdir() if p.name != "__MACOSX"]
    sources = entries
    if len(entries) == 1 and entries[0].is_dir():
        sources = list(entries[0].iterdir())

    placed = 0
    for source in sources:
        if source.name == "__MACOSX" or source.name.startswith("."):
            continue
        target = PROCESSED_DIR / source.name
        if target.exists():
            target.unlink()
        shutil.move(str(source), str(target))
        placed += 1

    shutil.rmtree(staging, ignore_errors=True)
    archive.unlink(missing_ok=True)
    return placed


def fetch(asset_name: str, tag: str = RELEASE_TAG) -> None:
    """Download one release asset and unpack it into data/processed/."""
    info = release_info(tag)
    assets = {a["name"]: a for a in info.get("assets", [])}

    if asset_name not in assets:
        available = ", ".join(sorted(assets)) or "(none)"
        sys.exit(
            f"ERROR: release '{tag}' has no asset named {asset_name}.\n"
            f"       It holds: {available}\n"
            f"       See {RELEASE_PAGE}"
        )

    asset = assets[asset_name]
    size_mb = asset.get("size", 0) / 1048576
    print(f"release {tag}  ({info.get('published_at', 'date unknown')})")
    print(f"  {asset_name}  {size_mb:.1f} MB")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    archive = PROCESSED_DIR / asset_name
    download(asset["browser_download_url"], archive)
    placed = unzip_into_processed(archive)

    print(f"  -> {placed} files in data/processed/")
    print(f"  source: release '{tag}'. If you have re-run the pipeline since "
          f"that release, this cache is stale.")


def list_assets(tag: str = RELEASE_TAG) -> None:
    """Print what the release holds, download nothing."""
    info = release_info(tag)
    print(f"release {tag}  ({info.get('published_at', 'date unknown')})")
    print(f"  {RELEASE_PAGE}")
    assets = info.get("assets", [])
    if not assets:
        print("  (no assets)")
        return
    for asset in sorted(assets, key=lambda a: a["name"]):
        print(f"  {asset['name']:28s} {asset.get('size', 0) / 1048576:8.1f} MB  "
              f"{asset.get('download_count', 0)} downloads")


def main(argv: list[str]) -> int:
    """Command-line entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dashboard", action="store_true",
                        help=f"fetch {DASHBOARD_ASSET} (39 MB): what the dashboard reads")
    parser.add_argument("--full", action="store_true",
                        help=f"fetch {FULL_ASSET} (338 MB): lets Phases 2-8 skip ingest")
    parser.add_argument("--list", action="store_true",
                        help="show what the release holds, download nothing")
    parser.add_argument("--tag", default=RELEASE_TAG,
                        help=f"release tag to pull from (default {RELEASE_TAG})")
    args = parser.parse_args(argv[1:])

    if args.list:
        list_assets(args.tag)
        return 0

    if not (args.dashboard or args.full):
        parser.print_help()
        print("\nNothing to do. Pass --dashboard, --full or --list.")
        return 2

    if args.full:
        fetch(FULL_ASSET, args.tag)
    if args.dashboard:
        fetch(DASHBOARD_ASSET, args.tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
