"""Feature engineering: calendar features, the semester flag, lags and rolling stats.

Everything here is derived from the timestamp or from past values of power, so
nothing leaks information from the future into a model. That matters in Phase 4,
where the train/test split is chronological.
"""

from __future__ import annotations

import warnings

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

    **This is the fallback, not the default.** The real calendar is published
    with the dataset on figshare and `load_official_calendar` reads it; this
    function is used only when those files are missing, and
    `add_calendar_features` warns loudly when it falls back.

    The windows in `config.VACATION_WINDOWS` are the shape of a typical
    IIIT-Delhi academic year (summer vacation mid-May to end of July, winter
    break in the second half of December). Measured against the published
    calendar they agree on only about 68% of days, chiefly because the official
    definition of low activity also counts weekends and public holidays --
    see `compare_calendar_to_approximation`.
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


def load_official_calendar() -> pd.DataFrame | None:
    """The real IIIT-Delhi calendar shipped with I-BLEND, or None if absent.

    One CSV per year, 2013-2017, indexed by date with two columns:

        working_day   1 = a working day, 0 = not
        activity      "H" = high-activity (term-time working day)
                      "L" = low-activity  (vacation, weekend or holiday)

    Note what "L" means: it is *low activity*, which includes weekends and
    public holidays as well as vacations. It is not the same concept as "inside
    a vacation window", and it is the better one -- it is what the people who
    ran the campus actually recorded.
    """
    files = C.calendar_files()
    if not files:
        return None

    frames = [pd.read_csv(path, parse_dates=["Date"]) for path in files]
    calendar = pd.concat(frames, ignore_index=True)
    calendar = calendar.drop_duplicates(subset="Date").set_index("Date").sort_index()
    calendar.index = calendar.index.date
    return calendar


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add hour, weekday, month, weekend and activity/working-day columns.

    Semester and vacation come from the **official calendar** when it is
    present. If it is missing the approximate windows are used instead and the
    frame is marked so the notebooks can say so.
    """
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

    calendar = load_official_calendar()
    if calendar is not None:
        dates = pd.Index(out["date"])
        activity = calendar["activity"].reindex(dates)
        working = calendar["working_day"].reindex(dates)

        # Days outside the published calendar fall back to the approximation
        # rather than becoming NaN, so no row is silently lost.
        approx = is_vacation(idx)
        low = activity.to_numpy() == "L"
        low = np.where(pd.isna(activity.to_numpy()), approx, low)

        out["is_vacation"] = low
        out["is_semester"] = ~low
        out["is_working_day"] = np.where(
            pd.isna(working.to_numpy()), ~out["is_weekend"].to_numpy(),
            working.to_numpy() == 1,
        )
        out["calendar_source"] = "official"
    else:
        # Falling back silently would be the worst outcome: every
        # semester-vs-vacation result would quietly rest on an approximation
        # that agrees with the real calendar on only about two-thirds of days,
        # and nothing downstream would say so.
        warnings.warn(
            "Official IIIT-Delhi calendar not found in "
            f"{C.DATASET_DIR} (looked for {', '.join(C.CALENDAR_GLOBS)}). "
            "Falling back to approximate vacation windows, which agree with "
            "the published calendar on only about 68% of days. "
            "Run `python tools/get_data.py` to fetch it.",
            RuntimeWarning,
            stacklevel=2,
        )
        vacation = is_vacation(idx)
        out["is_vacation"] = vacation
        out["is_semester"] = ~vacation
        out["is_working_day"] = ~out["is_weekend"]
        out["calendar_source"] = "approximated"

    out["period"] = pd.Categorical(
        np.where(out["is_vacation"], "vacation", "semester"),
        categories=["semester", "vacation"],
    )
    return out


def compare_calendar_to_approximation(index: pd.DatetimeIndex) -> dict:
    """How well the fallback approximation matches the official calendar.

    Worth reporting rather than hiding: the approximation used before the
    official calendar was located agrees on only about two-thirds of days.
    """
    calendar = load_official_calendar()
    if calendar is None:
        return {"official_calendar_available": False}

    days = pd.DatetimeIndex(sorted(set(index.normalize())))
    activity = calendar["activity"].reindex(days.date)
    known = ~pd.isna(activity.to_numpy())

    official_low = (activity.to_numpy() == "L")[known]
    approximate_low = is_vacation(days)[known]

    return {
        "official_calendar_available": True,
        "days_compared": int(known.sum()),
        "agreement_pct": round(100 * float((official_low == approximate_low).mean()), 1),
        "official_low_activity_pct": round(100 * float(official_low.mean()), 1),
        "approximated_vacation_pct": round(100 * float(approximate_low.mean()), 1),
    }


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
