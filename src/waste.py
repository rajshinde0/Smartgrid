"""The headline calculation: how much energy is used while a building is nearly empty.

The central definition
----------------------
I-BLEND occupancy never reads zero -- the minimum in every building is 1, because
WiFi counts idle devices. So "energy used while the building is empty" is not a
quantity this dataset can report, and the question has to be asked about *low*
occupancy against a stated threshold:

    low occupancy  =  occupancy <= LOW_OCC_FRACTION x (that building's p95 occupancy)

The threshold is **relative to each building's own scale** because an absolute
count is not comparable across a 600-person dormitory and a 47-person facilities
block. Because the choice of 5% is a judgement, every result is accompanied by a
sensitivity curve across 0-20% so a reader can see how much the answer depends on
it.

What counts as energy
---------------------
Only **usable** intervals: the meter was alive (not flagged `meter_off`), the
reading exists, and the occupancy count exists. Both the numerator and the
denominator use the same set, so the share is a genuine proportion of measured
consumption rather than an artefact of missing data. Every table reports the
coverage alongside the share.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import clean, config as C, ingest, occupancy as occ

BLOCKS_PER_HOUR = 6


def low_occupancy_share(
    df: pd.DataFrame,
    *,
    fraction: float = C.LOW_OCC_FRACTION,
    occupancy_col: str = "occupancy",
    usable_col: str = "usable",
) -> dict:
    """Share of a building's measured energy consumed at low occupancy."""
    usable = df[df[usable_col] & df[occupancy_col].notna() & df["kwh"].notna()]
    if usable.empty:
        return {"threshold": np.nan, "share_pct": np.nan, "reachable": False}

    p95 = float(np.percentile(usable[occupancy_col], C.LOW_OCC_PERCENTILE))
    threshold = fraction * p95
    low = usable[occupancy_col] <= threshold

    total_kwh = float(usable["kwh"].sum())
    low_kwh = float(usable.loc[low, "kwh"].sum())

    return {
        "threshold": round(threshold, 2),
        "p95_occupancy": round(p95, 1),
        "intervals_total": int(len(usable)),
        "intervals_low": int(low.sum()),
        "pct_intervals_low": round(100 * float(low.mean()), 2),
        "total_kwh": round(total_kwh, 1),
        "low_occ_kwh": round(low_kwh, 1),
        "share_pct": round(100 * low_kwh / total_kwh, 2) if total_kwh else np.nan,
        "mean_power_low_w": round(float(usable.loc[low, "power_w"].mean()), 1)
        if low.any() else np.nan,
        "mean_power_all_w": round(float(usable["power_w"].mean()), 1),
        "reachable": bool(low.sum() > 0),
    }


def sensitivity_curve(
    df: pd.DataFrame,
    *,
    fractions=C.SENSITIVITY_FRACTIONS,
    occupancy_col: str = "occupancy",
) -> pd.DataFrame:
    """Recompute the share as the threshold moves from 0% to 20% of p95.

    This is the check that stops the headline resting on one arbitrary number. A
    result that swings wildly across the curve is fragile; one that rises
    smoothly is robust, and the curve itself shows a reader what any other
    threshold would have given.
    """
    rows = []
    for fraction in fractions:
        result = low_occupancy_share(df, fraction=fraction, occupancy_col=occupancy_col)
        rows.append({
            "fraction_of_p95": fraction,
            "threshold_occupancy": result["threshold"],
            "pct_intervals_low": result["pct_intervals_low"],
            "share_pct": result["share_pct"],
            "reachable": result["reachable"],
        })
    return pd.DataFrame(rows)


def out_of_hours_share(
    df: pd.DataFrame,
    *,
    open_hour: int = 8,
    close_hour: int = 18,
    weekdays_only: bool = True,
) -> dict:
    """Share of energy used outside normal working hours, by the clock alone.

    This is the definition used by Masoso & Grobler (2010), who audited
    commercial buildings and found 56% of energy consumed outside working hours.
    Computing it here lets us compare like with like -- and, more importantly,
    lets us show how a clock-based rule and an occupancy-based rule differ.

    They are not the same question. A clock rule calls 3 p.m. on a vacation
    Tuesday "occupied" when the building is empty, and calls 7 p.m. on an exam
    night "unoccupied" when the library is full. That difference is the whole
    point of an occupancy-aware analysis.
    """
    usable = df[df["usable"] & df["kwh"].notna()]
    if usable.empty:
        return {"share_pct": np.nan}

    in_hours = (usable["hour"] >= open_hour) & (usable["hour"] < close_hour)
    if weekdays_only and "is_weekend" in usable.columns:
        in_hours &= ~usable["is_weekend"].astype(bool)

    total = float(usable["kwh"].sum())
    out_kwh = float(usable.loc[~in_hours, "kwh"].sum())
    return {
        "definition": f"outside {open_hour:02d}:00-{close_hour:02d}:00"
                      + (" on weekdays" if weekdays_only else ""),
        "pct_intervals_out_of_hours": round(100 * float((~in_hours).mean()), 2),
        "total_kwh": round(total, 1),
        "out_of_hours_kwh": round(out_kwh, 1),
        "share_pct": round(100 * out_kwh / total, 2) if total else np.nan,
    }


def intensity_ratio(result: dict) -> float:
    """Mean power when nearly empty, as a fraction of mean power overall.

    This is the number that makes the headline concrete. A ratio of 1.0 means the
    building draws exactly as much when nearly empty as it does on average -- it
    is not responding to its occupants at all. A ratio of 0.3 means it relaxes
    substantially.

    It is more directly interpretable than the energy share, because the share
    also depends on *how often* the building is nearly empty, which is a fact
    about the campus timetable rather than about the building.
    """
    if not result.get("reachable") or not result.get("mean_power_all_w"):
        return np.nan
    return round(result["mean_power_low_w"] / result["mean_power_all_w"], 3)


def first_reachable_fraction(curve: pd.DataFrame) -> float | None:
    """The lowest threshold on the curve that captures any data at all.

    Needed for Facilities, whose occupancy never falls to 5% of its own 95th
    percentile, so the standard threshold captures nothing.
    """
    reachable = curve[curve["reachable"]]
    return float(reachable["fraction_of_p95"].iloc[0]) if not reachable.empty else None


def by_period(df: pd.DataFrame, *, fraction: float = C.LOW_OCC_FRACTION) -> pd.DataFrame:
    """Low-occupancy share computed separately for semester and vacation.

    The threshold is fixed from the **whole** record rather than recomputed
    within each period. Recomputing it would move the definition of "low" between
    the two groups and make them incomparable -- a vacation-specific p95 would be
    lower, so its threshold would be lower, and the comparison would measure the
    threshold rather than the behaviour.
    """
    usable = df[df["usable"] & df["occupancy"].notna() & df["kwh"].notna()]
    if usable.empty:
        return pd.DataFrame()

    threshold = fraction * float(
        np.percentile(usable["occupancy"], C.LOW_OCC_PERCENTILE)
    )
    rows = []
    for period, part in usable.groupby("period", observed=True):
        low = part["occupancy"] <= threshold
        total = float(part["kwh"].sum())
        rows.append({
            "period": str(period),
            "threshold": round(threshold, 2),
            "intervals": int(len(part)),
            "total_kwh": round(total, 1),
            "low_occ_kwh": round(float(part.loc[low, "kwh"].sum()), 1),
            "share_pct": round(100 * float(part.loc[low, "kwh"].sum()) / total, 2)
            if total else np.nan,
            "mean_power_w": round(float(part["power_w"].mean()), 1),
        })
    return pd.DataFrame(rows)


def mains_vs_ups(building: str, df: pd.DataFrame,
                 *, fraction: float = C.LOW_OCC_FRACTION) -> pd.DataFrame:
    """For a dormitory, the low-occupancy share of each supply separately.

    Answers a question only this dataset can answer: when the rooms empty out,
    which supply keeps running -- the mains, or the backup UPS feed?
    """
    roles = [c.replace("power_w_", "") for c in df.columns
             if c.startswith("power_w_")]
    if len(roles) < 2:
        return pd.DataFrame()

    usable = df[df["usable"] & df["occupancy"].notna()]
    threshold = fraction * float(
        np.percentile(usable["occupancy"], C.LOW_OCC_PERCENTILE)
    )
    low = usable["occupancy"] <= threshold

    hours = 10 / 60
    rows = []
    for role in roles:
        power = usable[f"power_w_{role}"]
        kwh = power / 1000 * hours
        total = float(kwh.sum())
        rows.append({
            "building": building,
            "supply": role,
            "total_kwh": round(total, 1),
            "low_occ_kwh": round(float(kwh[low].sum()), 1),
            "share_pct": round(100 * float(kwh[low].sum()) / total, 2)
            if total else np.nan,
            "mean_power_w": round(float(power.mean()), 1),
            "mean_power_low_occ_w": round(float(power[low].mean()), 1),
        })
    return pd.DataFrame(rows)


def night_minimum(df: pd.DataFrame, start_hour: int = 2, end_hour: int = 5) -> float:
    """Median power in the small hours -- an independent read on the base load.

    Model A estimates the base load by extrapolating a fitted line to zero
    occupancy. This measures something similar directly, without any model. If
    the two agree, the base load is real rather than an artefact of the fit.
    """
    usable = df[df["usable"]]
    night = usable[(usable["hour"] >= start_hour) & (usable["hour"] <= end_hour)]
    return float(night["power_w"].median()) if len(night) else np.nan


def recompute_with_dead_meter_rule(
    building: str, hours: float
) -> pd.DataFrame | None:
    """Rebuild one building's usable flag under a different dead-meter threshold.

    Phase 1 found that a building switched off at the mains overnight and a dead
    meter both read exactly 0 W, and that the specified 6-hour rule cannot tell
    them apart (decision D01-07). This rebuilds the table with a longer rule --
    24 hours, say -- so the Lecture building's headline figure can be quoted
    under both and the reader can see what the ambiguity is worth.
    """
    spec = C.BUILDINGS[building]
    frames = []
    for meter_key in spec["meters"]:
        raw, _ = ingest.ingest_meter(meter_key, verbose=False)
        role = meter_key.rsplit("_", 1)[-1]
        table = raw.copy()
        table["meter_off"] = clean.flag_meter_off(table["power_max_w"], hours=hours)
        table["is_missing"] = table["n_readings"].eq(0)
        frames.append(
            table[["power_w", "meter_off", "is_missing"]].add_suffix(f"_{role}")
        )

    combined = pd.concat(frames, axis=1).sort_index()
    roles = [m.rsplit("_", 1)[-1] for m in spec["meters"]]
    power_cols = [f"power_w_{r}" for r in roles]
    combined["power_w"] = combined[power_cols].sum(axis=1, min_count=len(power_cols))
    combined["meter_off"] = combined[[f"meter_off_{r}" for r in roles]].any(axis=1)

    occupancy = occ.load_occupancy(building)
    merged = combined.join(occupancy, how="inner")
    merged["kwh"] = merged["power_w"] / 1000 * (10 / 60)
    merged["usable"] = (
        merged["power_w"].notna() & ~merged["meter_off"] & merged["occupancy"].notna()
    )
    merged["hour"] = merged.index.hour
    return merged


def responsiveness_rank(table: pd.DataFrame) -> pd.DataFrame:
    """Rank buildings from most to least responsive to their occupants.

    A building is efficient here if a large share of its consumption scales with
    the people in it. We use the share of mean power *not* explained by the base
    load: (mean power - base load) / mean power. High means the building follows
    its occupants; low means it runs regardless.
    """
    out = table.copy()
    out["variable_share_pct"] = (
        100 * (out["mean_power_kw"] - out["base_load_kw"]) / out["mean_power_kw"]
    ).round(1)
    out["responsiveness_rank"] = (
        out["variable_share_pct"].rank(ascending=False, method="min").astype(int)
    )
    return out.sort_values("responsiveness_rank")
