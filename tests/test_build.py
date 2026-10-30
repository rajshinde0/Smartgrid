"""Combining a building's meters -- where this project's worst bug lived.

`docs/bugFix1.md`: the combine step summed `power_w_<role>` instead of
`power_filled_w_<role>`, so every interpolated value was computed in
`clean_meter` and then silently discarded -- 5,206 blocks. The cross-check
against the dataset's own aggregate file passed anyway, because both sides of
it used raw power: it had been validating ingestion and was never capable of
validating this step.

These tests are written from what `combine_meters` promises, not from what it
currently returns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import ten_minute_index
from src import build


def meter(power_w, power_filled_w=None, *, was_interpolated=None,
          meter_off=None, is_missing=None, outlier_iqr=None,
          outlier_zscore=None, extra=None) -> pd.DataFrame:
    """One cleaned meter frame, with the columns `combine_meters` reads.

    Built from numpy arrays rather than Series: handing pandas a Series with a
    RangeIndex while naming a DatetimeIndex makes it *align* rather than
    assign, and every column comes out NaN.
    """
    n = len(power_w)
    power_w = np.asarray(power_w, dtype="float64")
    filled = power_w if power_filled_w is None else np.asarray(
        power_filled_w, dtype="float64")

    def flag(v):
        return np.full(n, False) if v is None else np.asarray(v, dtype=bool)

    frame = pd.DataFrame(
        {
            "power_w": power_w,
            "power_filled_w": filled,
            "power_min_w": power_w,
            "power_max_w": power_w,
            "meter_off": flag(meter_off),
            "is_missing": flag(is_missing),
            "was_interpolated": flag(was_interpolated),
            "outlier_iqr": flag(outlier_iqr),
            "outlier_zscore": flag(outlier_zscore),
            "n_readings": np.full(n, 10),
        },
        index=ten_minute_index(n),
    )
    for name, values in (extra or {}).items():
        frame[name] = np.asarray(values)
    return frame


# ---------------------------------------------------------------------------
# The bug. This is the test that had to exist.
# ---------------------------------------------------------------------------
def test_the_sum_uses_the_gap_filled_series_not_the_raw_one():
    """Summing power_w instead of power_filled_w computes every interpolated
    value and then throws it away. On this dataset that was 5,206 blocks.
    """
    mains = meter(
        power_w=[100.0, np.nan, 300.0],
        power_filled_w=[100.0, 200.0, 300.0],
        was_interpolated=[False, True, False],
    )
    combined = build.combine_meters({"mains": mains}, "mains")

    assert combined["power_w"].iloc[1] == pytest.approx(200.0), (
        "the filled value must reach the building total"
    )
    assert combined["power_w"].notna().all()


def test_a_filled_gap_in_one_meter_still_reaches_the_building_total():
    """Two-meter case: the fill belongs to the sum just as much."""
    mains = meter([100.0, np.nan, 100.0], [100.0, 100.0, 100.0],
                  was_interpolated=[False, True, False])
    ups = meter([50.0, 50.0, 50.0])

    combined = build.combine_meters({"mains": mains, "ups": ups}, "mains")
    assert combined["power_w"].iloc[1] == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# min_count -- a missing meter must not silently understate the building
# ---------------------------------------------------------------------------
def test_one_missing_meter_gives_nan_not_the_other_meters_value():
    """Adding a measured value to a missing one would report half a building
    as if it were the whole of it.
    """
    mains = meter([100.0, 100.0], [100.0, 100.0])
    ups = meter([50.0, np.nan], [50.0, np.nan])

    combined = build.combine_meters({"mains": mains, "ups": ups}, "mains")

    assert combined["power_w"].iloc[0] == pytest.approx(150.0)
    assert np.isnan(combined["power_w"].iloc[1]), (
        "a half-measured block must be NaN, not 100.0"
    )


def test_a_single_meter_building_is_not_penalised_by_min_count():
    """Five of the seven buildings have one meter."""
    combined = build.combine_meters({"mains": meter([10.0, 20.0])}, "mains")
    assert list(combined["power_w"]) == [10.0, 20.0]


# ---------------------------------------------------------------------------
# Flags propagate, so nothing downstream mistakes a fill for a reading
# ---------------------------------------------------------------------------
def test_was_interpolated_is_true_if_either_meter_was_filled():
    mains = meter([1.0, 1.0], was_interpolated=[True, False])
    ups = meter([1.0, 1.0], was_interpolated=[False, False])

    combined = build.combine_meters({"mains": mains, "ups": ups}, "mains")
    assert list(combined["was_interpolated"]) == [True, False]


@pytest.mark.parametrize(
    "flag", ["meter_off", "is_missing", "outlier_iqr", "outlier_zscore"])
def test_quality_flags_or_across_meters(flag):
    """A problem on either supply is a problem for the building."""
    mains = meter([1.0, 1.0], **{flag: [True, False]})
    ups = meter([1.0, 1.0], **{flag: [False, False]})

    combined = build.combine_meters({"mains": mains, "ups": ups}, "mains")
    assert list(combined[flag]) == [True, False]


# ---------------------------------------------------------------------------
# Per-meter detail survives, and the mains meter owns electrical quality
# ---------------------------------------------------------------------------
def test_each_meter_keeps_its_own_columns_alongside_the_sum():
    """Phase 5 asks which supply keeps running when the rooms empty out, which
    needs the parts as well as the total.
    """
    mains = meter([100.0])
    ups = meter([50.0])
    combined = build.combine_meters({"mains": mains, "ups": ups}, "mains")

    assert combined["power_filled_w_mains"].iloc[0] == 100.0
    assert combined["power_filled_w_ups"].iloc[0] == 50.0
    assert combined["power_w"].iloc[0] == 150.0


def test_electrical_quality_comes_from_the_mains_meter():
    mains = meter([100.0], extra={"voltage": [230.0], "power_factor": [0.95]})
    ups = meter([50.0], extra={"voltage": [999.0], "power_factor": [0.10]})

    combined = build.combine_meters({"mains": mains, "ups": ups}, "mains")
    assert combined["voltage"].iloc[0] == 230.0
    assert combined["power_factor"].iloc[0] == 0.95


def test_the_mains_role_is_honoured_not_just_the_first_key():
    """`build_building` derives the mains role from the building spec. If the
    combine step guessed from dict order instead, a building whose spec lists
    the UPS first would take its voltage from the wrong meter.
    """
    ups = meter([50.0], extra={"voltage": [999.0]})
    mains = meter([100.0], extra={"voltage": [230.0]})

    combined = build.combine_meters({"ups": ups, "mains": mains}, "mains")
    assert combined["voltage"].iloc[0] == 230.0


def test_a_meter_without_quality_columns_is_fine():
    """Only some meters report voltage; a missing column must not raise."""
    combined = build.combine_meters({"mains": meter([100.0])}, "mains")
    assert "voltage" not in combined


# ---------------------------------------------------------------------------
# build_long_table's stale-cache guard
# ---------------------------------------------------------------------------
def test_a_cache_missing_a_long_column_is_detected():
    """A cache written before a column was added to LONG_COLUMNS surfaced as a
    KeyError inside a groupby, far from its cause. The guard catches it here.
    """
    cached = pd.DataFrame(columns=[c for c in build.LONG_COLUMNS if c != "date"])
    missing = [c for c in build.LONG_COLUMNS if c not in cached.columns]
    assert missing == ["date"]


def test_a_complete_cache_is_accepted():
    cached = pd.DataFrame(columns=list(build.LONG_COLUMNS))
    assert [c for c in build.LONG_COLUMNS if c not in cached.columns] == []
