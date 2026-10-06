"""Regression models that predict a building's expected power.

Four models, each with a job:

    A  power ~ occupancy                 the intercept is the base load (watts
                                         with nobody there) and the slope is
                                         watts per extra occupant. Phase 5 needs
                                         both numbers.
    B  power ~ time features             the time-only baseline. Phase 6 turns
                                         its residuals into Detector T.
    C  power ~ time + occupancy          the main model. Phase 6 turns its
                                         residuals into Detector O.
    D  random forest on C's features     checks whether a non-linear model does
                                         much better, and gives importances.

**Why there are no lag features here.** Phase 2 found that power one hour ago
correlates with current power at about r = 0.95. A model given that feature would
score beautifully while learning nothing about *why* the building uses energy --
and it would track waste rather than flagging it, because a building that has
been wasting for an hour would be predicted to keep wasting. We want a baseline
of *expected* consumption given the time and the occupancy, not the best possible
forecast. Phase 4 fits a lag model once, purely to show the trap, and then never
uses it again.

Phase 8 adds two more, fitted only inside `fit_weather_models`:

    E  power ~ time + weather            knows the weather but not the people
    F  power ~ time + weather + occupancy  the full model

They exist to ask the sharper version of RQ2 -- does occupancy still help once
the weather is known? -- and they leave A-D untouched, because RQ2 and RQ3 are
already answered against those.

**Why the split is chronological.** `train_test_split(shuffle=True)` on a time
series lets the model see Thursday while being tested on Wednesday. Every split
here keeps time order.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler

from . import config as C

# Which columns feed which model
TIME_CATEGORICAL = ["hour", "weekday", "month"]
# is_working_day comes from the official IIIT-Delhi calendar, so it knows
# about public holidays that is_weekend cannot see.
TIME_BINARY = ["is_weekend", "is_semester", "is_working_day"]
OCCUPANCY = ["occupancy"]

# Outdoor conditions (Phase 8). `cdh` is cooling degree hours at the default
# base: zero on a mild day, rising linearly once cooling starts. Temperature
# alone is close to linear in the response; CDH encodes the threshold, and
# including both lets the model use whichever fits the building.
WEATHER = ["temp_c", "cdh"]


def usable_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Rows a model may legitimately learn from."""
    needed = ["power_w", "occupancy", "hour", "weekday", "month", "is_weekend",
              "is_semester", "is_working_day"]
    weather_cols = [c for c in WEATHER if c in df.columns]

    # Weather is deliberately NOT in the required set: models B and C must keep
    # the exact sample they were published on, so a missing temperature cannot
    # remove a row from them. Weather columns ride along and the weather models
    # drop their own NaNs at fit time.
    out = df.loc[df["usable"], needed].dropna()
    if weather_cols:
        out = out.join(df.loc[df["usable"], weather_cols], how="left")
    out = out.copy()
    out["weekday"] = out["weekday"].astype(str)   # one-hot wants plain labels
    return out


def chronological_split(
    df: pd.DataFrame,
    *,
    train: float = C.SPLIT_TRAIN,
    val: float = C.SPLIT_VAL,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split into train / validation / test **in time order**.

    Uses `train_test_split(..., shuffle=False)` twice, which is the scikit-learn
    way of saying "take the first N% as they come". Shuffling would leak the
    future into the past: the model would be fitted on data recorded after the
    data it is tested on, and every error measure would be optimistic.
    """
    first, rest = train_test_split(df, train_size=train, shuffle=False)
    val_share = val / (1 - train)
    second, third = train_test_split(rest, train_size=val_share, shuffle=False)
    return first, second, third


def metrics(y_true, y_pred) -> dict[str, float]:
    """MAE, RMSE and R-squared.

    Both MAE and RMSE are reported because they answer different questions. MAE
    is the average error in watts, which is what a building manager cares about.
    RMSE squares the errors first, so it is dominated by the rare large ones --
    and Phase 2 showed this data has a long right tail, so the two can disagree
    and the gap between them is itself informative.
    """
    y_true = np.asarray(y_true, dtype="float64")
    y_pred = np.asarray(y_pred, dtype="float64")

    # MAPE is undefined wherever the true value is zero, so those intervals are
    # excluded with nanmean rather than allowed to poison the whole average.
    # Using plain mean here returns NaN for the entire building as soon as one
    # reading is 0 W -- which happens whenever a meter is briefly off for less
    # than the dead-meter threshold.
    with np.errstate(divide="ignore", invalid="ignore"):
        relative = np.abs(
            (y_true - y_pred) / np.where(y_true == 0, np.nan, y_true)
        )
    mape = float(np.nanmean(relative) * 100) if np.isfinite(relative).any() else float("nan")

    return {
        "MAE_w": float(mean_absolute_error(y_true, y_pred)),
        "RMSE_w": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "MAPE_pct": mape,
    }


# ---------------------------------------------------------------------------
# Model A -- the one whose coefficients Phase 5 uses
# ---------------------------------------------------------------------------
def fit_model_a(frame: pd.DataFrame) -> dict:
    """power = a + b * occupancy.

    Deliberately unscaled, because the whole value of this model is that its two
    coefficients carry physical units:

        a  watts drawn with nobody present    -- the base load
        b  extra watts per extra occupant     -- how responsive the building is

    Scaling the inputs would make both numbers unitless and useless for Phase 5.
    """
    X = frame[["occupancy"]]          # keep the DataFrame so feature names survive
    y = frame["power_w"].to_numpy()

    model = LinearRegression().fit(X, y)
    return {
        "model": model,
        "a_base_load_w": float(model.intercept_),
        "b_watts_per_occupant": float(model.coef_[0]),
        "r2_in_sample": float(model.score(X, y)),
    }


# ---------------------------------------------------------------------------
# Models B, C, D -- pipelines
# ---------------------------------------------------------------------------
def make_preprocessor(
    include_occupancy: bool, include_weather: bool = False
) -> ColumnTransformer:
    """One-hot the cyclic/categorical time features, standardise the numeric ones.

    `hour` and `month` are numbers but they are **cyclic categories**: hour 23 is
    adjacent to hour 0, and treating them as a plain number would tell the model
    that 23:00 is twenty-three times 01:00. One-hot encoding avoids that.
    `drop="first"` removes one level per feature so the columns are not linearly
    dependent, which matters for a linear model.

    The scaler lives **inside the pipeline**, so it is fitted on the training
    fold only. Fitting it on all the data first would leak test-set information
    (its mean and spread) into training.
    """
    transformers = [
        ("categorical",
         OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False),
         TIME_CATEGORICAL),
        ("binary", "passthrough", TIME_BINARY),
    ]
    if include_occupancy:
        transformers.append(("numeric", StandardScaler(), OCCUPANCY))
    if include_weather:
        transformers.append(("weather", StandardScaler(), WEATHER))
    return ColumnTransformer(transformers, remainder="drop")


def make_linear_model(
    include_occupancy: bool, include_weather: bool = False
) -> Pipeline:
    """Linear regression behind the standard preprocessor.

    The flags select the model: neither is B (time only), occupancy alone is C,
    weather alone is E, and both is F. Everything is inside one `Pipeline` so
    the encoder and scaler are fitted on the training fold only -- fitting them
    on the full frame first would leak the test set into training.
    """
    return Pipeline([
        ("prep", make_preprocessor(include_occupancy, include_weather)),
        ("model", LinearRegression()),
    ])


def make_forest(include_occupancy: bool, *, max_depth: int | None = 12) -> Pipeline:
    """Model D: a random forest on the same features as the linear models.

    It answers one question -- would a non-linear model do much better? -- and
    supplies feature importances. The depth is capped and leaves are kept at
    five rows or more, because an unconstrained forest on 170,000 correlated
    time steps memorises the record instead of learning its shape.
    """
    return Pipeline([
        ("prep", make_preprocessor(include_occupancy)),
        ("model", RandomForestRegressor(
            n_estimators=120, max_depth=max_depth, random_state=C.SEED,
            n_jobs=-1, min_samples_leaf=5,
        )),
    ])


def feature_columns(
    include_occupancy: bool, include_weather: bool = False
) -> list[str]:
    """The exact input columns a model expects, in a fixed order.

    Single source of truth, shared by fitting, scoring and prediction. Building
    the list twice is how a model quietly ends up scored on columns in a
    different order from the ones it was fitted on.
    """
    cols = list(TIME_CATEGORICAL + TIME_BINARY)
    if include_occupancy:
        cols += OCCUPANCY
    if include_weather:
        cols += WEATHER
    return cols


def validation_bias(
    pipeline: Pipeline, val: pd.DataFrame, *, include_occupancy: bool,
    include_weather: bool = False,
) -> float:
    """Mean prediction error on the validation split.

    The campus load rose steadily between 2014 and 2017, so a model fitted on
    2014-2016 systematically under-predicts 2017 -- not because it has the shape
    of the day wrong, but because the whole building now draws more. This is
    concept drift, and in practice utilities handle it by re-baselining against
    recent data.

    We estimate the offset on the **validation** split, which lies entirely
    *before* the test split in time. Using the test split to correct predictions
    on the test split would be leakage; using the period before it is exactly
    what a deployed system could do.
    """
    cols = feature_columns(include_occupancy, include_weather)
    return float((val["power_w"] - pipeline.predict(val[cols])).mean())


def fit_and_score(
    pipeline: Pipeline,
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    *,
    include_occupancy: bool,
    include_weather: bool = False,
) -> dict:
    """Fit on train, then score on train, validation and test.

    Test metrics are reported twice: as-is, and after the validation-estimated
    bias correction described in `validation_bias`.
    """
    cols = feature_columns(include_occupancy, include_weather)
    pipeline.fit(train[cols], train["power_w"])

    out = {"pipeline": pipeline}
    for name, part in (("train", train), ("val", val), ("test", test)):
        prediction = pipeline.predict(part[cols])
        for key, value in metrics(part["power_w"], prediction).items():
            out[f"{name}_{key}"] = value

    bias = validation_bias(
        pipeline, val, include_occupancy=include_occupancy,
        include_weather=include_weather,
    )
    out["val_bias_w"] = bias
    corrected = pipeline.predict(test[cols]) + bias
    for key, value in metrics(test["power_w"], corrected).items():
        out[f"test_corrected_{key}"] = value
    return out


def cross_validate_timeseries(
    pipeline: Pipeline, train: pd.DataFrame, *, include_occupancy: bool,
    n_splits: int = C.CV_SPLITS,
) -> dict:
    """K-fold cross-validation that respects time order.

    Ordinary k-fold would put later data in a training fold and earlier data in
    the matching validation fold. `TimeSeriesSplit` always trains on a prefix and
    validates on the block immediately after it, which is what forecasting a
    building actually looks like.
    """
    cols = feature_columns(include_occupancy)
    splitter = TimeSeriesSplit(n_splits=n_splits)
    scores = cross_val_score(
        pipeline, train[cols], train["power_w"],
        cv=splitter, scoring="neg_mean_absolute_error",
    )
    return {
        "cv_folds": n_splits,
        "cv_mae_mean_w": float(-scores.mean()),
        "cv_mae_std_w": float(scores.std()),
        "cv_mae_per_fold_w": [float(-s) for s in scores],
    }


# ---------------------------------------------------------------------------
# Feature selection
# ---------------------------------------------------------------------------
def select_features(train: pd.DataFrame, k: int = 15) -> pd.DataFrame:
    """Rank the encoded features by univariate association with power.

    Two steps, as they are normally taught together:

    * a **correlation filter** -- how strongly does each encoded column move with
      power on its own
    * **SelectKBest with f_regression** -- the same idea expressed as an F-test,
      which gives a p-value and a ranking

    These are *univariate* methods: they judge each feature alone and cannot see
    that two features carry the same information. They are reported for
    transparency, not used to prune the models -- with only a few dozen one-hot
    columns and hundreds of thousands of rows, dropping features would buy
    nothing and cost interpretability.
    """
    prep = make_preprocessor(include_occupancy=True)
    encoded = prep.fit_transform(train[feature_columns(True)])
    names = list(prep.get_feature_names_out())
    y = train["power_w"].to_numpy()

    correlations = np.array([
        np.corrcoef(encoded[:, i], y)[0, 1] if encoded[:, i].std() > 0 else 0.0
        for i in range(encoded.shape[1])
    ])

    selector = SelectKBest(score_func=f_regression, k=min(k, encoded.shape[1]))
    selector.fit(encoded, y)

    table = pd.DataFrame({
        "feature": [n.split("__", 1)[-1] for n in names],
        "correlation_with_power": np.round(correlations, 3),
        "abs_correlation": np.round(np.abs(correlations), 3),
        "f_score": np.round(selector.scores_, 1),
        "p_value": selector.pvalues_,
        "kept_by_selectkbest": selector.get_support(),
    })
    return table.sort_values("abs_correlation", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Overfitting curve
# ---------------------------------------------------------------------------
def polynomial_overfitting_curve(
    train: pd.DataFrame, val: pd.DataFrame, max_degree: int = 10
) -> pd.DataFrame:
    """Fit power ~ polynomial(occupancy) at increasing degree.

    The classic demonstration: training error falls as the model gains freedom,
    while validation error falls, flattens, and eventually rises as the extra
    freedom is spent memorising noise. The degree where validation error stops
    improving is where overfitting starts.
    """
    rows = []
    for degree in range(1, max_degree + 1):
        pipeline = Pipeline([
            ("poly", PolynomialFeatures(degree=degree, include_bias=False)),
            ("scale", StandardScaler()),
            ("model", LinearRegression()),
        ])
        pipeline.fit(train[["occupancy"]], train["power_w"])
        rows.append({
            "degree": degree,
            "train_MAE_w": mean_absolute_error(
                train["power_w"], pipeline.predict(train[["occupancy"]])),
            "val_MAE_w": mean_absolute_error(
                val["power_w"], pipeline.predict(val[["occupancy"]])),
        })
    return pd.DataFrame(rows)


def forest_depth_curve(
    train: pd.DataFrame, val: pd.DataFrame, depths=(2, 4, 6, 8, 12, 16, 24, None)
) -> pd.DataFrame:
    """The same overfitting story for a random forest of increasing depth."""
    cols = feature_columns(True)
    rows = []
    for depth in depths:
        pipeline = make_forest(True, max_depth=depth)
        pipeline.fit(train[cols], train["power_w"])
        rows.append({
            "max_depth": "unlimited" if depth is None else depth,
            "train_MAE_w": mean_absolute_error(
                train["power_w"], pipeline.predict(train[cols])),
            "val_MAE_w": mean_absolute_error(
                val["power_w"], pipeline.predict(val[cols])),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# The whole thing, per building
# ---------------------------------------------------------------------------
def run_building(
    building: str, df: pd.DataFrame, *, with_forest: bool = True
) -> dict:
    """Fit models A-D for one building and collect everything later phases need."""
    frame = usable_frame(df)
    if len(frame) < 2000:
        return {"building": building, "skipped": True, "n": len(frame)}

    train, val, test = chronological_split(frame)

    model_a = fit_model_a(train)

    results = {"A": {
        "model": "A: power ~ occupancy",
        **{f"test_{k}": v for k, v in metrics(
            test["power_w"],
            model_a["model"].predict(test[["occupancy"]])).items()},
        **{f"train_{k}": v for k, v in metrics(
            train["power_w"],
            model_a["model"].predict(train[["occupancy"]])).items()},
    }}

    b = fit_and_score(make_linear_model(False), train, val, test,
                      include_occupancy=False)
    c = fit_and_score(make_linear_model(True), train, val, test,
                      include_occupancy=True)
    results["B"] = {"model": "B: time only", **b}
    results["C"] = {"model": "C: time + occupancy", **c}

    if with_forest:
        d = fit_and_score(make_forest(True), train, val, test,
                          include_occupancy=True)
        results["D"] = {"model": "D: random forest (time + occupancy)", **d}

    weather_models = fit_weather_models(train, val, test)
    if weather_models.get("available"):
        results["E"] = weather_models["E"]
        results["F"] = weather_models["F"]

    return {
        "building": building,
        "skipped": False,
        "weather": weather_models,
        "n_total": len(frame),
        "n_train": len(train),
        "n_val": len(val),
        "n_test": len(test),
        "train_period": (train.index.min(), train.index.max()),
        "val_period": (val.index.min(), val.index.max()),
        "test_period": (test.index.min(), test.index.max()),
        "model_a": model_a,
        "results": results,
        "splits": (train, val, test),
    }


def fit_weather_models(
    train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame
) -> dict:
    """Fit models E (time + weather) and F (time + weather + occupancy).

    These are **additional** models, not replacements. B and C keep their
    published definitions so that RQ2 and RQ3 stay answered against exactly the
    data and features they were answered on.

    What they add is a sharper question. Occupancy and outdoor temperature are
    *both* seasonal, so part of the contribution credited to occupancy in C-vs-B
    may be summer heat in disguise. **F against E** asks whether occupancy still
    helps once the weather is already known, which is the harder and more honest
    form of the question.

    Rows without a temperature reading are dropped here and only here -- about
    4% of the record, from gaps longer than two hours in the METAR archive.
    """
    weather_cols = WEATHER

    def usable(part: pd.DataFrame) -> pd.DataFrame:
        return part.dropna(subset=weather_cols)

    train_w, val_w, test_w = usable(train), usable(val), usable(test)
    if min(len(train_w), len(val_w), len(test_w)) < 500:
        return {"available": False, "reason": "too few intervals with weather"}

    out = {
        "available": True,
        "n_train": len(train_w), "n_val": len(val_w), "n_test": len(test_w),
        "pct_rows_with_weather": round(100 * len(train_w) / max(len(train), 1), 1),
    }

    # All four models are fitted on the **same** rows -- the ones that have a
    # temperature. Comparing E against the published B would otherwise confound
    # the effect of adding weather with the effect of dropping 4% of the sample.
    # The published B and C are untouched; these are re-fits for comparison only.
    grid = {
        "B_w": dict(occ=False, wx=False, name="B on weather rows: time only"),
        "C_w": dict(occ=True, wx=False, name="C on weather rows: time + occupancy"),
        "E": dict(occ=False, wx=True, name="E: time + weather"),
        "F": dict(occ=True, wx=True, name="F: time + weather + occupancy"),
    }

    for label, spec in grid.items():
        pipeline = make_linear_model(spec["occ"], include_weather=spec["wx"])
        scored = fit_and_score(
            pipeline, train_w, val_w, test_w,
            include_occupancy=spec["occ"], include_weather=spec["wx"],
        )
        out[label] = {"model": spec["name"], **scored}

    # The 2x2 that answers the refined question. Each gain is measured against
    # the model that differs from it by exactly one feature group.
    out["gains"] = {
        "weather_gain_without_occupancy": round(
            out["E"]["val_R2"] - out["B_w"]["val_R2"], 4),
        "weather_gain_with_occupancy": round(
            out["F"]["val_R2"] - out["C_w"]["val_R2"], 4),
        "occupancy_gain_without_weather": round(
            out["C_w"]["val_R2"] - out["B_w"]["val_R2"], 4),
        "occupancy_gain_given_weather": round(
            out["F"]["val_R2"] - out["E"]["val_R2"], 4),
    }

    return out


def residual_frame(
    pipeline: Pipeline,
    part: pd.DataFrame,
    *,
    include_occupancy: bool,
    include_weather: bool = False,
    bias: float = 0.0,
) -> pd.DataFrame:
    """Actual, predicted and residual for one split -- the input to Phase 6.

    `bias` is the validation-estimated offset. Without it, the drift between the
    training period and the test period would show up as a large constant
    residual, and an anomaly detector would flag the whole test period.
    """
    cols = feature_columns(include_occupancy, include_weather)
    predicted = pipeline.predict(part[cols]) + bias
    out = pd.DataFrame(
        {
            "actual_w": part["power_w"].to_numpy(),
            "predicted_w": predicted,
            "occupancy": part["occupancy"].to_numpy(),
        },
        index=part.index,
    )
    out["residual_w"] = out["actual_w"] - out["predicted_w"]
    return out


def drift_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Mean power per calendar year -- the evidence for concept drift."""
    yearly = frame.groupby(frame.index.year)["power_w"].agg(["count", "mean", "std"])
    yearly.index.name = "year"
    yearly["mean_kW"] = (yearly["mean"] / 1000).round(2)
    yearly["vs_first_year_%"] = (
        100 * (yearly["mean"] / yearly["mean"].iloc[0] - 1)
    ).round(1)
    return yearly[["count", "mean_kW", "vs_first_year_%"]].reset_index()
