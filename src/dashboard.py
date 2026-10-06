"""Prepare the files the Streamlit dashboard reads.

The dashboard must not retrain anything. Every model in this project is fitted
in the notebooks; this module runs them once more, writes the result to
`data/processed/dashboard_<building>.parquet`, and the dashboard does nothing but
read, filter and draw.

That separation matters for two reasons. A dashboard that refits models is slow
and unpredictable for whoever is demonstrating it, and -- more importantly -- it
would let the displayed numbers drift away from the ones in the report.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import anomaly as A, build, config as C, models as M, waste as W

DASH_PREFIX = "dashboard_"


def dashboard_path(building: str):
    """Where one building's scored table lives. The app reads only these."""
    return C.PROCESSED_DIR / f"{DASH_PREFIX}{building}.parquet"


def export_building(building: str, *, verbose: bool = True) -> pd.DataFrame | None:
    """Fit models B and C once, score every interval, and save the result.

    The saved table covers the whole usable record, with a `split` column saying
    which part the model was fitted on. The dashboard displays that, so nobody
    mistakes an in-sample fit for a prediction.
    """
    df, _ = build.build_building(building, verbose=False)
    frame = M.usable_frame(df)
    if len(frame) < 2000:
        if verbose:
            print(f"{building:13s} skipped -- only {len(frame):,} usable intervals")
        return None

    train, val, test = M.chronological_split(frame)

    b = M.fit_and_score(M.make_linear_model(False), train, val, test,
                        include_occupancy=False)
    c = M.fit_and_score(M.make_linear_model(True), train, val, test,
                        include_occupancy=True)

    # Predict across the whole record so the dashboard can show any date range.
    predicted_c = c["pipeline"].predict(frame[M.feature_columns(True)]) + c["val_bias_w"]
    predicted_b = b["pipeline"].predict(frame[M.feature_columns(False)]) + b["val_bias_w"]

    # Score on the test period only, then apply the same scale to the rest: the
    # anomaly threshold has to mean the same thing everywhere on the chart.
    test_residual = pd.Series(
        test["power_w"].to_numpy()
        - (c["pipeline"].predict(test[M.feature_columns(True)]) + c["val_bias_w"]),
        index=test.index,
    )
    median = float(test_residual.median())
    mad_scale = 1.4826 * float((test_residual - median).abs().median())

    out = pd.DataFrame(index=frame.index)
    out["power_w"] = frame["power_w"]
    out["occupancy"] = frame["occupancy"]
    out["expected_w"] = predicted_c
    out["expected_time_only_w"] = predicted_b
    out["residual_w"] = out["power_w"] - out["expected_w"]
    out["z"] = (out["residual_w"] - median) / (mad_scale if mad_scale else 1.0)
    out["band"] = A.classify(out["z"])
    # One-sided: only excess consumption is a candidate for waste (decision D06-05)
    out.loc[out["z"] < 0, "band"] = "NORMAL"

    # Outdoor conditions, so the dashboard can show what the weather was doing
    # alongside the power. About 4% of intervals have no reading -- gaps longer
    # than two hours in the METAR archive -- and those stay NaN so the chart
    # breaks the line rather than drawing through them.
    for column in ("temp_c", "cdh"):
        out[column] = frame[column] if column in frame.columns else np.nan

    threshold = W.low_occupancy_share(df)["threshold"]
    out["low_occupancy"] = out["occupancy"] <= threshold

    out["split"] = "train"
    out.loc[val.index, "split"] = "validation"
    out.loc[test.index, "split"] = "test"

    C.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(dashboard_path(building))

    if verbose:
        print(f"{building:13s} {len(out):>7,} intervals  "
              f"threshold {threshold:5.1f}  "
              f"{int(out['band'].eq('ANOMALY').sum()):>5,} flagged  "
              f"-> {dashboard_path(building).name}")
    return out


def export_all(verbose: bool = True) -> list[str]:
    """Export every building the dashboard can show."""
    done = []
    for building in C.BUILDING_ORDER:
        if export_building(building, verbose=verbose) is not None:
            done.append(building)
    return done


def available_buildings() -> list[str]:
    """Which buildings have an exported file (used by the dashboard)."""
    return [b for b in C.BUILDING_ORDER if dashboard_path(b).is_file()]
