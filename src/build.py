"""Assemble one clean, merged, feature-engineered 10-minute table per building.

This is the pipeline that turns 1.6 GB of raw CSVs into the seven tables every
later phase actually uses:

    raw CSV  --ingest--> 10-min cache  --clean--> flags  --merge--> occupancy
             --features--> hour/weekday/semester/lags/rolling/kWh
             --> data/processed/<Building>_10min.parquet

Run it once; every notebook after Phase 1 just reads the parquet.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import clean, config as C, features, ingest, occupancy as occ

# 10-minute blocks per hour, used to convert block counts into hours
BLOCKS_PER_HOUR = 6


def meter_role(meter_key: str) -> str:
    """'boys_ups' -> 'ups', 'acad_mains' -> 'mains'. Used for column names."""
    return meter_key.rsplit("_", 1)[-1]


def build_building(
    building: str, *, force: bool = False, verbose: bool = True
) -> tuple[pd.DataFrame, dict]:
    """Build the merged 10-minute table for one building.

    For the two dormitories this combines a mains meter and a UPS meter. Their
    powers are kept as separate columns *and* summed, because "which supply keeps
    running when the rooms empty out" is one of the Phase 5 questions. The sum is
    NaN whenever either meter is missing -- adding a measured value to a missing
    one would silently understate the building's total.
    """
    out_path = C.building_parquet(building)
    if out_path.is_file() and not force:
        df = pd.read_parquet(out_path)
        if verbose:
            print(f"[cache] {building}: {len(df):,} rows from {out_path.name}")
        return df, {}

    spec = C.BUILDINGS[building]
    per_meter: dict[str, pd.DataFrame] = {}
    meter_stats: dict[str, dict] = {}

    for meter_key in spec["meters"]:
        raw, _ = ingest.ingest_meter(meter_key, verbose=False)
        cleaned, stats = clean.clean_meter(raw)
        per_meter[meter_role(meter_key)] = cleaned
        meter_stats[meter_key] = stats

    # ---- assemble the building table on a common index --------------------
    frames = []
    for role, table in per_meter.items():
        frames.append(
            table[[
                "power_w", "power_filled_w", "power_min_w", "power_max_w",
                "meter_off", "is_missing", "was_interpolated",
                "outlier_iqr", "outlier_zscore", "n_readings",
            ]].add_suffix(f"_{role}")
        )
    combined = pd.concat(frames, axis=1).sort_index()

    roles = list(per_meter)
    power_cols = [f"power_w_{r}" for r in roles]

    # Total = sum of this building's meters, NaN if any one of them is missing.
    combined["power_w"] = combined[power_cols].sum(axis=1, min_count=len(power_cols))
    combined["meter_off"] = combined[[f"meter_off_{r}" for r in roles]].any(axis=1)
    combined["is_missing"] = combined[[f"is_missing_{r}" for r in roles]].any(axis=1)
    combined["was_interpolated"] = combined[
        [f"was_interpolated_{r}" for r in roles]
    ].any(axis=1)
    combined["outlier_iqr"] = combined[[f"outlier_iqr_{r}" for r in roles]].any(axis=1)
    combined["outlier_zscore"] = combined[
        [f"outlier_zscore_{r}" for r in roles]
    ].any(axis=1)

    # Electrical quality columns come from the mains meter (the UPS is a subset
    # of the same supply and its voltage adds nothing).
    mains_key = spec["meters"][0]
    mains = per_meter[meter_role(mains_key)]
    for col in ("voltage", "power_factor", "pf_neg_frac"):
        if col in mains:
            combined[col] = mains[col]

    # ---- merge with occupancy --------------------------------------------
    occupancy = occ.load_occupancy(building)

    # Inner join: every research question needs both signals, so the working
    # period is where they overlap. This is decision D00-01.
    merged = combined.join(occupancy, how="inner")

    # ---- features ---------------------------------------------------------
    merged = features.add_all_features(merged, power_col="power_w")
    merged["building"] = building
    merged["building_kind"] = spec["kind"]

    # A row is "usable" for analysis when the meter was alive, the reading is
    # present, and we know how many people were there.
    merged["usable"] = (
        merged["power_w"].notna() & ~merged["meter_off"] & merged["occupancy"].notna()
    )

    C.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(out_path)

    stats = {
        "building": building,
        "meters": len(spec["meters"]),
        "rows": len(merged),
        "first": merged.index.min(),
        "last": merged.index.max(),
        "usable_rows": int(merged["usable"].sum()),
        "pct_usable": round(100 * float(merged["usable"].mean()), 2),
        "pct_power_missing": round(100 * float(merged["power_w"].isna().mean()), 2),
        "pct_occupancy_missing": round(
            100 * float(merged["occupancy"].isna().mean()), 2
        ),
        "hours_meter_off": round(float(merged["meter_off"].sum()) / BLOCKS_PER_HOUR, 1),
        "blocks_interpolated": int(merged["was_interpolated"].sum()),
        "outliers_iqr": int(merged["outlier_iqr"].sum()),
        "outliers_zscore": int(merged["outlier_zscore"].sum()),
        "total_kwh": round(float(merged.loc[merged["usable"], "kwh"].sum()), 1),
        "mean_power_w": round(float(merged.loc[merged["usable"], "power_w"].mean()), 1),
    }
    stats["per_meter"] = meter_stats

    if verbose:
        print(
            f"[built] {building:13s} {len(merged):>7,} rows  "
            f"{stats['pct_usable']:>5.1f}% usable  "
            f"{stats['hours_meter_off']:>8,.0f} h meter-off  "
            f"-> {out_path.name}"
        )
    return merged, stats


def build_all(force: bool = False) -> dict[str, dict]:
    """Build every building, one at a time so memory stays flat."""
    all_stats: dict[str, dict] = {}
    for building in C.BUILDING_ORDER:
        _, stats = build_building(building, force=force)
        if stats:
            all_stats[building] = stats
    return all_stats


LONG_COLUMNS = [
    "building", "building_kind", "power_w", "occupancy", "kwh", "date", "hour",
    "weekday", "month", "year", "is_weekend", "is_vacation", "is_semester",
    "period", "meter_off", "is_missing", "usable", "outlier_iqr",
    "outlier_zscore", "power_lag_1h", "power_lag_1d", "power_roll24h_mean",
    "power_roll24h_std", "voltage", "power_factor",
]


def build_long_table(force: bool = False) -> pd.DataFrame:
    """Stack all seven buildings into one long table with a `building` column.

    Wide (one column per building) is convenient for plotting; long (one row per
    building per timestamp) is what `groupby` wants. We build long, because every
    cross-building summary in Phase 2 is a groupby.
    """
    if C.LONG_TABLE_PARQUET.is_file() and not force:
        df = pd.read_parquet(C.LONG_TABLE_PARQUET)
        # A cache written before a column was added to LONG_COLUMNS would be
        # silently missing it, and the failure would surface far away as a
        # KeyError inside a groupby. Check here instead.
        missing = [c for c in LONG_COLUMNS if c not in df.columns]
        if missing:
            print(f"[stale] long table is missing {missing}; rebuilding")
        else:
            print(f"[cache] long table: {len(df):,} rows")
            return df

    parts = []
    for building in C.BUILDING_ORDER:
        df, _ = build_building(building, verbose=False)
        keep = [c for c in LONG_COLUMNS if c in df.columns]
        parts.append(df[keep])

    long = pd.concat(parts, axis=0).sort_index()
    long["building"] = pd.Categorical(
        long["building"], categories=C.BUILDING_ORDER, ordered=False
    )
    long.to_parquet(C.LONG_TABLE_PARQUET)
    print(f"[built] long table: {len(long):,} rows x {len(long.columns)} columns")
    return long


def cross_check_against_wide(building: str, tolerance_pct: float = 1.0) -> dict:
    """Independent check: our per-meter totals vs `all_buildings_power.csv`.

    That file holds every meter's power side by side. It came down the same
    pipeline from the same meters, so agreement is not proof of correctness --
    but a *disagreement* would mean we had mishandled timestamps, units or
    chunk boundaries somewhere. It is a cheap guard against a silent error.
    """
    wide_cols = [c for c, m in C.WIDE_COL_TO_METER.items()
                 if m in C.BUILDINGS[building]["meters"]]

    total = 0.0
    count = 0
    for chunk in pd.read_csv(
        C.ALL_BUILDINGS_POWER_CSV, usecols=["timestamp"] + wide_cols,
        chunksize=500_000,
    ):
        ts = pd.to_datetime(chunk["timestamp"], unit="s", utc=True).dt.tz_convert(
            C.TIMEZONE
        )
        chunk = chunk.set_index(ts)
        values = chunk[wide_cols].sum(axis=1, min_count=len(wide_cols))
        total += float(values.sum(skipna=True))
        count += int(values.notna().sum())

    wide_mean = total / count if count else np.nan

    ours, _ = build_building(building, verbose=False)
    our_meters = [f"power_w_{meter_role(m)}" for m in C.BUILDINGS[building]["meters"]]
    # Compare like with like: the wide file has no occupancy, so compare mean
    # power over all blocks our cache holds, not just the merged window.
    cache = pd.concat(
        [ingest.ingest_meter(m, verbose=False)[0]["power_w"].rename(m)
         for m in C.BUILDINGS[building]["meters"]],
        axis=1,
    )
    our_total = cache.sum(axis=1, min_count=cache.shape[1])
    our_mean = float(our_total.mean())

    diff_pct = 100 * abs(our_mean - wide_mean) / wide_mean if wide_mean else np.nan
    return {
        "building": building,
        "mean_power_from_wide_file_w": round(wide_mean, 1),
        "mean_power_from_our_cache_w": round(our_mean, 1),
        "difference_pct": round(diff_pct, 3),
        "agrees": bool(diff_pct < tolerance_pct),
    }
