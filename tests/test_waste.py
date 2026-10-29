"""The headline calculation: energy spent while a building is nearly empty.

This is RQ1, the number the whole project is named for, so it gets a frame with
an answer worked out by hand rather than a plausible-looking one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import ten_minute_index
from src import waste as W


def frame(occupancy, power_w, usable=None) -> pd.DataFrame:
    """A minimal building table: the four columns `low_occupancy_share` reads.

    Built from numpy arrays, not Series. Handing pandas a Series with its own
    RangeIndex while naming a DatetimeIndex makes it *align* rather than
    assign, and every column silently comes out NaN -- the same trap that
    produced an all-NaN occupancy table early in this project.
    """
    n = len(occupancy)
    power = np.asarray(power_w, dtype="float64")
    return pd.DataFrame(
        {
            "occupancy": np.asarray(occupancy, dtype="float64"),
            "power_w": power,
            # 10 minutes of a watt reading, in kWh
            "kwh": power / 1000 * (10 / 60),
            "usable": np.full(n, True) if usable is None
            else np.asarray(usable, dtype=bool),
        },
        index=ten_minute_index(n),
    )


def test_share_and_ratio_on_a_hand_worked_frame():
    """80 busy intervals at 100 W, 20 empty ones at 50 W.

    p95 of the occupancy is 100, so a 5% fraction puts the threshold at 5 --
    which catches exactly the 20 zero-occupancy intervals and nothing else.
    """
    df = frame([100.0] * 80 + [0.0] * 20, [100.0] * 80 + [50.0] * 20)
    r = W.low_occupancy_share(df, fraction=0.05)

    assert r["intervals_low"] == 20
    assert r["threshold"] == pytest.approx(5.0)
    assert r["mean_power_low_w"] == pytest.approx(50.0)
    assert r["mean_power_all_w"] == pytest.approx(90.0)

    # 20 x 50 W of 80 x 100 W + 20 x 50 W  ->  1000 / 9000
    assert r["share_pct"] == pytest.approx(100 * 1000 / 9000, abs=0.01)
    assert W.intensity_ratio(r) == pytest.approx(50 / 90, abs=0.001)


def test_a_building_that_does_not_relax_scores_a_ratio_near_one():
    """The finding, in miniature: same power whether or not anyone is there."""
    df = frame([100.0] * 80 + [0.0] * 20, [100.0] * 100)
    assert W.intensity_ratio(W.low_occupancy_share(df)) == pytest.approx(1.0)


def test_a_building_that_switches_off_scores_a_low_ratio():
    df = frame([100.0] * 80 + [0.0] * 20, [100.0] * 80 + [5.0] * 20)
    assert W.intensity_ratio(W.low_occupancy_share(df)) < 0.1


# ---------------------------------------------------------------------------
# The Facilities case: no qualifying interval must not raise
# ---------------------------------------------------------------------------
def test_no_qualifying_interval_returns_a_blank_result_not_an_error():
    """Facilities. Callers index this dict directly, so an early return with
    fewer keys would raise a KeyError far from its cause.
    """
    df = frame([18.0] * 100, [100.0] * 100)
    r = W.low_occupancy_share(df)

    assert r["reachable"] is False
    assert r["intervals_low"] == 0
    assert np.isnan(W.intensity_ratio(r))


def test_the_blank_and_measured_results_carry_the_same_keys():
    measured = W.low_occupancy_share(
        frame([100.0] * 80 + [0.0] * 20, [100.0] * 100))
    blank = W.low_occupancy_share(
        frame([], []).astype({"occupancy": "float64", "power_w": "float64"}))

    assert set(blank) == set(measured), (
        "both return paths must produce the same keys"
    )


def test_unusable_intervals_are_excluded_entirely():
    """Dead-meter and out-of-range blocks must not reach the headline."""
    df = frame([0.0] * 100, [100.0] * 100, usable=[True] * 50 + [False] * 50)
    r = W.low_occupancy_share(df)
    assert r["intervals_total"] == 50


def test_missing_occupancy_is_excluded_from_the_denominator():
    """Numerator and denominator use the same set, so the share is a real
    proportion of measured consumption rather than an artefact of gaps.
    """
    occ = [100.0] * 50 + [np.nan] * 30 + [0.0] * 20
    df = frame(occ, [100.0] * 100)
    r = W.low_occupancy_share(df)
    assert r["intervals_total"] == 70


def test_a_lower_threshold_can_only_shrink_the_share():
    """The sensitivity sweep depends on this being monotone."""
    df = frame(list(np.linspace(0, 100, 200)), [100.0] * 200)
    shares = [W.low_occupancy_share(df, fraction=f)["intervals_low"]
              for f in (0.02, 0.05, 0.10, 0.20)]
    assert shares == sorted(shares)
