"""Cooling degree hours -- the quantity Phase 8 decomposes the waste with.

`max(0, T - base) / 6` per 10-minute block. The clip at zero is the whole
point: a building needs no cooling on a mild day, and without it the fit would
read cold weather as negative cooling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import weather as Wx


def test_cooling_is_zero_below_the_base():
    temps = pd.Series([5.0, 15.0, 23.9])
    assert (Wx.cooling_degree_hours(temps, base=24.0) == 0).all()


def test_cooling_is_zero_at_exactly_the_base():
    assert Wx.cooling_degree_hours(pd.Series([24.0]), base=24.0).iloc[0] == 0.0


def test_cooling_rises_linearly_above_the_base():
    temps = pd.Series([25.0, 30.0, 36.0])
    cdh = Wx.cooling_degree_hours(temps, base=24.0)

    # one degree-hour spread over a ten-minute block is a sixth of it
    assert cdh.iloc[0] == pytest.approx(1 / 6)
    assert cdh.iloc[1] == pytest.approx(6 / 6)
    assert cdh.iloc[2] == pytest.approx(12 / 6)


def test_a_higher_base_never_gives_more_cooling():
    """Phase 8 scans 16-30 C for the best fit, so this has to hold across it."""
    temps = pd.Series(np.linspace(10, 45, 200))
    totals = [Wx.cooling_degree_hours(temps, base=b).sum()
              for b in range(16, 31)]
    assert totals == sorted(totals, reverse=True)


def test_a_missing_temperature_stays_missing():
    """About 4% of intervals have no reading. They must not become zero
    cooling, which would be a measurement the archive never made.
    """
    cdh = Wx.cooling_degree_hours(pd.Series([30.0, np.nan, 30.0]), base=24.0)
    assert np.isnan(cdh.iloc[1])
    assert cdh.notna().sum() == 2


def test_the_delhi_range_produces_sensible_magnitudes():
    """The archive spans 2 to 49 C. At the hottest, one block should still be a
    few degree-hours, not hundreds -- a units check on the divide by six.
    """
    assert Wx.cooling_degree_hours(pd.Series([49.0]), base=24.0).iloc[0] == \
        pytest.approx(25 / 6)
