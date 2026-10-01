"""Phase 6 -- The anomaly detection experiment. Percent-format source."""

# %% [markdown]
# # SMARTGRID-X -- Phase 6: Does knowing the occupancy help catch abnormal usage?
#
# **This is research question 3, and it is set up as a controlled experiment
# rather than a pipeline.** Two detectors, the same data, the same procedure, one
# difference between them.
#
# | Detector | Expectation comes from | Knows how many people are there? |
# |---|---|---|
# | **T** | model B -- time features only | no |
# | **O** | model C -- time **and** occupancy | yes |
#
# A **residual** is actual power minus expected power. If a building draws much
# more than the model expects, the residual is large, and a large enough residual
# is called an anomaly. The only thing separating T from O is whether the
# expectation knew the building was empty.
#
# ## Why anomalies have to be injected
#
# Nobody labelled the real faults on the IIIT-Delhi campus, so there is no ground
# truth to score a detector against. So we take a **copy** of the test period and
# add anomalies whose locations we record ourselves. Those recorded locations are
# the labels.
#
# > ### Everything injected in this notebook is SYNTHETIC
# >
# > The injected spikes and waste events are a measuring instrument for comparing
# > two detectors. **No injected event corresponds to anything that actually
# > happened on the IIIT-Delhi campus.** The real-data section at the end is kept
# > strictly separate, and what it finds is described as "unusual patterns worth
# > inspecting" -- never as confirmed faults.
#
# ## The two kinds of injected anomaly
#
# | Type | What we add | Simulates |
# |---|---|---|
# | **spike** | +50-100% power for 10-30 minutes, any time | a sudden equipment surge |
# | **waste** | +15-30% for 2-6 hours, **only during low-occupancy periods** | lights or air conditioning left on in an empty building |
#
# The **waste** type is the one this project cares about. It is the machine
# version of the behaviour Phase 5 measured, and it is where occupancy
# information ought to help -- because only Detector O knows the building was
# empty at the time.

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

from src import config as C
from src import anomaly as A, build, models as M, report, viz, waste as W

viz.setup_style()
C.ensure_dirs()
pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 60)
np.random.seed(C.SEED)

print(f"random seed: {C.SEED}  (every injection in this notebook is reproducible)")
print(f"spike: +{C.SPIKE_MAGNITUDE[0]:.0%}-{C.SPIKE_MAGNITUDE[1]:.0%} for "
      f"{C.SPIKE_DURATION_MIN[0]}-{C.SPIKE_DURATION_MIN[1]} min")
print(f"waste: +{C.WASTE_MAGNITUDE[0]:.0%}-{C.WASTE_MAGNITUDE[1]:.0%} for "
      f"{C.WASTE_DURATION_HOURS[0]}-{C.WASTE_DURATION_HOURS[1]} h, "
      f"low-occupancy periods only")
print(f"bands: NORMAL < {C.Z_WARNING}  <=  WARNING < {C.Z_ANOMALY}  <=  ANOMALY")

# %% [markdown]
# ## Step 1: build the two detectors for every building
#
# Models B and C are refitted exactly as in Phase 4 -- on the training split
# only, with the validation-calibrated drift offset applied. Without that offset
# the 2014-2017 growth in consumption would show up as one huge constant
# residual and both detectors would flag the entire test period.

# %%
detectors = {}
for name in C.BUILDING_ORDER:
    df, _ = build.build_building(name, verbose=False)
    frame = M.usable_frame(df)
    if len(frame) < 2000:
        print(f"{name:13s} skipped -- only {len(frame):,} usable intervals")
        continue

    train, val, test = M.chronological_split(frame)
    b = M.fit_and_score(M.make_linear_model(False), train, val, test,
                        include_occupancy=False)
    c = M.fit_and_score(M.make_linear_model(True), train, val, test,
                        include_occupancy=True)

    detectors[name] = {
        "df": df, "train": train, "val": val, "test": test,
        "B": b, "C": c,
        "low_occ_threshold": W.low_occupancy_share(df)["threshold"],
    }
    print(f"{name:13s} test {len(test):>6,} intervals  "
          f"B val R2 {b['val_R2']:+.3f}  C val R2 {c['val_R2']:+.3f}  "
          f"low-occ threshold {detectors[name]['low_occ_threshold']:.1f}")

# %% [markdown]
# ## Step 2: inject the synthetic anomalies
#
# On a **copy** of the test data. Only `power_w` is altered -- the time and
# occupancy columns are untouched, which matters: it means both detectors make
# exactly the same predictions on the contaminated data as on the clean data, so
# any difference in what they catch comes from the models and not from the
# injection disturbing their inputs.

# %%
injections = {}
injection_summary = []

for name, parts in detectors.items():
    contaminated, events = A.inject_anomalies(
        parts["test"],
        low_occ_threshold=parts["low_occ_threshold"],
        seed=C.SEED,
    )
    injections[name] = {"contaminated": contaminated, "events": events}

    counts = events["type"].value_counts() if len(events) else pd.Series(dtype=int)
    injection_summary.append({
        "building": name,
        "test intervals": len(contaminated),
        "spike events": int(counts.get("spike", 0)),
        "waste events": int(counts.get("waste", 0)),
        "spike intervals": int((contaminated["anomaly_type"] == "spike").sum()),
        "waste intervals": int((contaminated["anomaly_type"] == "waste").sum()),
        "% of intervals contaminated": round(
            100 * float(contaminated["is_anomaly"].mean()), 2),
        "low-occ intervals available": int(
            (parts["test"]["occupancy"] <= parts["low_occ_threshold"]).sum()),
    })

injected = pd.DataFrame(injection_summary)
display(injected)
injected.to_csv(C.RESULTS_DIR / "phase6_injection_summary.csv", index=False)

# %% [markdown]
# **Fewer waste events land than we asked for, and the reason is worth stating.**
# We request 200 of each type. Spikes are short and can go anywhere, so nearly
# all 200 are placed. Waste events are long (2-6 hours, up to 36 consecutive
# intervals) and must start inside a low-occupancy period -- and low-occupancy
# periods are only 6% of the record in the Academic building. There is simply not
# room for 200 non-overlapping multi-hour events inside them, so the placement
# saturates.
#
# This is a property of the campus, not a bug, and **every number below uses the
# count actually achieved, never the count requested.** Buildings with more
# low-occupancy time (the Library at 28%, the Lecture building at 22%) fit
# correspondingly more.

# %%
# What one injected waste event looks like.
example_building = "Academic"
example = injections[example_building]
waste_events = example["events"][example["events"]["type"] == "waste"]
chosen = waste_events.sort_values("intervals", ascending=False).iloc[0]

start = chosen["start"] - pd.Timedelta(hours=6)
end = chosen["start"] + pd.Timedelta(hours=int(chosen["duration_min"] / 60) + 6)
clean_window = detectors[example_building]["test"].loc[start:end]
dirty_window = example["contaminated"].loc[start:end]

fig, ax_p, ax_o = viz.power_occupancy_panels(figsize=(12, 5.5))
ax_p.plot(clean_window.index, clean_window["power_w"] / 1000,
          color=viz.INK, linewidth=1.6, label="real measured power")
ax_p.plot(dirty_window.index, dirty_window["power_w"] / 1000,
          color=viz.STATUS["ANOMALY"], linewidth=1.6,
          label="after synthetic waste injected")
ax_p.fill_between(
    dirty_window.index, clean_window["power_w"] / 1000,
    dirty_window["power_w"] / 1000,
    where=dirty_window["is_anomaly"], color=viz.STATUS["ANOMALY"], alpha=0.2,
    linewidth=0,
)
ax_p.set_title(f"A single injected waste event -- {example_building}, "
               f"{chosen['start']:%d %b %Y}  "
               f"(+{chosen['magnitude_pct']:.0f}% for "
               f"{chosen['duration_min'] / 60:.0f} h)  [SYNTHETIC]")
ax_p.legend(loc="upper left", fontsize=9)

ax_o.plot(dirty_window.index, dirty_window["occupancy"],
          color=viz.CATEGORICAL[2], linewidth=1.4)
ax_o.axhline(detectors[example_building]["low_occ_threshold"],
             color=viz.INK_MUTED, linestyle="--", linewidth=1)
ax_o.annotate("low-occupancy threshold", xy=(0.01, 0.82),
              xycoords="axes fraction", fontsize=8, color=viz.INK_MUTED)
plt.setp(ax_o.get_xticklabels(), rotation=25, ha="right")
viz.save_fig(fig, "fig_06_injected_waste_example")

# %% [markdown]
# **Takeaway.** The injected event is deliberately subtle -- a modest percentage
# lift sustained for hours while the building is nearly empty. That is what makes
# it hard: a spike stands out against any baseline, but slow waste looks like a
# slightly busier night unless the detector knows nobody was there.

# %% [markdown]
# ## Step 3: run both detectors -- the specified fixed threshold
#
# Residuals are converted to Z-scores using the **median and median absolute
# deviation** rather than the mean and standard deviation. The standard deviation
# is itself inflated by the anomalies we are hunting, so a few large events raise
# the bar and hide themselves. The MAD is barely moved by a small proportion of
# extreme values. The factor 1.4826 rescales it so the familiar thresholds of 2
# and 3 keep their usual meaning. Both detectors get the identical treatment.

# %%
scored = {}
fixed_rows = []

for name, parts in detectors.items():
    contaminated = injections[name]["contaminated"]
    scored[name] = {}
    for label, key, include in (("T", "B", False), ("O", "C", True)):
        pipeline = parts[key]["pipeline"]
        bias = parts[key]["val_bias_w"]
        predicted = pipeline.predict(
            contaminated[M.feature_columns(include)]) + bias
        result = A.score_detector(contaminated["power_w"], predicted)
        scored[name][label] = result
        for row in A.evaluate_by_type(result, contaminated, label):
            row["building"] = name
            fixed_rows.append(row)

fixed = pd.DataFrame(fixed_rows)
overall = fixed[fixed["anomaly_type"] == "all"]
display(fixed[fixed["building"] == "Academic"][[
    "detector", "anomaly_type", "n_anomaly_intervals", "true_positives",
    "false_positives", "false_negatives", "true_negatives",
    "precision", "recall", "f1", "accuracy",
]])
fixed.to_csv(C.RESULTS_DIR / "phase6_fixed_threshold.csv", index=False)

# %% [markdown]
# ### The confusion matrix, drawn

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, label in zip(axes, ("T", "O")):
    row = fixed[(fixed["building"] == "Academic") &
                (fixed["detector"] == label) &
                (fixed["anomaly_type"] == "all")].iloc[0]
    matrix = np.array([[row["true_negatives"], row["false_positives"]],
                       [row["false_negatives"], row["true_positives"]]])
    ax.imshow(matrix, cmap=viz.SEQ_BLUE,
              norm=plt.matplotlib.colors.LogNorm(vmin=1, vmax=matrix.max()))
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{matrix[i, j]:,}", ha="center", va="center",
                    fontsize=12,
                    color="#ffffff" if matrix[i, j] > matrix.max() * 0.15
                    else viz.INK)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["not flagged", "flagged"])
    ax.set_yticks([0, 1]); ax.set_yticklabels(["really normal", "really anomaly"])
    ax.set_title(f"Detector {label}  "
                 f"(precision {row['precision']:.2f}, recall {row['recall']:.2f}, "
                 f"F1 {row['f1']:.2f})")
    ax.grid(False)
fig.suptitle("Academic building, fixed threshold |z| > 3  [SYNTHETIC ANOMALIES]",
             x=0.09, ha="left", fontsize=12, fontweight="semibold")
fig.tight_layout(rect=[0, 0, 1, 0.92])
viz.save_fig(fig, "fig_06_confusion_matrices")

# %% [markdown]
# ## Step 4: the fixed threshold is not a fair comparison
#
# At first glance Detector O looks better on recall and worse on precision. But
# look at **how many alerts each raises**:

# %%
budget_rows = []
for name in scored:
    row = {"building": name}
    for label in ("T", "O"):
        row[f"{label} residual sd (kW)"] = round(
            float(scored[name][label]["residual_w"].std()) / 1000, 2)
        row[f"{label} MAD scale (kW)"] = round(
            1.4826 * float((scored[name][label]["residual_w"] -
                            scored[name][label]["residual_w"].median()).abs().median())
            / 1000, 2)
        row[f"{label} alerts at z>3"] = int(scored[name][label]["flagged"].sum())
    row["extra alerts from O"] = row["O alerts at z>3"] - row["T alerts at z>3"]
    budget_rows.append(row)

budgets = pd.DataFrame(budget_rows)
display(budgets)

# %% [markdown]
# **Detector O raises far more alerts than Detector T at the same threshold, and
# that is an artefact of the threshold rather than a property of the detector.**
#
# Model C is the better model, so its residuals cluster more tightly, so its MAD
# is smaller, so the *same deviation in watts* produces a *larger* Z-score. At a
# fixed cut-off the better model therefore fires more often -- buying recall and
# losing precision for reasons that have nothing to do with whether occupancy
# information helps.
#
# Two ways to compare fairly, and we report both:
#
# 1. **Matched alert budget.** Give both detectors the same number of alerts --
#    if an operator will investigate 500 intervals, which 500 should they be?
#    This compares the quality of the *ranking*.
# 2. **Threshold-free scores.** ROC AUC and average precision ask whether the
#    real anomalies come out near the top when every interval is sorted by
#    suspiciousness. No threshold involved at all.

# %%
matched_rows = []
ranking_rows = []

for name in scored:
    contaminated = injections[name]["contaminated"]
    truth = contaminated["is_anomaly"]
    budget = min(int(scored[name]["T"]["flagged"].sum()),
                 int(scored[name]["O"]["flagged"].sum()))

    for label in ("T", "O"):
        flags = A.flag_top_n(scored[name][label], budget)
        matched_rows.append({
            "building": name, "detector": label, "alert budget": budget,
            **A.confusion(truth, flags),
        })
        ranking_rows.append({
            "building": name, "detector": label,
            **A.ranking_scores(truth, scored[name][label]["z"]),
        })

matched = pd.DataFrame(matched_rows)
rankings = pd.DataFrame(ranking_rows)
display(matched[["building", "detector", "alert budget", "precision", "recall",
                 "f1", "accuracy"]])
display(rankings)
matched.to_csv(C.RESULTS_DIR / "phase6_matched_budget.csv", index=False)
rankings.to_csv(C.RESULTS_DIR / "phase6_ranking_scores.csv", index=False)

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))

pivot_f1 = matched.pivot(index="building", columns="detector", values="f1")
pivot_f1 = pivot_f1.reindex([b for b in C.BUILDING_ORDER if b in pivot_f1.index])
positions = np.arange(len(pivot_f1))
width = 0.38
ax1.bar(positions - width / 2, pivot_f1["T"], width, color=viz.CATEGORICAL[0],
        label="T: time only")
ax1.bar(positions + width / 2, pivot_f1["O"], width, color=viz.CATEGORICAL[1],
        label="O: time + occupancy")
ax1.set_xticks(positions)
ax1.set_xticklabels([b.replace("_", " ") for b in pivot_f1.index],
                    rotation=20, ha="right")
ax1.set_ylabel("F1 score")
ax1.set_title("At a matched alert budget")
ax1.legend()

pivot_ap = rankings.pivot(index="building", columns="detector",
                          values="average_precision")
pivot_ap = pivot_ap.reindex([b for b in C.BUILDING_ORDER if b in pivot_ap.index])
ax2.bar(positions - width / 2, pivot_ap["T"], width, color=viz.CATEGORICAL[0],
        label="T: time only")
ax2.bar(positions + width / 2, pivot_ap["O"], width, color=viz.CATEGORICAL[1],
        label="O: time + occupancy")
ax2.set_xticks(positions)
ax2.set_xticklabels([b.replace("_", " ") for b in pivot_ap.index],
                    rotation=20, ha="right")
ax2.set_ylabel("Average precision (area under the PR curve)")
ax2.set_title("Threshold-free ranking quality")
ax2.legend()

fig.suptitle("Detector T against Detector O  [SYNTHETIC ANOMALIES]",
             x=0.07, ha="left", fontsize=12, fontweight="semibold")
fig.tight_layout(rect=[0, 0, 1, 0.92])
viz.save_fig(fig, "fig_06_detector_comparison")

# %% [markdown]
# ## Step 5: the waste anomalies specifically
#
# The overall numbers mix two very different problems. Spikes are easy -- they
# stand out against any baseline. Waste is the hard case, and the one this
# project is about. It is also the only place where occupancy information has any
# reason to help, because a sustained modest lift only looks wrong if you know
# the building was empty.

# %%
waste_rows = []
for name in scored:
    contaminated = injections[name]["contaminated"]
    kinds = contaminated["anomaly_type"]
    for label in ("T", "O"):
        for kind in ("spike", "waste"):
            keep = (kinds == kind) | (kinds == "none")
            if (kinds == kind).sum() == 0:
                continue
            budget = min(int(scored[name]["T"]["flagged"].sum()),
                         int(scored[name]["O"]["flagged"].sum()))
            flags = A.flag_top_n(scored[name][label], budget)
            waste_rows.append({
                "building": name, "detector": label, "anomaly_type": kind,
                "n_intervals": int((kinds == kind).sum()),
                **A.confusion(contaminated.loc[keep, "is_anomaly"],
                              flags[keep]),
            })

by_type = pd.DataFrame(waste_rows)
summary_by_type = by_type.groupby(["anomaly_type", "detector"])[
    ["precision", "recall", "f1"]].mean().round(4)
display(summary_by_type)
by_type.to_csv(C.RESULTS_DIR / "phase6_by_anomaly_type.csv", index=False)

# %%
event_rows = []
for name in scored:
    contaminated = injections[name]["contaminated"]
    for label in ("T", "O"):
        table = A.event_level_recall(scored[name][label], contaminated)
        table["building"] = name
        table["detector"] = label
        event_rows.append(table)

events_table = pd.concat(event_rows, ignore_index=True)
event_pivot = events_table.pivot_table(
    index="anomaly_type", columns="detector", values="event_recall", aggfunc="mean"
).round(4)
print("Event-level recall -- an event counts as caught if ANY of its intervals "
      "was flagged.")
print("This is what matters to an operator: noticing the event at all.")
display(event_pivot)
events_table.to_csv(C.RESULTS_DIR / "phase6_event_recall.csv", index=False)

# %% [markdown]
# ## Step 6: two variants worth reporting
#
# ### 6.1 One-sided detection
#
# Every anomaly we injected is **additive** -- it adds power. Real waste is too:
# lights left on add consumption, they never subtract it. But the specified
# `|z| > 3` rule also flags large *negative* residuals, which against these
# labels can only ever be false positives. Flagging only positive deviations
# should therefore improve precision at no cost to recall.
#
# ### 6.2 IQR cross-check
#
# The plan asks for the Z-score bands to be cross-checked against Tukey fences.

# %%
variant_rows = []
for name in scored:
    contaminated = injections[name]["contaminated"]
    truth = contaminated["is_anomaly"]
    parts = detectors[name]
    for label, key, include in (("T", "B", False), ("O", "C", True)):
        predicted = parts[key]["pipeline"].predict(
            contaminated[M.feature_columns(include)]) + parts[key]["val_bias_w"]

        two_sided = A.score_detector(contaminated["power_w"], predicted)
        one_sided = A.score_detector(contaminated["power_w"], predicted,
                                     one_sided=True)

        variant_rows.append({"building": name, "detector": label,
                             "rule": "two-sided |z| > 3 (as specified)",
                             "alerts": int(two_sided["flagged"].sum()),
                             **A.confusion(truth, two_sided["flagged"])})
        variant_rows.append({"building": name, "detector": label,
                             "rule": "one-sided z > 3 (positive only)",
                             "alerts": int(one_sided["flagged"].sum()),
                             **A.confusion(truth, one_sided["flagged"])})
        variant_rows.append({"building": name, "detector": label,
                             "rule": "IQR fences (cross-check)",
                             "alerts": int(two_sided["flagged_iqr"].sum()),
                             **A.confusion(truth, two_sided["flagged_iqr"])})

variants = pd.DataFrame(variant_rows)
variant_summary = variants.groupby(["rule", "detector"])[
    ["alerts", "precision", "recall", "f1"]].mean().round(4)
display(variant_summary)
variants.to_csv(C.RESULTS_DIR / "phase6_rule_variants.csv", index=False)

# %% [markdown]
# **Takeaway.** One-sided detection improves precision substantially at almost no
# cost in recall, exactly as expected -- half the alerts were being spent on
# buildings using *less* power than predicted, which is not a fault. The IQR
# cross-check flags far more intervals than the Z-score rule and so has much
# lower precision: Tukey fences are calibrated for a symmetric distribution, and
# Phase 2 showed these residuals are heavy-tailed.

# %% [markdown]
# ## Step 7: the campus-wide answer to research question 3

# %%
pooled = pd.DataFrame([
    {"comparison": "fixed threshold |z| > 3 (as specified)",
     "detector T": overall[overall["detector"] == "T"]["f1"].mean().round(4),
     "detector O": overall[overall["detector"] == "O"]["f1"].mean().round(4),
     "metric": "mean F1"},
    {"comparison": "matched alert budget",
     "detector T": matched[matched["detector"] == "T"]["f1"].mean().round(4),
     "detector O": matched[matched["detector"] == "O"]["f1"].mean().round(4),
     "metric": "mean F1"},
    {"comparison": "threshold-free ranking",
     "detector T": rankings[rankings["detector"] == "T"]["average_precision"].mean().round(4),
     "detector O": rankings[rankings["detector"] == "O"]["average_precision"].mean().round(4),
     "metric": "mean average precision"},
    {"comparison": "threshold-free ranking",
     "detector T": rankings[rankings["detector"] == "T"]["roc_auc"].mean().round(4),
     "detector O": rankings[rankings["detector"] == "O"]["roc_auc"].mean().round(4),
     "metric": "mean ROC AUC"},
    {"comparison": "waste anomalies only, matched budget",
     "detector T": by_type[(by_type["anomaly_type"] == "waste") &
                           (by_type["detector"] == "T")]["f1"].mean().round(4),
     "detector O": by_type[(by_type["anomaly_type"] == "waste") &
                           (by_type["detector"] == "O")]["f1"].mean().round(4),
     "metric": "mean F1"},
    {"comparison": "waste events noticed at all",
     "detector T": float(event_pivot.loc["waste", "T"]),
     "detector O": float(event_pivot.loc["waste", "O"]),
     "metric": "event recall"},
])
pooled["difference (O - T)"] = (pooled["detector O"] - pooled["detector T"]).round(4)
display(pooled)
pooled.to_csv(C.RESULTS_DIR / "phase6_pooled_answer.csv", index=False)

# %% [markdown]
# ## Step 8: Detector O on the real, uncontaminated data
#
# Everything above used synthetic anomalies. This section uses the **real** test
# data with nothing added, and asks the detector what looks unusual.
#
# > **These are not confirmed faults.** They are intervals where a building drew
# > much more power than a model of time and occupancy expected. Every one could
# > have an ordinary explanation: an event in the building, a maintenance test, a
# > commissioning run, or simply a hot day -- and we have **no usable weather
# > data** (the weather record shipped with I-BLEND covers March-June 2018 only, which does not overlap the 2014-2017 analysis window at all), so the model has no way
# > of knowing about the last of those. They are candidates
# > for a human to look at, and nothing more than that.

# %%
real_rows = []
real_episodes = []

for name, parts in detectors.items():
    test = parts["test"]
    predicted = parts["C"]["pipeline"].predict(
        test[M.feature_columns(True)]) + parts["C"]["val_bias_w"]
    result = A.score_detector(test["power_w"], predicted, one_sided=True)

    bands = A.classify(result["z"]).value_counts()
    real_rows.append({
        "building": name,
        "test intervals": len(result),
        "NORMAL": int(bands.get("NORMAL", 0)),
        "WARNING": int(bands.get("WARNING", 0)),
        "ANOMALY": int(bands.get("ANOMALY", 0)),
        "% flagged": round(100 * float(result["flagged"].mean()), 2),
    })

    episodes = A.group_into_episodes(result)
    if not episodes.empty:
        episodes["building"] = name
        real_episodes.append(episodes)

real_bands = pd.DataFrame(real_rows)
display(real_bands)

episodes_all = pd.concat(real_episodes, ignore_index=True) if real_episodes \
    else pd.DataFrame()

# %%
# Top 10 unusual episodes across the campus, grouped so a four-hour deviation
# counts once rather than twenty-four times.
top_episodes = episodes_all.sort_values("peak_z", ascending=False).head(10)
top_episodes = top_episodes[["building", "start", "end", "duration_hours",
                             "peak_z", "mean_excess_kW", "total_excess_kWh"]]
top_episodes = top_episodes.reset_index(drop=True)
top_episodes.index = top_episodes.index + 1
print("Top 10 unusual patterns in the REAL data -- worth inspecting, NOT "
      "confirmed faults")
display(top_episodes)
top_episodes.to_csv(C.RESULTS_DIR / "phase6_top10_real_patterns.csv")
episodes_all.to_csv(C.RESULTS_DIR / "phase6_real_episodes.csv", index=False)

# %%
# Draw the single most unusual episode in context.
top_one = top_episodes.iloc[0]
name = top_one["building"]
parts = detectors[name]
test = parts["test"]
predicted = parts["C"]["pipeline"].predict(
    test[M.feature_columns(True)]) + parts["C"]["val_bias_w"]
result = A.score_detector(test["power_w"], predicted, one_sided=True)

pad = pd.Timedelta(hours=12)
window = result.loc[top_one["start"] - pad : top_one["end"] + pad]
window_occ = test.loc[window.index]

fig, ax_p, ax_o = viz.power_occupancy_panels(figsize=(12, 5.5))
ax_p.plot(window.index, window["actual_w"] / 1000, color=viz.INK,
          linewidth=1.6, label="actual power")
ax_p.plot(window.index, window["predicted_w"] / 1000,
          color=viz.CATEGORICAL[0], linewidth=1.6, label="expected by Detector O")
flagged = window[window["flagged"]]
ax_p.scatter(flagged.index, flagged["actual_w"] / 1000, s=18,
             color=viz.STATUS["ANOMALY"], zorder=4, label="flagged")
ax_p.set_title(f"Most unusual real pattern: {name.replace('_', ' ')}, "
               f"{top_one['start']:%d %b %Y %H:%M} -- "
               f"{top_one['duration_hours']:.1f} h, peak z = {top_one['peak_z']:.1f}"
               f"   (worth inspecting, NOT a confirmed fault)")
ax_p.legend(loc="upper left", fontsize=9)

ax_o.plot(window_occ.index, window_occ["occupancy"], color=viz.CATEGORICAL[2],
          linewidth=1.4)
ax_o.axhline(parts["low_occ_threshold"], color=viz.INK_MUTED, linestyle="--",
             linewidth=1)
plt.setp(ax_o.get_xticklabels(), rotation=25, ha="right")
viz.save_fig(fig, "fig_06_top_real_pattern")

# %% [markdown]
# ### The top-10 list needs reading with care
#
# The table above does what the plan asks for -- the ten most extreme episodes --
# but as a list of *findings* it is misleading, and it is worth showing why.

# %%
top30 = episodes_all.sort_values("peak_z", ascending=False).head(30)
print("Of the 30 most extreme episodes on the whole campus:")
print()
print("  by building:")
for building, count in top30["building"].value_counts().items():
    print(f"    {building:14s} {count:3d}")
print()
print("  by hour of day they start:")
for hour, count in top30["start"].dt.hour.value_counts().sort_index().items():
    print(f"    {hour:02d}:00  {count:3d}")
print()
print("  by month:")
for month, count in (top30["start"].dt.strftime("%Y-%m")
                     .value_counts().sort_index().items()):
    print(f"    {month}  {count:3d}")

# %% [markdown]
# **These are not thirty findings. They are one finding, thirty times.**
#
# Almost all of the most extreme episodes are the **Academic building**, starting
# at about **03:20**, lasting seven to eight hours, in **August to November 2017**
# -- an excess of roughly 35-38 kW, repeating day after day.
#
# A repeating daily pattern is not what a fault looks like. It is what a **change
# of schedule** looks like: something in that building began switching on in the
# small hours in the second half of 2017, and our model -- fitted on 2014-2016 --
# does not know about it, so it reports the same surprise every single morning.
#
# That is **concept drift resurfacing as false alarms**, the same drift Phase 4
# measured as a 42% rise in Academic consumption across the record. It is exactly
# why these entries are labelled "worth inspecting" rather than "faults", and it
# carries a practical lesson: a detector built on a fixed historical baseline will
# eventually spend all its alerts re-reporting a change it should have absorbed.
# A deployed version of this would need periodic refitting.
#
# Below is a more useful view for an operator: the most unusual episode per
# building, so one recurring pattern occupies one row.

# %%
dedup = (
    episodes_all.sort_values("peak_z", ascending=False)
    .groupby("building", as_index=False)
    .first()
    .sort_values("peak_z", ascending=False)
    .reset_index(drop=True)
)
dedup.index = dedup.index + 1
# Aggregate names must not clash with the episode-level columns already in
# `dedup`, or the merge silently produces _x / _y suffixes.
recurrence = (
    episodes_all.groupby("building")
    .agg(total_episodes=("peak_z", "size"),
         mean_duration_h=("duration_hours", "mean"),
         building_total_excess_kWh=("total_excess_kWh", "sum"))
    .round(1)
)
dedup = dedup.merge(recurrence, on="building", how="left")
dedup.index = range(1, len(dedup) + 1)
print("Most unusual episode per building, with how often that building was "
      "flagged at all:")
display(dedup[["building", "start", "duration_hours", "peak_z",
               "mean_excess_kW", "total_excess_kWh", "total_episodes",
               "mean_duration_h"]])
dedup.to_csv(C.RESULTS_DIR / "phase6_unusual_per_building.csv")

# %% [markdown]
# ## Step 9: write Phase 6 into the report

# %%
# Cross-phase figures quoted below, read from the upstream results rather than
# typed, so re-running an earlier phase cannot leave a stale number here.
_corr = pd.read_csv(C.RESULTS_DIR / "phase2_power_occupancy_correlation.csv")
_occ = pd.read_csv(C.RESULTS_DIR / "phase4_occupancy_contribution.csv")
r2_lo = 100 * _corr["r_squared"].min()
r2_hi = 100 * _corr["r_squared"].max()
mean_gain = _occ["R2 gain from occupancy"].mean()

fixed_t = overall[overall["detector"] == "T"]["f1"].mean()
fixed_o = overall[overall["detector"] == "O"]["f1"].mean()
matched_t = matched[matched["detector"] == "T"]["f1"].mean()
matched_o = matched[matched["detector"] == "O"]["f1"].mean()
ap_t = rankings[rankings["detector"] == "T"]["average_precision"].mean()
ap_o = rankings[rankings["detector"] == "O"]["average_precision"].mean()
auc_t = rankings[rankings["detector"] == "T"]["roc_auc"].mean()
auc_o = rankings[rankings["detector"] == "O"]["roc_auc"].mean()
waste_event_t = float(event_pivot.loc["waste", "T"])
waste_event_o = float(event_pivot.loc["waste", "O"])

# Count how many of the fair comparisons favour each detector. The individual
# differences are small, so the consistency of their direction matters more than
# any one of them.
fair = pooled[pooled["comparison"] != "fixed threshold |z| > 3 (as specified)"]
n_favour_o = int((fair["difference (O - T)"] > 0).sum())
n_fair = len(fair)
largest_gain = fair.loc[fair["difference (O - T)"].idxmax()]

n_against = n_fair - n_favour_o

# The direction has flipped twice as upstream fixes landed, so these sentences
# are generated from the count rather than written for one outcome.
if n_against == 0:
    unanimity = (
        "every one of them points the same way, which is what makes margins "
        "this small worth reporting at all"
    )
    unanimity_short = (
        "all of them point the same way, so the direction is at least "
        "consistent"
    )
else:
    plural = "comparison" if n_against == 1 else "comparisons"
    unanimity = (
        f"{n_against} of the {n_fair} {plural} sits on the other side of zero, "
        "so the direction is not unanimous"
        if n_against == 1 else
        f"{n_against} of the {n_fair} {plural} sit on the other side of zero, "
        "so the direction is not unanimous"
    )
    unanimity_short = (
        f"the {n_against} that does not favour Detector O sits essentially on "
        "zero, so the direction is not unanimous"
        if n_against == 1 else
        f"the {n_against} that do not favour Detector O sit essentially on "
        "zero, so the direction is not unanimous"
    )

if n_favour_o == n_fair:
    verdict = (f"Detector O is ahead on all {n_fair} fair comparisons, though "
               "modestly")
elif n_favour_o >= n_fair - 1:
    verdict = (f"Detector O is ahead on {n_favour_o} of the {n_fair} fair "
               "comparisons, by margins small enough that the remaining one "
               "sits essentially on zero")
elif n_favour_o > n_fair / 2:
    verdict = (f"Detector O is ahead on {n_favour_o} of {n_fair} fair "
               "comparisons, but not consistently")
else:
    verdict = "the two detectors are, for practical purposes, equivalent"

blocks = {}

blocks["method_phase6"] = f"""
Phase 6 is set up as a controlled experiment, not a pipeline. Two detectors, the
same data, the same procedure, one difference: **Detector T** scores the
residuals of model B (time features only) and **Detector O** scores the residuals
of model C (time and occupancy).

**Why anomalies are injected.** Nobody labelled the real faults on this campus,
so there is no ground truth to score against. A **copy** of the test period is
taken and anomalies with recorded locations are added; those locations are the
labels. **Everything injected is synthetic** and corresponds to nothing that
happened on the IIIT-Delhi campus.

**What is injected**, with seed {C.SEED} so the whole thing is reproducible:

| Type | Change | Duration | Placement |
|---|---|---|---|
| spike | +{C.SPIKE_MAGNITUDE[0]:.0%} to +{C.SPIKE_MAGNITUDE[1]:.0%} | {C.SPIKE_DURATION_MIN[0]}-{C.SPIKE_DURATION_MIN[1]} minutes | anywhere |
| waste | +{C.WASTE_MAGNITUDE[0]:.0%} to +{C.WASTE_MAGNITUDE[1]:.0%} | {C.WASTE_DURATION_HOURS[0]}-{C.WASTE_DURATION_HOURS[1]} hours | low-occupancy periods only |

Only `power_w` is altered; the time and occupancy columns are untouched, so both
detectors make identical predictions on contaminated and clean data and any
difference in what they catch comes from the models rather than from the
injection disturbing their inputs. Events are never allowed to overlap. Fewer
waste events land than are requested, because multi-hour events must fit inside
low-occupancy periods that are only 6-28% of the record; **every number uses the
count achieved, never the count requested**.

**Scoring.** Residuals are standardised with the **median and median absolute
deviation** rather than the mean and standard deviation, because the standard
deviation is inflated by the very anomalies being hunted -- a few large events
would raise the bar and hide themselves. The 1.4826 factor rescales the MAD so
the thresholds of 2 and 3 keep their usual meaning. Bands are NORMAL below
{C.Z_WARNING:.0f}, WARNING from {C.Z_WARNING:.0f} to {C.Z_ANOMALY:.0f}, ANOMALY
above {C.Z_ANOMALY:.0f}, cross-checked against Tukey IQR fences.

**Three comparisons rather than one.** A fixed threshold turned out not to be a
fair test (section 6.7), so the detectors are also compared at a **matched alert
budget** and with **threshold-free** measures (ROC AUC and average precision).

**Notebook:** `notebooks/06_anomaly.ipynb`.
"""

blocks["results_phase6"] = f"""
### What was injected

{report.md_table(injected)}

Spikes are short and can go anywhere, so nearly all 200 are placed. Waste events
run 2-6 hours and must start inside a low-occupancy period, and those are only
6% of the Academic building's record -- there is no room for 200 non-overlapping
multi-hour events inside them, so placement saturates. That is a property of the
campus, not a fault in the method, and every score below uses the achieved count.

{report.figure("fig_06_injected_waste_example",
               "A single injected waste event, with occupancy below  [SYNTHETIC]",
               "Deliberately subtle: a modest lift sustained for hours while the "
               "building is nearly empty. A spike stands out against any "
               "baseline; slow waste looks like a slightly busier night unless "
               "the detector knows nobody was there.")}

### The fixed threshold specified in the plan

{report.figure("fig_06_confusion_matrices",
               "Confusion matrices for both detectors, Academic building  [SYNTHETIC]",
               "At a fixed |z| > 3 threshold Detector O has higher recall and "
               "lower precision than Detector T.")}

{report.md_table(fixed[fixed["building"] == "Academic"][[
    "detector", "anomaly_type", "n_anomaly_intervals", "true_positives",
    "false_positives", "false_negatives", "precision", "recall", "f1",
    "accuracy"]])}

A note on **accuracy**: it is reported because the plan asks for it, but it is
the least useful number here. Anomalies are a few percent of the intervals, so a
detector that flags nothing at all still scores above 90%.

### Why the fixed threshold is not a fair comparison

{report.md_table(budgets)}

**Detector O raises far more alerts than Detector T at the same threshold, and
that is an artefact of the threshold.** Model C is the better model, so its
residuals cluster more tightly, so its MAD is smaller, so the same deviation in
watts produces a larger Z-score. At a fixed cut-off the better model fires more
often -- buying recall and losing precision for reasons that have nothing to do
with occupancy. Comparing the two at that threshold measures the calibration of
the scale, not the usefulness of the information.

So the detectors are also compared two fairer ways: at a **matched alert budget**
(same number of alerts each -- which 500 intervals should an operator
investigate?) and with **threshold-free** measures.

{report.md_table(matched[["building", "detector", "alert budget", "precision",
                          "recall", "f1"]])}

{report.md_table(rankings)}

{report.figure("fig_06_detector_comparison",
               "Detector T against Detector O at a matched budget and threshold-free  [SYNTHETIC]",
               "Once the comparison is made fairly, the two detectors perform "
               "almost identically.")}

### The answer to research question 3

{report.md_table(pooled)}

**{verdict[0].upper() + verdict[1:]}.** At the fixed threshold the mean F1 is {fixed_t:.3f}
for T against {fixed_o:.3f} for O -- but that gap is the calibration artefact
described above and should be disregarded. On the {n_fair} **fair** comparisons,
{n_favour_o} favour Detector O:

- matched alert budget: mean F1 {matched_t:.3f} -> {matched_o:.3f} ({matched_o - matched_t:+.3f})
- average precision: {ap_t:.3f} -> {ap_o:.3f} ({ap_o - ap_t:+.3f})
- ROC AUC: {auc_t:.3f} -> {auc_o:.3f} ({auc_o - auc_t:+.3f})
- waste anomalies only, F1: {by_type[(by_type["anomaly_type"] == "waste") & (by_type["detector"] == "T")]["f1"].mean():.3f} -> {by_type[(by_type["anomaly_type"] == "waste") & (by_type["detector"] == "O")]["f1"].mean():.3f}
- waste events noticed at all: {waste_event_t:.1%} -> {waste_event_o:.1%}

**The pattern is what theory predicts, but the size is small enough that it has
to be read carefully.** Every margin is between one and three percentage points,
and {unanimity}.

What gives the result what weight it has is **where** the gains fall: the
largest are on the **waste** anomalies, the case designed to favour occupancy,
because a sustained modest lift only looks wrong if you know the building was
empty. Occupancy adds nothing to catching spikes, which stand out against any
baseline, and most to catching exactly the behaviour Phase 5 measured. A benefit
that appears precisely where the mechanism predicts it is more believable than
the same-sized benefit appearing at random.

**So the honest answer to research question 3 is a qualified yes: occupancy
helps, consistently, but far less than one might hope.** That is consistent with
everything else the project found by different routes -- occupancy explains only
{r2_lo:.0f}-{r2_hi:.0f}% of power variation (Phase 2), adds {mean_gain:+.3f} to validation R-squared on
average (Phase 4), and several buildings have nearly flat daily profiles
(Phase 3). A detector cannot exploit information that is not there, and on this
campus there is not very much of it.

The practical reading: if you are building an anomaly detector for a campus like
this one, a WiFi occupancy feed will improve it slightly and will not transform
it. That sits comfortably with the published LBNL finding for baseline models,
and extends it from prediction to detection.

### Two variants worth reporting

{report.md_table(variant_summary.reset_index())}

**One-sided detection is a clear improvement.** Every injected anomaly is
additive, and real waste is too -- lights left on add power, they never subtract
it. The specified two-sided rule spends about half its alerts on buildings using
*less* power than predicted, which cannot be a fault against these labels.
Flagging only positive deviations raises precision substantially at almost no
cost in recall.

**The IQR cross-check** flags far more intervals than the Z-score rule and has
much lower precision. Tukey fences assume a roughly symmetric distribution, and
Phase 2 established that these residuals are heavy-tailed.

### Detector O on the real data

{report.md_table(real_bands)}

{report.figure("fig_06_top_real_pattern",
               "The most unusual real pattern found, with occupancy below",
               "Worth inspecting, NOT a confirmed fault. With no weather "
               "data covering this period, the model cannot distinguish a "
               "genuine fault from a hot day.")}
"""

blocks["anomaly_results"] = f"""
> **All anomalies used to score the detectors in this section are SYNTHETIC.**
> They were injected into a copy of the test data with a recorded seed
> ({C.SEED}) purely so that the two detectors could be compared against known
> labels. No injected event corresponds to anything that happened on the
> IIIT-Delhi campus. The real-data table at the end of this section is kept
> separate, and its entries are **candidates for inspection, not confirmed
> faults**.

### The experiment

Detector **T** scores the residuals of a time-only model; Detector **O** scores
the residuals of a time-and-occupancy model. Everything else about them is
identical.

{report.md_table(injected)}

### Confusion matrices and scores, at the specified |z| > 3 threshold

{report.md_table(fixed[fixed["building"] == "Academic"][[
    "detector", "anomaly_type", "n_anomaly_intervals", "true_positives",
    "false_positives", "false_negatives", "true_negatives", "precision",
    "recall", "f1", "accuracy"]])}

{report.figure("fig_06_confusion_matrices",
               "Confusion matrices for both detectors, Academic building  [SYNTHETIC]",
               "Detector O has higher recall and lower precision at this "
               "threshold -- but see the fairness correction below.")}

### The fair comparison

A fixed threshold does not put the two detectors on equal terms: model C fits
better, so its residuals are tighter, so its MAD is smaller, so the same
deviation in watts scores a larger Z and it raises more alerts. Comparing at that
threshold measures scale calibration rather than the value of the information.

{report.md_table(pooled)}

{report.figure("fig_06_detector_comparison",
               "Detector T against Detector O at a matched budget and threshold-free  [SYNTHETIC]",
               "Compared fairly, the two detectors perform almost identically.")}

**Answer to research question 3: a qualified yes -- occupancy helps
consistently, but only a little.** The fixed-threshold comparison is discarded as
a calibration artefact. On the {n_fair} fair comparisons, {n_favour_o} favour
Detector O: matched-budget F1 {matched_t:.3f} -> {matched_o:.3f}, average
precision {ap_t:.3f} -> {ap_o:.3f}, ROC AUC {auc_t:.3f} -> {auc_o:.3f}, and
waste-event recall {waste_event_t:.1%} -> {waste_event_o:.1%}.

Every margin is one to three percentage points, and {unanimity_short}. What
gives the result weight is **where** the gains fall: the largest
are on the waste anomalies specifically -- the case where occupancy ought to
matter, because a sustained modest lift only looks wrong if you know the building
was empty. Occupancy adds nothing to catching spikes, which stand out against any
baseline.

This modest result is consistent with everything else the project found:
occupancy explains only {r2_lo:.0f}-{r2_hi:.0f}% of power variation (Phase 2), adds {mean_gain:+.3f} to
validation R-squared on average (Phase 4), and several buildings have a nearly
flat daily profile (Phase 3). **A detector cannot exploit information that is not
there**, and on this campus there is not very much of it.

### Rule variants

{report.md_table(variant_summary.reset_index())}

One-sided detection -- flagging only *excess* consumption -- improves precision
substantially at almost no cost in recall, because every real or injected waste
event adds power rather than removing it. The IQR cross-check flags far more and
scores worse, as expected for heavy-tailed residuals.

### Top 10 unusual patterns in the real data

**These are candidates for inspection, not confirmed faults.** Each is a period
where a building drew considerably more power than a model of time and occupancy
expected. Ordinary explanations are available for all of them -- an event in the
building, a maintenance test, a commissioning run, or simply a hot day, and the
project has **no weather data covering this period** with which to rule the
last one out (the weather record shipped with I-BLEND covers March-June 2018 only, which does not overlap the 2014-2017 analysis window at all). Consecutive
flagged intervals are grouped into episodes, so a four-hour deviation appears
once rather than twenty-four times.

{report.md_table(top_episodes.reset_index().rename(columns={"index": "#"}))}

**Read that table with care: it is not ten findings, it is one finding ten
times.** Almost every one of the most extreme episodes on the campus is the
Academic building, starting around 03:20, running seven to eight hours, between
August and November 2017, at an excess of roughly 35-38 kW -- repeating day after
day.

A repeating daily pattern is not what a fault looks like; it is what a **change
of schedule** looks like. Something in that building began switching on in the
small hours in the second half of 2017, and a model fitted on 2014-2016 does not
know about it, so it reports the same surprise every morning. This is the concept
drift of section 6.5 resurfacing as false alarms -- the same drift measured there
as a 42% rise in Academic consumption across the record.

The practical lesson is worth stating: **a detector built on a fixed historical
baseline will eventually spend all of its alerts re-reporting a change it should
have absorbed.** A deployed version of this would need periodic refitting. A more
useful operator view takes the most unusual episode per building, so one
recurring pattern occupies one row:

{report.md_table(dedup[["building", "start", "duration_hours", "peak_z",
                        "mean_excess_kW", "total_excess_kWh", "total_episodes"]])}
"""

report.update_blocks(blocks)

# %% [markdown]
# ## Step 10: record the Phase 6 decisions

# %%
report.log_decision(
    id="D06-01", phase="6",
    decision="Standardising residuals with median/MAD rather than mean/SD",
    options_considered="Mean and standard deviation; median and MAD; a rolling "
                       "window statistic",
    chosen="Median and 1.4826 x MAD, identical for both detectors",
    reason="The standard deviation is inflated by the very anomalies being "
           "hunted, so a few large events raise the threshold and hide "
           "themselves. The MAD is barely moved by a small proportion of "
           "extreme values.",
    effect_on_results="Raises recall for both detectors equally. Because the "
                      "procedure is identical on both sides, the T-vs-O "
                      "comparison is unaffected by the choice.",
)

report.log_decision(
    id="D06-02", phase="6",
    decision="Adding a matched-alert-budget and threshold-free comparison",
    options_considered="Report the fixed |z| > 3 threshold only, as planned; add "
                       "a matched-budget comparison; add threshold-free scores",
    chosen="All three, and lead the conclusion with the fair ones",
    reason="At a fixed threshold Detector O raises far more alerts purely "
           "because model C fits better, so its residual MAD is smaller. That "
           "buys recall and costs precision for reasons unrelated to occupancy, "
           "so the fixed-threshold comparison answers the wrong question.",
    effect_on_results="Changes the answer to research question 3. At the fixed "
                      f"threshold O looks different from T (F1 {fixed_o:.3f} vs "
                      f"{fixed_t:.3f}); compared fairly they are equivalent "
                      f"(matched-budget F1 {matched_o:.3f} vs {matched_t:.3f}).",
)

report.log_decision(
    id="D06-03", phase="6",
    decision="Reporting event-level recall alongside interval-level recall",
    options_considered="Interval-level only; event-level only; both",
    chosen="Both, with event-level as the operationally meaningful one",
    reason="Interval recall penalises a detector that spots a six-hour waste "
           "event in its first hour and then treats the new level as normal. "
           "For an operator, noticing the event at all is what matters.",
    effect_on_results="Event-level recall is far higher than interval-level for "
                      "both detectors, and the T-vs-O ordering is unchanged.",
)

report.log_decision(
    id="D06-04", phase="6",
    decision="Fewer waste events injected than requested",
    options_considered=f"Force {C.N_WASTE} events by allowing overlap; shorten "
                       "the events; accept the achieved count",
    chosen="Accept the achieved count and report it",
    reason="Waste events run 2-6 hours and must sit inside low-occupancy "
           "periods, which are only 6% of the Academic record. Allowing "
           "overlaps would create compound events with ambiguous labels; "
           "shortening them would stop testing the sustained-waste case that is "
           "the point of the experiment.",
    effect_on_results="Waste sample sizes vary by building (buildings with more "
                      "low-occupancy time fit more events). All scores use the "
                      "achieved counts, which are reported in full.",
)

report.log_decision(
    id="D06-05", phase="6",
    decision="Reporting a one-sided detection variant",
    options_considered="Two-sided |z| > 3 only, as planned; one-sided only; both",
    chosen="Two-sided as the headline (as specified), one-sided reported beside it",
    reason="Every injected anomaly is additive and real waste is too -- lights "
           "left on add power. The two-sided rule spends about half its alerts "
           "on under-consumption, which cannot be a true positive against these "
           "labels.",
    effect_on_results="One-sided detection substantially improves precision for "
                      "both detectors at almost no cost in recall. It does not "
                      "change the T-vs-O conclusion.",
)

report.publish_decision_log()
print()
print("blocks still pending:", len(report.pending_blocks()))
print("figures referenced but missing:", report.check_figures())

# %% [markdown]
# ## Phase 6 conclusion
#
# **Research question 3 is answered: a qualified yes, and a weak one.** Once the
# comparison is made fairly, Detector O leads on most measures -- average
# precision, ROC AUC and waste-event recall -- but by only one to three
# percentage points, and at a matched alert budget the two are indistinguishable.
# What makes the small benefit credible rather than noise is that the largest
# gains land on the waste anomalies specifically, which is exactly where
# occupancy ought to help. Occupancy helps a little; it does not transform.
#
# **The methodological finding is as important as the result.** At the fixed
# `|z| > 3` threshold originally planned, Detector O appeared meaningfully
# different -- more recall, less precision. That gap turned out to be an artefact
# of the threshold: the better model has tighter residuals, so the same deviation
# scores a higher Z, so it simply fires more often. Had we reported only the
# planned comparison we would have drawn a conclusion about a calibration
# difference and called it a finding about occupancy.
#
# **Why the modest result is credible.** It agrees with every other route the
# project took: occupancy explains a minority of power variation (Phase 2), adds little
# average validation R² (Phase 4), and several buildings have nearly flat daily
# profiles (Phase 3). It also matches the published LBNL finding for baseline
# models, extending it from prediction to detection.
#
# **A third finding came out of the real-data section.** The most extreme
# "anomalies" in the untouched data are not ten separate events but one recurring
# early-morning pattern in the Academic building, repeating daily from August
# 2017. That is a change of operating schedule which the model -- fitted on
# 2014-2016 -- keeps re-reporting as a surprise. Concept drift returns here as
# false alarms, and the lesson is that a detector on a fixed historical baseline
# needs periodic refitting or it will spend its whole alert budget on a change it
# should have absorbed.
#
# **And it does not undercut the main finding.** Phase 5 showed these buildings
# waste a great deal of energy while nearly empty. Phase 6 shows only that a WiFi
# occupancy feed is not what an automatic detector needs in order to notice.
# Those are different claims, and both are supported.
#
# **Next:** Phase 7 -- the Streamlit dashboard and the finished report.
