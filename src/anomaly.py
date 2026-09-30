"""The anomaly experiment: does knowing the occupancy help catch abnormal usage?

Two detectors, the same data, the same procedure
------------------------------------------------
    Detector T  residuals of model B (time features only)
    Detector O  residuals of model C (time + occupancy)

A residual is actual minus expected. If a building draws much more than the model
expects, the residual is large, and a large enough residual is called an anomaly.
The only difference between the two detectors is whether the expectation knew how
many people were in the building.

How we test them
----------------
We cannot evaluate a detector on real data, because nobody labelled the real
faults. So we take a **copy** of the test period and inject anomalies whose
locations we record. Those labels are the ground truth.

**Everything injected here is synthetic.** It is a measuring instrument for
comparing two detectors, and no injected event corresponds to anything that
happened on the IIIT-Delhi campus. The real-data section at the end is kept
strictly separate and its findings are described as "unusual patterns worth
inspecting", never as confirmed faults.

Two kinds of injected anomaly
-----------------------------
    spike  +50-100% for 10-30 minutes, at any time
           simulates a sudden equipment surge
    waste  +15-30% for 2-6 hours, only during low-occupancy periods
           simulates lights or air conditioning left on in an empty building

The waste type is the one that matters for this project: it is the machine
version of the behaviour Phase 5 measured, and it is where occupancy information
should help, because only Detector O knows the building was empty at the time.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

BLOCKS_PER_HOUR = 6
MINUTES_PER_BLOCK = 10


# ---------------------------------------------------------------------------
# Injection
# ---------------------------------------------------------------------------
def inject_anomalies(
    test: pd.DataFrame,
    *,
    low_occ_threshold: float,
    n_spikes: int = C.N_SPIKES,
    n_waste: int = C.N_WASTE,
    seed: int = C.SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add labelled synthetic anomalies to a **copy** of the test data.

    Only `power_w` is altered. The time and occupancy columns are left exactly as
    they were, which matters: it means both detectors make precisely the same
    predictions on the contaminated data as on the clean data, so any difference
    in what they catch comes from the models themselves and not from the
    injection disturbing their inputs.

    Returns the contaminated copy and a table describing every event.
    """
    rng = np.random.default_rng(seed)
    contaminated = test.copy()
    n = len(contaminated)

    contaminated["is_anomaly"] = False
    contaminated["anomaly_type"] = "none"
    contaminated["injected_extra_w"] = 0.0
    contaminated["event_id"] = -1

    events: list[dict] = []
    event_id = 0

    # ---- spikes: short, large, anywhere --------------------------------
    for _ in range(n_spikes):
        duration_min = int(rng.integers(C.SPIKE_DURATION_MIN[0],
                                        C.SPIKE_DURATION_MIN[1] + 1))
        length = max(1, duration_min // MINUTES_PER_BLOCK)
        start = int(rng.integers(0, n - length))
        window = slice(start, start + length)

        if contaminated["is_anomaly"].iloc[window].any():
            continue                     # do not stack events on top of each other

        magnitude = float(rng.uniform(*C.SPIKE_MAGNITUDE))
        base = contaminated["power_w"].iloc[window].to_numpy()
        extra = base * magnitude

        contaminated.iloc[window, contaminated.columns.get_loc("power_w")] = base + extra
        contaminated.iloc[window, contaminated.columns.get_loc("is_anomaly")] = True
        contaminated.iloc[window, contaminated.columns.get_loc("anomaly_type")] = "spike"
        contaminated.iloc[window, contaminated.columns.get_loc("injected_extra_w")] = extra
        contaminated.iloc[window, contaminated.columns.get_loc("event_id")] = event_id

        events.append({
            "event_id": event_id, "type": "spike",
            "start": contaminated.index[start],
            "intervals": length,
            "duration_min": length * MINUTES_PER_BLOCK,
            "magnitude_pct": round(100 * magnitude, 1),
            "mean_extra_w": round(float(extra.mean()), 1),
        })
        event_id += 1

    # ---- waste: long, small, only when the building is nearly empty ----
    low_occ = (contaminated["occupancy"] <= low_occ_threshold).to_numpy()
    eligible = np.flatnonzero(low_occ)

    # Waste events are long (up to 36 blocks) and must start inside a
    # low-occupancy period, so a single attempt each collides with an existing
    # event most of the time. We keep trying until the target is reached or the
    # attempt budget runs out, and report how many actually landed -- the
    # achieved count is what the evaluation uses, never the requested one.
    placed = 0
    attempts = 0
    max_attempts = n_waste * 50

    while placed < n_waste and attempts < max_attempts and eligible.size:
        attempts += 1
        duration_hours = float(rng.uniform(*C.WASTE_DURATION_HOURS))
        length = max(1, int(duration_hours * BLOCKS_PER_HOUR))
        start = int(rng.choice(eligible))
        if start + length > n:
            continue
        window = slice(start, start + length)

        if contaminated["is_anomaly"].iloc[window].any():
            continue
        placed += 1

        magnitude = float(rng.uniform(*C.WASTE_MAGNITUDE))
        base = contaminated["power_w"].iloc[window].to_numpy()
        extra = base * magnitude

        contaminated.iloc[window, contaminated.columns.get_loc("power_w")] = base + extra
        contaminated.iloc[window, contaminated.columns.get_loc("is_anomaly")] = True
        contaminated.iloc[window, contaminated.columns.get_loc("anomaly_type")] = "waste"
        contaminated.iloc[window, contaminated.columns.get_loc("injected_extra_w")] = extra
        contaminated.iloc[window, contaminated.columns.get_loc("event_id")] = event_id

        events.append({
            "event_id": event_id, "type": "waste",
            "start": contaminated.index[start],
            "intervals": length,
            "duration_min": length * MINUTES_PER_BLOCK,
            "magnitude_pct": round(100 * magnitude, 1),
            "mean_extra_w": round(float(extra.mean()), 1),
        })
        event_id += 1

    return contaminated, pd.DataFrame(events)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def robust_zscore(residuals: pd.Series) -> pd.Series:
    """Z-score using the median and the median absolute deviation.

    The ordinary Z-score divides by the standard deviation -- but the standard
    deviation is itself inflated by the very anomalies we are trying to find, so
    a few large events raise the bar and hide themselves. The MAD is barely moved
    by a small proportion of extreme values.

    The factor 1.4826 rescales the MAD so that, for normally distributed data, it
    matches the standard deviation. That keeps the familiar thresholds (2 and 3)
    meaning what they usually mean.

    Both detectors are scored by this identical procedure, so the comparison
    between them is unaffected by the choice.
    """
    median = residuals.median()
    mad = (residuals - median).abs().median()
    scale = 1.4826 * mad
    if scale == 0 or not np.isfinite(scale):
        scale = residuals.std()
    return (residuals - median) / scale


def classify(z: pd.Series) -> pd.Series:
    """NORMAL below 2, WARNING between 2 and 3, ANOMALY above 3."""
    magnitude = z.abs()
    return pd.Series(
        np.select(
            [magnitude >= C.Z_ANOMALY, magnitude >= C.Z_WARNING],
            ["ANOMALY", "WARNING"],
            default="NORMAL",
        ),
        index=z.index,
        dtype="object",
    )


def iqr_flags(residuals: pd.Series, k: float = 1.5) -> pd.Series:
    """Cross-check: flag residuals outside the Tukey fences."""
    q1, q3 = residuals.quantile(0.25), residuals.quantile(0.75)
    iqr = q3 - q1
    return (residuals < q1 - k * iqr) | (residuals > q3 + k * iqr)


def score_detector(
    actual: pd.Series, predicted: np.ndarray, *, one_sided: bool = False
) -> pd.DataFrame:
    """Turn a model's predictions into residuals, Z-scores and bands.

    `one_sided` flags only residuals that are large and **positive** -- the
    building using more than expected. Every anomaly we inject is additive, and
    in practice waste is too: lights left on add power, they never subtract it.
    Flagging large negative residuals as well can only produce false positives
    against these labels, so the one-sided variant is reported alongside the
    two-sided one specified in the plan.
    """
    out = pd.DataFrame(index=actual.index)
    out["actual_w"] = actual.to_numpy()
    out["predicted_w"] = predicted
    out["residual_w"] = out["actual_w"] - out["predicted_w"]
    out["z"] = robust_zscore(out["residual_w"])
    out["band"] = classify(out["z"])
    out["flagged"] = (
        out["z"].gt(C.Z_ANOMALY) if one_sided else out["band"].eq("ANOMALY")
    )
    out["flagged_iqr"] = iqr_flags(out["residual_w"])
    return out


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def confusion(truth: pd.Series, flagged: pd.Series) -> dict:
    """Confusion matrix and the four standard scores.

    * **precision** -- of the intervals we flagged, how many really were anomalies
    * **recall**    -- of the real anomalies, how many did we catch
    * **F1**        -- their harmonic mean, which punishes ignoring either one
    * **accuracy**  -- included because it is asked for, but it is the least
      useful number here: anomalies are a few percent of the data, so a detector
      that flags nothing at all still scores over 90%
    """
    truth = truth.astype(bool)
    flagged = flagged.astype(bool)

    tp = int((truth & flagged).sum())
    fp = int((~truth & flagged).sum())
    fn = int((truth & ~flagged).sum())
    tn = int((~truth & ~flagged).sum())

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / max(tp + tn + fp + fn, 1)

    return {
        "true_positives": tp, "false_positives": fp,
        "false_negatives": fn, "true_negatives": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }


def evaluate_by_type(
    scored: pd.DataFrame, contaminated: pd.DataFrame, detector: str
) -> list[dict]:
    """Confusion scores overall and for each anomaly type separately.

    For a single type, the negatives are the *clean* intervals only -- intervals
    holding the other type of anomaly are excluded rather than counted as
    negatives, which would otherwise punish a detector for correctly catching
    them.
    """
    truth = contaminated["is_anomaly"]
    kinds = contaminated["anomaly_type"]
    rows = [{
        "detector": detector, "anomaly_type": "all",
        "n_anomaly_intervals": int(truth.sum()),
        **confusion(truth, scored["flagged"]),
    }]

    for kind in ("spike", "waste"):
        keep = (kinds == kind) | (kinds == "none")
        rows.append({
            "detector": detector, "anomaly_type": kind,
            "n_anomaly_intervals": int((kinds == kind).sum()),
            **confusion(truth[keep], scored.loc[keep, "flagged"]),
        })
    return rows


def flag_top_n(scored: pd.DataFrame, n_flags: int) -> pd.Series:
    """Flag the `n_flags` most extreme intervals, ignoring the z threshold.

    Why this is needed. A fixed threshold of z > 3 does **not** put the two
    detectors on equal terms. Model C is the better model, so its residuals are
    more tightly clustered, so its MAD is smaller, so the same deviation in watts
    produces a larger Z-score. At a fixed threshold the better model simply
    raises more alerts -- which buys it recall and costs it precision, for
    reasons that have nothing to do with whether occupancy helps.

    Giving both detectors the same **alert budget** removes that confound: if an
    operator will investigate 500 intervals, which 500 should they be? This is a
    fair comparison of ranking quality.
    """
    order = scored["z"].abs().sort_values(ascending=False)
    chosen = order.head(n_flags).index
    return pd.Series(scored.index.isin(chosen), index=scored.index)


def ranking_scores(truth: pd.Series, score: pd.Series) -> dict:
    """Threshold-free quality of the ranking: ROC AUC and average precision.

    These ask "if we sort every interval by how suspicious it looks, do the real
    anomalies come out near the top?" -- which is the question that matters and
    the one a single threshold cannot answer.

    Average precision (the area under the precision-recall curve) is the more
    informative of the two here, because anomalies are rare and ROC AUC is
    optimistic when the negative class is overwhelming.
    """
    from sklearn.metrics import average_precision_score, roc_auc_score

    truth = truth.astype(bool).to_numpy()
    values = score.abs().to_numpy()
    if truth.sum() == 0 or truth.all():
        return {"roc_auc": np.nan, "average_precision": np.nan}
    return {
        "roc_auc": round(float(roc_auc_score(truth, values)), 4),
        "average_precision": round(float(average_precision_score(truth, values)), 4),
        "baseline_precision": round(float(truth.mean()), 4),
    }


def event_level_recall(
    scored: pd.DataFrame, contaminated: pd.DataFrame
) -> pd.DataFrame:
    """How many whole *events* were caught, not just how many intervals.

    Interval-level recall undercounts a detector that catches a six-hour waste
    event in its first hour and then treats the new level as normal. For an
    operator, noticing an event at all is what matters -- so an event counts as
    caught if any one of its intervals was flagged.
    """
    rows = []
    for kind in ("spike", "waste"):
        mask = contaminated["anomaly_type"] == kind
        if not mask.any():
            continue
        frame = pd.DataFrame({
            "event_id": contaminated.loc[mask, "event_id"],
            "flagged": scored.loc[mask, "flagged"],
        })
        by_event = frame.groupby("event_id")["flagged"].any()
        rows.append({
            "anomaly_type": kind,
            "events": int(len(by_event)),
            "events_detected": int(by_event.sum()),
            "event_recall": round(float(by_event.mean()), 4),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Real data
# ---------------------------------------------------------------------------
def top_unusual(
    scored: pd.DataFrame, extra: pd.DataFrame, n: int = 10
) -> pd.DataFrame:
    """The n most unusual intervals in the **real**, uncontaminated data.

    These are *not* confirmed faults. They are intervals where a building drew
    much more power than a model of time and occupancy expected. Every one could
    have an ordinary explanation -- an event in the building, a maintenance test,
    a hot day the model has no way of knowing about, since we have no weather
    data. They are candidates for a human to look at, nothing more.
    """
    joined = scored.join(extra[["occupancy", "hour", "weekday", "period"]],
                         how="left")
    top = joined.reindex(joined["z"].abs().sort_values(ascending=False).index).head(n)
    return pd.DataFrame({
        "timestamp": top.index,
        "weekday": top["weekday"].astype(str).to_numpy(),
        "hour": top["hour"].to_numpy(),
        "period": top["period"].astype(str).to_numpy(),
        "occupancy": top["occupancy"].to_numpy(),
        "actual_kW": (top["actual_w"] / 1000).round(2).to_numpy(),
        "expected_kW": (top["predicted_w"] / 1000).round(2).to_numpy(),
        "excess_kW": ((top["actual_w"] - top["predicted_w"]) / 1000).round(2).to_numpy(),
        "z_score": top["z"].round(2).to_numpy(),
    })


def group_into_episodes(
    scored: pd.DataFrame, max_gap_blocks: int = 3
) -> pd.DataFrame:
    """Merge consecutive flagged intervals into episodes.

    A four-hour deviation is one event an operator would investigate once, not 24
    separate alerts. Consecutive flagged intervals (allowing small gaps) are
    collapsed into a single episode with a start, a duration and a peak.
    """
    flagged = scored[scored["flagged"]]
    if flagged.empty:
        return pd.DataFrame()

    positions = np.flatnonzero(scored["flagged"].to_numpy())
    breaks = np.flatnonzero(np.diff(positions) > max_gap_blocks)
    groups = np.split(positions, breaks + 1)

    rows = []
    for group in groups:
        window = scored.iloc[group]
        rows.append({
            "start": window.index[0],
            "end": window.index[-1],
            "intervals": len(group),
            "duration_hours": round(len(group) / BLOCKS_PER_HOUR, 2),
            "peak_z": round(float(window["z"].abs().max()), 2),
            "mean_excess_kW": round(float(window["residual_w"].mean()) / 1000, 2),
            "total_excess_kWh": round(
                float(window["residual_w"].sum()) / 1000 * (10 / 60), 2),
        })
    return pd.DataFrame(rows).sort_values("peak_z", ascending=False).reset_index(
        drop=True)
