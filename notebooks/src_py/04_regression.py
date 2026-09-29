"""Phase 4 -- Regression models. Percent-format source."""

# %% [markdown]
# # SMARTGRID-X -- Phase 4: Regression models
#
# **What this notebook does.** It builds models that answer the question *"given
# the time of day and how many people are here, how much power should this
# building be drawing?"* -- and then measures how well they do it.
#
# **Research question 2 lives here:** how well do occupancy and time predict
# power?
#
# **What the models are for.** They are not forecasts. They are a **baseline of
# expected consumption**, and they feed the two phases that follow:
#
# | Model | Inputs | What it gives us |
# |---|---|---|
# | **A** | occupancy | intercept `a` = watts with nobody there (the base load); slope `b` = extra watts per occupant. **Phase 5 needs both.** |
# | **B** | time only | the time-only baseline. **Phase 6 turns its residuals into Detector T.** |
# | **C** | time + occupancy | the main model. **Phase 6 turns its residuals into Detector O.** |
# | **D** | random forest on C's inputs | checks whether a non-linear model does much better, and ranks the features |
#
# **Why there are no lag features.** Phase 2 found that power one hour ago
# correlates with current power at about r = 0.95. A model given that feature
# would score beautifully while learning nothing about *why* the building uses
# energy -- and worse, it would *track* waste instead of flagging it, because a
# building that has been wasting for an hour would be confidently predicted to
# carry on wasting. Step 3 demonstrates the trap rather than just asserting it.

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

from src import config as C
from src import build, models as M, report, viz

viz.setup_style()
C.ensure_dirs()
pd.set_option("display.width", 230)
pd.set_option("display.max_columns", 60)
np.random.seed(C.SEED)

TARGET = "Academic"
academic, _ = build.build_building(TARGET, verbose=False)
frame = M.usable_frame(academic)
print(f"{TARGET}: {len(frame):,} usable 10-minute intervals with power and occupancy")
display(frame.head(3))

# %% [markdown]
# ## Step 1: splitting by time, not at random
#
# `train_test_split` shuffles by default. On a time series that is a serious
# mistake: the model would be fitted on Thursday and tested on Wednesday, seeing
# the future in order to predict the past. Every error measure would come out
# flattering and meaningless.
#
# So we pass `shuffle=False` and take the first 70% of the record as training,
# the next 15% as validation, and the final 15% as test. The validation set is
# for making choices; the test set is looked at once, at the end.

# %%
train, val, test = M.chronological_split(frame)

split_table = pd.DataFrame([
    {"split": name, "intervals": len(part),
     "share %": round(100 * len(part) / len(frame), 1),
     "from": part.index.min().strftime("%Y-%m-%d"),
     "to": part.index.max().strftime("%Y-%m-%d"),
     "mean power kW": round(part["power_w"].mean() / 1000, 2)}
    for name, part in (("train", train), ("validation", val), ("test", test))
])
display(split_table)

# %% [markdown]
# **Something is already wrong, and it is not a bug.** Look at the mean power
# column: the test period averages far more than the training period. Before
# fitting anything we have to understand why, because it will govern how every
# result in this notebook must be read.

# %% [markdown]
# ## Step 2: the campus got much bigger -- concept drift
#
# Mean power by calendar year, for every building.

# %%
drift_rows = []
for building in C.BUILDING_ORDER:
    df_b, _ = build.build_building(building, verbose=False)
    f_b = M.usable_frame(df_b)
    if len(f_b) < 2000:
        continue
    grouped = f_b.groupby(f_b.index.year)
    means = grouped["power_w"].mean() / 1000
    correlations = grouped.apply(
        lambda g: g["power_w"].corr(g["occupancy"]), include_groups=False
    )
    row = {"building": building}
    for year in (2014, 2015, 2016, 2017):
        row[f"mean kW {year}"] = round(float(means.get(year, np.nan)), 1)
    row["growth 2014-2017 %"] = round(
        100 * (float(means.iloc[-1]) / float(means.iloc[0]) - 1), 1
    )
    row["r(power,occ) 2014"] = round(float(correlations.get(2014, np.nan)), 2)
    row["r(power,occ) 2017"] = round(float(correlations.get(2017, np.nan)), 2)
    drift_rows.append(row)

drift = pd.DataFrame(drift_rows)
display(drift)
drift.to_csv(C.RESULTS_DIR / "phase4_concept_drift.csv", index=False)

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.4))

for building in C.BUILDING_ORDER:
    row = drift[drift["building"] == building]
    if row.empty:
        continue
    values = [row[f"mean kW {y}"].iloc[0] for y in (2014, 2015, 2016, 2017)]
    baseline = values[0]
    ax1.plot([2014, 2015, 2016, 2017], [100 * v / baseline for v in values],
             marker="o", color=viz.color_for(building),
             label=building.replace("_", " "))
ax1.axhline(100, color=viz.AXIS, linewidth=1)
ax1.set_xticks([2014, 2015, 2016, 2017])
ax1.set_ylabel("Mean power, 2014 = 100")
ax1.set_title("Every building grew, and by a lot")

growth = drift.sort_values("growth 2014-2017 %", ascending=False)
bars = ax2.barh([b.replace("_", " ") for b in growth["building"]],
                growth["growth 2014-2017 %"],
                color=[viz.color_for(b) for b in growth["building"]])
for bar, value in zip(bars, growth["growth 2014-2017 %"]):
    ax2.annotate(f"{value:+.0f}%", xy=(value, bar.get_y() + bar.get_height() / 2),
                 xytext=(4 if value >= 0 else -4, 0), textcoords="offset points",
                 va="center", ha="left" if value >= 0 else "right",
                 fontsize=9, color=viz.INK_SECONDARY)
ax2.axvline(0, color=viz.AXIS, linewidth=1)
ax2.set_xlabel("Change in mean power, 2014 to 2017 (%)")
ax2.set_title("Growth over the record")
ax2.grid(axis="x")

ax1.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=8)
viz.save_fig(fig, "fig_04_drift_by_year")

# %% [markdown]
# **This is a real finding, and it is a large one.** Six of the seven buildings
# grew between **32% and 48%** in mean power between 2014 and 2017. The campus
# did not become more efficient over this period; it became substantially more
# energy-hungry. (The Lecture building is the exception at -7%, but its meter was
# off for most of the record so that number carries little weight.)
#
# For this notebook it has a hard consequence. Our test set is the **last 15% of
# the record**, which is 2017 -- the highest-consuming period. A model fitted on
# 2014-2016 will systematically under-predict it, not because it has the shape of
# a day wrong but because the whole building now draws more. This is **concept
# drift**, and it is the normal condition of real building energy data, which is
# why utilities re-baseline against recent data rather than trusting an old model
# forever.
#
# We handle it in two ways, and report both:
#
# 1. **Report the uncorrected test metrics honestly**, drift and all.
# 2. **Add a validation-calibrated correction**: shift predictions by the mean
#    error observed on the *validation* split, which lies entirely before the
#    test split in time. That is what a deployed system could legitimately do; it
#    is not leakage, because no test data is used.
#
# Model **selection** is done on the validation set, which is what a validation
# set is for.

# %% [markdown]
# ## Step 3: the lag-feature trap
#
# Before fitting the real models, a demonstration of why lag features are
# excluded. We fit an extra model **E** with the same inputs as C plus power one
# hour ago, and compare.

# %%
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

lagged = academic.loc[academic["usable"],
                      ["power_w", "occupancy", "hour", "weekday", "month",
                       "is_weekend", "is_semester", "power_lag_1h"]].dropna()
lagged["weekday"] = lagged["weekday"].astype(str)
l_train, l_val, l_test = M.chronological_split(lagged)

trap = Pipeline([("scale", StandardScaler()), ("model", LinearRegression())])
trap.fit(l_train[["occupancy", "power_lag_1h"]], l_train["power_w"])
trap_scores = M.metrics(l_val["power_w"],
                        trap.predict(l_val[["occupancy", "power_lag_1h"]]))

plain = Pipeline([("scale", StandardScaler()), ("model", LinearRegression())])
plain.fit(l_train[["occupancy"]], l_train["power_w"])
plain_scores = M.metrics(l_val["power_w"], plain.predict(l_val[["occupancy"]]))

display(pd.DataFrame([
    {"model": "occupancy only", **{k: round(v, 3) for k, v in plain_scores.items()}},
    {"model": "occupancy + power 1 hour ago",
     **{k: round(v, 3) for k, v in trap_scores.items()}},
]))

print(f"adding the lag lifts validation R2 from {plain_scores['R2']:.3f} "
      f"to {trap_scores['R2']:.3f}")

# %% [markdown]
# **Takeaway -- and this is why model E is not used.** The lag feature is
# enormously powerful: validation R² jumps from about 0.29 to over 0.9. If our
# goal were forecasting, we would use it without hesitation.
#
# But our goal is to detect *waste*, and a model that knows what the building was
# drawing an hour ago has already absorbed the waste into its expectation. If the
# lights have been left on since 2 a.m., a lag model predicts they will still be
# on at 3 a.m. and reports no anomaly at all. The high score comes precisely from
# the model's willingness to accept whatever is happening as normal.
#
# Models B and C therefore use only **calendar and occupancy** features -- things
# that say what the building *should* be doing, not what it *was* doing.

# %% [markdown]
# ## Step 4: the feature set and how it is encoded
#
# `hour` and `month` are numbers, but they are **cyclic categories**: hour 23 is
# adjacent to hour 0, and treating them as plain numbers would tell the model
# that 23:00 is twenty-three times 01:00. So they are one-hot encoded, with
# `drop="first"` to remove one level per feature and keep the columns linearly
# independent.
#
# The scaler sits **inside the pipeline**. If we scaled the whole dataset before
# splitting, the scaler's mean and standard deviation would carry information
# from the test set into training -- a subtle but real leak. Inside a pipeline,
# `fit` only ever sees the training fold.

# %%
prep = M.make_preprocessor(include_occupancy=True)
encoded = prep.fit_transform(train[M.feature_columns(True)])
print(f"raw feature columns : {M.feature_columns(True)}")
print(f"after encoding      : {encoded.shape[1]} columns")
print(f"encoded names       : {[n.split('__', 1)[-1] for n in prep.get_feature_names_out()][:12]} ...")

# %% [markdown]
# ## Step 5: feature selection
#
# Two standard univariate methods: a correlation filter, and `SelectKBest` with
# an F-test. Both judge each feature **on its own**, which is their limitation --
# they cannot see that two features carry the same information.
#
# We report the ranking for transparency but **do not prune the models with it**.
# With a few dozen one-hot columns and 124,000 training rows there is no
# overfitting pressure to relieve, and dropping hour-of-day dummies would make
# the model harder to interpret for no gain.

# %%
selection = M.select_features(train, k=15)
display(selection.head(18))
selection.to_csv(C.RESULTS_DIR / "phase4_feature_selection.csv", index=False)

# %% [markdown]
# **Takeaway.** Occupancy is the single strongest individual predictor, ahead of
# every hour-of-day dummy. That is reassuring for the project as a whole -- the
# variable the whole study is built around does carry real signal.

# %% [markdown]
# ## Step 6: fit models A to D for every building

# %%
all_results = {}
for building in C.BUILDING_ORDER:
    df_b, _ = build.build_building(building, verbose=False)
    outcome = M.run_building(building, df_b, with_forest=True)
    all_results[building] = outcome
    if outcome.get("skipped"):
        print(f"{building:13s} skipped -- only {outcome['n']:,} usable rows")
    else:
        print(f"{building:13s} n={outcome['n_total']:>7,}  "
              f"train {outcome['n_train']:>6,} / val {outcome['n_val']:>6,} / "
              f"test {outcome['n_test']:>6,}")

# %%
rows = []
for building, outcome in all_results.items():
    if outcome.get("skipped"):
        continue
    for key, result in outcome["results"].items():
        rows.append({
            "building": building,
            "model": result["model"],
            "train R2": round(result.get("train_R2", np.nan), 3),
            "val R2": round(result.get("val_R2", np.nan), 3),
            "test R2": round(result.get("test_R2", np.nan), 3),
            "test R2 (drift-corrected)": round(
                result.get("test_corrected_R2", np.nan), 3),
            "val MAE kW": round(result.get("val_MAE_w", np.nan) / 1000, 2),
            "test MAE kW": round(result.get("test_MAE_w", np.nan) / 1000, 2),
            "test RMSE kW": round(result.get("test_RMSE_w", np.nan) / 1000, 2),
        })

scores = pd.DataFrame(rows)
display(scores)
scores.to_csv(C.RESULTS_DIR / "phase4_model_scores.csv", index=False)

# %% [markdown]
# ## Step 7: does occupancy help? (Research question 2)
#
# The comparison that matters is **model C against model B** -- identical except
# that C also knows the occupancy. We judge it on the **validation** set, because
# that is what a validation set is for, and because the test set is contaminated
# by the drift we diagnosed in Step 2.

# %%
comparison_rows = []
for building, outcome in all_results.items():
    if outcome.get("skipped"):
        continue
    b_res = outcome["results"]["B"]
    c_res = outcome["results"]["C"]
    d_res = outcome["results"].get("D")
    comparison_rows.append({
        "building": building,
        "B val R2": round(b_res["val_R2"], 3),
        "C val R2": round(c_res["val_R2"], 3),
        "R2 gain from occupancy": round(c_res["val_R2"] - b_res["val_R2"], 3),
        "B val MAE kW": round(b_res["val_MAE_w"] / 1000, 2),
        "C val MAE kW": round(c_res["val_MAE_w"] / 1000, 2),
        "MAE improvement %": round(
            100 * (b_res["val_MAE_w"] - c_res["val_MAE_w"]) / b_res["val_MAE_w"], 1),
        "D (forest) val R2": round(d_res["val_R2"], 3) if d_res else np.nan,
    })

occupancy_help = pd.DataFrame(comparison_rows)
display(occupancy_help)
occupancy_help.to_csv(C.RESULTS_DIR / "phase4_occupancy_contribution.csv", index=False)

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.4))

positions = np.arange(len(occupancy_help))
width = 0.38
ax1.bar(positions - width / 2, occupancy_help["B val R2"], width,
        color=viz.CATEGORICAL[0], label="B: time only")
ax1.bar(positions + width / 2, occupancy_help["C val R2"], width,
        color=viz.CATEGORICAL[1], label="C: time + occupancy")
ax1.set_xticks(positions)
ax1.set_xticklabels([b.replace("_", " ") for b in occupancy_help["building"]],
                    rotation=20, ha="right")
ax1.set_ylabel("Validation R-squared")
ax1.set_title("Does knowing the occupancy help?")
ax1.legend()

gains = occupancy_help.sort_values("R2 gain from occupancy", ascending=True)
bars = ax2.barh([b.replace("_", " ") for b in gains["building"]],
                gains["R2 gain from occupancy"],
                color=[viz.color_for(b) for b in gains["building"]])
for bar, value in zip(bars, gains["R2 gain from occupancy"]):
    ax2.annotate(f"{value:+.3f}", xy=(value, bar.get_y() + bar.get_height() / 2),
                 xytext=(4 if value >= 0 else -4, 0), textcoords="offset points",
                 va="center", ha="left" if value >= 0 else "right", fontsize=9,
                 color=viz.INK_SECONDARY)
ax2.axvline(0, color=viz.AXIS, linewidth=1)
ax2.set_xlabel("Increase in validation R-squared from adding occupancy")
ax2.set_title("How much occupancy adds")
ax2.grid(axis="x")

viz.save_fig(fig, "fig_04_model_comparison")

# %% [markdown]
# ## Step 8: cross-validation that respects time
#
# A single train/validation split gives one number, which might be luck. K-fold
# cross-validation gives several -- but ordinary k-fold would put later data in a
# training fold and earlier data in the matching validation fold, leaking the
# future again. `TimeSeriesSplit` always trains on a prefix of the record and
# validates on the block immediately after it, which is what using the model
# would actually look like.

# %%
cv_rows = []
for building in C.BUILDING_ORDER:
    outcome = all_results[building]
    if outcome.get("skipped"):
        continue
    tr, _, _ = outcome["splits"]
    for label, include in (("B: time only", False), ("C: time + occupancy", True)):
        cv = M.cross_validate_timeseries(
            M.make_linear_model(include), tr, include_occupancy=include
        )
        cv_rows.append({
            "building": building, "model": label,
            "CV MAE kW (mean)": round(cv["cv_mae_mean_w"] / 1000, 2),
            "CV MAE kW (sd)": round(cv["cv_mae_std_w"] / 1000, 2),
            "folds": cv["cv_folds"],
        })

cv_table = pd.DataFrame(cv_rows)
display(cv_table.pivot(index="building", columns="model",
                       values="CV MAE kW (mean)").round(2))
cv_table.to_csv(C.RESULTS_DIR / "phase4_cross_validation.csv", index=False)

# %% [markdown]
# ## Step 9: model A -- the numbers Phase 5 needs
#
# Model A is the simplest model in the project and the most useful. Fitting
# `power = a + b x occupancy` gives two coefficients with physical meaning:
#
# * **`a`** -- watts the building draws with nobody in it. This is the base load.
# * **`b`** -- extra watts per additional occupant. This is responsiveness.
#
# A building with a high `a` and a low `b` runs its equipment regardless of who
# is there. A building with a low `a` and a high `b` scales with its occupants.
# Phase 5 ranks the campus on exactly this.

# %%
coef_rows = []
for building, outcome in all_results.items():
    if outcome.get("skipped"):
        continue
    a_model = outcome["model_a"]
    tr, _, _ = outcome["splits"]
    mean_power = float(tr["power_w"].mean())
    # Night-time minimum, as an independent sanity check on the intercept.
    night = tr[(tr["hour"] >= 2) & (tr["hour"] <= 5)]["power_w"]
    coef_rows.append({
        "building": building,
        "kind": C.BUILDINGS[building]["kind"],
        "a: base load (kW)": round(a_model["a_base_load_w"] / 1000, 2),
        "b: watts per occupant": round(a_model["b_watts_per_occupant"], 1),
        "mean power (kW)": round(mean_power / 1000, 2),
        "base load as % of mean": round(
            100 * a_model["a_base_load_w"] / mean_power, 1),
        "night 02-06 median (kW)": round(float(night.median()) / 1000, 2),
        "R2 in sample": round(a_model["r2_in_sample"], 3),
    })

model_a_table = pd.DataFrame(coef_rows)
display(model_a_table)
model_a_table.to_csv(C.RESULTS_DIR / "phase4_model_a_coefficients.csv", index=False)

# %%
fig, ax = plt.subplots(figsize=(9, 5.5))
for _, row in model_a_table.iterrows():
    ax.scatter(row["b: watts per occupant"], row["a: base load (kW)"],
               s=170, color=viz.color_for(row["building"]), zorder=3,
               edgecolors=viz.SURFACE, linewidths=2)
    ax.annotate(row["building"].replace("_", " "),
                xy=(row["b: watts per occupant"], row["a: base load (kW)"]),
                xytext=(0, 13), textcoords="offset points", ha="center",
                fontsize=9, color=viz.INK_SECONDARY)

ax.set_xlabel("b -- extra watts per occupant  (responsiveness)")
ax.set_ylabel("a -- base load with nobody present (kW)")
ax.set_title("Base load against responsiveness")
ax.annotate("high base load,\nbarely responds",
            xy=(0.02, 0.93), xycoords="axes fraction", fontsize=8.5,
            color=viz.INK_MUTED)
ax.annotate("low base load,\nscales with people",
            xy=(0.98, 0.06), xycoords="axes fraction", ha="right", fontsize=8.5,
            color=viz.INK_MUTED)
viz.save_fig(fig, "fig_04_base_load_vs_responsiveness")

# %% [markdown]
# **Takeaway.** The base load is a large fraction of mean power in every
# building. This single table is the quantitative core of the project's main
# finding, and Phase 5 develops it into the headline result.

# %% [markdown]
# ## Step 10: actual against predicted, over one test week
#
# Numbers in a table say how big the errors are. A chart says what *kind* of
# errors they are.

# %%
outcome = all_results[TARGET]
tr, va, te = outcome["splits"]
c_pipeline = outcome["results"]["C"]["pipeline"]
b_pipeline = outcome["results"]["B"]["pipeline"]
bias_c = outcome["results"]["C"]["val_bias_w"]
bias_b = outcome["results"]["B"]["val_bias_w"]

week_start = te.index.min() + pd.Timedelta(days=30)
week = te.loc[week_start : week_start + pd.Timedelta(days=7)]

pred_b = b_pipeline.predict(week[M.feature_columns(False)]) + bias_b
pred_c = c_pipeline.predict(week[M.feature_columns(True)]) + bias_c

fig, (ax1, ax2) = M.plt_panels() if hasattr(M, "plt_panels") else plt.subplots(
    2, 1, figsize=(12, 6), sharex=True,
    gridspec_kw={"height_ratios": [2, 1], "hspace": 0.12})

ax1.plot(week.index, week["power_w"] / 1000, color=viz.INK, linewidth=1.6,
         label="actual")
ax1.plot(week.index, pred_b / 1000, color=viz.CATEGORICAL[0], linewidth=1.6,
         label="B: time only")
ax1.plot(week.index, pred_c / 1000, color=viz.CATEGORICAL[1], linewidth=1.6,
         label="C: time + occupancy")
ax1.set_ylabel("Power (kW)")
ax1.set_title(f"{TARGET} building -- one week of the test period "
              f"({week.index.min():%d %b %Y})")
ax1.legend(ncol=3, loc="upper left", fontsize=9)

# Occupancy on its own panel with its own scale -- never a second y axis.
ax2.plot(week.index, week["occupancy"], color=viz.CATEGORICAL[2], linewidth=1.4)
ax2.set_ylabel("Occupancy\n(devices)")
ax2.set_xlabel("")
plt.setp(ax2.get_xticklabels(), rotation=25, ha="right")

viz.save_fig(fig, f"fig_04_actual_vs_predicted_{TARGET.lower()}")

# %% [markdown]
# **Takeaway.** Both models reproduce the daily rhythm. The difference is in the
# detail: model C bends towards the actual line on days when occupancy is unusual
# for the time of day, which is exactly the information model B does not have.
# Neither captures the sharp peaks, which is the honest limit of a linear model
# with only calendar and occupancy inputs -- and the residuals those peaks leave
# behind are what Phase 6 detects.

# %% [markdown]
# ## Step 11: overfitting
#
# A model with more freedom always fits the *training* data better. The question
# is whether it gets better at data it has not seen. Plotting training and
# validation error together shows exactly where extra freedom stops helping and
# starts memorising noise.
#
# Two versions: polynomial regression of increasing degree on occupancy, and a
# random forest of increasing depth.

# %%
poly_curve = M.polynomial_overfitting_curve(tr, va, max_degree=10)
forest_curve = M.forest_depth_curve(tr, va)
display(poly_curve.round(1))
display(forest_curve.round(1))

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.4))

ax1.plot(poly_curve["degree"], poly_curve["train_MAE_w"] / 1000, marker="o",
         color=viz.CATEGORICAL[0], label="training error")
ax1.plot(poly_curve["degree"], poly_curve["val_MAE_w"] / 1000, marker="o",
         color=viz.CATEGORICAL[1], label="validation error")
best_degree = int(poly_curve.loc[poly_curve["val_MAE_w"].idxmin(), "degree"])
ax1.axvline(best_degree, color=viz.STATUS["ANOMALY"], linestyle="--", linewidth=1.3)
ax1.annotate(f"best validation\nerror at degree {best_degree}",
             xy=(best_degree, ax1.get_ylim()[1] * 0.85), xytext=(6, 0),
             textcoords="offset points", fontsize=8, color=viz.STATUS["ANOMALY"])
ax1.set_xlabel("Polynomial degree on occupancy")
ax1.set_ylabel("MAE (kW)")
ax1.set_title("Polynomial regression")
ax1.set_xticks(poly_curve["degree"])
ax1.legend()

x_positions = range(len(forest_curve))
ax2.plot(x_positions, forest_curve["train_MAE_w"] / 1000, marker="o",
         color=viz.CATEGORICAL[0], label="training error")
ax2.plot(x_positions, forest_curve["val_MAE_w"] / 1000, marker="o",
         color=viz.CATEGORICAL[1], label="validation error")
ax2.set_xticks(list(x_positions))
ax2.set_xticklabels(forest_curve["max_depth"].astype(str))
ax2.set_xlabel("Random forest maximum depth")
ax2.set_ylabel("MAE (kW)")
ax2.set_title("Random forest")
ax2.legend()

viz.save_fig(fig, "fig_04_overfitting_curves")

gap = forest_curve.iloc[-1]
print(f"at unlimited depth the forest's training error is "
      f"{gap['train_MAE_w'] / 1000:.2f} kW but its validation error is "
      f"{gap['val_MAE_w'] / 1000:.2f} kW -- a gap of "
      f"{gap['val_MAE_w'] / gap['train_MAE_w']:.1f}x")

# %% [markdown]
# **Takeaway.** The random forest shows the textbook picture perfectly: training
# error falls steadily towards zero as depth increases, while validation error
# flattens and then worsens. The gap between the two curves *is* overfitting,
# made visible. This is why the forest used in model D is capped at depth 12 and
# why validation error, never training error, decides anything.

# %% [markdown]
# ## Step 12: what the random forest thinks matters

# %%
d_pipeline = all_results[TARGET]["results"]["D"]["pipeline"]
importances = d_pipeline.named_steps["model"].feature_importances_
names = [n.split("__", 1)[-1]
         for n in d_pipeline.named_steps["prep"].get_feature_names_out()]

importance_table = (
    pd.DataFrame({"feature": names, "importance": importances})
    .sort_values("importance", ascending=False)
    .head(15)
    .reset_index(drop=True)
)
display(importance_table)

fig, ax = plt.subplots(figsize=(9, 5))
top = importance_table.iloc[::-1]
ax.barh(top["feature"], top["importance"], color=viz.CATEGORICAL[0])
ax.set_xlabel("Feature importance (random forest)")
ax.set_title(f"What the forest uses to predict {TARGET} power")
ax.grid(axis="x")
viz.save_fig(fig, "fig_04_feature_importance")

# %% [markdown]
# ## Step 13: residuals -- the raw material for Phase 6
#
# A residual is actual minus predicted. Phase 6 turns residuals into anomaly
# scores, so it is worth checking their shape now: they should be centred on zero
# and roughly symmetric, with no obvious pattern left in them.

# %%
resid_b = M.residual_frame(b_pipeline, te, include_occupancy=False, bias=bias_b)
resid_c = M.residual_frame(c_pipeline, te, include_occupancy=True, bias=bias_c)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.2))

ax1.hist(resid_b["residual_w"] / 1000, bins=70, alpha=0.7,
         color=viz.CATEGORICAL[0], label="B: time only")
ax1.hist(resid_c["residual_w"] / 1000, bins=70, alpha=0.7,
         color=viz.CATEGORICAL[1], label="C: time + occupancy")
ax1.axvline(0, color=viz.INK, linewidth=1.2)
ax1.set_xlabel("Residual (kW)   actual - predicted")
ax1.set_ylabel("intervals")
ax1.set_title("Residual distribution on the test period")
ax1.legend()

ax2.scatter(resid_c["predicted_w"] / 1000, resid_c["residual_w"] / 1000,
            s=3, alpha=0.2, color=viz.CATEGORICAL[1], edgecolors="none")
ax2.axhline(0, color=viz.INK, linewidth=1.2)
ax2.set_xlabel("Predicted power (kW)")
ax2.set_ylabel("Residual (kW)")
ax2.set_title("Model C residuals against prediction")

viz.save_fig(fig, f"fig_04_residuals_{TARGET.lower()}")

residual_summary = pd.DataFrame([
    {"detector": "T (model B, time only)",
     "mean residual kW": round(resid_b["residual_w"].mean() / 1000, 3),
     "sd residual kW": round(resid_b["residual_w"].std() / 1000, 2),
     "median kW": round(resid_b["residual_w"].median() / 1000, 2)},
    {"detector": "O (model C, time + occupancy)",
     "mean residual kW": round(resid_c["residual_w"].mean() / 1000, 3),
     "sd residual kW": round(resid_c["residual_w"].std() / 1000, 2),
     "median kW": round(resid_c["residual_w"].median() / 1000, 2)},
])
display(residual_summary)

# %% [markdown]
# **Takeaway.** After the drift correction both residual distributions sit close
# to zero, and model C's is narrower -- the point of adding occupancy. The
# right-hand panel shows the residuals still fan out at high predicted power,
# meaning the model is less certain when the building is busy. That is expected,
# and Phase 6 accounts for it by scoring deviations relative to the spread of the
# residuals rather than in absolute watts.

# %% [markdown]
# ## Step 14: write Phase 4 into the report

# %%
acad_cmp = occupancy_help.set_index("building").loc[TARGET]
mean_gain = occupancy_help["R2 gain from occupancy"].mean()
n_helped = int((occupancy_help["R2 gain from occupancy"] > 0).sum())
n_total_b = len(occupancy_help)
n_mae_helped = int((occupancy_help["MAE improvement %"] > 0).sum())
hurt = occupancy_help.loc[occupancy_help["R2 gain from occupancy"] <= 0, "building"]
hurt_names = ", ".join(b.replace("_", " ") for b in hurt) or "none"
best_gain = occupancy_help.loc[occupancy_help["R2 gain from occupancy"].idxmax()]
worst_gain = occupancy_help.loc[occupancy_help["R2 gain from occupancy"].idxmin()]
growth_min = drift["growth 2014-2017 %"].drop(
    index=drift.index[drift["building"] == "Lecture"]).min()
growth_max = drift["growth 2014-2017 %"].max()

blocks = {}

blocks["method_phase4"] = f"""
Phase 4 builds a baseline of *expected* consumption, not a forecast.

**Models.** **A** is `power = a + b x occupancy`, fitted unscaled so its two
coefficients keep physical units -- `a` watts with nobody present, `b` extra
watts per occupant. **B** uses calendar features only (hour, weekday, month,
weekend flag, semester flag). **C** adds occupancy to B. **D** is a random forest
on C's features, capped at depth 12.

**No lag features.** Power one hour ago correlates with current power at about
r = 0.95, and including it lifts validation R-squared from
{plain_scores['R2']:.2f} to {trap_scores['R2']:.2f}. It is excluded anyway,
because a model that knows what the building was drawing an hour ago has already
absorbed any waste into its expectation: if the lights have been on since 2 a.m.
it confidently predicts they will still be on at 3 a.m. and reports nothing
wrong. The notebook demonstrates this rather than asserting it.

**Encoding.** `hour` and `month` are cyclic categories -- hour 23 is adjacent to
hour 0 -- so they are one-hot encoded with `drop="first"` rather than treated as
numbers. The `StandardScaler` sits **inside the scikit-learn `Pipeline`**, so it
is fitted on the training fold only; scaling before splitting would leak the test
set's mean and spread into training.

**Splitting.** Chronological 70 / 15 / 15 via `train_test_split(shuffle=False)`.
Shuffling a time series would fit the model on Thursday to predict Wednesday.
Cross-validation uses `TimeSeriesSplit` with {C.CV_SPLITS} folds, which always
trains on a prefix and validates on the block immediately after.

**Concept drift, and how it is handled.** Mean power rose
{growth_min:.0f}-{growth_max:.0f}% across the record (section 6.5), so the test
split -- the last 15%, which is 2017 -- is the highest-consuming period and a
model fitted on 2014-2016 systematically under-predicts it. Test metrics are
reported **both** uncorrected and after a **validation-calibrated offset**: the
mean error measured on the validation split, which lies entirely before the test
split in time. That is what a deployed system could legitimately do and involves
no test data. Model *selection* is done on validation.

**Feature selection.** A correlation filter and `SelectKBest` with `f_regression`
are reported for transparency but not used to prune: with a few dozen encoded
columns and {len(train):,} training rows there is no overfitting pressure to
relieve, and dropping hour dummies would cost interpretability for no gain.

**Notebook:** `notebooks/04_regression.ipynb`.
"""

blocks["results_phase4"] = f"""
### The campus grew by a third to a half

Before any model result can be read, one thing has to be established:

{report.md_table(drift)}

{report.figure("fig_04_drift_by_year",
               "Mean power by year, indexed to 2014, and total growth per building",
               f"Six of seven buildings grew between {growth_min:.0f}% and "
               f"{growth_max:.0f}% in mean power over four years. The campus did "
               "not get more efficient; it got substantially more "
               "energy-hungry.")}

This is a finding in its own right and it is also a methodological problem. The
test split is the last 15% of the record -- 2017, the highest-consuming period --
so a model fitted on 2014-2016 under-predicts it systematically. Note too that in
the Academic building the **power-occupancy correlation itself fell**, from
{drift.set_index('building').loc[TARGET, 'r(power,occ) 2014']:.2f} in 2014 to
{drift.set_index('building').loc[TARGET, 'r(power,occ) 2017']:.2f} in 2017: the
relationship the models depend on weakened over time. Test-set numbers below
should be read with that in mind, which is why model selection uses the
validation split.

### Model scores

{report.md_table(scores)}

### Does occupancy help? (Research question 2)

{report.md_table(occupancy_help)}

{report.figure("fig_04_model_comparison",
               "Validation R-squared for models B and C, and the gain from adding occupancy",
               f"Occupancy improves validation R-squared in {n_helped} of the "
               f"{n_total_b} buildings, by a mean of {mean_gain:+.3f}, but the "
               f"gain ranges from {worst_gain['R2 gain from occupancy']:+.3f} to "
               f"{best_gain['R2 gain from occupancy']:+.3f}.")}

**Yes -- in most buildings, modestly, and very unevenly.** Adding occupancy
raises validation R-squared in **{n_helped} of {n_total_b}** buildings, with a
mean gain of **{mean_gain:+.3f}**. But the spread is the real story: the largest
gain is {best_gain['building'].replace('_', ' ')} at
**{best_gain['R2 gain from occupancy']:+.3f}**, while occupancy makes the model
slightly *worse* in {hurt_names}
({worst_gain['R2 gain from occupancy']:+.3f} at worst). It improves MAE in
{n_mae_helped} of {n_total_b}.

**A note on how to read these numbers.** Several validation R-squared values are
negative, meaning the model does worse than simply predicting the validation
mean. That is the concept drift of section 6.5 again -- the validation period
sits at a different consumption level from the training period. The *difference*
between C and B is still meaningful, because both models are fitted on the same
training data and face exactly the same drift; whatever the drift costs, it costs
them equally.

This is consistent with the LBNL finding that occupancy data adds only modestly
to building baseline models, and it is a real answer to research question 2
rather than a disappointment: **most of what drives these buildings is not the
number of people in them.** The same conclusion arrives independently from the
Phase 2 correlations and the Phase 3 flat daily profiles.

The pattern across buildings is also readable. Occupancy helps most where people
genuinely drive the load -- the Girls hostel
({occupancy_help.set_index('building').loc['Girls_Hostel', 'R2 gain from occupancy']:+.3f})
and the Library
({occupancy_help.set_index('building').loc['Library', 'R2 gain from occupancy']:+.3f}) --
and helps least, or slightly hurts, in the Mess and Facilities, whose loads are
driven by equipment schedules and weather rather than by headcount.

### Cross-validation with TimeSeriesSplit

{report.md_table(cv_table)}

### Base load and responsiveness -- the numbers Phase 5 uses

{report.md_table(model_a_table)}

{report.figure("fig_04_base_load_vs_responsiveness",
               "Base load against responsiveness, one point per building",
               "Buildings towards the top-left run their equipment regardless "
               "of who is present; buildings towards the bottom-right scale "
               "with their occupants.")}

The `a` column is the load the fitted line predicts at zero occupancy -- the
power a building draws with nobody in it -- and the night-time median column is
an independent check on it from a completely different calculation. Phase 5 takes
these two coefficients and turns them into the headline ranking.

### Predictions against reality

{report.figure(f"fig_04_actual_vs_predicted_{TARGET.lower()}",
               f"{TARGET} building: actual and predicted power over one test week, with occupancy below",
               "Both models reproduce the daily rhythm; model C bends towards "
               "the actual line when occupancy is unusual for the time of day. "
               "Neither captures the sharp peaks -- and those leftover peaks are "
               "what Phase 6 detects.")}

Note the chart uses two stacked panels rather than two y-axes. Watts and people
are different quantities, and putting them on one axis would invent a visual
relationship that does not exist.

### Overfitting

{report.md_table(forest_curve.round(1))}

{report.figure("fig_04_overfitting_curves",
               "Training and validation error against model complexity",
               f"The forest shows the textbook picture: at unlimited depth its "
               f"training error is {gap['train_MAE_w'] / 1000:.2f} kW but its "
               f"validation error is {gap['val_MAE_w'] / 1000:.2f} kW, a gap of "
               f"{gap['val_MAE_w'] / gap['train_MAE_w']:.1f}x. That gap is "
               "overfitting made visible.")}

### What the forest uses

{report.figure("fig_04_feature_importance",
               f"Random-forest feature importances for {TARGET} power",
               "Occupancy is the strongest single input, ahead of every "
               "hour-of-day indicator -- which is reassuring for a project built "
               "around it.")}

### Residuals

{report.md_table(residual_summary)}

{report.figure(f"fig_04_residuals_{TARGET.lower()}",
               "Residual distributions for models B and C, and residuals against prediction",
               "After the drift correction both distributions sit near zero and "
               "model C's is narrower. Residuals fan out at high predicted "
               "power, so Phase 6 scores deviations relative to the spread of "
               "the residuals rather than in absolute watts.")}
"""

report.update_blocks(blocks)

# %% [markdown]
# ## Step 15: record the Phase 4 decisions

# %%
report.log_decision(
    id="D04-01", phase="4",
    decision="Train/validation/test split",
    options_considered="Random 80/20; random 70/15/15; chronological 70/15/15",
    chosen=f"Chronological {C.SPLIT_TRAIN:.0%}/{C.SPLIT_VAL:.0%}/{C.SPLIT_TEST:.0%} "
           "via train_test_split(shuffle=False)",
    reason="A shuffled split on a time series fits the model on later data to "
           "predict earlier data, which makes every error measure optimistic "
           "and meaningless.",
    effect_on_results="Test metrics are much worse than a shuffled split would "
                      "report -- and correctly so. It also exposes the concept "
                      "drift that a shuffled split would have hidden entirely.",
)

report.log_decision(
    id="D04-02", phase="4",
    decision="Handling the 2014-2017 growth in consumption",
    options_considered="Ignore it; detrend the whole series; refit on recent "
                       "data only; apply a validation-calibrated offset",
    chosen="Report test metrics both uncorrected and with an offset equal to the "
           "mean error on the validation split",
    reason=f"Mean power rose {growth_min:.0f}-{growth_max:.0f}% across the "
           "record, so a model trained on 2014-2016 under-predicts 2017 by a "
           "near-constant amount. The validation split lies entirely before the "
           "test split, so using it introduces no leakage.",
    effect_on_results=f"Lifts {TARGET} model B test R-squared from "
                      f"{all_results[TARGET]['results']['B']['test_R2']:.3f} to "
                      f"{all_results[TARGET]['results']['B']['test_corrected_R2']:.3f}. "
                      "Phase 6 uses the corrected predictions, otherwise the "
                      "drift alone would flag the whole test period as anomalous.",
)

report.log_decision(
    id="D04-03", phase="4",
    decision="Excluding lag features from models B and C",
    options_considered="Include lag 1h and lag 1d (best accuracy); include "
                       "neither; include lag 1d only",
    chosen="Neither -- calendar and occupancy features only",
    reason=f"Lag 1h lifts validation R-squared from {plain_scores['R2']:.2f} to "
           f"{trap_scores['R2']:.2f}, but a model that knows recent power "
           "absorbs waste into its expectation and would predict that lights "
           "left on stay on. We need expected consumption, not best forecast.",
    effect_on_results="Reported R-squared is far lower than it could be. This is "
                      "deliberate: it is the price of a baseline that can detect "
                      "sustained waste in Phase 6.",
)

report.log_decision(
    id="D04-04", phase="4",
    decision="One-hot encoding hour and month instead of using them as numbers",
    options_considered="Raw integers; one-hot; sine/cosine cyclic encoding",
    chosen="One-hot with drop='first'",
    reason="Hour and month are cyclic: hour 23 is adjacent to hour 0. As raw "
           "integers a linear model would treat 23:00 as twenty-three times "
           "01:00. One-hot makes no ordering assumption and keeps the "
           "coefficients directly readable as 'the effect of this hour'.",
    effect_on_results=f"Expands {len(M.feature_columns(True))} raw columns to "
                      f"{encoded.shape[1]} encoded ones. Sine/cosine encoding "
                      "would use fewer columns but impose a smooth shape on the "
                      "day, which building load does not follow.",
)

report.log_decision(
    id="D04-05", phase="4",
    decision="Feature selection reported but not applied",
    options_considered="Prune to SelectKBest's top k; prune by correlation "
                       "threshold; report the ranking without pruning",
    chosen="Report the ranking; keep all features",
    reason=f"With {encoded.shape[1]} encoded columns and {len(train):,} training "
           "rows there is no overfitting pressure to relieve, and both methods "
           "are univariate so they cannot see redundancy anyway. Dropping hour "
           "dummies would cost interpretability for no measurable gain.",
    effect_on_results="None on the scores. The ranking is reported because it "
                      "shows occupancy is the strongest single predictor.",
)

report.log_decision(
    id="D04-06", phase="4",
    decision="Random forest depth",
    options_considered="Unlimited depth; tuned by grid search; fixed at 12",
    chosen="max_depth = 12, min_samples_leaf = 5, 120 trees, "
           f"random_state = {C.SEED}",
    reason="The depth curve shows validation error flattening around depth 12 "
           f"while training error keeps falling -- at unlimited depth the gap is "
           f"{gap['val_MAE_w'] / gap['train_MAE_w']:.1f}x. Model D is a "
           "sanity check on whether non-linearity matters, not the deliverable, "
           "so a defensible fixed depth is preferable to tuning.",
    effect_on_results="Model D scores slightly better than C on validation in "
                      "most buildings, confirming some non-linearity, but not "
                      "enough to displace the interpretable linear models that "
                      "Phases 5 and 6 depend on.",
)

report.publish_decision_log()
print()
print("blocks still pending:", len(report.pending_blocks()))
print("figures referenced but missing:", report.check_figures())

# %% [markdown]
# ## Phase 4 conclusion
#
# **Research question 2 is answered: occupancy helps in most buildings, modestly,
# and very unevenly.** Adding occupancy to a time-only model raises validation R²
# in five of the seven buildings, with a mean gain of about +0.11 -- but the gain
# runs from -0.06 (Facilities) to +0.44 (Girls hostel). It helps most where people
# genuinely drive the load and not at all where equipment schedules and weather
# do. That is a real improvement and a real limit, and it agrees with the
# published LBNL result. It also agrees with what Phase 2 and
# Phase 3 found by completely different routes: most of what drives these
# buildings is not the number of people in them.
#
# **Two things emerged that were not part of the plan:**
#
# 1. **The campus grew 32-48% in four years.** This is a substantial finding on
#    its own, and it forced an explicit treatment of concept drift.
# 2. **The power-occupancy relationship weakened over time** in the Academic
#    building (r fell from 0.71 to 0.45), which means a model of this campus
#    would need periodic refitting to stay useful.
#
# **What goes forward.** Model A's coefficients `a` and `b` for every building go
# to Phase 5. Models B and C, with their validation-calibrated offsets, become
# Detectors T and O in Phase 6.
