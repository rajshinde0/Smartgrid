"""Cleaning rules applied to the 10-minute data: dead meters, outliers, gaps.

The invalid-value rules (impossible power, out-of-range voltage, the sign of
power factor) are applied while reading, in `ingest.py`. This module handles the
things that can only be seen once the data is on a time grid: runs of zeros,
statistical outliers, and short gaps.

A principle runs through all of it: **flag, do not delete.** An outlier in an
energy meter might be a measurement error, or it might be exactly the abnormal
event Phase 6 is built to detect. Deleting them would quietly remove the
phenomenon we are studying, so every judgement is recorded as an extra boolean
column and the original value is left alone.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

BLOCKS_PER_HOUR = 6          # 10-minute blocks in an hour


def flag_meter_off(
    power_max: pd.Series,
    *,
    hours: float = C.DEAD_METER_HOURS,
    bridge_steps: int = C.INTERPOLATE_LIMIT_STEPS,
) -> pd.Series:
    """Flag long unbroken runs of exactly-zero power as "meter off".

    A building really can draw very little at 4 a.m., but it does not draw
    *exactly* 0.000 W for six hours straight -- that is a meter that stopped
    reporting. The Lecture building does this for most of the record.

    We test on the **maximum** power within each 10-minute block, so a block only
    counts as zero if every one of its 1-minute readings was zero.

    **Short gaps bridge a run rather than breaking it.** A missing block carries
    no evidence either way, but letting it split a run meant a single dropout
    inside a ten-hour outage produced two five-hour runs, neither of which
    crossed the threshold, so the whole outage went unflagged and its zeros were
    counted as real consumption. On this dataset that hid 2,413 zero-blocks
    (about 402 hours) in the Lecture building alone. Gaps longer than
    `bridge_steps` still break the run: at that length the absence is its own
    event, not a dropout.

    The flag itself is never set on a missing block -- only on blocks that
    actually read zero.

    Returns a boolean Series aligned to the input.
    """
    min_blocks = int(round(hours * BLOCKS_PER_HOUR))

    is_zero = power_max.eq(0.0)          # NaN compares False, as intended
    is_missing = power_max.isna()

    # Treat a short gap as part of whatever surrounds it, so it neither breaks a
    # zero-run nor becomes one. Only gaps bounded by zeros on both sides can
    # extend a zero-run; a gap next to real consumption stays a break.
    bridged = is_zero.copy()
    short_gap = is_missing & (gap_runs(power_max) <= bridge_steps)
    if short_gap.any():
        # Blank out the missing positions so ffill/bfill reach past them to the
        # nearest block that actually has a reading. Without the mask these are
        # plain booleans with nothing to fill and the result is always False.
        known = is_zero.where(~is_missing)
        zero_before = known.ffill().fillna(False).astype(bool)
        zero_after = known.bfill().fillna(False).astype(bool)
        bridged |= short_gap & zero_before & zero_after

    # Give every unbroken run of identical values its own group id, then measure
    # how long each run is. This is the standard run-length trick.
    run_id = (bridged != bridged.shift()).cumsum()
    run_length = bridged.groupby(run_id).transform("size")

    # A bridged gap counts towards the run's length but is not itself flagged:
    # we never claim a meter was off during a block we have no reading for.
    return is_zero & bridged & (run_length >= min_blocks)


def zero_run_lengths(power_max: pd.Series) -> pd.Series:
    """Length in hours of every unbroken run of exactly-zero power.

    Used to check whether the dead-meter rule is separating two genuinely
    different things. A building switched off at the mains overnight produces
    runs of roughly 10-14 hours; a meter that has stopped reporting produces
    runs of days or months. If both populations are present, a single threshold
    cannot distinguish them, and that has to be said out loud.
    """
    is_zero = power_max.fillna(-1.0).eq(0.0)
    run_id = (is_zero != is_zero.shift()).cumsum()
    runs = is_zero.groupby(run_id).agg(["first", "size"])
    zero_runs = runs.loc[runs["first"], "size"]
    return (zero_runs / BLOCKS_PER_HOUR).rename("hours").reset_index(drop=True)


def flag_outliers_iqr(series: pd.Series, k: float = 1.5) -> pd.Series:
    """Flag values outside the Tukey fences Q1 - k*IQR and Q3 + k*IQR."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return (series < q1 - k * iqr) | (series > q3 + k * iqr)


def flag_outliers_zscore(
    series: pd.Series, threshold: float = C.ZSCORE_OUTLIER
) -> pd.Series:
    """Flag values more than `threshold` standard deviations from the mean."""
    mean, sd = series.mean(), series.std()
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(False, index=series.index)
    return ((series - mean).abs() / sd) > threshold


def iqr_fences(series: pd.Series, k: float = 1.5) -> tuple[float, float]:
    """The two Tukey fence values, for reporting."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return float(q1 - k * iqr), float(q3 + k * iqr)


def gap_runs(series: pd.Series) -> pd.Series:
    """Length, in blocks, of the run of missing values each row belongs to.

    Rows that are not missing get the length of their own non-missing run, so
    only combine this with an `isna()` mask.
    """
    missing = series.isna()
    run_id = (missing != missing.shift()).cumsum()
    return missing.groupby(run_id).transform("size")


def interpolate_short_gaps(
    series: pd.Series, *, limit_steps: int = C.INTERPOLATE_LIMIT_STEPS
) -> tuple[pd.Series, pd.Series]:
    """Fill gaps of at most `limit_steps` missing blocks; leave longer ones **whole**.

    Filling a 20-minute gap between two similar readings is safe. Filling a
    200-day gap would be inventing data.

    **Why this does not use pandas' `limit=` argument.** `limit` caps the number
    of *consecutive* NaNs filled, which is not the same rule: given a 200-day
    gap it fills the first `limit` blocks and stops, rather than skipping the
    gap. Those blocks are drawn along a straight line between the last reading
    before the gap and the first one after it -- readings that may be months
    apart -- so they are exactly the invented data the limit was meant to
    prevent. On this dataset that behaviour produced 5,301 fabricated blocks
    against 2,498 legitimate ones.

    So we measure each gap's **whole** length first and fill only the runs that
    are short enough in their entirety.

    Returns the filled series and a boolean Series marking which values were
    filled rather than measured -- so nothing downstream can mistake an
    interpolated value for a reading.
    """
    missing = series.isna()
    short_gap = missing & (gap_runs(series) <= limit_steps)

    # Interpolate without a limit, then keep the result only where the gap was
    # short enough. limit_area="inside" still refuses to extrapolate before the
    # first reading or after the last.
    candidate = series.interpolate(method="time", limit_area="inside")
    filled = series.where(~short_gap, candidate)

    return filled, short_gap & filled.notna()


def clean_meter(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply the 10-minute-grid cleaning rules to one meter's table.

    Adds these columns, and never removes a row:

    * `meter_off`      -- a long run of exactly-zero power (see flag_meter_off)
    * `is_missing`     -- the block contained no readings at all
    * `power_filled`   -- power after short gaps are interpolated
    * `was_interpolated` -- this value was filled, not measured
    * `outlier_iqr`, `outlier_zscore` -- flagged, never dropped
    """
    out = df.copy()

    out["is_missing"] = out["n_readings"].eq(0)
    out["meter_off"] = flag_meter_off(out["power_max_w"])

    # Interpolate only genuine short gaps. Blocks during a dead meter are not
    # gaps -- they are a known zero -- so they are excluded from the fill.
    gap_source = out["power_w"].where(~out["meter_off"])
    filled, interpolated = interpolate_short_gaps(gap_source)
    out["power_filled_w"] = filled
    out["was_interpolated"] = interpolated

    # Outliers are judged on real, live readings only: including a dead meter's
    # zeros would drag the mean down and make normal nights look abnormal.
    live = out.loc[~out["meter_off"] & out["power_w"].notna(), "power_w"]
    out["outlier_iqr"] = False
    out["outlier_zscore"] = False
    if len(live) > 10:
        out.loc[live.index, "outlier_iqr"] = flag_outliers_iqr(live)
        out.loc[live.index, "outlier_zscore"] = flag_outliers_zscore(live)

    low_fence, high_fence = iqr_fences(live) if len(live) > 10 else (np.nan, np.nan)

    stats = {
        "blocks": len(out),
        "blocks_missing": int(out["is_missing"].sum()),
        "blocks_meter_off": int(out["meter_off"].sum()),
        "hours_meter_off": round(float(out["meter_off"].sum()) / BLOCKS_PER_HOUR, 1),
        "blocks_interpolated": int(out["was_interpolated"].sum()),
        "outliers_iqr": int(out["outlier_iqr"].sum()),
        "outliers_zscore": int(out["outlier_zscore"].sum()),
        "iqr_low_fence_w": round(low_fence, 1) if np.isfinite(low_fence) else None,
        "iqr_high_fence_w": round(high_fence, 1) if np.isfinite(high_fence) else None,
        "pct_usable": round(
            100 * float((~out["is_missing"] & ~out["meter_off"]).mean()), 2
        ),
    }
    return out, stats
