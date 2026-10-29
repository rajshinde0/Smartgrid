"""The RQ3 machinery: robust scoring, banding, and the confusion counts.

Both detectors are scored by exactly this procedure, so a bug here would move
the comparison between them -- which is the entire experiment.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import anomaly as A
from src import config as C


# ---------------------------------------------------------------------------
# robust_zscore -- median + 1.4826 * MAD, not mean + SD
# ---------------------------------------------------------------------------
def test_zscore_is_centred_on_the_median():
    r = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    assert A.robust_zscore(r).iloc[2] == pytest.approx(0.0)


def test_the_scale_is_the_rescaled_mad():
    r = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    median = r.median()
    expected = (r - median) / (1.4826 * (r - median).abs().median())
    pd.testing.assert_series_equal(A.robust_zscore(r), expected)


def test_a_few_huge_values_do_not_inflate_the_scale():
    """The reason for using the MAD at all: with mean + SD, a handful of large
    anomalies raise the bar and hide themselves.
    """
    base = pd.Series([0.0] * 100 + [1.0] * 100)
    spiked = pd.concat([base, pd.Series([5000.0] * 5)], ignore_index=True)

    sd_scale = spiked.std()
    mad_scale = 1.4826 * (spiked - spiked.median()).abs().median()
    assert mad_scale < sd_scale / 10, "the MAD should barely notice the spikes"

    # and the spikes still score as extreme
    assert A.robust_zscore(spiked).iloc[-1] > 3


def test_a_constant_series_does_not_divide_by_zero():
    z = A.robust_zscore(pd.Series([7.0] * 50))
    assert not np.isinf(z).any()


# ---------------------------------------------------------------------------
# classify -- the bands the dashboard colours by
# ---------------------------------------------------------------------------
def test_bands_are_normal_warning_anomaly():
    z = pd.Series([0.0, 1.9, 2.0, 2.9, 3.0, 10.0])
    assert list(A.classify(z)) == [
        "NORMAL", "NORMAL", "WARNING", "WARNING", "ANOMALY", "ANOMALY",
    ]


def test_banding_uses_magnitude_so_large_negatives_band_too():
    """`classify` is two-sided; one-sidedness is applied later, deliberately
    (decision D06-05), so that the band itself stays a pure magnitude.
    """
    assert list(A.classify(pd.Series([-3.5, -2.5, -1.0]))) == [
        "ANOMALY", "WARNING", "NORMAL",
    ]


def test_the_thresholds_are_the_published_ones():
    assert (C.Z_WARNING, C.Z_ANOMALY) == (2.0, 3.0)


# ---------------------------------------------------------------------------
# confusion -- the four counts and the four scores
# ---------------------------------------------------------------------------
def test_counts_are_right_on_a_hand_worked_example():
    truth   = pd.Series([True,  True,  False, False, False])
    flagged = pd.Series([True,  False, True,  False, False])

    c = A.confusion(truth, flagged)
    assert (c["true_positives"], c["false_negatives"],
            c["false_positives"], c["true_negatives"]) == (1, 1, 1, 2)
    assert c["precision"] == pytest.approx(0.5)
    assert c["recall"] == pytest.approx(0.5)
    assert c["f1"] == pytest.approx(0.5)
    assert c["accuracy"] == pytest.approx(0.6)


def test_flagging_nothing_scores_zero_not_nan():
    truth = pd.Series([True, False, False])
    c = A.confusion(truth, pd.Series([False, False, False]))
    assert c["precision"] == 0.0 and c["recall"] == 0.0 and c["f1"] == 0.0


def test_accuracy_is_high_even_for_a_detector_that_flags_nothing():
    """Why the report leads with F1 instead: with anomalies at a few percent, a
    detector that does nothing at all still scores over 90% accuracy.
    """
    truth = pd.Series([True] * 3 + [False] * 97)
    c = A.confusion(truth, pd.Series([False] * 100))
    assert c["accuracy"] > 0.9
    assert c["f1"] == 0.0


def test_a_perfect_detector_scores_one():
    truth = pd.Series([True, False, True, False])
    c = A.confusion(truth, truth.copy())
    assert c["precision"] == 1.0 and c["recall"] == 1.0 and c["f1"] == 1.0


# ---------------------------------------------------------------------------
# iqr_flags -- the cross-check on the z-score rule
# ---------------------------------------------------------------------------
def test_iqr_flags_catch_both_tails():
    r = pd.Series([0.0] * 50 + [500.0, -500.0])
    flags = A.iqr_flags(r)
    assert flags.iloc[-2] and flags.iloc[-1]
    assert flags.sum() == 2
