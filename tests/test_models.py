"""The model input contract.

`feature_columns` is the single source of truth shared by fitting, scoring and
prediction. Its own docstring names the failure it exists to prevent: building
the list twice is how a model quietly ends up scored on columns in a different
order from the ones it was fitted on.
"""

from __future__ import annotations

import pytest

from src import models as M


def test_the_time_only_model_takes_time_features_and_nothing_else():
    """Model B. Phase 6 turns its residuals into Detector T."""
    cols = M.feature_columns(include_occupancy=False)
    assert cols == M.TIME_CATEGORICAL + M.TIME_BINARY
    assert "occupancy" not in cols
    assert "temp_c" not in cols


def test_occupancy_is_added_to_the_time_features_not_substituted_for_them():
    """Model C differs from B by exactly one feature group -- that is what
    makes the C-vs-B comparison answer RQ2 rather than something else.
    """
    b = M.feature_columns(include_occupancy=False)
    c = M.feature_columns(include_occupancy=True)

    assert c[:len(b)] == b, "the time features must stay, in place"
    assert set(c) - set(b) == set(M.OCCUPANCY)


def test_weather_is_added_the_same_way():
    """Models E and F. Phase 8 compares them against B and C on identical rows,
    so each must differ by exactly one group.
    """
    b = M.feature_columns(include_occupancy=False)
    e = M.feature_columns(include_occupancy=False, include_weather=True)
    f = M.feature_columns(include_occupancy=True, include_weather=True)

    assert set(e) - set(b) == set(M.WEATHER)
    assert set(f) - set(e) == set(M.OCCUPANCY)


def test_the_order_is_stable_across_calls():
    """The failure the docstring describes: fitting and scoring call this
    separately, and a different order between the two would score a model on
    columns it was not fitted on.
    """
    for occ in (False, True):
        for wx in (False, True):
            first = M.feature_columns(occ, include_weather=wx)
            assert first == M.feature_columns(occ, include_weather=wx)


def test_no_column_is_listed_twice():
    """A duplicate would be silently one-hot encoded twice."""
    for occ in (False, True):
        for wx in (False, True):
            cols = M.feature_columns(occ, include_weather=wx)
            assert len(cols) == len(set(cols))


def test_no_lag_or_rolling_feature_can_reach_a_model():
    """Decision D04-03. Power an hour ago correlates at r = 0.95 and would lift
    validation R-squared from 0.55 to 0.83 -- and a model that knows recent
    power tracks waste instead of flagging it, because lights left on since
    2 a.m. are predicted to stay on. The columns exist in the table; they must
    never reach a model.
    """
    for occ in (False, True):
        for wx in (False, True):
            cols = M.feature_columns(occ, include_weather=wx)
            assert not [c for c in cols if "lag" in c or "roll" in c]
