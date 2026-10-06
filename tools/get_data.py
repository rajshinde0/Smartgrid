"""Download the I-BLEND dataset into Dataset/.

    python tools/get_data.py            # energy + occupancy (what the analysis needs)
    python tools/get_data.py --all      # also the 2018 campus weather file
    python tools/get_data.py --list     # show what is available, download nothing

Why this script exists
----------------------
I-BLEND is about 1.6 GB. Five of its files are larger than GitHub's hard 100 MB
per-file limit, so the data cannot live in this repository even if we wanted it
to -- and it should not, because figshare already hosts it under a DOI. This
script makes the repo self-sufficient anyway: clone it, run this, and you have
everything the notebooks need.

Nothing is hard-coded except the collection DOI. The script asks the figshare
API which articles the collection contains and which files each article holds,
so it keeps working if figshare reorganises the record.

Source
------
Rashid, H., Singh, P. & Singh, A. (2019). I-BLEND, a campus-scale commercial and
residential buildings electrical energy dataset. Scientific Data 6, 190015.
Collection: https://doi.org/10.6084/m9.figshare.c.3893581
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "Dataset"

COLLECTION_ID = 3893581
API = "https://api.figshare.com/v2"

# Which articles the analysis actually needs, and what each unzips to. The
# script matches on the article title, so it does not depend on figshare's
# internal article ids staying the same.
# The semester calendar is required: Phase 1 uses it for the activity flag.
# The weather record is optional because it covers March-June 2018 only, which
# does not overlap the energy/occupancy window at all.
CORE = ("Energy dataset", "Occupancy dataset", "semester calendar")
EXTRA = ("Weather data",)

TIMEOUT = 120


def fetch_json(url: str):
    """GET a URL and parse the response as JSON."""
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        import json

        return json.load(response)


def collection_files() -> list[dict]:
    """Every downloadable file in the I-BLEND collection, with its article."""
    articles = fetch_json(f"{API}/collections/{COLLECTION_ID}/articles?page_size=50")
    out = []
    for article in articles:
        detail = fetch_json(f"{API}/articles/{article['id']}")
        for file_info in detail.get("files", []):
            out.append({
                "article": detail.get("title", ""),
                "name": file_info["name"],
                "size": file_info["size"],
                "url": file_info["download_url"],
            })
    return out


def wanted(entry: dict, include_extra: bool) -> bool:
    """Should this figshare article be downloaded?

    Matching is on the article title because figshare item ids are not
    stable across collection revisions. CORE is the energy, occupancy and
    calendar data the analysis cannot run without; EXTRA is the 2018
    campus weather file, which is useful context but has no overlap with
    the analysis window, so it is opt-in via --all.
    """
    title = entry["article"]
    if any(key.lower() in title.lower() for key in CORE):
        return True
    if include_extra and any(key.lower() in title.lower() for key in EXTRA):
        return True
    return False


def download(url: str, destination: Path) -> None:
    """Download with a simple progress line, into a .part file first."""
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.parent.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        with open(partial, "wb") as handle:
            while chunk := response.read(1 << 20):
                handle.write(chunk)
                done += len(chunk)
                if total:
                    pct = 100 * done / total
                    print(f"\r    {done / 1048576:8.1f} / {total / 1048576:.1f} MB "
                          f"({pct:5.1f}%)", end="", flush=True)
                else:
                    print(f"\r    {done / 1048576:8.1f} MB", end="", flush=True)
    print()
    partial.replace(destination)


def place_plain_file(downloaded: Path) -> None:
    """Keep a non-archive download as-is, under its own name in Dataset/."""
    target = DATASET_DIR / downloaded.name
    if target.resolve() != downloaded.resolve():
        if target.exists():
            print(f"    keeping existing {downloaded.name} (already present)")
            downloaded.unlink(missing_ok=True)
            return
        shutil.move(str(downloaded), str(target))
    print(f"    -> Dataset/{target.name}")


def unzip_into_dataset(archive: Path) -> None:
    """Unzip, then flatten a single wrapping folder if the archive has one.

    Every file in the collection is a .zip today, but figshare records do get
    reorganised and a plain CSV would otherwise reach ZipFile and raise
    BadZipFile -- and then be deleted by the cleanup step. So anything that is
    not actually a zip is kept as a normal file instead.
    """
    if not zipfile.is_zipfile(archive):
        print(f"    {archive.name} is not a zip archive; keeping it as a file")
        place_plain_file(archive)
        return

    staging = DATASET_DIR / f"_staging_{archive.stem}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    with zipfile.ZipFile(archive) as zf:
        zf.extractall(staging)

    entries = [p for p in staging.iterdir() if p.name != "__MACOSX"]
    sources = entries
    if len(entries) == 1 and entries[0].is_dir():
        sources = list(entries[0].iterdir())

    for source in sources:
        if source.name == "__MACOSX":
            continue
        target = DATASET_DIR / source.name
        if target.exists():
            print(f"    keeping existing {source.name} (already present)")
            continue
        shutil.move(str(source), str(target))
        print(f"    -> Dataset/{source.name}")

    shutil.rmtree(staging, ignore_errors=True)


def main(argv: list[str]) -> int:
    """Command-line entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true",
                        help="also fetch the 2018 campus weather file (the "
                             "semester calendar is always fetched)")
    parser.add_argument("--list", action="store_true",
                        help="list what the collection contains, download nothing")
    parser.add_argument("--keep-zips", action="store_true",
                        help="keep the downloaded .zip files after extracting")
    args = parser.parse_args(argv[1:])

    print(f"I-BLEND collection {COLLECTION_ID} (doi:10.6084/m9.figshare.c.{COLLECTION_ID})")
    try:
        files = collection_files()
    except Exception as exc:
        print(f"\nERROR: could not reach the figshare API: {exc}")
        print("Download manually from https://doi.org/10.6084/m9.figshare.c.3893581")
        print("and unzip into Dataset/ so that Dataset/energy_dataset/ exists.")
        return 1

    print(f"{len(files)} files available:\n")
    for entry in files:
        mark = "*" if wanted(entry, include_extra=True) else " "
        print(f"  {mark} {entry['article'][:44]:46s} {entry['name']:34s} "
              f"{entry['size'] / 1048576:8.1f} MB")

    if args.list:
        print("\n(--list: nothing downloaded)")
        return 0

    targets = [e for e in files if wanted(e, include_extra=args.all)]
    if not args.all:
        print("\nFetching energy, occupancy and the semester calendar. Use "
              "--all to include the weather record too -- note it covers only "
              "March-June 2018 and does not overlap the analysis window.")

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    print()

    for entry in targets:
        archive = DATASET_DIR / entry["name"]
        expected = entry["name"].replace(".zip", "")

        if (DATASET_DIR / expected).exists():
            print(f"[skip] {entry['name']} -- Dataset/{expected}/ already exists")
            continue

        print(f"[get ] {entry['name']}  ({entry['size'] / 1048576:.1f} MB)")
        download(entry["url"], archive)

        was_zip = zipfile.is_zipfile(archive)
        print(f"[{'unzip' if was_zip else 'place'}] {entry['name']}")
        unzip_into_dataset(archive)

        # Only delete the download if it was an archive we extracted. Removing a
        # plain file here would throw away the thing we just fetched.
        if was_zip and not args.keep_zips:
            archive.unlink(missing_ok=True)

    print("\nDone. Check with:")
    print("  python -c \"import sys; sys.path.insert(0, '.'); "
          "from src import config as C; print(C.ENERGY_DIR.is_dir(), C.OCCUPANCY_DIR.is_dir())\"")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
