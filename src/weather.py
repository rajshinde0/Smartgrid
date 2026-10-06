"""Outdoor weather for the analysis window, from Delhi airport METAR.

Why this module exists
----------------------
The largest limitation in this project was that no weather data covered the
study period. Delhi's long summer vacation is also its hottest season, so some
of what we measured as "energy used while nearly empty" is air conditioning
cooling an empty building. That is still waste, but a different kind needing a
different remedy, and without temperature the two could not be separated.

I-BLEND does ship a weather file, but it covers March-June 2018 and does not
overlap the 2014-2017 analysis window at all. So the temperature used here comes
from **METAR** -- the routine weather report every airport issues -- for Delhi
Indira Gandhi International (ICAO **VIDP**), archived by Iowa State University's
Environmental Mesonet and free to download.

What it is and is not
---------------------
VIDP is about 25 km from the IIIT-Delhi campus. Airport weather is **not**
campus weather: urban heat island, local shading and built form all differ. This
replaces an unmeasured confound with a measured proxy -- better, not perfect --
and every result derived from it carries that caveat.

Cooling degree hours
--------------------
The standard way to relate building power to outdoor temperature is not raw
temperature but **cooling degree hours**: `max(0, T - T_base)`. Below the base
temperature a building needs no cooling and the relationship is flat; above it,
load rises roughly linearly. `T_base` is *fitted* per building here rather than
assumed, because each building starts cooling at its own setpoint.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from . import clean, config as C

# IEM's ASOS/AWOS archive. Returns CSV, needs no key, and accepts a timezone so
# the timestamps come back already in Asia/Kolkata.
IEM_ENDPOINT = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

# Gaps up to this many 10-minute blocks are interpolated. Two hours is generous
# compared with the 30 minutes allowed for power, and deliberately so: outdoor
# temperature moves slowly and smoothly, where building power does not.
WEATHER_GAP_LIMIT_STEPS = 12


def metar_url(start: pd.Timestamp, end: pd.Timestamp) -> str:
    """The IEM request URL for our station and date range."""
    fields = "&".join(f"data={f}" for f in ("tmpc", "relh"))
    return (
        f"{IEM_ENDPOINT}?station={C.METAR_STATION}&{fields}"
        f"&year1={start.year}&month1={start.month}&day1={start.day}"
        f"&year2={end.year}&month2={end.month}&day2={end.day}"
        "&tz=Asia%2FKolkata&format=onlycomma&latlon=no"
        "&missing=M&trace=T&direct=no&report_type=3&report_type=4"
    )


def fetch_metar(
    *,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    force: bool = False,
    verbose: bool = True,
) -> Path:
    """Download the METAR archive to data/weather/, or reuse the cache.

    Like the energy data, this is fetched rather than committed: the project
    rule is that data files never enter the repository.
    """
    start = start or pd.Timestamp(C.WEATHER_START)
    end = end or pd.Timestamp(C.WEATHER_END)
    path = C.METAR_CSV

    if path.is_file() and not force:
        if verbose:
            size = path.stat().st_size / 1024
            print(f"[cache] weather: {path.name} ({size:,.0f} KB)")
        return path

    url = metar_url(start, end)
    path.parent.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"[get ] METAR for {C.METAR_STATION}, {start:%Y-%m-%d} to {end:%Y-%m-%d}")

    try:
        with urllib.request.urlopen(url, timeout=300) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"Could not download METAR data: {exc}\n"
            f"Fetch it by hand from:\n  {url}\n"
            f"and save it as {path}"
        ) from exc

    if len(payload) < 1000:
        raise RuntimeError(
            f"METAR download returned only {len(payload)} bytes -- the archive "
            f"may be unavailable. URL:\n  {url}"
        )

    path.write_bytes(payload)
    if verbose:
        print(f"[saved] {path.name} ({len(payload) / 1024:,.0f} KB)")
    return path


def load_weather(*, fetch: bool = True, verbose: bool = False) -> pd.DataFrame:
    """Temperature and humidity on the project's 10-minute grid.

    METAR is reported roughly every 30 minutes, so it is resampled up to the
    10-minute grid by time interpolation. Only **short** gaps are filled, using
    the same whole-run rule as `clean.interpolate_short_gaps`: a run of missing
    values is filled only if the entire run is short enough, so a multi-day
    outage is never partly filled along a line drawn across it.
    """
    path = C.METAR_CSV
    if not path.is_file():
        if not fetch:
            raise FileNotFoundError(
                f"{path} not found. Run `python tools/get_data.py --weather`."
            )
        fetch_metar(verbose=verbose)

    # "M" marks a missing value and "T" a trace; both must become NaN rather
    # than poisoning the column into object dtype.
    raw = pd.read_csv(path, na_values=["M", "T", ""], low_memory=False)

    ts = pd.to_datetime(raw["valid"], errors="coerce")
    frame = pd.DataFrame(
        {
            "temp_c": pd.to_numeric(raw["tmpc"], errors="coerce").to_numpy(),
            "relh": pd.to_numeric(raw["relh"], errors="coerce").to_numpy(),
        },
        index=pd.DatetimeIndex(ts),
    )
    frame = frame[frame.index.notna()].sort_index()
    frame = frame[~frame.index.duplicated(keep="first")]

    # The file has no timezone marker but IEM was asked for Asia/Kolkata, so
    # label it as such rather than converting.
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize(C.TIMEZONE)

    # Snap onto the 10-minute grid, then interpolate only genuinely short gaps.
    grid = pd.date_range(
        frame.index.min().floor(C.TARGET_FREQ),
        frame.index.max().ceil(C.TARGET_FREQ),
        freq=C.TARGET_FREQ,
    )
    out = frame.reindex(frame.index.union(grid)).sort_index()

    for column in ("temp_c", "relh"):
        short = out[column].isna() & (
            clean.gap_runs(out[column]) <= WEATHER_GAP_LIMIT_STEPS
        )
        filled = out[column].interpolate(method="time", limit_area="inside")
        out[column] = out[column].where(~short, filled)

    out = out.reindex(grid)
    out.index.name = "ts"
    return out


def cooling_degree_hours(temp_c: pd.Series, base: float) -> pd.Series:
    """Cooling degree hours per 10-minute block.

    `max(0, T - base)` is degrees above the point where cooling starts; dividing
    by six converts a degree-hour rate into the degree-hours accumulated in one
    ten-minute block. Zero whenever it is cooler than the base, which is the
    whole point -- a building needs no cooling on a mild day.
    """
    return (temp_c - base).clip(lower=0) / 6.0


def fit_base_temperature(
    power_w: pd.Series,
    temp_c: pd.Series,
    *,
    candidates=None,
) -> dict:
    """Find the temperature at which a building starts responding to heat.

    Scans candidate base temperatures and keeps the one whose cooling-degree
    regression explains most of the variation in power. This is the standard
    changepoint approach: rather than assuming a setpoint, we let each building
    tell us its own, and the fitted value is itself worth reporting.

    Returns the best base, its R-squared, and the fitted slope and intercept --
    the intercept being load that does not respond to weather at all.
    """
    from sklearn.linear_model import LinearRegression

    candidates = candidates if candidates is not None else C.CDH_BASE_SCAN

    pair = pd.DataFrame({"power": power_w, "temp": temp_c}).dropna()
    if len(pair) < 100:
        return {"base_c": np.nan, "r2": np.nan, "slope_w_per_degree_hour": np.nan,
                "intercept_w": np.nan, "n": len(pair)}

    best = {"r2": -np.inf}
    y = pair["power"].to_numpy()

    for base in candidates:
        cdh = cooling_degree_hours(pair["temp"], base).to_numpy().reshape(-1, 1)
        if cdh.max() <= 0:
            continue                      # never warm enough to tell anything
        model = LinearRegression().fit(cdh, y)
        r2 = model.score(cdh, y)
        if r2 > best["r2"]:
            best = {
                "base_c": float(base),
                "r2": float(r2),
                "slope_w_per_degree_hour": float(model.coef_[0]),
                "intercept_w": float(model.intercept_),
                "n": int(len(pair)),
            }

    return best if np.isfinite(best["r2"]) else {
        "base_c": np.nan, "r2": np.nan, "slope_w_per_degree_hour": np.nan,
        "intercept_w": np.nan, "n": int(len(pair)),
    }


def _blank_decomposition(n: int, reason: str) -> dict:
    """A result with every key present and nothing claimed."""
    return {
        "n": int(n), "base_c": np.nan, "r2": np.nan, "mean_power_kw": np.nan,
        "schedule_kw": np.nan, "weather_kw": np.nan,
        "weather_share_pct": np.nan, "slope_w_per_degree_hour": np.nan,
        "mean_cdh": np.nan, "identifiable": False, "reason": reason,
    }


def decompose_low_occupancy(
    df: pd.DataFrame,
    low_occ_mask: pd.Series,
    *,
    power_col: str = "power_w",
) -> dict:
    """Split low-occupancy consumption into weather-driven and schedule-driven.

    Within the intervals where a building is nearly empty, fit

        power = intercept + slope x cooling_degree_hours + hour-of-day effects

    and read the two parts off the fit:

    * **intercept** -- power drawn regardless of both weather and people. A
      controls and commissioning problem.
    * **slope x mean CDH** -- cooling an empty building. A setpoint problem.

    They have different remedies, which is why separating them is worth the
    trouble.

    **Why hour-of-day is controlled for.** Nearly half of all low-occupancy
    intervals fall between midnight and 6 a.m., when it is both empty *and*
    cool. Without hour dummies the fit confuses "cooler at night" with "needs
    less cooling", and the cooling response comes out far too weak -- on this
    data, R-squared roughly trebles once hour is included.

    **When the answer is "cannot tell".** In some buildings the low-occupancy
    intervals are themselves seasonal: the Library and Lecture building are
    *closed* during the hot vacation months, so within that sample high
    temperature coincides with a shut building and the fitted slope comes out
    negative. That is a confound between season and usage, not a cooling
    response, and a negative "weather share" would be nonsense. Those buildings
    are returned with `identifiable=False` and a reason rather than a number.
    """
    from sklearn.linear_model import LinearRegression

    sub = df.loc[low_occ_mask, [power_col, "temp_c", "hour"]].dropna()
    if len(sub) < 500:
        return _blank_decomposition(len(sub), "too few low-occupancy intervals")

    hours = pd.get_dummies(sub["hour"], prefix="h", drop_first=True)
    y = sub[power_col].to_numpy()

    best = {"r2": -np.inf}
    for base in C.CDH_BASE_SCAN:
        cdh = cooling_degree_hours(sub["temp_c"], base)
        if cdh.max() <= 0:
            continue
        design = pd.concat([cdh.rename("cdh"), hours], axis=1)
        model = LinearRegression().fit(design, y)
        r2 = model.score(design, y)
        if r2 > best["r2"]:
            best = {
                "r2": float(r2),
                "base_c": float(base),
                "slope": float(model.coef_[0]),
                "mean_cdh": float(cdh.mean()),
            }

    if not np.isfinite(best["r2"]):
        return _blank_decomposition(len(sub), "no warm intervals to fit against")

    if best["slope"] <= 0:
        out = _blank_decomposition(
            len(sub),
            "cooling response not identifiable: within this building's "
            "low-occupancy intervals the hot months are vacation closures, so "
            "temperature and usage are confounded and the fitted slope is "
            "negative",
        )
        out.update({"base_c": best["base_c"], "r2": round(best["r2"], 4),
                    "slope_w_per_degree_hour": round(best["slope"], 1),
                    "mean_power_kw": round(float(y.mean()) / 1000, 2)})
        return out

    mean_power = float(y.mean())
    weather_w = best["slope"] * best["mean_cdh"]

    return {
        "n": int(len(sub)),
        "base_c": best["base_c"],
        "r2": round(best["r2"], 4),
        "mean_power_kw": round(mean_power / 1000, 2),
        "schedule_kw": round((mean_power - weather_w) / 1000, 2),
        "weather_kw": round(weather_w / 1000, 2),
        "weather_share_pct": round(100 * weather_w / mean_power, 1)
        if mean_power else np.nan,
        "slope_w_per_degree_hour": round(best["slope"], 1),
        "mean_cdh": round(best["mean_cdh"], 3),
        "identifiable": True,
        "reason": "",
    }
