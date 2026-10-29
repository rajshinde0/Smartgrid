"""What counts as "low occupancy" -- the most consequential definition here.

The threshold is **relative** to each building's own scale (decision D05-01).
An absolute cut-off would mean "deserted" in a 400-device Academic building and
"busy" in Facilities, which rarely exceeds 20. The headline number moves with
this definition, so it is worth pinning.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import config as C
from src import occupancy as occ


def test_threshold_is_a_fraction_of_the_buildings_own_percentile():
    counts = pd.Series(np.arange(0, 201, dtype="float64"))
    p95 = np.percentile(counts, 95)

    assert occ.low_occupancy_threshold(counts, fraction=0.05, percentile=95) == \
        pytest.approx(0.05 * p95)


def test_the_same_fraction_gives_different_thresholds_for_different_buildings():
    """This is the entire point of a relative rule."""
    big = pd.Series(np.arange(0, 401, dtype="float64"))
    small = pd.Series(np.arange(0, 21, dtype="float64"))

    assert occ.low_occupancy_threshold(big) > occ.low_occupancy_threshold(small)


def test_missing_counts_are_ignored_when_setting_the_threshold():
    clean = pd.Series([1.0, 2.0, 3.0, 4.0])
    gappy = pd.Series([1.0, np.nan, 2.0, 3.0, np.nan, 4.0])

    assert occ.low_occupancy_threshold(gappy) == \
        pytest.approx(occ.low_occupancy_threshold(clean))


def test_the_mask_is_inclusive_of_the_threshold():
    counts = pd.Series([4.0, 5.0, 6.0])
    assert list(occ.low_occupancy_mask(counts, 5.0)) == [True, True, False]


def test_missing_occupancy_is_never_low():
    """Absent evidence is not evidence of an empty building."""
    counts = pd.Series([1.0, np.nan, 100.0])
    assert list(occ.low_occupancy_mask(counts, 5.0)) == [True, False, False]


def test_the_default_fraction_is_the_published_one():
    """The report quotes 5% of the 95th percentile. If this changes, every
    headline number changes with it.
    """
    assert C.LOW_OCC_FRACTION == 0.05
    assert C.LOW_OCC_PERCENTILE == 95


def test_a_building_whose_threshold_falls_below_its_minimum_matches_nothing():
    """Facilities. Its 5% threshold works out at 0.9 devices, below its own
    observed minimum of 1, so it has no qualifying interval at all -- reported
    as blank rather than bending the rule for one building.
    """
    counts = pd.Series(np.full(100, 18.0))
    counts.iloc[0] = 1.0

    threshold = occ.low_occupancy_threshold(counts)
    assert threshold < counts.min(), "this fixture should reproduce the case"
    assert not occ.low_occupancy_mask(counts, threshold).any()
