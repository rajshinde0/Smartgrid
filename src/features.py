"""Feature engineering: calendar features, the semester flag, lags and rolling stats.

Everything here is derived from the timestamp or from past values of power, so
nothing leaks information from the future into a model. That matters in Phase 4,
where the train/test split is chronological.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

WEEKDAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]

BLOCKS_PER_HOUR = 6
BLOCKS_PER_DAY = 144


def is_vacation(index: pd.DatetimeIndex) -> np.ndarray:
    """True for dates inside an approximate IIIT-Delhi vacation window.

    **This is an approximation and is logged as such.** The I-BLEND project site
    does not publish an academic calendar -- we checked; the repository contains
    only the website's assets and the reading scripts. So the windows in
    `config.VACATION_WINDOWS` are taken from the shape of a typical IIIT-Delhi
    academic year (summer vacation from mid-May to the end of July, winter break
    in the second half of December).

    `validate_semester_flag` below checks the approximation against the data
    itself, by testing whether dormitory occupancy actually collapses inside
    these windows.
    """
    month = index.month.to_numpy()
    day = index.day.to_numpy()
    flag = np.zeros(len(index), dtype=bool)

    for (start_m, start_d), (end_m, end_d) in C.VACATION_WINDOWS:
        after_start = (month > start_m) | ((month == start_m) & (day >= start_d))
        before_end = (month < end_m) | ((month == end_m) & (day <= end_d))
        if (start_m, start_d) <= (end_m, end_d):
            flag |= after_start & before_end
        else:                       # a window that wraps around new year
            flag |= after_start | before_end
    return flag


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add hour, weekday, month, weekend and semester/vacation columns."""
    out = df.copy()
    idx = out.index

    out["hour"] = idx.hour
    out["minute_of_day"] = idx.hour * 60 + idx.minute
    out["month"] = idx.month
    out["year"] = idx.year
    out["date"] = idx.date

    # Day of week is *ordinal*: Monday really does come before Tuesday, and an
    # ordered categorical is how pandas represents that. It also makes charts
    # come out in calendar order instead of alphabetical order.
    out["weekday"] = pd.Categorical(
        idx.day_name(), categories=WEEKDAY_ORDER, ordered=True
    )
    out["is_weekend"] = idx.dayofweek >= 5

    vacation = is_vacation(idx)
    out["is_vacation"] = vacation
    out["is_semester"] = ~vacation
    out["period"] = pd.Categorical(
        np.where(vacation, "vacation", "semester"),
        categories=["semester", "vacation"],
    )
    return out


def add_energy_column(df: pd.DataFrame, power_col: str = "power_w") -> pd.DataFrame:
    """Add kWh consumed in each 10-minute block.

    Power is an instantaneous rate in watts; energy is power multiplied by time.
    A 10-minute block is 1/6 of an hour, so
    kWh = watts / 1000 * (10 / 60). This is the column every "how much energy"
    question is answered from -- never by averaging watts.
    """
    out = df.copy()
    hours = 10 / 60
    out["kwh"] = out[power_col] / 1000.0 * hours
    return out


def add_lag_features(df: pd.DataFrame, power_col: str = "power_w") -> pd.DataFrame:
    """Add power one hour ago and one day ago.

    Both are strictly past values, so using them as model inputs does not leak
    the future. The 1-day lag is the strongest single predictor in most building
    energy series, because buildings repeat their daily routine.
    """
    out = df.copy()
    out["power_lag_1h"] = out[power_col].shift(BLOCKS_PER_HOUR)
    out["power_lag_1d"] = out[power_col].shift(BLOCKS_PER_DAY)
    return out


def add_rolling_features(df: pd.DataFrame, power_col: str = "power_w") -> pd.DataFrame:
    """Add a 24-hour rolling mean and standard deviation of power.

    `closed="left"` excludes the current block, so the window describes the
    24 hours *before* each point and never includes the value being predicted.
    """
    out = df.copy()
    window = out[power_col].rolling("24h", closed="left", min_periods=BLOCKS_PER_HOUR)
    out["power_roll24h_mean"] = window.mean()
    out["power_roll24h_std"] = window.std()
    return out


def add_all_features(df: pd.DataFrame, power_col: str = "power_w") -> pd.DataFrame:
    """Every derived column, in one call."""
    out = add_calendar_features(df)
    out = add_energy_column(out, power_col)
    out = add_lag_features(out, power_col)
    out = add_rolling_features(out, power_col)
    return out


def validate_semester_flag(
    occupancy: pd.Series, index: pd.DatetimeIndex | None = None
) -> dict:
    """Check the approximate calendar against the data.

    If our vacation windows are roughly right, dormitory occupancy should be
    clearly lower inside them than outside. This returns the two medians and
    their ratio so the approximation can be reported with evidence rather than
    asserted.
    """
    index = index if index is not None else occupancy.index
    vacation = is_vacation(index)

    in_vac = occupancy[vacation].dropna()
    in_sem = occupancy[~vacation].dropna()

    median_vac = float(in_vac.median()) if len(in_vac) else np.nan
    median_sem = float(in_sem.median()) if len(in_sem) else np.nan

    return {
        "median_occupancy_semester": round(median_sem, 1),
        "median_occupancy_vacation": round(median_vac, 1),
        "ratio_vacation_to_semester": round(median_vac / median_sem, 3)
        if median_sem
        else np.nan,
        "n_semester_intervals": int(len(in_sem)),
        "n_vacation_intervals": int(len(in_vac)),
    }


def monthly_occupancy_profile(occupancy: pd.Series) -> pd.Series:
    """Median occupancy by calendar month -- used to sanity-check the calendar."""
    return occupancy.groupby(occupancy.index.month).median()
