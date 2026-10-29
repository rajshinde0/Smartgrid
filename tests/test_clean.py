"""Cleaning rules -- the part of this project that has broken most.

Both outside-eye review rounds landed here, and both bugs were in functions
small enough to fit on a screen. These tests pin the behaviour each fix
established, written from what the docstrings say the rules *are* rather than
from what the code currently returns. See docs/bugFix1.md and bugFix2.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import series
from src import clean


# ---------------------------------------------------------------------------
# gap_runs -- whole-run length, which is what the interpolation rule needs
# ---------------------------------------------------------------------------
def test_gap_runs_gives_every_row_its_whole_run_length():
    s = series([1.0, None, None, None, 5.0])
    assert list(clean.gap_runs(s)[1:4]) == [3, 3, 3]


def test_gap_runs_counts_each_run_separately():
    s = series([1.0, None, 3.0, None, None, 6.0])
    runs = clean.gap_runs(s)
    assert runs.iloc[1] == 1
    assert list(runs[3:5]) == [2, 2]


# ---------------------------------------------------------------------------
# interpolate_short_gaps -- the pandas `limit=` bug (bugFix2)
# ---------------------------------------------------------------------------
def test_short_gap_is_filled_completely():
    s = series([10.0, None, None, 40.0])
    filled, was_filled = clean.interpolate_short_gaps(s, limit_steps=3)

    assert filled.notna().all(), "a gap inside the limit must be filled whole"
    assert filled.iloc[1] == pytest.approx(20.0)
    assert filled.iloc[2] == pytest.approx(30.0)
    assert list(was_filled) == [False, True, True, False]


def test_long_gap_is_left_entirely_alone():
    """The bug that `limit=` caused: a long gap got its first N blocks filled.

    pandas' `limit` caps *consecutive* NaNs, so `interpolate(limit=3)` filled
    the first three blocks of a 200-day gap along a straight line drawn between
    readings months apart. The rule is whole-run: a gap over the limit keeps
    every one of its missing blocks.
    """
    s = series([10.0] + [None] * 10 + [110.0])
    filled, was_filled = clean.interpolate_short_gaps(s, limit_steps=3)

    assert filled.isna().sum() == 10, "no block of an over-limit gap may be filled"
    assert not was_filled.any()


def test_a_gap_exactly_at_the_limit_is_filled():
    s = series([0.0, None, None, None, 40.0])
    filled, _ = clean.interpolate_short_gaps(s, limit_steps=3)
    assert filled.notna().all()


def test_a_gap_one_block_over_the_limit_is_not():
    s = series([0.0, None, None, None, None, 50.0])
    filled, _ = clean.interpolate_short_gaps(s, limit_steps=3)
    assert filled.isna().sum() == 4


def test_leading_and_trailing_gaps_are_never_extrapolated():
    """Filling before the first reading or after the last invents data."""
    s = series([None, None, 30.0, 40.0, None, None])
    filled, was_filled = clean.interpolate_short_gaps(s, limit_steps=3)

    assert filled.iloc[:2].isna().all(), "must not extrapolate backwards"
    assert filled.iloc[4:].isna().all(), "must not extrapolate forwards"
    assert not was_filled.any()


def test_the_mask_marks_filled_values_and_nothing_else():
    """Nothing downstream may mistake an interpolated value for a reading."""
    s = series([10.0, None, 30.0, 40.0])
    filled, was_filled = clean.interpolate_short_gaps(s, limit_steps=3)

    assert was_filled.sum() == 1
    assert was_filled.iloc[1]
    # every position the mask marks really is a value the input lacked
    assert s[was_filled].isna().all()
    assert filled[was_filled].notna().all()


def test_a_series_with_no_gaps_is_returned_unchanged():
    s = series([1.0, 2.0, 3.0])
    filled, was_filled = clean.interpolate_short_gaps(s)
    pd.testing.assert_series_equal(filled, s)
    assert not was_filled.any()


# ---------------------------------------------------------------------------
# flag_meter_off -- the bridging bug (bugFix2) and the rule itself
# ---------------------------------------------------------------------------
def test_a_long_zero_run_is_flagged(blocks_per_hour):
    """Six hours of exactly 0.000 W is a meter that stopped, not a quiet night."""
    n = 8 * blocks_per_hour
    s = series([50.0] + [0.0] * n + [50.0])
    flags = clean.flag_meter_off(s, hours=6)
    assert flags.sum() == n


def test_a_short_zero_run_is_left_alone(blocks_per_hour):
    """A building really can draw nothing briefly; that is not a dead meter."""
    s = series([50.0] + [0.0] * (2 * blocks_per_hour) + [50.0])
    assert not clean.flag_meter_off(s, hours=6).any()


def test_one_dropout_inside_a_long_zero_run_does_not_split_it(blocks_per_hour):
    """The bug: a single missing block broke a ten-hour outage into two
    five-hour runs, neither long enough to flag, so the whole outage passed as
    real consumption. A short gap bridges the run instead of breaking it.
    """
    half = 5 * blocks_per_hour
    s = series([50.0] + [0.0] * half + [None] + [0.0] * half + [50.0])

    flags = clean.flag_meter_off(s, hours=6, bridge_steps=3)
    assert flags.sum() == 2 * half, "the run should survive one dropout"


def test_a_gap_longer_than_the_bridge_still_breaks_the_run(blocks_per_hour):
    """At that length the absence is its own event, not a dropout."""
    half = 5 * blocks_per_hour
    s = series([50.0] + [0.0] * half + [None] * 8 + [0.0] * half + [50.0])

    assert not clean.flag_meter_off(s, hours=6, bridge_steps=3).any()


def test_a_missing_block_is_never_itself_flagged(blocks_per_hour):
    """The flag means 'this block read zero', so it cannot sit on a NaN."""
    half = 5 * blocks_per_hour
    s = series([50.0] + [0.0] * half + [None] + [0.0] * half + [50.0])

    flags = clean.flag_meter_off(s, hours=6, bridge_steps=3)
    assert not flags[s.isna()].any()


def test_nan_is_not_treated_as_zero():
    s = series([None] * 60)
    assert not clean.flag_meter_off(s, hours=6).any()


# ---------------------------------------------------------------------------
# zero_run_lengths -- used to show the dead-meter threshold separates two
# genuinely different populations
# ---------------------------------------------------------------------------
def test_zero_run_lengths_reports_hours_per_run(blocks_per_hour):
    s = series([50.0] + [0.0] * (3 * blocks_per_hour) +
               [50.0] + [0.0] * (12 * blocks_per_hour) + [50.0])
    assert sorted(clean.zero_run_lengths(s)) == [3.0, 12.0]


def test_zero_run_lengths_is_empty_when_nothing_is_zero():
    assert len(clean.zero_run_lengths(series([1.0, 2.0, 3.0]))) == 0


# ---------------------------------------------------------------------------
# iqr_fences -- outliers are flagged, never deleted, so the fences must be the
# textbook ones
# ---------------------------------------------------------------------------
def test_iqr_fences_are_the_tukey_fences():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    low, high = clean.iqr_fences(s, k=1.5)

    assert low == pytest.approx(q1 - 1.5 * (q3 - q1))
    assert high == pytest.approx(q3 + 1.5 * (q3 - q1))


def test_flag_outliers_marks_the_extreme_value_only():
    s = pd.Series([10.0] * 20 + [1000.0])
    flags = clean.flag_outliers_iqr(s)
    assert flags.sum() == 1
    assert flags.iloc[-1]
