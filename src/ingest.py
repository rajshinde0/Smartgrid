"""Read the raw I-BLEND energy CSVs and cache them as 10-minute parquet.

The rule we work under
---------------------
The energy folder is about 1.6 GB of 1-minute CSVs. We never load all of it at
once. This module reads **one meter at a time**, in chunks, keeps only the
columns we need, aggregates each chunk down to 10-minute blocks, and writes the
result to data/processed/energy_10min_<meter>.parquet. Every later phase reads
that parquet and never touches the raw CSV again.

Why sum-and-count instead of resample().mean()
----------------------------------------------
A 10-minute block can be split across two chunks. Averaging each chunk and then
averaging the averages would be wrong. So each chunk contributes per-block
*sums and counts*; the sums and counts are added up across chunks, and only then
is the mean formed. The result is bit-for-bit what a single-pass mean would give.

Cleaning applied while reading (all of it logged, all of it counted)
-------------------------------------------------------------------
* power outside [0, POWER_MAX_W]        -> NaN  (physically impossible)
* voltage outside [VOLTAGE_MIN_V, VOLTAGE_MAX_V] -> NaN
* power_factor: the sign is a leading/lagging convention, not a fault, so we
  keep abs(power_factor) as the usable value AND count how many readings were
  negative. See the Decision log.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

CHUNK_ROWS = 500_000
WANTED_COLS = ["timestamp", "power", "current", "voltage", "frequency", "power_factor"]

# 1-minute readings expected inside one 10-minute block
READINGS_PER_BLOCK = 10


def csv_columns(path: Path) -> list[str]:
    """Header of a CSV without reading the body."""
    return list(pd.read_csv(path, nrows=0).columns)


def _clean_chunk(chunk: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply the invalid-value rules to one chunk; return it plus fix counts."""
    fixes: dict[str, int] = {}

    # Count what was missing in the file *before* we invalidate anything.
    # Counting afterwards would report every reading rejected by the range rule
    # in both power_invalid and power_missing, so the two columns of the Phase 1
    # data-quality table would double-count the same rows.
    fixes["power_missing_in_source"] = (
        int(chunk["power"].isna().sum()) if "power" in chunk else 0
    )

    # --- power: negative or absurdly large is not a real reading -------------
    if "power" in chunk:
        bad = (chunk["power"] < 0) | (chunk["power"] > C.POWER_MAX_W)
        fixes["power_invalid"] = int(bad.sum())
        chunk.loc[bad, "power"] = np.nan

    # --- voltage: a 230 V feeder outside 180-270 V is a meter artefact -------
    if "voltage" in chunk:
        v = chunk["voltage"]
        bad = v.notna() & ((v < C.VOLTAGE_MIN_V) | (v > C.VOLTAGE_MAX_V))
        fixes["voltage_invalid"] = int(bad.sum())
        chunk.loc[bad, "voltage"] = np.nan

    # --- power factor: keep magnitude, count the sign -----------------------
    if "power_factor" in chunk:
        pf = chunk["power_factor"]
        neg = pf.notna() & (pf < 0)
        fixes["pf_negative"] = int(neg.sum())
        chunk["power_factor"] = pf.abs()
        chunk["pf_was_negative"] = neg.astype("int8")

    fixes["rows_read"] = len(chunk)
    # Missing after cleaning = missing in the source + whatever we invalidated.
    # Both are reported so the table adds up and neither is mistaken for the other.
    fixes["power_missing"] = int(chunk["power"].isna().sum()) if "power" in chunk else 0
    fixes["current_missing"] = (
        int(chunk["current"].isna().sum()) if "current" in chunk else 0
    )
    fixes["power_zero"] = (
        int((chunk["power"] == 0).sum()) if "power" in chunk else 0
    )
    return chunk, fixes


def _aggregate_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Collapse one cleaned chunk to per-10-minute sums, counts, mins and maxes."""
    block = chunk["ts"].dt.floor(C.TARGET_FREQ)

    parts: dict[str, pd.Series] = {}
    grouped = chunk.groupby(block, sort=False)

    parts["power_sum"] = grouped["power"].sum(min_count=1)
    parts["power_cnt"] = grouped["power"].count()
    parts["power_min"] = grouped["power"].min()
    parts["power_max"] = grouped["power"].max()

    for col in ("voltage", "current", "frequency", "power_factor"):
        if col in chunk:
            parts[f"{col}_sum"] = grouped[col].sum(min_count=1)
            parts[f"{col}_cnt"] = grouped[col].count()

    if "pf_was_negative" in chunk:
        parts["pf_neg_cnt"] = grouped["pf_was_negative"].sum()

    parts["rows"] = grouped.size()

    out = pd.DataFrame(parts)
    out.index.name = "ts"
    return out


def _combine(parts: list[pd.DataFrame]) -> pd.DataFrame:
    """Add up per-chunk aggregates so blocks split across chunks come out exact."""
    allp = pd.concat(parts)
    how: dict[str, str] = {}
    for col in allp.columns:
        if col.endswith("_min"):
            how[col] = "min"
        elif col.endswith("_max"):
            how[col] = "max"
        else:
            how[col] = "sum"
    return allp.groupby(level=0).agg(how).sort_index()


def _finalise(agg: pd.DataFrame) -> pd.DataFrame:
    """Turn sums and counts into means, on a gap-free 10-minute grid."""
    out = pd.DataFrame(index=agg.index)
    out["power_w"] = agg["power_sum"] / agg["power_cnt"].replace(0, np.nan)
    out["power_min_w"] = agg["power_min"]
    out["power_max_w"] = agg["power_max"]
    out["n_readings"] = agg["power_cnt"].astype("int32")

    for col in ("voltage", "current", "frequency", "power_factor"):
        if f"{col}_sum" in agg:
            out[col] = agg[f"{col}_sum"] / agg[f"{col}_cnt"].replace(0, np.nan)

    if "pf_neg_cnt" in agg:
        denom = agg["power_factor_cnt"].replace(0, np.nan)
        out["pf_neg_frac"] = agg["pf_neg_cnt"] / denom

    # Reindex onto a complete 10-minute grid so missing blocks become explicit
    # NaN rows instead of silently vanishing. This is what makes the
    # missing-data accounting in Phase 1 honest.
    full = pd.date_range(out.index.min(), out.index.max(), freq=C.TARGET_FREQ)
    out = out.reindex(full)
    out["n_readings"] = out["n_readings"].fillna(0).astype("int32")
    out.index.name = "ts"
    return out


def ingest_meter(
    meter_key: str, *, force: bool = False, verbose: bool = True
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Read one raw meter CSV -> cleaned 10-minute table (cached to parquet).

    Returns the table and a dictionary of raw-data quality counts.
    """
    out_path = C.energy_parquet(meter_key)
    stats_path = out_path.with_suffix(".stats.json")

    if out_path.is_file() and not force:
        import json

        df = pd.read_parquet(out_path)
        stats = json.loads(stats_path.read_text()) if stats_path.is_file() else {}
        if verbose:
            print(f"[cache] {meter_key}: {len(df):,} 10-min rows from {out_path.name}")
        return df, stats

    src = C.meter_path(meter_key)
    usecols = [c for c in WANTED_COLS if c in csv_columns(src)]

    totals: dict[str, int] = {}
    parts: list[pd.DataFrame] = []

    for chunk in pd.read_csv(src, usecols=usecols, chunksize=CHUNK_ROWS):
        chunk, fixes = _clean_chunk(chunk)
        for k, v in fixes.items():
            totals[k] = totals.get(k, 0) + v
        # UNIX seconds -> Asia/Kolkata, exactly as the I-BLEND readme instructs
        chunk["ts"] = (
            pd.to_datetime(chunk["timestamp"], unit="s", utc=True)
            .dt.tz_convert(C.TIMEZONE)
        )
        parts.append(_aggregate_chunk(chunk))
        del chunk

    table = _finalise(_combine(parts))
    del parts

    totals["blocks_10min"] = len(table)
    totals["blocks_missing"] = int((table["n_readings"] == 0).sum())
    totals["blocks_partial"] = int(
        ((table["n_readings"] > 0) & (table["n_readings"] < READINGS_PER_BLOCK)).sum()
    )
    totals["first_ts"] = str(table.index.min())
    totals["last_ts"] = str(table.index.max())

    C.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    table.to_parquet(out_path)

    import json

    stats_path.write_text(json.dumps(totals, indent=2, default=str))

    if verbose:
        print(
            f"[built] {meter_key}: {totals['rows_read']:,} raw rows -> "
            f"{len(table):,} 10-min blocks  "
            f"({totals['blocks_missing']:,} empty)  -> {out_path.name}"
        )
    return table, totals


def ingest_all(force: bool = False) -> dict[str, dict[str, int]]:
    """Ingest every building meter, one at a time. Returns the quality counts."""
    stats: dict[str, dict[str, int]] = {}
    for meter_key in C.METERS:
        _, s = ingest_meter(meter_key, force=force)
        stats[meter_key] = s
    return stats
