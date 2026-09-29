"""Profiling helpers for Phase 0: describe every raw file without loading it all.

Each function reads one file at a time, in chunks, keeping only the columns it
needs. Nothing here modifies the Dataset folder -- it is read-only source data.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

CHUNK_ROWS = 500_000


def file_inventory(directory: Path) -> pd.DataFrame:
    """Every file in a folder with its size in MB, biggest first."""
    rows = [
        {"file": p.name, "size_mb": round(p.stat().st_size / 1024 / 1024, 2)}
        for p in sorted(directory.iterdir())
        if p.is_file()
    ]
    return (
        pd.DataFrame(rows)
        .sort_values("size_mb", ascending=False)
        .reset_index(drop=True)
    )


def head_tail(path: Path, n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """First and last n rows of a CSV, read in chunks so memory stays flat."""
    head = pd.read_csv(path, nrows=n)
    last: pd.DataFrame | None = None
    for chunk in pd.read_csv(path, chunksize=CHUNK_ROWS):
        last = chunk.tail(n)
    tail = last.reset_index(drop=True) if last is not None else head.iloc[0:0]
    return head, tail


def to_ist(unix_seconds: pd.Series) -> pd.Series:
    """UNIX seconds -> Asia/Kolkata, the conversion the I-BLEND readme mandates."""
    return (
        pd.to_datetime(unix_seconds, unit="s", utc=True).dt.tz_convert(C.TIMEZONE)
    )


def profile_energy_csv(path: Path, label: str) -> dict:
    """Coverage, gaps and data-quality counts for one 1-minute energy CSV."""
    cols = list(pd.read_csv(path, nrows=0).columns)
    df = pd.read_csv(path, usecols=[c for c in cols if c != "current"] )

    ts = to_ist(df["timestamp"])
    step = df["timestamp"].diff().dropna()
    span_min = (ts.max() - ts.min()).total_seconds() / 60 + 1
    expected = int(round(span_min))

    out: dict = {
        "file": path.name,
        "label": label,
        "columns": len(cols),
        "rows": len(df),
        "first": ts.min(),
        "last": ts.max(),
        "span_days": round((ts.max() - ts.min()).days + 1, 1),
        "expected_minutes": expected,
        "row_coverage_pct": round(100 * len(df) / expected, 2),
        "gaps_over_1min": int((step > 60).sum()),
        "largest_gap_hours": round(float(step.max()) / 3600, 1),
    }

    if "power" in df:
        p = df["power"]
        out.update(
            {
                "power_min_w": round(float(p.min()), 1),
                "power_mean_w": round(float(p.mean()), 1),
                "power_max_w": round(float(p.max()), 1),
                "power_zero_pct": round(100 * float((p == 0).mean()), 2),
                "power_na_pct": round(100 * float(p.isna().mean()), 2),
            }
        )
    if "power_factor" in df:
        pf = df["power_factor"]
        out["pf_negative_pct"] = round(100 * float((pf < 0).mean()), 2)
        out["pf_min"] = round(float(pf.min()), 3)
        out["pf_max"] = round(float(pf.max()), 3)
    if "voltage" in df:
        v = df["voltage"]
        bad = v.notna() & ((v < C.VOLTAGE_MIN_V) | (v > C.VOLTAGE_MAX_V))
        out["voltage_out_of_range_pct"] = round(100 * float(bad.mean()), 3)
        out["voltage_min"] = round(float(v.min()), 2)
        out["voltage_max"] = round(float(v.max()), 2)

    # `current` is known to be NA early on; count it without holding the column
    if "current" in cols:
        na = 0
        total = 0
        for chunk in pd.read_csv(path, usecols=["current"], chunksize=CHUNK_ROWS):
            na += int(chunk["current"].isna().sum())
            total += len(chunk)
        out["current_na_pct"] = round(100 * na / total, 2)

    del df
    return out


def profile_occupancy_csv(path: Path, building: str) -> dict:
    """Coverage and distribution summary for one 10-minute occupancy CSV."""
    df = pd.read_csv(path)
    ts = to_ist(df["timestamp"])
    occ = df["occupancy_count"]

    span_steps = int((ts.max() - ts.min()).total_seconds() / 600) + 1
    p95 = float(occ.quantile(0.95))
    thr = C.LOW_OCC_FRACTION * p95

    return {
        "file": path.name,
        "building": building,
        "rows": len(df),
        "first": ts.min(),
        "last": ts.max(),
        "span_days": (ts.max() - ts.min()).days + 1,
        "expected_10min_steps": span_steps,
        "row_coverage_pct": round(100 * len(df) / span_steps, 2),
        "occ_min": int(occ.min()),
        "occ_p05": round(float(occ.quantile(0.05)), 1),
        "occ_median": round(float(occ.median()), 1),
        "occ_mean": round(float(occ.mean()), 1),
        "occ_p95": round(p95, 1),
        "occ_max": int(occ.max()),
        "low_occ_threshold": round(thr, 2),
        "pct_rows_at_or_below_threshold": round(100 * float((occ <= thr).mean()), 2),
        "aligned_to_10min": bool((df["timestamp"].astype("int64") % 600 == 0).all()),
    }


def monthly_coverage(path: Path, readings_per_day: int) -> pd.Series:
    """Percent of expected readings actually present, month by month.

    A bar showing only "first timestamp to last timestamp" is misleading: a
    meter can be silent for 200 days in the middle and the bar still looks
    solid. Counting readings per calendar month and dividing by how many that
    month should contain shows the holes.

    `readings_per_day` is 1440 for the 1-minute energy files and 144 for the
    10-minute occupancy files.
    """
    counts: dict = {}
    for chunk in pd.read_csv(path, usecols=["timestamp"], chunksize=CHUNK_ROWS):
        months = to_ist(chunk["timestamp"]).dt.to_period("M").value_counts()
        for period, n in months.items():
            counts[period] = counts.get(period, 0) + int(n)

    actual = pd.Series(counts).sort_index()
    expected = pd.Series(
        {p: p.days_in_month * readings_per_day for p in actual.index}
    )
    return (100 * actual / expected).clip(upper=100)


def coverage_matrix() -> pd.DataFrame:
    """Monthly coverage % for every energy meter and every occupancy file.

    Rows are data sources, columns are calendar months. Missing months appear as
    NaN (nothing recorded at all) rather than as 0, so "never started yet" and
    "recorded nothing this month" stay visually distinct.
    """
    series: dict[str, pd.Series] = {}
    for meter_key in C.METERS:
        series[f"{meter_key} (energy)"] = monthly_coverage(
            C.meter_path(meter_key), readings_per_day=1440
        )
    for building in C.BUILDING_ORDER:
        series[f"{building} (occupancy)"] = monthly_coverage(
            C.occupancy_path(building), readings_per_day=144
        )

    matrix = pd.DataFrame(series).T
    matrix.columns = [str(c) for c in matrix.columns]
    return matrix.reindex(sorted(matrix.columns), axis=1)


def overlap_window(
    energy_profiles: pd.DataFrame, occ_profiles: pd.DataFrame
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """The period where energy and occupancy both exist -- our working window."""
    start = max(energy_profiles["first"].min(), occ_profiles["first"].min())
    end = min(energy_profiles["last"].max(), occ_profiles["last"].max())
    return start, end


def status_missing_by_month(path: Path = None) -> pd.DataFrame:
    """Monthly share of present 1-minute readings, per building.

    Built from data_present_status_buildings.csv, where 1 = reading present and
    0 = missing. Read in chunks; the mean of the 0/1 flags in a month is exactly
    that month's coverage fraction.
    """
    path = path or C.STATUS_BUILDINGS_CSV
    sums: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, chunksize=CHUNK_ROWS, parse_dates=["timestamp"]):
        chunk = chunk.set_index("timestamp")
        month = chunk.index.to_period("M")
        grouped = chunk.groupby(month)
        agg = grouped.sum()
        agg["_n"] = grouped.size()
        sums.append(agg)

    total = pd.concat(sums).groupby(level=0).sum()
    n = total.pop("_n")
    coverage = total.div(n, axis=0) * 100
    coverage.index.name = "month"
    return coverage
