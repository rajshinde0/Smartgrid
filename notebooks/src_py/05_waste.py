"""Phase 5 -- Wasted energy: the headline finding. Percent-format source."""

# %% [markdown]
# # SMARTGRID-X -- Phase 5: How much energy do nearly-empty buildings use?
#
# **This is the main research question, and this notebook answers it.**
#
# ## The definition, stated up front
#
# Phase 0 established that I-BLEND occupancy **never reads zero** -- the minimum
# in every one of the seven buildings is 1, because WiFi counts idle devices. So
# "energy used while the building is empty" is not a quantity this dataset can
# report. The question has to be asked about *low* occupancy, against a threshold
# we state openly:
#
# > **Low occupancy = occupancy at or below 5% of that building's own
# > 95th-percentile occupancy.**
#
# The threshold is **relative to each building's own scale**, because an absolute
# count is not comparable between a 600-person dormitory and a 47-person
# facilities block. Because 5% is a judgement, **every headline number in this
# notebook comes with a sensitivity curve** showing what any threshold from 0% to
# 20% would have given.
#
# ## What counts as energy
#
# Only **usable** intervals: the meter was alive, the reading exists, and the
# occupancy count exists. Numerator and denominator use the same set, so the
# share is a real proportion of measured consumption and not an artefact of
# missing data. Coverage is reported beside every number.

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

from src import config as C
from src import build, occupancy as occ, report, viz, waste as W

viz.setup_style()
C.ensure_dirs()
pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 60)
np.random.seed(C.SEED)

buildings = {}
for name in C.BUILDING_ORDER:
    buildings[name], _ = build.build_building(name, verbose=False)
print(f"loaded {len(buildings)} buildings")

# Model A coefficients computed in Phase 4 -- the base load and responsiveness.
model_a = pd.read_csv(C.RESULTS_DIR / "phase4_model_a_coefficients.csv")
display(model_a)

# %% [markdown]
# ## Step 1: the threshold for each building
#
# Before any result, the numbers the definition produces.

# %%
threshold_rows = []
for name, df in buildings.items():
    result = W.low_occupancy_share(df)
    threshold_rows.append({
        "building": name,
        "kind": C.BUILDINGS[name]["kind"],
        "p95 occupancy": result["p95_occupancy"],
        "threshold (5% of p95)": result["threshold"],
        "usable intervals": result["intervals_total"],
        "intervals at/below threshold": result["intervals_low"],
        "% of intervals": result["pct_intervals_low"],
        "threshold reachable": result["reachable"],
    })

thresholds = pd.DataFrame(threshold_rows)
display(thresholds)

# %% [markdown]
# **Facilities is the exception we predicted in Phase 0.** Its occupancy runs
# from 1 to 47 with a 95th percentile of 18, so 5% of that is **0.9** -- below
# its own minimum observed count. **No interval qualifies.** We keep the identical
# rule for every building rather than bending the definition for one, report the
# empty cell honestly, and read Facilities off the sensitivity curve in Step 4
# instead.

# %% [markdown]
# ## Step 2: the headline table
#
# Two numbers per building, and they answer different questions:
#
# * **Low-occupancy energy share** -- what fraction of everything the building
#   consumed was consumed while nearly empty. This depends partly on *how often*
#   the building is nearly empty, which is a fact about the campus timetable.
# * **Intensity ratio** -- mean power while nearly empty, divided by mean power
#   overall. A ratio of 1.0 means the building draws just as much when empty as
#   it does on average: it is not responding to its occupants at all. This is a
#   fact about the *building*, and it is the more directly interpretable number.

# %%
headline_rows = []
for name, df in buildings.items():
    result = W.low_occupancy_share(df)
    coefficients = model_a[model_a["building"] == name]
    headline_rows.append({
        "building": name,
        "kind": C.BUILDINGS[name]["kind"],
        "threshold": result["threshold"],
        "coverage %": round(100 * result["intervals_total"] / len(df), 1),
        "total kWh measured": result["total_kwh"],
        "low-occupancy kWh": result["low_occ_kwh"],
        "low-occupancy energy share %": result["share_pct"],
        "% of intervals low": result["pct_intervals_low"],
        "mean power overall (kW)": round(result["mean_power_all_w"] / 1000, 2),
        "mean power when low (kW)": round(result["mean_power_low_w"] / 1000, 2)
        if result["reachable"] else np.nan,
        "intensity ratio": W.intensity_ratio(result),
        "base load a (kW)": float(coefficients["a: base load (kW)"].iloc[0])
        if len(coefficients) else np.nan,
        "watts per occupant b": float(coefficients["b: watts per occupant"].iloc[0])
        if len(coefficients) else np.nan,
    })

headline = pd.DataFrame(headline_rows)
display(headline)
headline.to_csv(C.RESULTS_DIR / "phase5_headline.csv", index=False)

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 4.8))

plotted = headline[headline["intensity ratio"].notna()].sort_values(
    "low-occupancy energy share %", ascending=False)

bars = ax1.bar([b.replace("_", " ") for b in plotted["building"]],
               plotted["low-occupancy energy share %"],
               color=[viz.color_for(b) for b in plotted["building"]])
for bar, value in zip(bars, plotted["low-occupancy energy share %"]):
    ax1.annotate(f"{value:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, value),
                 xytext=(0, 4), textcoords="offset points", ha="center",
                 fontsize=9, color=viz.INK_SECONDARY)
ax1.set_ylabel("% of measured energy")
ax1.set_title("Energy consumed while nearly empty")
plt.setp(ax1.get_xticklabels(), rotation=20, ha="right")

ranked = headline[headline["intensity ratio"].notna()].sort_values(
    "intensity ratio", ascending=False)
bars2 = ax2.bar([b.replace("_", " ") for b in ranked["building"]],
                ranked["intensity ratio"],
                color=[viz.color_for(b) for b in ranked["building"]])
for bar, value in zip(bars2, ranked["intensity ratio"]):
    ax2.annotate(f"{value:.0%}", xy=(bar.get_x() + bar.get_width() / 2, value),
                 xytext=(0, 4), textcoords="offset points", ha="center",
                 fontsize=9, color=viz.INK_SECONDARY)
ax2.axhline(1.0, color=viz.STATUS["ANOMALY"], linestyle="--", linewidth=1.3)
ax2.annotate("1.0 = draws exactly as much when empty as on average",
             xy=(0.02, 1.01), xycoords=("axes fraction", "data"),
             fontsize=8, color=viz.STATUS["ANOMALY"])
ax2.set_ylim(0, 1.15)
ax2.set_ylabel("Mean power when nearly empty\n / mean power overall")
ax2.set_title("How much does each building relax when empty?")
plt.setp(ax2.get_xticklabels(), rotation=20, ha="right")

viz.save_fig(fig, "fig_05_headline")

# %% [markdown]
# **The headline finding, in one sentence: when these buildings are nearly
# empty, they still draw between 62% and 85% of their average power.**
#
# The intensity ratio is the number to quote, because it isolates the building's
# behaviour from the campus timetable. The Library is the most responsive at 0.62
# -- it does noticeably wind down. The Lecture building is the least at 0.85.
# Nothing on this campus comes close to switching off.
#
# The energy-share column is lower than people expect (4.5% to 19%), and the
# reason is arithmetic rather than virtue: the 5%-of-p95 threshold is **strict**,
# capturing only 6% to 28% of intervals. A building cannot spend a large share of
# its energy in a state it is rarely in. Step 5 compares this with the much looser
# clock-based definitions used in the published literature.

# %% [markdown]
# ## Step 3: one sentence per building

# %%
for _, row in headline.iterrows():
    name = row["building"].replace("_", " ")
    if pd.isna(row["intensity ratio"]):
        print(f"{name:14s} no interval in the record meets the 5%-of-p95 "
              f"threshold (it would be {row['threshold']:.1f} occupants, below "
              f"the minimum ever observed), so no share can be quoted at the "
              f"standard definition -- see the sensitivity curve.")
    else:
        print(f"{name:14s} uses {row['low-occupancy energy share %']:.1f}% of its "
              f"energy while occupancy is at or below "
              f"{row['threshold']:.0f} devices, and even then still draws "
              f"{row['intensity ratio']:.0%} of its average power "
              f"({row['mean power when low (kW)']:.1f} kW against "
              f"{row['mean power overall (kW)']:.1f} kW).")

# %% [markdown]
# ## Step 4: the sensitivity curve
#
# The 5% threshold is a judgement. This is the check that stops the headline
# resting on it: the same calculation repeated for every threshold from 0% to 20%
# of each building's 95th percentile.
#
# A result that swings wildly across this curve would be fragile. One that rises
# smoothly is robust, and the curve lets any reader read off what a different
# threshold would have given.

# %%
curves = {}
for name, df in buildings.items():
    curves[name] = W.sensitivity_curve(df)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 4.8))

for name, curve in curves.items():
    ax1.plot(100 * curve["fraction_of_p95"], curve["share_pct"],
             color=viz.color_for(name), label=name.replace("_", " "))
    ax2.plot(100 * curve["fraction_of_p95"], curve["pct_intervals_low"],
             color=viz.color_for(name))

for ax in (ax1, ax2):
    ax.axvline(100 * C.LOW_OCC_FRACTION, color=viz.STATUS["ANOMALY"],
               linestyle="--", linewidth=1.3)
    ax.set_xlabel("Threshold as % of the building's 95th-percentile occupancy")
ax1.annotate("our headline\nthreshold", xy=(100 * C.LOW_OCC_FRACTION, ax1.get_ylim()[1] * 0.75),
             xytext=(6, 0), textcoords="offset points", fontsize=8,
             color=viz.STATUS["ANOMALY"])
ax1.set_ylabel("% of energy used at or below the threshold")
ax1.set_title("Low-occupancy energy share against threshold")
ax2.set_ylabel("% of intervals at or below the threshold")
ax2.set_title("How much of the record the threshold captures")
ax1.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=8)

viz.save_fig(fig, "fig_05_sensitivity_curve")

sensitivity_summary = pd.concat(
    [curve.assign(building=name) for name, curve in curves.items()]
)[["building", "fraction_of_p95", "threshold_occupancy", "pct_intervals_low",
   "share_pct"]]
sensitivity_summary.to_csv(C.RESULTS_DIR / "phase5_sensitivity_curve.csv", index=False)
display(sensitivity_summary[sensitivity_summary["fraction_of_p95"].isin(
    [0.0, 0.05, 0.10, 0.15, 0.20])].pivot(
    index="building", columns="fraction_of_p95", values="share_pct"))

# %% [markdown]
# **Takeaway.** Six of the seven curves rise smoothly with no jumps, which means
# the headline does not depend on the exact threshold. Moving from 5% to 10%
# roughly doubles the captured share -- as it must, since a looser threshold
# captures more intervals -- but the *ranking* of buildings barely changes. The
# finding is about which buildings behave which way, and that is stable.
#
# **Facilities is the exception, and its shape is diagnostic.** Its curve is a
# staircase, jumping at about 6%, 12% and 17% and flat in between. That is not
# noise: occupancy in Facilities is a small integer, running from 1 to 47 with a
# 95th percentile of 18, so as the threshold slides upward it only ever crosses
# whole numbers -- from "at or below 0" to "at or below 1" to "at or below 2".
# Between those crossings nothing changes, hence the flat treads.
#
# This is the same fact that made the standard threshold unreachable for this
# building, seen from another angle. A relative threshold assumes occupancy is
# effectively continuous, and in a building this small it simply is not. Worth
# remembering before applying this method to any small building.

# %%
# Facilities: read its operating point off the curve, as decided in Phase 0.
facilities_curve = curves["Facilities"]
first_fraction = W.first_reachable_fraction(facilities_curve)
print(f"Facilities: the standard {C.LOW_OCC_FRACTION:.0%} threshold "
      f"({facilities_curve['threshold_occupancy'].iloc[5]:.2f} occupants) "
      f"captures nothing.")
if first_fraction is not None:
    row = facilities_curve[facilities_curve["fraction_of_p95"] == first_fraction].iloc[0]
    print(f"The lowest threshold on the curve that captures any data is "
          f"{100 * first_fraction:.0f}% of p95 "
          f"(occupancy <= {row['threshold_occupancy']:.2f}), "
          f"which covers {row['pct_intervals_low']:.1f}% of its intervals and "
          f"gives a low-occupancy energy share of {row['share_pct']:.2f}%.")
    facilities_operating_point = row
else:
    facilities_operating_point = None
    print("No threshold up to 20% of p95 captures any Facilities interval.")

# %% [markdown]
# ## Step 5: comparison with the published literature
#
# Two published figures are the natural comparison, and comparing honestly means
# first computing **their** definition on **our** data. Both use a clock-based
# rule -- outside working hours -- not a measured occupancy signal.
#
# * **Masoso & Grobler (2010)** audited commercial buildings and found **56% of
#   energy used outside working hours**.
# * **Anderson et al. (2015)** found **27.5-31.5% of dormitory energy used while
#   unoccupied**.

# %%
comparison_rows = []
for name, df in buildings.items():
    clock = W.out_of_hours_share(df, open_hour=8, close_hour=18, weekdays_only=True)
    occupancy_based = W.low_occupancy_share(df)
    comparison_rows.append({
        "building": name,
        "kind": C.BUILDINGS[name]["kind"],
        "out-of-hours share % (clock rule)": clock["share_pct"],
        "% intervals out of hours": clock["pct_intervals_out_of_hours"],
        "low-occupancy share % (occupancy rule)": occupancy_based["share_pct"],
        "% intervals low occupancy": occupancy_based["pct_intervals_low"],
    })

published = pd.DataFrame(comparison_rows)
display(published)
published.to_csv(C.RESULTS_DIR / "phase5_published_comparison.csv", index=False)

# %%
fig, ax = plt.subplots(figsize=(11, 5))

positions = np.arange(len(published))
width = 0.38
ax.bar(positions - width / 2, published["out-of-hours share % (clock rule)"],
       width, color=viz.CATEGORICAL[0],
       label="clock rule: outside 08:00-18:00 weekdays")
ax.bar(positions + width / 2, published["low-occupancy share % (occupancy rule)"],
       width, color=viz.CATEGORICAL[1],
       label="occupancy rule: at or below 5% of p95")

ax.axhline(56, color=viz.STATUS["SERIOUS"], linestyle="--", linewidth=1.5)
ax.annotate("Masoso & Grobler 2010: 56% out of hours (commercial)",
            xy=(len(published) - 0.4, 56), xytext=(0, 4),
            textcoords="offset points", ha="right", fontsize=8,
            color=viz.STATUS["SERIOUS"])
ax.axhspan(27.5, 31.5, color=viz.STATUS["WARNING"], alpha=0.18, zorder=0)
ax.annotate("Anderson et al. 2015: 27.5-31.5% unoccupied (dormitories)",
            xy=(len(published) - 0.4, 31.8), xytext=(0, 2),
            textcoords="offset points", ha="right", fontsize=8,
            color="#8a6000")

ax.set_xticks(positions)
ax.set_xticklabels([b.replace("_", " ") for b in published["building"]],
                   rotation=20, ha="right")
ax.set_ylabel("% of measured energy")
ax.set_title("Two definitions of 'unoccupied', and what the literature reports")
ax.legend(loc="upper left", fontsize=9)
viz.save_fig(fig, "fig_05_published_comparison")

# %% [markdown]
# **Takeaway -- and this is the most striking result in the project.**
#
# Applying **Masoso & Grobler's own clock-based definition** to our data gives
# the Academic building **55.3%** and the Library **55.0%** -- against their
# published **56%**. Two different continents, fifteen years apart, and the
# commercial buildings land within a percentage point. That is a strong external
# corroboration that our pipeline is measuring what we think it is measuring.
#
# It also makes the difference between the two definitions visible. The
# clock-based bars are an order of magnitude taller than the occupancy-based
# ones, and they are **not measuring the same thing**:
#
# * The clock rule calls 3 p.m. on a vacation Tuesday "occupied" when the
#   building is actually empty, and 8 p.m. during exams "unoccupied" when the
#   Library is full.
# * The occupancy rule uses what was actually measured -- but is far stricter,
#   because WiFi over-counting means genuinely quiet periods still register
#   double-digit device counts.
#
# The honest reading is that the truth lies between them, and that **our
# occupancy-based figure is a conservative lower bound.** The dormitory
# comparison is the same story: our hostels show 4.5-5.0% on the occupancy rule
# against Anderson's 27.5-31.5% on an unoccupancy rule, and 74% on the clock
# rule -- which for a residential building is not a meaningful comparison at all,
# since people are home in the evenings.

# %% [markdown]
# ## Step 6: base load against the night-time minimum
#
# Phase 4's model A estimates the base load by extrapolating a fitted line to
# zero occupancy. Here we check it against something measured directly and with
# no model at all: the median power between 02:00 and 06:00.
#
# If a model extrapolation and a direct measurement agree, the base load is real
# rather than an artefact of the fit.

# %%
base_rows = []
for name, df in buildings.items():
    coefficients = model_a[model_a["building"] == name]
    if coefficients.empty:
        continue
    a_kw = float(coefficients["a: base load (kW)"].iloc[0])
    night_kw = W.night_minimum(df) / 1000
    mean_kw = float(df.loc[df["usable"], "power_w"].mean()) / 1000
    base_rows.append({
        "building": name,
        "base load a from model A (kW)": round(a_kw, 2),
        "night 02:00-06:00 median (kW)": round(night_kw, 2),
        "difference (kW)": round(a_kw - night_kw, 2),
        "difference %": round(100 * (a_kw - night_kw) / night_kw, 1),
        "mean power (kW)": round(mean_kw, 2),
        "base load as % of mean": round(100 * a_kw / mean_kw, 1),
    })

base_load = pd.DataFrame(base_rows)
display(base_load)
base_load.to_csv(C.RESULTS_DIR / "phase5_base_load.csv", index=False)

# %%
fig, ax = plt.subplots(figsize=(9, 6))
limit = max(base_load["base load a from model A (kW)"].max(),
            base_load["night 02:00-06:00 median (kW)"].max()) * 1.15

ax.plot([0, limit], [0, limit], color=viz.AXIS, linestyle="--", linewidth=1.2,
        zorder=1)
ax.annotate("perfect agreement", xy=(limit * 0.72, limit * 0.75), fontsize=8,
            color=viz.INK_MUTED, rotation=38)

for _, row in base_load.iterrows():
    ax.scatter(row["night 02:00-06:00 median (kW)"],
               row["base load a from model A (kW)"],
               s=170, color=viz.color_for(row["building"]), zorder=3,
               edgecolors=viz.SURFACE, linewidths=2)
    ax.annotate(row["building"].replace("_", " "),
                xy=(row["night 02:00-06:00 median (kW)"],
                    row["base load a from model A (kW)"]),
                xytext=(0, 13), textcoords="offset points", ha="center",
                fontsize=9, color=viz.INK_SECONDARY)

ax.set_xlabel("Measured directly: median power 02:00-06:00 (kW)")
ax.set_ylabel("Estimated by model A: intercept at zero occupancy (kW)")
ax.set_title("Two independent routes to the base load")
ax.set_xlim(0, limit)
ax.set_ylim(0, limit)
viz.save_fig(fig, "fig_05_base_load_vs_night")

# %% [markdown]
# **Takeaway.** The two estimates track each other closely for most buildings,
# which is real corroboration: a regression intercept and a raw night-time median
# are computed in completely different ways. Where they differ the direction is
# informative. The Boys hostel's night median is far *above* its model intercept,
# which is exactly right for a dormitory -- people are home and asleep at 4 a.m.,
# so the small hours are not a low-occupancy period there at all. This is why the
# occupancy-based definition matters: a clock-based rule would have called those
# hours "unoccupied" and been wrong.

# %% [markdown]
# ## Step 7: ranking buildings by responsiveness
#
# A building is doing well here if a large share of its consumption scales with
# the people in it rather than running regardless. There are two ways to measure
# that, and **they disagree** -- which is itself worth understanding before
# either is trusted.
#
# * **Measured:** the intensity ratio from Step 2. Mean power when nearly empty
#   divided by mean power overall. Lower is more responsive. Entirely observed.
# * **Modelled:** the share of mean power that is *not* model A base load,
#   `(mean - a) / mean`. Higher is more responsive. This depends on an
#   extrapolation of the fitted line down to zero occupancy.
#
# Step 6 already showed where the modelled version gets into trouble: for the two
# dormitories and the Lecture building, the model A intercept sits far below the
# directly measured night-time median. That is not a coding error, it is what
# extrapolation does. Occupancy in a dormitory almost never approaches zero, so
# "power at zero occupancy" is a point well outside the data the line was fitted
# to, and the line is under no obligation to be right out there.
#
# So we rank by the **measured** ratio and report the modelled one beside it,
# flagged where the extrapolation is unreliable.

# %%
rank_input = base_load.rename(columns={
    "base load a from model A (kW)": "base_load_kw",
    "mean power (kW)": "mean_power_kw",
})[["building", "base_load_kw", "mean_power_kw"]]
ranking = W.responsiveness_rank(rank_input)
ranking = ranking.merge(
    headline[["building", "intensity ratio", "watts per occupant b"]], on="building"
)
ranking = ranking.merge(
    base_load[["building", "difference %"]].rename(
        columns={"difference %": "model A vs night median %"}),
    on="building",
)

# Flag buildings where the two base-load estimates disagree by more than 25%:
# there the extrapolated intercept should not be used for ranking.
ranking["model A reliable?"] = np.where(
    ranking["model A vs night median %"].abs() > 25, "NO -- extrapolated", "yes"
)
ranking["measured rank"] = ranking["intensity ratio"].rank(
    ascending=True, method="min"
)
ranking = ranking.sort_values(
    "intensity ratio", na_position="last"
).reset_index(drop=True)

display(ranking[[
    "building", "intensity ratio", "measured rank", "variable_share_pct",
    "responsiveness_rank", "base_load_kw", "model A vs night median %",
    "model A reliable?", "watts per occupant b",
]])
ranking.to_csv(C.RESULTS_DIR / "phase5_responsiveness_ranking.csv", index=False)

night_lookup = base_load.set_index("building")["night 02:00-06:00 median (kW)"]
print("\nWhere the two rankings disagree, it is because the modelled one "
      "extrapolates to zero occupancy:")
for _, r in ranking.iterrows():
    if str(r["model A reliable?"]).startswith("NO"):
        print(f"  {r['building']:13s} model A base load {r['base_load_kw']:5.2f} kW "
              f"vs measured night median {night_lookup[r['building']]:5.2f} kW "
              f"({r['model A vs night median %']:+.0f}%)")

# %%
fig, ax = plt.subplots(figsize=(10, 4.6))
ordered = ranking.sort_values("variable_share_pct", ascending=True)
positions = np.arange(len(ordered))

ax.barh(positions, ordered["variable_share_pct"],
        color=[viz.color_for(b) for b in ordered["building"]],
        label="varies with occupancy")
ax.barh(positions, 100 - ordered["variable_share_pct"],
        left=ordered["variable_share_pct"], color="#dcdbd5",
        label="base load: drawn regardless")

for i, (_, row) in enumerate(ordered.iterrows()):
    ax.annotate(f"{row['variable_share_pct']:.0f}%",
                xy=(row["variable_share_pct"] / 2, i), ha="center", va="center",
                fontsize=9, color="#ffffff", fontweight="bold")

ax.set_yticks(positions)
ax.set_yticklabels([b.replace("_", " ") for b in ordered["building"]])
ax.set_xlabel("% of mean power")
ax.set_xlim(0, 100)
ax.set_title("How much of each building's load actually follows its occupants")
ax.grid(axis="x")
ax.legend(loc="lower right", fontsize=9)
viz.save_fig(fig, "fig_05_responsiveness")

# %% [markdown]
# **Takeaway.** The chart uses the modelled split, so the two dormitories and the
# Lecture building should be read with the caveat above -- their base-load bars
# are extrapolations, and the directly measured night-time figures are higher
# still, which means their true fixed share is **larger** than shown, not smaller.
#
# The conclusion is unaffected and holds on either metric: **in every building
# the fixed part of the load is the larger share**, and even the best performer
# has the majority of its consumption drawn whether or not anyone is present. On
# this campus, most electricity is not a response to people.

# %% [markdown]
# ## Step 8: semester against vacation
#
# Does the low-occupancy share rise when the students leave? The threshold is
# held fixed from the whole record rather than recomputed within each period --
# recomputing it would move the definition of "low" between the two groups and
# make them incomparable.

# %%
period_rows = []
for name, df in buildings.items():
    table = W.by_period(df)
    if table.empty:
        continue
    table["building"] = name
    period_rows.append(table)

periods = pd.concat(period_rows, ignore_index=True)
period_pivot = periods.pivot(index="building", columns="period",
                             values="share_pct")
period_pivot["change (pp)"] = (
    period_pivot.get("vacation", np.nan) - period_pivot.get("semester", np.nan)
).round(2)
display(period_pivot)
periods.to_csv(C.RESULTS_DIR / "phase5_semester_vacation.csv", index=False)

# %%
mean_pivot = periods.pivot(index="building", columns="period", values="mean_power_w") / 1000

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.4))
positions = np.arange(len(period_pivot))
width = 0.38

ax1.bar(positions - width / 2, period_pivot["semester"], width,
        color=viz.CATEGORICAL[0], label="semester")
ax1.bar(positions + width / 2, period_pivot["vacation"], width,
        color=viz.CATEGORICAL[1], label="vacation")
ax1.set_xticks(positions)
ax1.set_xticklabels([b.replace("_", " ") for b in period_pivot.index],
                    rotation=20, ha="right")
ax1.set_ylabel("Low-occupancy energy share %")
ax1.set_title("Share of energy used at low occupancy")
ax1.legend()

ax2.bar(positions - width / 2, mean_pivot["semester"], width,
        color=viz.CATEGORICAL[0], label="semester")
ax2.bar(positions + width / 2, mean_pivot["vacation"], width,
        color=viz.CATEGORICAL[1], label="vacation")
ax2.set_xticks(positions)
ax2.set_xticklabels([b.replace("_", " ") for b in mean_pivot.index],
                    rotation=20, ha="right")
ax2.set_ylabel("Mean power (kW)")
ax2.set_title("Mean power")
ax2.legend()

viz.save_fig(fig, "fig_05_semester_vacation")

# %% [markdown]
# ## Step 9: hostel mains against UPS
#
# A question only this dataset can answer, because only I-BLEND meters the two
# supplies separately: when the rooms empty out, which feed keeps running?

# %%
supply_rows = []
for name in ("Boys_Hostel", "Girls_Hostel"):
    table = W.mains_vs_ups(name, buildings[name])
    if not table.empty:
        supply_rows.append(table)

supplies = pd.concat(supply_rows, ignore_index=True)
display(supplies)
supplies.to_csv(C.RESULTS_DIR / "phase5_mains_vs_ups.csv", index=False)

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.2))

for ax, column, title, ylabel in (
    (ax1, "share_pct", "Low-occupancy energy share by supply",
     "% of that supply's energy"),
    (ax2, "mean_power_low_occ_w", "Mean power when nearly empty, by supply",
     "watts"),
):
    labels = [f"{r['building'].replace('_', ' ')}\n{r['supply']}"
              for _, r in supplies.iterrows()]
    values = supplies[column]
    colours = [viz.color_for(r["building"]) if r["supply"] == "mains" else "#b9b8b1"
               for _, r in supplies.iterrows()]
    bars = ax.bar(labels, values, color=colours)
    for bar, value in zip(bars, values):
        ax.annotate(f"{value:,.1f}" if column == "share_pct" else f"{value:,.0f}",
                    xy=(bar.get_x() + bar.get_width() / 2, value),
                    xytext=(0, 4), textcoords="offset points", ha="center",
                    fontsize=9, color=viz.INK_SECONDARY)
    ax.set_title(title)
    ax.set_ylabel(ylabel)

from matplotlib.patches import Patch
ax1.legend(handles=[Patch(facecolor=viz.INK_MUTED, label="mains supply"),
                    Patch(facecolor="#b9b8b1", label="UPS / backup supply")],
           fontsize=8)
viz.save_fig(fig, "fig_05_mains_vs_ups")

# %% [markdown]
# ## Step 10: commercial against residential

# %%
kind_summary = headline.groupby("kind").agg(
    buildings=("building", "count"),
    mean_low_occ_share=("low-occupancy energy share %", "mean"),
    mean_intensity_ratio=("intensity ratio", "mean"),
    mean_base_load_kw=("base load a (kW)", "mean"),
    total_kwh=("total kWh measured", "sum"),
).round(3)
display(kind_summary)

for kind, group in headline.groupby("kind"):
    valid = group[group["intensity ratio"].notna()]
    print(f"{kind:12s} n={len(valid)}  "
          f"mean low-occupancy share {valid['low-occupancy energy share %'].mean():.2f}%  "
          f"mean intensity ratio {valid['intensity ratio'].mean():.3f}")

# %% [markdown]
# ## Step 11: the two sensitivity checks owed from earlier phases
#
# ### 11.1 Lecture building under a 24-hour dead-meter rule
#
# Phase 1 found that a building switched off at the mains overnight and a meter
# that has stopped reporting both read exactly 0 W, and that the specified
# 6-hour rule cannot tell them apart (decision D01-07). The Lecture building's
# zero runs formed two populations -- nightly ones around 13 hours, and outages
# lasting up to 46 days. Here we recompute its headline figure with a 24-hour
# rule, which treats the nightly switch-offs as genuine zero consumption.

# %%
lecture_6h = W.low_occupancy_share(buildings["Lecture"])
lecture_24h_df = W.recompute_with_dead_meter_rule("Lecture", hours=24)
lecture_24h = W.low_occupancy_share(lecture_24h_df)

lecture_check = pd.DataFrame([
    {"dead-meter rule": f"{C.DEAD_METER_HOURS} h (as specified)",
     "usable intervals": lecture_6h["intervals_total"],
     "total kWh": lecture_6h["total_kwh"],
     "low-occupancy share %": lecture_6h["share_pct"]},
    {"dead-meter rule": "24 h (nightly switch-offs kept as real zeros)",
     "usable intervals": lecture_24h["intervals_total"],
     "total kWh": lecture_24h["total_kwh"],
     "low-occupancy share %": lecture_24h["share_pct"]},
])
display(lecture_check)
print(f"\nThe ambiguity is worth "
      f"{abs(lecture_6h['share_pct'] - lecture_24h['share_pct']):.2f} percentage "
      f"points on the Lecture building's headline figure.")
lecture_check.to_csv(C.RESULTS_DIR / "phase5_lecture_deadmeter_check.csv", index=False)

# %% [markdown]
# **Takeaway.** Relaxing the rule more than doubles the usable intervals and
# moves the headline share by about one percentage point. The ambiguity is real
# but small, and the Lecture figure survives it. Both numbers are reported.

# %% [markdown]
# ### 11.2 Corrected occupancy
#
# Phase 0 decided (D00-06) to build the headline on **raw** WiFi counts and to
# report a corrected variant separately. The I-BLEND authors note the counts
# include roughly 20 idle devices per building, about 50 in the Academic
# building. Subtracting that constant gives a rough estimate of real occupancy.
#
# It is **not** used for the headline, because it is an approximate constant from
# the paper rather than something we measured -- building the main result on it
# would rest the project on an estimate. But quantifying how far the answer moves
# is exactly what a robustness check is for.

# %%
corrected_rows = []
for name, df in buildings.items():
    adjusted = df.copy()
    adjusted["occupancy_corrected"] = occ.corrected_occupancy(
        adjusted["occupancy"], name
    )
    raw_result = W.low_occupancy_share(df)
    corrected_result = W.low_occupancy_share(
        adjusted, occupancy_col="occupancy_corrected"
    )
    corrected_rows.append({
        "building": name,
        "idle devices subtracted": C.IDLE_DEVICE_BASELINE.get(name, 20),
        "raw threshold": raw_result["threshold"],
        "corrected threshold": corrected_result["threshold"],
        "raw share %": raw_result["share_pct"],
        "corrected share %": corrected_result["share_pct"],
        "change (pp)": round(
            (corrected_result["share_pct"] or 0) - (raw_result["share_pct"] or 0), 2),
        "raw % intervals low": raw_result["pct_intervals_low"],
        "corrected % intervals low": corrected_result["pct_intervals_low"],
    })

corrected = pd.DataFrame(corrected_rows)
display(corrected)
corrected.to_csv(C.RESULTS_DIR / "phase5_corrected_occupancy.csv", index=False)

# %% [markdown]
# **Takeaway.** Subtracting the idle-device baseline makes every building look
# emptier more often, so the low-occupancy share rises everywhere -- confirming
# that our raw-count headline is a **conservative lower bound**. The effect is
# largest where the baseline is a big fraction of typical occupancy. For
# Facilities the correction is drastic: subtracting 20 from a building whose 95th
# percentile is 18 pushes almost every interval to zero, which is not a credible
# description of the building and is a good illustration of why we did not build
# the headline on this adjustment.

# %% [markdown]
# ## Step 12: write Phase 5 into the report

# %%
measured_ranked = ranking[ranking["intensity ratio"].notna()].sort_values(
    "intensity ratio")
measured_best = measured_ranked.iloc[0]
measured_worst = measured_ranked.iloc[-1]
modelled_ranked = ranking.sort_values("variable_share_pct", ascending=False)
most_responsive = modelled_ranked.iloc[0]
least_responsive = modelled_ranked.iloc[-1]
worst_extrapolation = abs(base_load["difference %"]).max()
ratio_valid = headline[headline["intensity ratio"].notna()]
acad_ooh = published.set_index("building").loc["Academic",
                                               "out-of-hours share % (clock rule)"]
lib_ooh = published.set_index("building").loc["Library",
                                              "out-of-hours share % (clock rule)"]

sentences = []
for _, row in headline.iterrows():
    name = row["building"].replace("_", " ")
    if pd.isna(row["intensity ratio"]):
        sentences.append(
            f"- **{name}** -- no interval in the record meets the standard "
            f"threshold (it would be {row['threshold']:.1f} occupants, below the "
            f"minimum ever observed), so no share is quoted at the standard "
            f"definition; see the sensitivity curve."
        )
    else:
        sentences.append(
            f"- **{name}** uses **{row['low-occupancy energy share %']:.1f}%** of "
            f"its energy while occupancy is at or below {row['threshold']:.0f} "
            f"devices, and even then still draws "
            f"**{row['intensity ratio']:.0%}** of its average power "
            f"({row['mean power when low (kW)']:.1f} kW against "
            f"{row['mean power overall (kW)']:.1f} kW)."
        )

blocks = {}

blocks["method_phase5"] = f"""
**The definition.** I-BLEND occupancy never reads zero -- the minimum in every
building is 1, because WiFi counts idle devices -- so "energy used while empty"
is not a quantity this dataset can report. The question is asked about *low*
occupancy instead:

> **low occupancy = occupancy at or below {C.LOW_OCC_FRACTION:.0%} of that
> building's own {C.LOW_OCC_PERCENTILE}th-percentile occupancy.**

The threshold is relative to each building's own scale because an absolute count
is not comparable between a 600-person dormitory and a 47-person facilities
block. Thresholds are reported per building.

**What counts as energy.** Only *usable* intervals: meter alive, reading present,
occupancy known. Numerator and denominator use the same set, so the share is a
true proportion of measured consumption rather than an artefact of missing data;
coverage is reported beside every figure.

**Two measures, because they answer different questions.** The *low-occupancy
energy share* depends partly on how often a building happens to be nearly empty,
which is a fact about the campus timetable. The *intensity ratio* -- mean power
when nearly empty divided by mean power overall -- isolates the building's own
behaviour, and is the number to quote.

**Sensitivity.** Because 5% is a judgement, the whole calculation is repeated for
every threshold from 0% to 20% of p95 and published as a curve.

**Comparison with the literature.** The published figures use a *clock-based*
rule, not a measured occupancy signal, so we compute their definition on our data
(outside 08:00-18:00 on weekdays) as well as our own, and compare like with like.

**Two sensitivity checks owed from earlier phases** are settled here: the Lecture
building recomputed under a 24-hour dead-meter rule (D01-07), and a
corrected-occupancy run subtracting the documented idle-device baseline (D00-06).

**Notebook:** `notebooks/05_waste.ipynb`.
"""

blocks["results_phase5"] = f"""
### Thresholds

{report.md_table(thresholds)}

Facilities is the exception predicted in Phase 0: its occupancy runs 1 to 47 with
a 95th percentile of 18, so the threshold is **0.9** -- below its own minimum
observed count -- and **no interval qualifies**. The rule is kept identical for
every building rather than bent for one; its behaviour is read off the
sensitivity curve instead.

### The headline table

{report.md_table(headline)}

{report.figure("fig_05_headline",
               "Low-occupancy energy share and intensity ratio, per building",
               "The right-hand panel is the one to read: when nearly empty, "
               f"these buildings still draw between "
               f"{ratio_valid['intensity ratio'].min():.0%} and "
               f"{ratio_valid['intensity ratio'].max():.0%} of their average "
               "power.")}

### Sensitivity to the threshold

{report.figure("fig_05_sensitivity_curve",
               "Low-occupancy energy share against threshold, 0% to 20% of p95",
               "Six of seven curves rise smoothly and the ranking of buildings "
               "barely changes across the range, so the finding does not depend "
               "on the exact threshold. Facilities is a staircase because its "
               "occupancy is a small integer.")}

Six of the seven curves rise smoothly with no jumps, and the ranking of buildings
is stable across the whole range, so the headline does not rest on the choice of
5%. **Facilities is the exception, and the shape of its curve is diagnostic**: it
is a staircase, jumping at roughly 6%, 12% and 17% and flat in between. Occupancy
there is a small integer running from 1 to 47, so a sliding threshold only ever
crosses whole numbers, and between crossings nothing changes. That is the same
fact that made the standard threshold unreachable for this building, seen from
another angle -- a relative threshold assumes occupancy is effectively
continuous, and in a building this small it is not.

### Comparison with the published literature

{report.md_table(published)}

{report.figure("fig_05_published_comparison",
               "Clock-based and occupancy-based definitions against the published figures",
               "Applying Masoso & Grobler's own clock-based definition to this "
               f"data gives the Academic building {acad_ooh:.1f}% and the "
               f"Library {lib_ooh:.1f}%, against their published 56%.")}

**This is the strongest external check in the project.** Applying Masoso &
Grobler's clock-based definition to our data gives the Academic building
**{acad_ooh:.1f}%** and the Library **{lib_ooh:.1f}%** -- against their published
**56%**, from different buildings on a different continent fifteen years earlier.
Landing within a percentage point is good evidence that the pipeline measures
what it claims to.

It also shows that the two definitions are **not measuring the same thing**. A
clock rule calls 3 p.m. on a vacation Tuesday "occupied" when the building is
empty, and 8 p.m. during exams "unoccupied" when the Library is full. The
occupancy rule uses what was actually measured but is far stricter, because WiFi
over-counting means genuinely quiet periods still register double-digit device
counts. The truth lies between them, and **our occupancy-based figure is a
conservative lower bound** -- a conclusion the corrected-occupancy check below
independently confirms.

### Base load: two independent routes to the same number

{report.md_table(base_load)}

{report.figure("fig_05_base_load_vs_night",
               "Model A intercept against the directly measured night-time median",
               "A regression intercept and a raw night-time median are computed "
               "in completely different ways; that they track each other is real "
               "corroboration that the base load is not an artefact of the fit.")}

Where the two disagree, the direction is informative. The Boys hostel's night
median sits far *above* its model intercept -- exactly right for a dormitory,
where people are home and asleep at 4 a.m. The small hours are simply not a
low-occupancy period there, which is precisely why an occupancy-based definition
is worth the trouble: a clock-based rule would have called those hours
unoccupied and been wrong.

### Responsiveness ranking

{report.md_table(ranking)}

{report.figure("fig_05_responsiveness",
               "How much of each building's load actually follows its occupants",
               "In every building the base load -- the part drawn whether or not "
               "anyone is present -- is the larger share.")}

**The two metrics disagree, and the disagreement is informative.** Ranked by the
*measured* intensity ratio, the most responsive building is
**{measured_best['building'].replace('_', ' ')}**
({measured_best['intensity ratio']:.0%} of average power when nearly empty) and
the least is **{measured_worst['building'].replace('_', ' ')}**
({measured_worst['intensity ratio']:.0%}). Ranked by the *modelled*
non-base-load share the order differs, because that version extrapolates model A
down to zero occupancy -- and for the two dormitories and the Lecture building
that point lies far outside the occupancy range ever observed. In the worst case
the extrapolated intercept sits {worst_extrapolation:.0f}% away from the directly
measured night-time median.

Where the two disagree we rank on the measured ratio and flag the modelled value
as unreliable. The conclusion survives either way: **even the best performer has
the majority of its consumption fixed**, and for the flagged buildings the true
fixed share is larger than the modelled figure, not smaller.

### Semester against vacation

{report.md_table(period_pivot.reset_index())}

{report.figure("fig_05_semester_vacation",
               "Low-occupancy share and mean power, semester against vacation",
               "Holding the threshold fixed across both periods so the "
               "comparison measures behaviour rather than the definition.")}

### Hostel mains against UPS

{report.md_table(supplies)}

{report.figure("fig_05_mains_vs_ups",
               "Low-occupancy share and mean power by supply, for the two dormitories",
               "Only I-BLEND meters the mains and backup supplies separately, so "
               "this comparison is not available in other campus datasets.")}

### Commercial against residential

{report.md_table(kind_summary.reset_index())}

### Sensitivity check 1: Lecture under a 24-hour dead-meter rule

{report.md_table(lecture_check)}

Phase 1 established that a building switched off at the mains overnight and a
meter that has stopped reporting both read exactly 0 W, and that the specified
6-hour rule cannot separate them (D01-07). Relaxing the rule to 24 hours more
than doubles the usable intervals and moves the headline share by
**{abs(lecture_6h['share_pct'] - lecture_24h['share_pct']):.2f} percentage
points**. The ambiguity is real but small, and the Lecture figure survives it.

### Sensitivity check 2: corrected occupancy

{report.md_table(corrected)}

Subtracting the documented idle-device baseline makes every building look emptier
more often, so the low-occupancy share rises everywhere. This **confirms that the
raw-count headline is a conservative lower bound**. For Facilities the correction
is drastic -- subtracting 20 from a building whose 95th percentile is 18 pushes
nearly every interval to zero -- which is not a credible description of the
building and illustrates why the headline was not built on this adjustment
(D00-06).
"""

blocks["headline_findings"] = f"""
> **When these seven campus buildings are at their emptiest, they still draw
> between {ratio_valid['intensity ratio'].min():.0%} and
> {ratio_valid['intensity ratio'].max():.0%} of their average power.**

{chr(10).join(sentences)}

**The campus-wide picture.** In every building the base load -- the power drawn
whether or not anyone is present -- is the *larger* share of mean consumption,
ranging from {ranking['variable_share_pct'].max():.0f}% down to
{ranking['variable_share_pct'].min():.0f}% of load that actually varies with
occupancy. On the directly measured intensity ratio the most responsive building
is {measured_best['building'].replace('_', ' ')}
({measured_best['intensity ratio']:.0%} of average power when nearly empty) and
the least is {measured_worst['building'].replace('_', ' ')}
({measured_worst['intensity ratio']:.0%}).

**In context.** Applying the clock-based definition used by Masoso & Grobler
(2010) to this data gives {acad_ooh:.1f}% for the Academic building and
{lib_ooh:.1f}% for the Library, against their published 56% for audited
commercial buildings elsewhere. Our stricter occupancy-based figures are lower by
construction and should be read as a conservative lower bound.

**The headline table**

{report.md_table(headline)}
"""

report.update_blocks(blocks)

# %% [markdown]
# ## Step 13: record the Phase 5 decisions

# %%
report.log_decision(
    id="D05-01", phase="5",
    decision="Reporting an intensity ratio alongside the energy share",
    options_considered="Energy share only (as specified); intensity ratio only; "
                       "both",
    chosen="Both, leading with the intensity ratio in the narrative",
    reason="The energy share depends partly on how *often* a building is nearly "
           "empty, which is a fact about the campus timetable rather than about "
           "the building. The ratio of mean power when empty to mean power "
           "overall isolates the building's own behaviour.",
    effect_on_results="Adds a column; changes no specified number. It is what "
                      "lets the headline be stated as 'still draws 62-85% of "
                      "average power' rather than only as a share.",
)

report.log_decision(
    id="D05-02", phase="5",
    decision="Computing the published clock-based definition on our own data",
    options_considered="Quote the published figures beside ours; compute their "
                       "definition on our data and compare like with like",
    chosen="Compute outside-08:00-18:00-weekdays share on our data as well",
    reason="Our occupancy threshold captures only 6-28% of intervals while a "
           "clock rule captures about 70%. Comparing the two directly would be "
           "misleading, and the difference between the definitions is itself "
           "the point of an occupancy-aware analysis.",
    effect_on_results=f"Yields {acad_ooh:.1f}% for Academic and {lib_ooh:.1f}% "
                      "for Library against the published 56% -- a strong "
                      "external check that the pipeline measures what it claims.",
)

report.log_decision(
    id="D05-03", phase="5",
    decision="Threshold held fixed across semester and vacation",
    options_considered="Recompute p95 within each period; hold the whole-record "
                       "threshold fixed",
    chosen="Fixed threshold from the whole record",
    reason="Recomputing p95 within each period would move the definition of "
           "'low' between the two groups -- a vacation p95 is lower, so its "
           "threshold would be lower -- and the comparison would measure the "
           "threshold rather than the behaviour.",
    effect_on_results="Makes the semester/vacation comparison meaningful. With a "
                      "per-period threshold both columns would tend towards the "
                      "same value by construction.",
)

report.log_decision(
    id="D05-04", phase="5",
    decision="Defining responsiveness as the non-base-load share of mean power",
    options_considered="Rank by slope b alone; rank by base load a alone; rank "
                       "by (mean - a) / mean",
    chosen="(mean power - base load) / mean power",
    reason="Slope b alone is not comparable across buildings whose occupancy "
           "ranges differ by a factor of twenty (Facilities peaks at 47 "
           "occupants, the Boys hostel at 614). Base load alone ignores building "
           "size. The ratio is dimensionless and comparable.",
    effect_on_results="Determines the ranking in section 6.6. A slope-only "
                      "ranking would put Facilities first purely because its "
                      "small occupancy range forces a large coefficient.",
)

report.publish_decision_log()
print()
print("blocks still pending:", len(report.pending_blocks()))
print("figures referenced but missing:", report.check_figures())

# %% [markdown]
# ## Phase 5 conclusion
#
# **The main research question is answered.** When these buildings are at their
# emptiest, they still draw 62% to 85% of their average power. In every one of
# them the base load -- the part that runs regardless of who is present -- is the
# larger share of consumption.
#
# **The result is robust.** It survives the threshold sensitivity curve, agrees
# with an independent night-time measurement, survives the Lecture building's
# dead-meter ambiguity, and moves only in the direction of *more* waste when the
# WiFi over-count is corrected. Applying the published literature's own
# definition to our data reproduces their headline figure to within a percentage
# point.
#
# **What it does not show.** We have no *usable* weather data -- the weather record shipped with I-BLEND covers March-June 2018 only, which does not overlap the 2014-2017 analysis window at all
# -- so we cannot separate air conditioning from occupancy-driven load -- and Phase 2 showed vacation power
# rising in some buildings precisely because Delhi's summer break is its hottest
# season. Some of what we are calling low-occupancy consumption is cooling an
# empty building, which is still waste, but of a kind that needs a different
# remedy than switching off lights.
#
# **Next:** Phase 6 -- does knowing the occupancy help an automatic detector
# catch this kind of waste?
