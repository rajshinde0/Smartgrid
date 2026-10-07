"""Make sure the dashboard has data to read, wherever it is running.

On a local clone the parquet is already there, written by `src/dashboard.py`
after the notebooks have run, and this module does nothing at all.

On Streamlit Community Cloud there is no `data/` directory: the deploy is a
fresh checkout of the repository, and the repository deliberately contains no
data. So the first boot fetches the seven scored tables from the project's
GitHub Release and unpacks them into the path `src/config.py` already expects.

That keeps one rule intact in both places -- **data is fetched, never
committed** -- without the app needing to know which place it is in.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config as C          # noqa: E402
from src import dashboard as D       # noqa: E402


def data_is_present() -> bool:
    """True when at least one building's scored table is already on disk."""
    return any(C.PROCESSED_DIR.glob(f"{D.DASH_PREFIX}*.parquet"))


def ensure_data(*, verbose: bool = True) -> bool:
    """Fetch the dashboard cache if it is missing. Returns True if data is ready.

    Safe to call on every boot: it is a no-op once the files exist, so a local
    run never touches the network. A failed fetch returns False rather than
    raising -- the app then shows its own "no data found" message, which tells
    the reader what to do, instead of a traceback that does not.
    """
    if data_is_present():
        return True

    if verbose:
        print("dashboard: no local parquet; fetching from the GitHub Release...")

    try:
        from tools import get_cache

        get_cache.fetch(get_cache.DASHBOARD_ASSET)
    except SystemExit as exc:              # get_cache exits with a readable message
        print(f"dashboard: fetch failed -- {exc}")
        return False
    except Exception as exc:               # noqa: BLE001 -- boot must not crash
        print(f"dashboard: fetch failed -- {type(exc).__name__}: {exc}")
        return False

    return data_is_present()
