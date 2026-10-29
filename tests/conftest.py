"""Shared fixtures. Everything here is synthetic.

The suite must run on a bare clone -- no `Dataset/`, no parquet cache, no
network -- so no test may read a real file. If a test needs a 10-minute series,
it builds one here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# The project root is one level up from tests/.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ten_minute_index(n: int, start: str = "2015-06-01 00:00") -> pd.DatetimeIndex:
    """`n` consecutive 10-minute stamps in Asia/Kolkata.

    Tz-aware on purpose: a naive timestamp anywhere in this project is a bug,
    and `interpolate(method="time")` behaves differently without one.
    """
    return pd.date_range(start, periods=n, freq="10min", tz="Asia/Kolkata")


def series(values, start: str = "2015-06-01 00:00") -> pd.Series:
    """A float Series on the 10-minute grid. `None` entries become NaN."""
    return pd.Series(values, index=ten_minute_index(len(values), start),
                     dtype="float64")


@pytest.fixture
def blocks_per_hour() -> int:
    """6 ten-minute blocks to the hour, as `src.clean` defines it."""
    return 6
