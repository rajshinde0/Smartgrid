"""Loading occupancy counts and defining what "low occupancy" means.

The occupancy files are small (about 3 MB each), so unlike the energy data they
can be read in one go. The interesting work here is not loading but *defining*:
the I-BLEND occupancy signal never reads zero, so "the building is empty" is not
a state this dataset can report, and the main research question has to be built
on a threshold instead.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


def load_occupancy(building: str) -> pd.DataFrame:
    """One building's occupancy on a gap-free 10-minute index in India time."""
    raw = pd.read_csv(C.occupancy_path(building))
    ts = pd.to_datetime(raw["timestamp"], unit="s", utc=True).dt.tz_convert(C.TIMEZONE)

    # Pass the values as a plain array, not as a Series: handing pandas a Series
    # together with a different index makes it *align* on the Series' own index
    # (0, 1, 2, ...) against the timestamps, which silently produces all-NaN.
    out = pd.DataFrame(
        {"occupancy": raw["occupancy_count"].to_numpy(dtype="float64")},
        index=pd.DatetimeIndex(ts),
    ).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    out.index.name = "ts"

    # Reindex onto a complete grid so missing intervals are explicit NaN rather
    # than silently absent rows.
    full = pd.date_range(out.index.min(), out.index.max(), freq=C.TARGET_FREQ)
    return out.reindex(full).rename_axis("ts")


def low_occupancy_threshold(
    occupancy: pd.Series,
    *,
    fraction: float = C.LOW_OCC_FRACTION,
    percentile: int = C.LOW_OCC_PERCENTILE,
) -> float:
    """The low-occupancy cut-off for one building.

    Defined relative to the building's own scale -- a fraction of its 95th
    percentile -- because an absolute count means completely different things in
    a 600-person dormitory and a 47-person facilities block.
    """
    return float(fraction * np.nanpercentile(occupancy.dropna(), percentile))


def low_occupancy_mask(occupancy: pd.Series, threshold: float) -> pd.Series:
    """Which intervals count as low occupancy. NaN occupancy is never low."""
    return occupancy.notna() & (occupancy <= threshold)


def corrected_occupancy(occupancy: pd.Series, building: str) -> pd.Series:
    """Occupancy with the documented idle-device baseline subtracted.

    The I-BLEND authors note that WiFi counts include devices nobody is using --
    roughly 20 per building, about 50 in the Academic building. Subtracting that
    constant gives a rough estimate of real occupancy.

    This is used **only** for the robustness check in Phase 5, never for the
    headline result, because the baseline is an approximate constant from the
    paper rather than something we measured.
    """
    baseline = C.IDLE_DEVICE_BASELINE.get(building, 20)
    return (occupancy - baseline).clip(lower=0)


def occupancy_summary(occupancy: pd.Series, building: str) -> dict:
    """The distribution facts we quote when explaining the threshold."""
    clean = occupancy.dropna()
    p95 = float(np.percentile(clean, C.LOW_OCC_PERCENTILE))
    threshold = C.LOW_OCC_FRACTION * p95
    mask = low_occupancy_mask(occupancy, threshold)
    return {
        "building": building,
        "n": int(len(clean)),
        "min": float(clean.min()),
        "median": float(clean.median()),
        "p95": p95,
        "max": float(clean.max()),
        "threshold": round(threshold, 2),
        "intervals_low_occ": int(mask.sum()),
        "pct_intervals_low_occ": round(100 * float(mask.sum()) / max(len(clean), 1), 2),
        "threshold_reachable": bool(mask.sum() > 0),
    }
