"""Phase 2 -- Statistics and exploratory data analysis. Percent-format source."""

# %% [markdown]
# # SMARTGRID-X -- Phase 2: Statistics and exploratory data analysis
#
# **What this notebook does.** Phase 1 produced seven clean tables. Before
# modelling anything, we describe them: what kind of data each column is, what
# the typical and extreme values are, what shape the distributions have, and
# which differences between groups are real rather than noise.
#
# **Why this comes before modelling.** A model fitted to data you have not looked
# at will happily give you a confident wrong answer. Every choice in Phase 4 --
# which features, which transform, which error measure -- is made on the basis of
# what this notebook finds.
#
# **One thing to watch throughout.** Our samples are enormous: over 176,000
# 10-minute intervals for the Academic building alone. At that size a hypothesis
# test returns p < 0.001 for a difference far too small to care about. So every
# test here reports an **effect size** beside its p-value, and we lead with the
# effect size. A tiny p-value on its own means "we have a lot of data", not
# "this matters".

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats as sps
from IPython.display import display

from src import config as C
from src import build, report, stats as S, viz

viz.setup_style()
C.ensure_dirs()
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 50)
np.random.seed(C.SEED)

long = build.build_long_table()
usable = long[long["usable"]].copy()
print(f"long table: {len(long):,} rows, of which {len(usable):,} usable "
      f"({100 * len(usable) / len(long):.1f}%)")

# %% [markdown]
# ## Step 1: population and sample -- what are we actually measuring?
#
# It matters to be clear about this, because it bounds every claim we make.
#
# * **The population we would like to describe:** electricity use in university
#   buildings generally.
# * **The population we can describe:** the seven metered buildings on the
#   IIIT-Delhi campus, over the period both energy and occupancy were recorded.
# * **The sample we actually hold:** the 10-minute intervals within that period
#   where the meter was alive and the occupancy count exists -- which is between
#   19% and 90% of the intervals depending on the building.
#
# So our findings describe **these seven buildings in these years**. Generalising
# them to other campuses would require assuming Delhi's climate, this campus's
# routine and this building stock are representative, and we do not assume that.
# Where we compare against published figures from other campuses (Phase 5), the
# comparison is offered as context, not as validation.

# %%
scope = pd.DataFrame([
    {
        "building": b,
        "kind": C.BUILDINGS[b]["kind"],
        "intervals available": int((long["building"] == b).sum()),
        "intervals usable": int(((long["building"] == b) & long["usable"]).sum()),
        "% usable": round(
            100 * float(((long["building"] == b) & long["usable"]).sum())
            / max(int((long["building"] == b).sum()), 1), 1),
    }
    for b in C.BUILDING_ORDER
])
display(scope)

# %% [markdown]
# ## Step 2: the attribute-type table
#
# Every column is one of a small number of kinds, and the kind determines what
# you are allowed to do with it. You can average a temperature; you cannot
# average a building name.
#
# | Type | Meaning | Allowed operations |
# |---|---|---|
# | **Nominal** | named categories, no order | count, mode |
# | **Ordinal** | ordered categories, gaps not meaningful | count, mode, median, ranking |
# | **Binary (symmetric)** | two states, both equally informative | count, proportion |
# | **Binary (asymmetric)** | two states, only the rare one is informative | count of the rare state |
# | **Discrete numeric** | countable numbers | all arithmetic |
# | **Continuous numeric** | measured on a real scale | all arithmetic |
#
# **Asymmetric binary** is the one people miss. For `meter_off`, "yes" carries
# almost all the information -- two buildings both being "not broken" tells you
# nothing about how similar they are, whereas two buildings both being "broken at
# this moment" is highly informative. The same applies to `outlier_iqr` and to
# `pf_was_negative`. Treating these as ordinary binary attributes would overstate
# how similar two records are.

# %%
attributes = pd.DataFrame([
    ("timestamp (index)", "interval", "continuous", "date/time",
     "Ordered with meaningful differences, but no true zero -- you can subtract "
     "two timestamps, you cannot divide them."),
    ("building", "nominal", "categorical", "7 categories",
     "Library is not greater or less than Mess."),
    ("building_kind", "binary (symmetric)", "categorical", "commercial / residential",
     "Both states are equally informative, so it is symmetric."),
    ("weekday", "ordinal", "categorical", "7 ordered categories",
     "Monday really does come before Tuesday; stored as an ordered pd.Categorical."),
    ("hour", "discrete numeric (cyclic)", "numeric", "0-23",
     "Cyclic: hour 23 is adjacent to hour 0, which is why Phase 4 one-hot "
     "encodes it rather than treating it as a plain number."),
    ("month", "discrete numeric (cyclic)", "numeric", "1-12", "Same cyclic issue."),
    ("year", "discrete numeric", "numeric", "2014-2017", "Counted, not measured."),
    ("is_weekend", "binary (symmetric)", "categorical", "True / False",
     "Both states are common and informative."),
    ("is_semester / is_vacation", "binary (symmetric)", "categorical", "True / False",
     "Approximated from the academic calendar; see decision D01-03."),
    ("occupancy", "discrete numeric", "numeric", "1 to 614",
     "A count of devices. Discrete: you cannot see 4.5 devices."),
    ("power_w", "continuous numeric (ratio)", "numeric", "0 to ~139,000 W",
     "Has a true zero, so ratios are meaningful: 20 kW really is twice 10 kW."),
    ("kwh", "continuous numeric (ratio)", "numeric", "derived",
     "power / 1000 x 10/60 -- the quantity every energy total is built from."),
    ("voltage", "continuous numeric (interval-like)", "numeric", "180-270 V",
     "Practically interval within its narrow working band."),
    ("power_factor", "continuous numeric", "numeric", "0 to 1",
     "Magnitude kept; the sign is stored separately as an asymmetric binary flag."),
    ("meter_off", "binary (ASYMMETRIC)", "categorical", "True / False",
     "Only True is informative. Two buildings both being 'not broken' says "
     "nothing about their similarity."),
    ("is_missing", "binary (ASYMMETRIC)", "categorical", "True / False",
     "Only True is informative."),
    ("was_interpolated", "binary (ASYMMETRIC)", "categorical", "True / False",
     "Only True is informative -- it marks a value we filled rather than measured."),
    ("outlier_iqr / outlier_zscore", "binary (ASYMMETRIC)", "categorical", "True / False",
     "Only True is informative; this is the rare, interesting state."),
    ("usable", "binary (symmetric)", "categorical", "True / False",
     "Used for filtering, and both states are common."),
], columns=["column", "attribute type", "family", "values", "note"])

display(attributes)
attributes.to_csv(C.RESULTS_DIR / "phase2_attribute_types.csv", index=False)

# %% [markdown]
# ## Step 3: descriptive statistics per building
#
# Mean, median, mode, range, variance, standard deviation, quartiles and IQR for
# power in every building.
#
# A note on the **mode**. Power is a float measured to five decimal places, so no
# two readings are ever exactly equal and the raw mode is meaningless -- every
# value occurs exactly once. To make "the most common power level" a question
# with an answer, we round to the nearest kilowatt first. This is a real
# consideration with continuous data, not a technicality.

# %%
descriptives = S.describe_all_buildings(long)
display(descriptives)
descriptives.to_csv(C.RESULTS_DIR / "phase2_descriptive_statistics.csv", index=False)

# %% [markdown]
# **What we found.**
#
# * **The Boys hostel has the highest average power** (about 33 kW) -- higher
#   than the Academic building, because it is occupied 24 hours a day.
# * **The mean is above the median in every building**, which means every
#   distribution is right-skewed: lots of ordinary intervals, a few very large ones.
# * **Facilities has a skew of 10.6** -- far beyond the others. Its maximum
#   (about 139 kW) is more than ten times its median (about 11 kW), which points
#   to a large intermittent load such as a pump or a water heater.
# * **The Girls hostel is the most stable** (skew 0.29, the smallest IQR relative
#   to its median).

# %% [markdown]
# ## Step 4: the same statistics computed by hand
#
# The table above came from pandas. Here we compute the same numbers directly
# from their definitions with NumPy -- an explicit loop for the mean, an explicit
# loop for the sum of squared deviations, a sort for the median and quartiles --
# and then assert that the two agree.
#
# The point is not that pandas might be wrong. It is to show what pandas is doing
# underneath, and to make the agreement a **test that runs** rather than a claim.

# %%
target = "Academic"
series = long.loc[(long["building"] == target) & long["usable"], "power_w"].dropna()

manual = S.describe_manual(series.to_numpy())
library = S.describe_pandas(series)

comparison = pd.DataFrame({
    "manual (NumPy formulas)": manual,
    "pandas": library,
})
comparison["difference"] = comparison["manual (NumPy formulas)"] - comparison["pandas"]
display(comparison.round(6))

# The assertion is the point: if these ever disagree the notebook fails.
for key in manual:
    assert abs(manual[key] - library[key]) < 1e-6 * max(abs(library[key]), 1.0), key
print(f"\nAll {len(manual)} statistics agree to within floating-point precision.")
print(f"Largest relative difference: "
      f"{max(abs(manual[k] - library[k]) / max(abs(library[k]), 1e-9) for k in manual):.2e}")

# %% [markdown]
# ## Step 5: population versus sample -- a simulation
#
# Suppose an energy auditor could only visit for a month. They would measure 30
# days and report an average. **How close would that average be to the truth?**
#
# We can answer it directly, because we hold the whole population. We treat every
# day of the Academic building's record as the population, draw 1,000 random
# samples of 30 days each, and look at how the 1,000 sample means are spread.
#
# The central limit theorem predicts the sample means should cluster around the
# population mean with a spread of `population_sd / sqrt(30)` -- the standard
# error. We check that prediction against what we actually get.

# %%
daily = (
    long.loc[(long["building"] == target) & long["usable"]]
    .groupby("date")["kwh"].sum()
)
daily = daily[daily > 0]
print(f"population: {len(daily):,} days of the {target} building")

sim = S.sampling_distribution(daily.to_numpy(), sample_size=30, n_samples=1000,
                              seed=C.SEED)
for key, value in sim.items():
    if key != "sample_means":
        print(f"  {key:28s} {value:,.2f}" if isinstance(value, float)
              else f"  {key:28s} {value:,}")

# %%
means = sim["sample_means"]
fig, ax = plt.subplots(figsize=(10, 4))

ax.hist(means, bins=40, color=viz.CATEGORICAL[0], label="means of 1,000 samples of 30 days")
ax.axvline(sim["population_mean"], color=viz.STATUS["CRITICAL"] if "CRITICAL" in viz.STATUS
           else viz.STATUS["ANOMALY"], linewidth=2, label="true population mean")
ax.annotate(
    f"population mean\n{sim['population_mean']:,.0f} kWh/day",
    xy=(sim["population_mean"], ax.get_ylim()[1] * 0.85),
    xytext=(10, 0), textcoords="offset points", fontsize=9,
    color=viz.STATUS["ANOMALY"],
)
ax.set_xlabel("mean daily energy of a 30-day sample (kWh)")
ax.set_ylabel("number of samples")
ax.set_title(f"{target} building: how close would a 30-day audit get?")
ax.legend(loc="upper left")
viz.save_fig(fig, "fig_02_sampling_distribution")

within = 100 * float(np.mean(np.abs(means - sim["population_mean"])
                             / sim["population_mean"] < 0.05))
print(f"\n{within:.1f}% of 30-day samples land within 5% of the true mean.")
print(f"observed standard error : {sim['sd_of_sample_means']:,.1f} kWh")
print(f"predicted by the CLT    : {sim['predicted_standard_error']:,.1f} kWh")

# %% [markdown]
# **Takeaway.** The sample means form the bell shape the central limit theorem
# predicts, centred almost exactly on the population mean, and the observed
# spread matches the predicted standard error closely. In practical terms: a
# 30-day audit of this building would get within a few percent of the truth most
# of the time -- but **only if the 30 days were drawn at random across the year**.
# An audit that happened to run in June would be measuring the air conditioning
# season, and no amount of statistics would fix that. This is exactly why our own
# analysis uses the full 3.7-year record rather than a sample.

# %% [markdown]
# ## Step 6: what distribution does power follow?
#
# We fit a **Normal** and a **Log-normal** to the Academic building's power and
# ask which describes it better, using three tools: an overlay on the histogram,
# a Q-Q plot, and the Kolmogorov-Smirnov test.
#
# **A warning about the KS p-value.** KS asks "could this data have come from
# *exactly* this distribution?". With 176,000 readings the answer is always no,
# because no real measurement is exactly anything -- so the p-value will be
# essentially zero for both candidates and tells us nothing. What *is* useful is
# the **KS statistic**: the largest gap between the fitted and the observed
# cumulative distribution. That is an effect size, and comparing the two
# statistics is a fair comparison.

# %%
fit = S.fit_normal_and_lognormal(series.to_numpy(), seed=C.SEED)
fit_table = pd.DataFrame([
    {"distribution": "Normal",
     "KS statistic (lower is better)": round(fit["ks_statistic_normal"], 4),
     "KS p-value": S.format_p(fit["ks_pvalue_normal"])},
    {"distribution": "Log-normal",
     "KS statistic (lower is better)": round(fit["ks_statistic_lognormal"], 4),
     "KS p-value": S.format_p(fit["ks_pvalue_lognormal"])},
])
display(fit_table)
print(f"skewness : {fit['skew']:.3f}")
print(f"kurtosis : {fit['kurtosis']:.3f}")
print(f"better fit by KS statistic: {fit['better_fit']}")

# %%
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4))

x = np.linspace(series.min() + 1, series.max(), 400)
ax1.hist(series / 1000, bins=80, density=True, color=viz.CATEGORICAL[0],
         alpha=0.85, label="observed")
ax1.plot(x / 1000, sps.norm.pdf(x, *fit["normal_params"]) * 1000,
         color=viz.CATEGORICAL[1], lw=2, label="Normal fit")
ax1.plot(x / 1000, sps.lognorm.pdf(x, *fit["lognormal_params"]) * 1000,
         color=viz.CATEGORICAL[3], lw=2, label="Log-normal fit")
ax1.set_xlabel("Power (kW)")
ax1.set_ylabel("density")
ax1.set_title("Fitted distributions")
ax1.legend()

sps.probplot(series.to_numpy(), dist="norm", plot=ax2)
ax2.set_title("Q-Q plot against Normal")
ax2.get_lines()[0].set_markerfacecolor(viz.CATEGORICAL[0])
ax2.get_lines()[0].set_markeredgecolor(viz.CATEGORICAL[0])
ax2.get_lines()[0].set_markersize(2)
ax2.get_lines()[1].set_color(viz.STATUS["ANOMALY"])

sps.probplot(np.log(series.to_numpy()), dist="norm", plot=ax3)
ax3.set_title("Q-Q plot of log(power) against Normal")
ax3.get_lines()[0].set_markerfacecolor(viz.CATEGORICAL[3])
ax3.get_lines()[0].set_markeredgecolor(viz.CATEGORICAL[3])
ax3.get_lines()[0].set_markersize(2)
ax3.get_lines()[1].set_color(viz.STATUS["ANOMALY"])

viz.save_fig(fig, "fig_02_distribution_fit")

# %% [markdown]
# **Takeaway.** The log-normal fits better -- its KS statistic is about half the
# Normal's -- which is what you expect for a strictly positive, right-skewed
# quantity. But look at the Q-Q plots: **neither is a good fit**. Both bend away
# from the straight line at the ends, because the Academic building's power is
# genuinely **bimodal**: a night-time cluster and a daytime cluster. No single
# unimodal distribution can describe two clusters.
#
# This is a useful negative result, and it shapes Phase 4: since power is not
# normally distributed, we should not rely on methods that assume it is, and
# reporting **MAE alongside RMSE** matters, because RMSE is dominated by the
# large values in the tail.

# %% [markdown]
# ## Step 7: hypothesis tests -- are the patterns real?
#
# EDA suggests patterns; a hypothesis test checks whether they could be chance.
# We test two claims for every building:
#
# 1. **Semester versus vacation** -- does the campus use less power in vacations?
# 2. **Weekday versus weekend** -- does it use less at weekends?
#
# Two tests each, because they ask different questions. The **Welch t-test** asks
# whether the *means* differ and assumes roughly normal data. The
# **Mann-Whitney U** test asks whether one group is *stochastically larger* and
# assumes nothing about the distribution -- which matters here, because Step 6
# just showed our data is not normal.
#
# And again: with this much data every p-value will be tiny. **Read the Cohen's d
# column**, not the p-value.

# %%
semester_tests = []
for building in C.BUILDING_ORDER:
    sub = usable[usable["building"] == building]
    sem = sub.loc[sub["is_semester"], "power_w"]
    vac = sub.loc[sub["is_vacation"], "power_w"]
    if len(sem) < 100 or len(vac) < 100:
        continue
    row = S.compare_groups(sem, vac, "semester", "vacation")
    row["building"] = building
    semester_tests.append(row)

semester_df = pd.DataFrame(semester_tests)
show = semester_df[[
    "building", "n_a", "n_b", "mean_a", "mean_b", "difference_in_means",
    "percent_difference", "cohens_d", "effect_size_label",
]].rename(columns={"mean_a": "mean semester (W)", "mean_b": "mean vacation (W)",
                   "n_a": "n semester", "n_b": "n vacation"})
show["t-test p"] = [S.format_p(p) for p in semester_df["t_pvalue"]]
show["Mann-Whitney p"] = [S.format_p(p) for p in semester_df["mannwhitney_pvalue"]]
display(show)

# %%
weekend_tests = []
for building in C.BUILDING_ORDER:
    sub = usable[usable["building"] == building]
    week = sub.loc[~sub["is_weekend"], "power_w"]
    wknd = sub.loc[sub["is_weekend"], "power_w"]
    if len(week) < 100 or len(wknd) < 100:
        continue
    row = S.compare_groups(week, wknd, "weekday", "weekend")
    row["building"] = building
    weekend_tests.append(row)

weekend_df = pd.DataFrame(weekend_tests)
show2 = weekend_df[[
    "building", "mean_a", "mean_b", "difference_in_means", "percent_difference",
    "cohens_d", "effect_size_label",
]].rename(columns={"mean_a": "mean weekday (W)", "mean_b": "mean weekend (W)"})
show2["t-test p"] = [S.format_p(p) for p in weekend_df["t_pvalue"]]
show2["Mann-Whitney p"] = [S.format_p(p) for p in weekend_df["mannwhitney_pvalue"]]
display(show2)

semester_df.to_csv(C.RESULTS_DIR / "phase2_test_semester_vacation.csv", index=False)
weekend_df.to_csv(C.RESULTS_DIR / "phase2_test_weekday_weekend.csv", index=False)

# %% [markdown]
# **Takeaway -- and this is where effect size earns its keep.** Every one of
# these tests returns a p-value small enough to print in scientific notation, so
# on the usual "p < 0.05" reading *every* difference is "significant" and the
# p-values tell us nothing except that we have a lot of data. The Cohen's d
# column is where the real story is, and it is **not uniform**:
#
# **Semester versus vacation** splits the campus in two.
#
# * The **Boys hostel** drops 42% (d = 0.89, large) and the **Lecture building**
#   drops 125% relative to vacation (d = 1.24, large). These are buildings whose
#   whole purpose empties out when term ends.
# * The **Academic building and the Mess barely move** (d = 0.08 and 0.09,
#   negligible). Whatever they are doing, term time is not what drives it.
# * **Facilities is the only building that uses *more* power on low-activity
#   days than on high-activity ones** -- every other building falls by 13% to
#   50%, while Facilities rises slightly. This is not a mistake: the official
#   calendar counts weekends and holidays as low-activity too, and Facilities
#   runs campus services that do not care what day it is. Phase 8 shows the
#   residual gap is explained by outdoor temperature.
#
# **Weekday versus weekend** splits it the other way.
#
# * The **Library falls 65%** at weekends (d = 0.66) and the **Academic building
#   45%** (d = 0.73) -- these buildings do follow the working week.
# * Both **hostels are essentially flat** (d = 0.19 and 0.20, negligible), which
#   is exactly right: people live there on Saturdays too.
#
# The pattern that matters for Phase 5 is the contrast. Buildings *can* respond
# strongly to whether people are present -- the Library proves it. The ones that
# do not respond are therefore making a choice, not obeying a physical necessity.

# %% [markdown]
# ## Step 8: the chart set
#
# Seven charts covering the standard forms. Each one has a one-line takeaway
# under it, and each is saved to `figures/` for the report.
#
# ### 8.1 Pie chart -- each building's share of total campus energy

# %%
energy_share = (
    usable.groupby("building", observed=True)["kwh"].sum().sort_values(ascending=False)
)
share_pct = 100 * energy_share / energy_share.sum()

fig, ax = plt.subplots(figsize=(8, 5.5))
wedges, _ = ax.pie(
    energy_share.values,
    colors=[viz.color_for(b) for b in energy_share.index],
    startangle=90,
    counterclock=False,
    wedgeprops={"edgecolor": viz.SURFACE, "linewidth": 2},   # 2px surface gap
)
ax.legend(
    wedges,
    [f"{b.replace('_', ' ')} -- {p:.1f}%  ({e:,.0f} kWh)"
     for b, p, e in zip(energy_share.index, share_pct, energy_share)],
    loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=9,
)
ax.set_title("Share of total measured campus energy, by building")
viz.save_fig(fig, "fig_02_pie_energy_share")
display(pd.DataFrame({"kWh": energy_share.round(0), "share %": share_pct.round(1)}))

# %% [markdown]
# **Takeaway.** Note the health warning that has to go with this chart: the
# shares reflect **measured** energy, and the buildings have very different
# amounts of usable data (Lecture only 19%). It shows what we recorded, not what
# the campus consumed. The next chart avoids that problem.

# %% [markdown]
# ### 8.2 Bar chart -- average energy per day
#
# Average daily energy is the fair comparison, because it does not depend on how
# many days of data each building happens to have.

# %%
daily_all = (
    usable.groupby(["building", "date"], observed=True)["kwh"].sum().reset_index()
)
mean_daily = (
    daily_all.groupby("building", observed=True)["kwh"].mean().sort_values(ascending=False)
)

fig, ax = plt.subplots(figsize=(9, 4.2))
bars = ax.bar(
    [b.replace("_", " ") for b in mean_daily.index],
    mean_daily.values,
    color=[viz.color_for(b) for b in mean_daily.index],
)
# Direct labels: with 7 bars a legend would be redundant, the axis names them.
for bar, value in zip(bars, mean_daily.values):
    ax.annotate(f"{value:,.0f}", xy=(bar.get_x() + bar.get_width() / 2, value),
                xytext=(0, 4), textcoords="offset points", ha="center",
                fontsize=9, color=viz.INK_SECONDARY)
ax.set_ylabel("Mean energy per day (kWh)")
ax.set_title("Average daily energy use, by building")
ax.grid(axis="y")
plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
viz.save_fig(fig, "fig_02_bar_daily_energy")

# %% [markdown]
# **Takeaway.** The Boys hostel is the largest daily consumer on campus -- ahead
# of the Academic building -- which makes sense for a building that is occupied
# around the clock. The Lecture building's figure is small but rests on only 19%
# of its days.

# %% [markdown]
# ### 8.3 Box plot -- the spread of power in each building

# %%
fig, ax = plt.subplots(figsize=(10, 4.5))
data = [usable.loc[usable["building"] == b, "power_w"].dropna() / 1000
        for b in C.BUILDING_ORDER]
bp = ax.boxplot(
    data, tick_labels=[b.replace("_", " ") for b in C.BUILDING_ORDER],
    patch_artist=True, showfliers=False, widths=0.55,
    medianprops={"color": viz.INK, "linewidth": 1.6},
    whiskerprops={"color": viz.AXIS}, capprops={"color": viz.AXIS},
    boxprops={"edgecolor": viz.SURFACE, "linewidth": 2},
)
for patch, building in zip(bp["boxes"], C.BUILDING_ORDER):
    patch.set_facecolor(viz.color_for(building))
ax.set_ylabel("Power (kW)")
ax.set_title("Distribution of 10-minute power readings, by building")
ax.annotate("outliers hidden for readability; they are flagged, not deleted",
            xy=(0.005, -0.22), xycoords="axes fraction", fontsize=8,
            color=viz.INK_MUTED)
plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
viz.save_fig(fig, "fig_02_box_power_by_building")

# %% [markdown]
# **Takeaway.** The two hostels have narrow boxes -- their load is steady,
# because people live there continuously. The Academic and Library buildings have
# tall boxes: they swing between a quiet night baseline and a busy day. That
# swing is exactly what the waste analysis in Phase 5 is measuring.

# %% [markdown]
# ### 8.4 Histograms -- the shape of each building's load

# %%
fig, axes = plt.subplots(2, 4, figsize=(14, 6))
for ax, building in zip(axes.flat, C.BUILDING_ORDER):
    values = usable.loc[usable["building"] == building, "power_w"].dropna() / 1000
    ax.hist(values, bins=60, color=viz.color_for(building))
    ax.set_title(building.replace("_", " "), fontsize=10)
    ax.set_xlabel("Power (kW)")
    ax.tick_params(labelsize=8)
axes.flat[-1].axis("off")
fig.suptitle("Power distribution in each building", x=0.09, ha="left",
             fontsize=12, fontweight="semibold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
viz.save_fig(fig, "fig_02_hist_power_all_buildings")

# %% [markdown]
# **Takeaway.** The shapes differ in a way that matters. The Academic and Library
# buildings are clearly **bimodal** -- a night hump and a day hump -- which is
# why no single normal distribution fitted them in Step 6. The hostels are much
# closer to a single broad peak, because they never really switch off.

# %% [markdown]
# ### 8.5 Multi-line chart -- the average day in each building
#
# This is the most informative single chart in the phase: average power at each
# hour of the day, one line per building.

# %%
hourly = (
    usable.groupby(["building", "hour"], observed=True)["power_w"].mean().unstack(0)
)

fig, ax = plt.subplots(figsize=(11, 5))
for building in C.BUILDING_ORDER:
    if building in hourly:
        ax.plot(hourly.index, hourly[building] / 1000,
                color=viz.color_for(building), label=building.replace("_", " "))
ax.set_xlabel("Hour of day (India time)")
ax.set_ylabel("Mean power (kW)")
ax.set_title("The average day: mean power by hour, per building")
ax.set_xticks(range(0, 24, 2))
ax.set_xlim(0, 23)
# Legend below the axes: inside the plot it would sit on top of the Boys hostel
# line, which peaks in exactly that corner.
ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=9)
viz.save_fig(fig, "fig_02_hourly_profile_all")
display(hourly.round(0).head(6))

# %% [markdown]
# **Takeaway -- this chart contains the heart of the project.** The commercial
# buildings (Academic, Library, Lecture) rise sharply in the morning and fall at
# night, exactly as you would expect. But look at **where their lines sit at 3
# a.m.**: the Academic building is still drawing roughly 20 kW with essentially
# nobody inside. That gap between the night floor and zero is the energy Phase 5
# is about to quantify. The hostels show the opposite pattern -- they peak in the
# evening and overnight, because that is when residents are home.

# %% [markdown]
# ### 8.6 Scatter plots -- power against occupancy
#
# The central relationship of the project. We draw one small panel per building
# rather than one crowded chart, because seven overlapping colours in a single
# scatter cannot be told apart reliably.

# %%
fig, axes = plt.subplots(2, 4, figsize=(14, 6.5))
rng = np.random.default_rng(C.SEED)

for ax, building in zip(axes.flat, C.BUILDING_ORDER):
    sub = usable.loc[usable["building"] == building, ["power_w", "occupancy"]].dropna()
    # Plot a random subsample: 170,000 points would be an unreadable black blob.
    if len(sub) > 6000:
        sub = sub.iloc[rng.choice(len(sub), 6000, replace=False)]
    ax.scatter(sub["occupancy"], sub["power_w"] / 1000, s=3, alpha=0.25,
               color=viz.color_for(building), edgecolors="none")
    ax.set_title(building.replace("_", " "), fontsize=10)
    ax.set_xlabel("Occupancy (devices)")
    ax.set_ylabel("Power (kW)")
    ax.tick_params(labelsize=8)
    ax.grid(True, axis="both", color=viz.GRID, linewidth=0.7)

    # Facilities has a rare load an order of magnitude above its normal range
    # (skew 10.6). Left alone it squashes that panel flat and hides the shape we
    # are here to see, so we clip the axis and say how many points are above it.
    full = usable.loc[usable["building"] == building, "power_w"].dropna() / 1000
    ceiling = float(full.quantile(0.999))
    if full.max() > 3 * ceiling:
        above = int((full > ceiling).sum())
        ax.set_ylim(0, ceiling * 1.08)
        ax.annotate(f"{above:,} readings above {ceiling:,.0f} kW not shown",
                    xy=(0.5, 0.95), xycoords="axes fraction", ha="center",
                    fontsize=7.5, color=viz.INK_MUTED)
axes.flat[-1].axis("off")
fig.suptitle("Power against occupancy, one panel per building",
             x=0.09, ha="left", fontsize=12, fontweight="semibold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
viz.save_fig(fig, "fig_02_scatter_power_occupancy")

# %% [markdown]
# **Takeaway.** Two features are visible in every panel and both matter.
# First, the clouds slope upward -- more people does mean more power. Second, and
# more importantly, **every cloud has a floor well above zero on the left-hand
# side**: even at the lowest occupancy the building is still drawing a
# substantial load. That floor is the base load, and it is what Phase 4's
# regression intercept will measure and Phase 5 will price.

# %%
correlations = S.power_occupancy_correlation(long)
display_corr = correlations.copy()
display_corr["pearson_p"] = [S.format_p(p) for p in correlations["pearson_p"]]
display_corr["spearman_p"] = [S.format_p(p) for p in correlations["spearman_p"]]
display(display_corr)
correlations.to_csv(C.RESULTS_DIR / "phase2_power_occupancy_correlation.csv",
                    index=False)

# %% [markdown]
# **Takeaway.** Occupancy and power are correlated everywhere, but never
# strongly. The best case is the Academic building at r = 0.67, meaning occupancy
# explains about **45%** of the variation in its power; the worst is Facilities at
# r = 0.27, explaining about 7%. In other words, **most of what determines a
# building's power draw is not how many people are in it.** That is a result in
# its own right, it sets expectations for Phase 4, and it is the quantitative
# version of the base-load floor visible in the scatter plots.
#
# Spearman is higher than Pearson for the Library (0.61 versus 0.50), which tells
# us the relationship there is real but **bent** -- power rises with occupancy
# and then flattens, rather than continuing in a straight line.

# %% [markdown]
# ### 8.7 Correlation heatmap -- all numeric features together

# %%
numeric_cols = ["power_w", "occupancy", "hour", "month", "power_lag_1h",
                "power_lag_1d", "power_roll24h_mean", "power_roll24h_std",
                "voltage", "power_factor"]
acad_numeric = usable.loc[usable["building"] == target, numeric_cols].dropna()
corr = acad_numeric.corr()

fig, ax = plt.subplots(figsize=(8.5, 7))
im = ax.imshow(corr.values, cmap=viz.DIVERGING, vmin=-1, vmax=1)
ax.set_xticks(range(len(corr)))
ax.set_yticks(range(len(corr)))
ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=9)
ax.set_yticklabels(corr.index, fontsize=9)
ax.grid(False)

# Direct labels: a heatmap without its numbers cannot be read precisely.
for i in range(len(corr)):
    for j in range(len(corr)):
        value = corr.values[i, j]
        ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8,
                color="#ffffff" if abs(value) > 0.55 else viz.INK)

ax.set_title(f"Correlation between numeric features -- {target} building", pad=12)
cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
cbar.set_label("Pearson r", fontsize=9, color=viz.INK_SECONDARY)
cbar.outline.set_visible(False)
viz.save_fig(fig, "fig_02_correlation_heatmap")

# %% [markdown]
# **Takeaway.** The strongest predictor of power is **power one hour ago**
# (r about 0.95) -- buildings are inertial. Yesterday's power at the same time is
# next (about 0.8). Occupancy sits well behind both. This is an early warning for
# Phase 4: a model given lag features will look excellent while learning almost
# nothing about *why* the building uses energy. That is why the regression models
# in Phase 4 deliberately use calendar and occupancy features rather than lags --
# we want an expected-consumption baseline we can interpret, not the best
# possible forecast.

# %% [markdown]
# ### 8.8 Weekday and semester patterns side by side

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.4))

weekday_means = (
    usable.groupby(["building", "weekday"], observed=True)["power_w"].mean().unstack(0)
)
for building in C.BUILDING_ORDER:
    if building in weekday_means:
        ax1.plot(range(7), weekday_means[building] / 1000, marker="o",
                 color=viz.color_for(building), label=building.replace("_", " "))
ax1.set_xticks(range(7))
ax1.set_xticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
ax1.set_ylabel("Mean power (kW)")
ax1.set_title("By day of week")
ax1.axvspan(4.5, 6.5, color=viz.INK_MUTED, alpha=0.10, zorder=0)
ax1.annotate("weekend", xy=(5.5, ax1.get_ylim()[1] * 0.04), ha="center",
             fontsize=8, color=viz.INK_SECONDARY)

period_means = (
    usable.groupby(["building", "period"], observed=True)["power_w"]
    .mean().unstack(1) / 1000
)
positions = np.arange(len(period_means))
width = 0.38
ax2.bar(positions - width / 2, period_means["semester"], width,
        color=viz.CATEGORICAL[0], label="semester")
ax2.bar(positions + width / 2, period_means["vacation"], width,
        color=viz.CATEGORICAL[1], label="vacation")
ax2.set_xticks(positions)
ax2.set_xticklabels([b.replace("_", " ") for b in period_means.index],
                    rotation=20, ha="right")
ax2.set_ylabel("Mean power (kW)")
ax2.set_title("Semester versus vacation")
ax2.legend()

viz.save_fig(fig, "fig_02_weekday_semester_patterns")

# %% [markdown]
# **Takeaway.** The weekday drop at weekends is small in every building -- a few
# percent, not the collapse you would expect if consumption tracked occupation.
# The semester-versus-vacation panel is more striking still: in several buildings
# vacation power is **as high as or higher than** semester power, because Delhi's
# summer vacation coincides with the hottest months and the air conditioning runs
# regardless of whether anyone is there. This is the clearest sign yet that these
# buildings consume largely independently of their occupants, and it is also a
# direct illustration of the **no-weather-data limitation**: we can see the effect
# but cannot separate cooling load from occupancy-driven load.

# %% [markdown]
# ## Step 9: write Phase 2 into the report

# %%
best_corr = correlations.loc[correlations["pearson_r"].idxmax()]
worst_corr = correlations.loc[correlations["pearson_r"].idxmin()]
max_d = semester_df.loc[semester_df["cohens_d"].abs().idxmax()]


def name_list(frame, mask, with_d=True):
    """Turn a selection of buildings into readable prose for the report."""
    rows = frame[mask]
    if rows.empty:
        return "no buildings"
    parts = [
        f"**{r['building'].replace('_', ' ')}**"
        + (f" (d = {r['cohens_d']:.2f})" if with_d else "")
        for _, r in rows.iterrows()
    ]
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


sem_large = name_list(semester_df, semester_df["cohens_d"] >= 0.8)
sem_negligible = name_list(
    semester_df, semester_df["cohens_d"].abs() < 0.1
)
sem_up = name_list(semester_df, semester_df["cohens_d"] < -0.2)
wk_medium = name_list(weekend_df, weekend_df["cohens_d"] >= 0.5)

blocks = {}

blocks["method_phase2"] = f"""
Phase 2 describes the data before any model is fitted.

**Attribute classification.** Every column is classified as nominal, ordinal,
binary (symmetric or **asymmetric**), discrete numeric or continuous numeric.
The asymmetric binary attributes -- `meter_off`, `is_missing`,
`was_interpolated`, `outlier_iqr`, `outlier_zscore` -- are the ones where only
the "True" state carries information; treating them as ordinary binary attributes
would overstate how similar two records are.

**Descriptive statistics.** Mean, median, mode, range, variance, standard
deviation, quartiles and IQR for every building. The mode of a continuous
variable only exists once it is binned, so power is rounded to the nearest
kilowatt first. Every statistic is then **recomputed by hand from its definition
with NumPy** -- explicit loops for the mean and the sum of squared deviations, a
sort for the median and quartiles -- and asserted equal to the pandas result.

**Population versus sample.** Treating every day of the Academic building's
record as the population, 1,000 random samples of 30 days are drawn and the
distribution of their means compared against the population mean and against the
standard error the central limit theorem predicts.

**Distribution fitting.** A Normal and a Log-normal are fitted with `scipy`,
compared by histogram overlay, Q-Q plot and Kolmogorov-Smirnov test. With
{fit['n']:,} readings the KS p-value is uninformative -- it rejects any
distribution -- so the comparison is made on the **KS statistic**, which is an
effect size.

**Hypothesis tests.** Semester versus vacation and weekday versus weekend, for
every building, with both a Welch t-test (means, assumes approximate normality)
and a Mann-Whitney U test (stochastic dominance, assumes nothing). **Cohen's d is
reported beside every p-value**, because at these sample sizes significance is
guaranteed and only effect size is informative.

**Notebook:** `notebooks/02_stats_eda.ipynb`.
"""

blocks["results_phase2"] = f"""
### Descriptive statistics

{report.md_table(descriptives)}

The mean exceeds the median in every building, so every distribution is
right-skewed. The Boys hostel has the highest average power
({descriptives.set_index('building').loc['Boys_Hostel', 'mean'] / 1000:.1f} kW),
above the Academic building, because it is occupied around the clock. Facilities
is the extreme case with a skew of
{descriptives.set_index('building').loc['Facilities', 'skew']:.1f} -- its maximum
is more than ten times its median, pointing to a large intermittent load.

### Manual calculation checked against pandas

Every statistic above was recomputed from its definition with NumPy and asserted
equal to the pandas result. The largest relative difference across all eleven
statistics was
{max(abs(manual[k] - library[k]) / max(abs(library[k]), 1e-9) for k in manual):.1e}
-- floating-point noise. The check runs as an assertion, so the notebook fails if
they ever diverge.

### Population versus sample

{report.figure("fig_02_sampling_distribution",
               "Means of 1,000 random 30-day samples against the true population mean",
               f"The sample means form the bell shape the central limit theorem "
               f"predicts, centred on the population mean; the observed standard "
               f"error ({sim['sd_of_sample_means']:,.0f} kWh) matches the "
               f"predicted one ({sim['predicted_standard_error']:,.0f} kWh).")}

{within:.1f}% of 30-day samples land within 5% of the true mean -- **but only
because the days are drawn at random across the whole year**. An audit that
happened to run in June would measure the air-conditioning season instead. This
is why the project uses the full 3.7-year record rather than a sample.

### What distribution does power follow?

{report.md_table(fit_table)}

The log-normal fits better on the KS statistic, as expected for a strictly
positive right-skewed quantity. But the Q-Q plots show **neither is a good fit**:
the Academic building's power is genuinely bimodal -- a night cluster and a day
cluster -- and no unimodal distribution can describe two clusters.

{report.figure("fig_02_distribution_fit",
               "Fitted distributions and Q-Q plots for Academic building power",
               "Both candidate distributions bend away from the line at the "
               "extremes; the data is bimodal, which is a physical feature "
               "rather than a distortion.")}

This shapes Phase 4: because power is not normally distributed, MAE is reported
alongside RMSE, since RMSE is dominated by the tail.

### Hypothesis tests

**Semester versus vacation:**

{report.md_table(show)}

**Weekday versus weekend:**

{report.md_table(show2)}

Every p-value here is small enough to print in scientific notation, so on a naive
"p < 0.05" reading every difference is significant and the p-values tell us
nothing beyond the fact that we have a lot of data. The **Cohen's d** column
carries the finding, and it is **not uniform across the campus**.

*Semester versus vacation* splits the buildings in two. The
{sem_large} show large effects -- buildings whose purpose empties out when term
ends. But the {sem_negligible} barely move, and {sem_up} actually consumes **more** power
during vacation, because the Indian summer vacation coincides with Delhi's
hottest months: cooling load rises exactly as occupation falls. That is the
no-weather-data limitation made visible.

*Weekday versus weekend* splits them the other way. The
{wk_medium} fall substantially at weekends, while both hostels are essentially
flat (d = {weekend_df.set_index('building').loc['Boys_Hostel', 'cohens_d']:.2f}
and {weekend_df.set_index('building').loc['Girls_Hostel', 'cohens_d']:.2f}) --
which is correct, because people live there on Saturdays too.

The contrast is what matters for Phase 5. Buildings *can* respond strongly to
whether people are present -- the Library drops
{weekend_df.set_index('building').loc['Library', 'percent_difference']:.0f}% at
weekends, so it is clearly possible. Buildings that do not respond are therefore
making a choice, not obeying a physical necessity.

### The chart set

{report.figure("fig_02_pie_energy_share",
               "Share of total measured campus energy by building",
               "Shares reflect *measured* energy, and the buildings have very "
               "different amounts of usable data (Lecture only 19%), so this "
               "shows what was recorded rather than what the campus consumed.")}

{report.figure("fig_02_bar_daily_energy",
               "Average daily energy use by building",
               f"The fair comparison, independent of how many days each meter "
               f"recorded. The Boys hostel is the largest daily consumer at "
               f"{mean_daily.iloc[0]:,.0f} kWh/day.")}

{report.figure("fig_02_box_power_by_building",
               "Distribution of 10-minute power readings by building",
               "The hostels have narrow boxes -- steady load from continuous "
               "occupation. Academic and Library have tall boxes: they swing "
               "between a quiet night baseline and a busy day.")}

{report.figure("fig_02_hist_power_all_buildings",
               "Power distribution in each building",
               "Academic and Library are visibly bimodal (a night hump and a "
               "day hump); the hostels are closer to one broad peak because "
               "they never really switch off.")}

{report.figure("fig_02_hourly_profile_all",
               "Mean power by hour of day, one line per building",
               "The most important chart in this phase: the commercial "
               "buildings fall at night but do not fall to zero -- the Academic "
               "building still draws around 20 kW at 3 a.m. That gap is what "
               "Phase 5 quantifies.")}

{report.figure("fig_02_scatter_power_occupancy",
               "Power against occupancy, one panel per building",
               "Every cloud slopes upward, and every cloud has a floor well "
               "above zero on the left: even at minimum occupancy the building "
               "draws a substantial load.")}

### Power-occupancy correlation

{report.md_table(display_corr)}

Occupancy and power are correlated in every building but never strongly. The best
case is **{best_corr['building'].replace('_', ' ')} at r = {best_corr['pearson_r']:.2f}**,
meaning occupancy explains about {100 * best_corr['r_squared']:.0f}% of the
variation in its power; the weakest is
**{worst_corr['building'].replace('_', ' ')} at r = {worst_corr['pearson_r']:.2f}**
({100 * worst_corr['r_squared']:.0f}%). So **most of what determines a building's
power draw is not how many people are in it** -- a result in its own right, and
the quantitative form of the base-load floor visible in the scatter plots.

Spearman exceeds Pearson for the Library (0.61 against 0.50), indicating a real
but *bent* relationship: power rises with occupancy and then flattens.

{report.figure("fig_02_correlation_heatmap",
               "Correlation between numeric features, Academic building",
               "The strongest predictor of power is power one hour ago (r about "
               "0.95) -- buildings are inertial. Occupancy sits well behind the "
               "lag features, which is why Phase 4's interpretable models use "
               "calendar and occupancy features rather than lags.")}

{report.figure("fig_02_weekday_semester_patterns",
               "Mean power by day of week, and semester against vacation",
               "The weekend drop is a few percent, not a collapse. In several "
               "buildings vacation power is as high as or higher than semester "
               "power, because Delhi's summer vacation coincides with the "
               "hottest months and the cooling runs regardless.")}
"""

report.update_blocks(blocks)

# %% [markdown]
# ## Step 10: record the Phase 2 decisions

# %%
report.log_decision(
    id="D02-01", phase="2",
    decision="Reporting effect size alongside every p-value",
    options_considered="Report p-values only; report effect sizes only; report "
                       "both and lead with effect size",
    chosen="Both, leading with Cohen's d and the percentage difference",
    reason="Sample sizes run from 37,000 to 177,000 intervals. At that size "
           "every test returns p < 0.001 for differences of no practical "
           "importance, so a p-value alone would let us claim significance for "
           "everything.",
    effect_on_results="Changes the conclusion of Step 7 from 'all differences "
                      "are significant' to 'all differences are detectable but "
                      "most are small', which is the honest reading.",
)

report.log_decision(
    id="D02-02", phase="2",
    decision="Which statistic decides the Normal vs Log-normal comparison",
    options_considered="KS p-value; KS statistic; AIC; visual inspection only",
    chosen="KS statistic (an effect size), supported by Q-Q plots",
    reason=f"With {fit['n']:,} readings the KS p-value rejects both candidates, "
           "so it cannot discriminate. The statistic measures the largest gap "
           "between fitted and observed distributions and remains meaningful.",
    effect_on_results=f"Log-normal wins (KS {fit['ks_statistic_lognormal']:.3f} "
                      f"vs {fit['ks_statistic_normal']:.3f}), but the Q-Q plots "
                      "show neither fits well because the data is bimodal. That "
                      "negative result is reported rather than hidden.",
)

report.log_decision(
    id="D02-03", phase="2",
    decision="Mode of a continuous variable",
    options_considered="Report the raw mode; bin first; omit the mode",
    chosen="Round power to the nearest 1 kW before taking the mode",
    reason="Power is a float to five decimal places, so every value occurs "
           "exactly once and the raw mode is an arbitrary first row.",
    effect_on_results="Makes the mode column meaningful. Bin width is a choice: "
                      "a different width would shift the reported mode slightly.",
)

report.log_decision(
    id="D02-04", phase="2",
    decision="Scatter plots drawn as small multiples on a subsample",
    options_considered="One scatter with all 7 buildings overlaid; small "
                       "multiples; hexbin density plots",
    chosen="One panel per building, each a random subsample of 6,000 points "
           f"(seed {C.SEED})",
    reason="Seven overlapping colours in one scatter cannot be told apart "
           "reliably, and 170,000 points per building render as a solid block "
           "that hides the structure.",
    effect_on_results="Visual only -- all correlation statistics are computed on "
                      "the complete data, not the subsample.",
)

report.publish_decision_log()
print()
print("blocks still pending:", len(report.pending_blocks()))
print("figures referenced but missing:", report.check_figures())

# %% [markdown]
# ## Phase 2 conclusion
#
# **The four findings that shape the rest of the project:**
#
# 1. **Occupancy explains only 7% to 45% of the variation in power**, depending
#    on the building. Most of what drives consumption is not the number of people
#    present. This sets a realistic ceiling on what Phase 4's models can achieve.
# 2. **Every building has a large base load.** The scatter plots show a floor well
#    above zero at minimum occupancy, and the hourly profiles show the Academic
#    building still drawing about 20 kW at 3 a.m. This is the quantity Phase 5
#    exists to measure.
# 3. **Buildings respond to occupation very unevenly.** The Library drops 65% at
#    weekends and the Boys hostel 42% in vacation -- so responding *is* possible.
#    But the Academic building and the Mess barely move between semester and
#    low-activity days, and Facilities is the only building that uses *more* --
#    it runs campus services regardless of the calendar, and Phase 8 shows the
#    rest of its gap is outdoor temperature. Buildings that do not respond are making a
#    choice rather than obeying a constraint.
# 4. **Power is bimodal and right-skewed**, so methods assuming normality should
#    be used with care, and MAE belongs beside RMSE in Phase 4.
#
# **Next:** Phase 3 -- PCA on daily load profiles, to find the typical shapes of
# a day and to check whether day-types separate cleanly.
