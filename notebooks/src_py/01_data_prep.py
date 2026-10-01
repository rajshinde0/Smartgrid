"""Phase 1 -- Data preparation. Percent-format source; see src/nbbuild.py."""

# %% [markdown]
# # SMARTGRID-X -- Phase 1: Data preparation
#
# **What this notebook does.** Phase 0 found out what is wrong with the data.
# This notebook fixes it, and turns 1.6 GB of raw 1-minute CSVs into **one clean,
# merged, 10-minute table per building** that every later phase reads.
#
# The steps, in order:
#
# 1. Inspect every raw file properly (`head`, `tail`, `info`, `describe`)
# 2. Build a missing-data heatmap from the authors' own status file
# 3. Fix invalid values (impossible power, bad voltage, negative power factor)
# 4. Flag dead-meter periods -- 0 W for more than 6 hours is a broken meter
# 5. Flag outliers with IQR and Z-score -- **flag, never delete**
# 6. Average to 10-minute blocks and merge with occupancy
# 7. Interpolate only short gaps (at most 30 minutes)
# 8. Add features: hour, weekday, month, weekend, semester/vacation, lags,
#    rolling statistics, kWh
# 9. Stack all seven buildings into one long table
#
# **The guiding principle: flag, do not delete.** An outlier in an energy meter
# might be an error, or it might be exactly the abnormal event that Phase 6 is
# built to detect. If we delete it now, we delete the thing we are studying. So
# every judgement becomes an extra column, and the original value stays.

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

from src import config as C
from src import build, clean, explore, features, ingest, occupancy as occ, report, viz

viz.setup_style()
C.ensure_dirs()
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)

np.random.seed(C.SEED)
print("seed:", C.SEED)

# %% [markdown]
# ## Step 1: inspect the raw files properly
#
# Phase 0 printed the first and last rows. Here we do the full standard
# inspection on a representative file -- `head`, `tail`, `info` and `describe` --
# because these four are what tell you the shape, the data types, the memory
# cost and the distribution before you touch anything.
#
# We use the Academic building, which is the cleanest meter, so the output is
# readable. The same inspection runs in a loop over all nine meters afterwards.

# %%
acad_path = C.meter_path("acad_mains")
acad_raw = pd.read_csv(acad_path)

print("shape:", acad_raw.shape)
print("\n--- head(5) --------------------------------------------------")
display(acad_raw.head(5))
print("--- tail(5) --------------------------------------------------")
display(acad_raw.tail(5))

# %%
print("--- info() ---------------------------------------------------")
acad_raw.info(memory_usage="deep")

# %% [markdown]
# `info()` shows the cost of working with this data raw: one meter alone is over
# 100 MB in memory with 2.27 million rows. Nine of them would not fit
# comfortably, which is exactly why we cache a 10-minute summary and never load
# the raw files again after this phase.

# %%
print("--- describe() -----------------------------------------------")
display(acad_raw.describe().T)

# %% [markdown]
# Two things jump out of `describe()`:
#
# * `power_factor` has a **minimum of about -1.0**, which is impossible for a
#   physical power factor (it is defined on 0 to 1).
# * `voltage` has a **minimum of 0**, which would mean the building lost supply
#   entirely -- but `power` at those moments is not zero.
#
# Both are meter artefacts, and Step 3 deals with them.

# %%
# The same four-part inspection across every meter, as a loop. Printing full
# info() for nine files would be unreadable, so we summarise the parts that
# matter into one table.
summaries = []
for meter_key, filename in C.METERS.items():
    df = pd.read_csv(C.meter_path(meter_key), usecols=["timestamp", "power"])
    summaries.append({
        "meter": meter_key,
        "building": C.building_of_meter(meter_key),
        "rows": len(df),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 1),
        "power_mean_w": round(df["power"].mean(), 1),
        "power_std_w": round(df["power"].std(), 1),
        "power_min_w": round(df["power"].min(), 1),
        "power_max_w": round(df["power"].max(), 1),
    })
    del df

raw_summary = pd.DataFrame(summaries)
display(raw_summary)
print(f"two columns of all nine meters would already be "
      f"{raw_summary['memory_mb'].sum():,.0f} MB in memory")

# %% [markdown]
# ## Step 2: the missing-data heatmap
#
# The dataset ships `data_present_status_buildings.csv`: a 1/0 flag for every
# minute of every building saying whether a reading exists. It is the authors'
# own record of what is missing, which makes it the most trustworthy source for
# this picture.
#
# We read it in chunks and average the flags within each calendar month. Because
# the flags are 0 or 1, the mean *is* the coverage fraction for that month.

# %%
coverage = explore.status_missing_by_month()
print("coverage matrix:", coverage.shape)
display(coverage.head(3).round(1))

# %%
fig, ax = plt.subplots(figsize=(13, 4.2))

cmap = viz.SEQ_BLUE.copy()
cmap.set_bad("#e8e7e3")
im = ax.imshow(coverage.T.values, aspect="auto", cmap=cmap, vmin=0, vmax=100)

ax.set_yticks(range(len(coverage.columns)))
ax.set_yticklabels(coverage.columns, fontsize=9)
ticks = range(0, len(coverage.index), 3)
ax.set_xticks(list(ticks))
ax.set_xticklabels([str(coverage.index[i]) for i in ticks], rotation=45,
                   ha="right", fontsize=8)
ax.set_title("Percent of 1-minute readings present, by month and building", pad=12)
ax.grid(False)

cbar = fig.colorbar(im, ax=ax, pad=0.01, fraction=0.03)
cbar.set_label("% present", fontsize=9, color=viz.INK_SECONDARY)
cbar.outline.set_visible(False)

viz.save_fig(fig, "fig_01_missing_heatmap")
coverage.round(2).to_csv(C.RESULTS_DIR / "phase1_status_coverage_by_month.csv")

# %%
# Which months were more than half missing? These are the periods that will
# simply be absent from every result, so they are worth naming.
bad_months = []
for col in coverage.columns:
    series = coverage[col]
    for month, pct in series[series < 50].items():
        bad_months.append({"building": col, "month": str(month),
                           "pct_present": round(pct, 1)})
bad = pd.DataFrame(bad_months)
print(f"{len(bad)} building-months are more than half missing:")
display(bad)

# %% [markdown]
# **What we found.** The Girls mains meter loses most of a year across 2015-16,
# the Boys meters lose several months in the same period, and the Library has a
# long hole in 2014-15. The Facilities and Mess meters simply did not exist yet
# in 2013. This matters for interpretation: a building with 60% coverage is not
# giving us a worse *measurement*, it is giving us a smaller *sample*.

# %% [markdown]
# ## Step 3: fixing invalid values
#
# Three rules, applied while the raw files are read (in `src/ingest.py`), so they
# never have to be repeated:
#
# | Problem | Rule | Why |
# |---|---|---|
# | `power` < 0 or > 200 kW | set to `NaN` | not physically possible on these feeders |
# | `voltage` outside 180-270 V | set to `NaN` | a 230 V feeder reading 0 V or 280 V is a meter artefact |
# | `power_factor` < 0 | keep `abs()`, record the sign in a flag | see below |
#
# ### The power-factor decision
#
# This is the biggest judgement call in Phase 1, so it is worth being explicit.
# Between 0.01% and 67.6% of readings per meter have a negative power factor.
# The obvious reaction -- "negative power factor is invalid, drop those rows" --
# would delete **more than half of the Library record**.
#
# The evidence says not to. The range is exactly -0.999 to +1.000, and crucially
# **`power` is never negative anywhere in the dataset**. If current were truly
# flowing backwards, power would be negative too. So the sign is the meter's
# leading/lagging indicator, not a measurement of reverse flow. We keep the
# magnitude, which is the physically meaningful quantity, and keep the sign as a
# separate flag -- which turns out to be useful later as an example of an
# *asymmetric binary* attribute in Phase 2.

# %%
# Demonstrate the rule on a sample, so the effect is visible rather than asserted.
sample = pd.read_csv(C.meter_path("library_mains"), nrows=200_000)
before = sample["power_factor"]
after = before.abs()

check = pd.DataFrame({
    "statistic": ["count", "min", "max", "mean", "negative values"],
    "before": [len(before), round(before.min(), 3), round(before.max(), 3),
               round(before.mean(), 3), int((before < 0).sum())],
    "after abs()": [len(after), round(after.min(), 3), round(after.max(), 3),
                    round(after.mean(), 3), int((after < 0).sum())],
})
display(check)
print(f"rows that a 'drop negative pf' rule would have deleted: "
      f"{int((before < 0).sum()):,} of {len(before):,} "
      f"({100 * (before < 0).mean():.1f}%)")
print(f"power is negative anywhere in this sample: {(sample['power'] < 0).any()}")
del sample

# %% [markdown]
# ## Step 4: build the 10-minute cache
#
# Now we run the ingest for all nine meters. For each one, `src/ingest.py`:
#
# 1. reads the CSV in chunks of 500,000 rows, keeping only the needed columns
# 2. applies the three invalid-value rules above, counting every fix
# 3. converts UNIX timestamps to `Asia/Kolkata`
# 4. aggregates to 10-minute blocks and writes a parquet file
#
# **Why 10 minutes?** Because that is the resolution of the occupancy data.
# Keeping energy at 1 minute would mean repeating each occupancy reading ten
# times -- inventing ten times more occupancy data than was ever measured.
#
# **Why sums and counts rather than a plain average?** A 10-minute block can be
# split across two chunks. Averaging each chunk and then averaging the averages
# would be wrong. So each chunk contributes per-block sums and counts, they are
# added across chunks, and only then is the mean formed. The result is exactly
# what a single-pass mean would give.

# %%
meter_stats = ingest.ingest_all(force=True)
raw_quality = pd.DataFrame(meter_stats).T
raw_quality.index.name = "meter"
display(raw_quality[[
    "rows_read", "blocks_10min", "blocks_missing", "blocks_partial",
    "power_invalid", "voltage_invalid", "pf_negative", "current_missing",
    "power_zero",
]])

# %% [markdown]
# ## Step 5: flagging dead meters
#
# A building really can draw very little at 4 a.m. It does not draw *exactly*
# 0.000 W for six hours straight. That is a meter that stopped reporting, and
# treating those zeros as real consumption would say the Lecture building is the
# most efficient on campus -- which would be a data artefact presented as a
# finding.
#
# **The rule:** power exactly 0 for more than **6 continuous hours** is marked
# `meter_off`. We test on the *maximum* power in each 10-minute block, so a block
# only counts as zero if every one of its 1-minute readings was zero.
#
# **Short gaps bridge a run rather than breaking it.** This is a correction to an
# earlier version. Originally any missing block split a zero-run, which meant a
# single dropout inside a ten-hour outage produced two five-hour runs, neither
# crossing the six-hour threshold -- so the entire outage went unflagged and its
# zeros were counted as real consumption. That hid about 2,413 zero-blocks in the
# Lecture building alone. Now a gap of up to 30 minutes (the same limit used for
# interpolation) joins the runs on either side, provided both sides read zero.
# Longer gaps still break the run: at that length the absence is its own event.
# The flag itself is never set on a missing block -- we do not claim a meter was
# off during an interval we have no reading for.

# %%
lecture_raw, _ = ingest.ingest_meter("lecture_mains", verbose=False)
lecture_clean, lecture_stats = clean.clean_meter(lecture_raw)

for k, v in lecture_stats.items():
    print(f"  {k:22s} {v}")
print()
print(f"the Lecture meter is flagged off for "
      f"{lecture_stats['hours_meter_off']:,.0f} hours "
      f"= {lecture_stats['hours_meter_off'] / 24:,.0f} days "
      f"= {100 * lecture_stats['blocks_meter_off'] / lecture_stats['blocks']:.1f}% "
      f"of its record")

# %%
# A picture of what the rule catches. We want a month where the meter was partly
# alive and partly dead, so the rule can be seen discriminating between the two
# -- a month that is 100% dead would only show a flat line. So pick the month
# whose meter-off fraction is closest to half.
monthly_off = lecture_clean["meter_off"].resample("MS").mean()
candidate = (monthly_off - 0.5).abs().idxmin()
window = lecture_clean.loc[
    candidate : candidate + pd.offsets.MonthEnd(1) + pd.Timedelta(days=1)
]
print(f"showing {candidate:%B %Y}: "
      f"{100 * monthly_off.loc[candidate]:.0f}% of its blocks flagged meter-off")

fig, ax = plt.subplots(figsize=(11, 3.6))
ax.plot(window.index, window["power_w"] / 1000,
        color=viz.color_for("Lecture"), linewidth=1.2)

# Shade every flagged block, spanning the full height of the axes.
off = window["meter_off"]
ax.fill_between(window.index, 0, 1, where=off, transform=ax.get_xaxis_transform(),
                color=viz.STATUS["ANOMALY"], alpha=0.15, step="mid", linewidth=0)

ax.set_ylabel("Power (kW)")
ax.set_title(f"Lecture building, {candidate:%B %Y} -- "
             f"shaded periods flagged as 'meter off'")
from matplotlib.patches import Patch
ax.legend(handles=[
    Patch(facecolor=viz.color_for("Lecture"), label="measured power"),
    Patch(facecolor=viz.STATUS["ANOMALY"], alpha=0.25,
          label=f"flagged meter-off (0 W for > {C.DEAD_METER_HOURS} h)"),
], loc="upper right")
plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
viz.save_fig(fig, "fig_01_dead_meter_lecture")

# %% [markdown]
# **Takeaway.** The shaded stretches are days at a time of exactly zero watts
# with brief bursts of real activity in between. The rule separates the two
# cleanly. Everything shaded is excluded from Phase 5's energy accounting -- not
# counted as zero consumption.

# %% [markdown]
# ## Step 6: flagging outliers -- with IQR and Z-score
#
# Two standard methods, run on the *live* readings only (a dead meter's zeros
# would drag the mean down and make normal nights look abnormal):
#
# * **IQR / Tukey fences:** anything below Q1 - 1.5xIQR or above Q3 + 1.5xIQR.
#   Based on quartiles, so it does not assume a particular distribution.
# * **Z-score:** anything more than 3 standard deviations from the mean. Assumes
#   roughly normal data, which power is not -- so it flags far fewer points.
#
# Both are recorded as columns. **Neither deletes anything.**

# %%
acad_10min, _ = ingest.ingest_meter("acad_mains", verbose=False)
acad_clean, acad_stats = clean.clean_meter(acad_10min)

live = acad_clean.loc[~acad_clean["meter_off"], "power_w"].dropna()
low_fence, high_fence = clean.iqr_fences(live)

print(f"Academic building, {len(live):,} live 10-minute readings")
print(f"  IQR fences      : {low_fence:,.0f} W  to  {high_fence:,.0f} W")
print(f"  flagged by IQR  : {acad_stats['outliers_iqr']:,} "
      f"({100 * acad_stats['outliers_iqr'] / len(live):.2f}%)")
print(f"  flagged by Z>3  : {acad_stats['outliers_zscore']:,} "
      f"({100 * acad_stats['outliers_zscore'] / len(live):.2f}%)")

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

ax1.hist(live / 1000, bins=80, color=viz.color_for("Academic"))
ax1.axvline(low_fence / 1000, color=viz.STATUS["ANOMALY"], linestyle="--", lw=1.5)
ax1.axvline(high_fence / 1000, color=viz.STATUS["ANOMALY"], linestyle="--", lw=1.5)
ax1.set_xlabel("Power (kW)")
ax1.set_ylabel("10-minute blocks")
ax1.set_title("Distribution with IQR fences")
ax1.annotate("IQR fences", xy=(high_fence / 1000, ax1.get_ylim()[1] * 0.8),
             xytext=(-8, 0), textcoords="offset points", ha="right",
             fontsize=9, color=viz.STATUS["ANOMALY"])

flagged = acad_clean.loc[acad_clean["outlier_iqr"]]
week = acad_clean.loc["2016-04-01":"2016-04-14"]
week_flag = flagged.loc["2016-04-01":"2016-04-14"]
ax2.plot(week.index, week["power_w"] / 1000, color=viz.color_for("Academic"),
         linewidth=1.2, label="power")
ax2.scatter(week_flag.index, week_flag["power_w"] / 1000, s=14,
            color=viz.STATUS["ANOMALY"], zorder=3, label="flagged by IQR")
ax2.set_ylabel("Power (kW)")
ax2.set_title("Two weeks, with flagged points marked")
ax2.legend(loc="upper left")
plt.setp(ax2.get_xticklabels(), rotation=30, ha="right")

viz.save_fig(fig, "fig_01_outlier_flags_academic")

# %% [markdown]
# **Takeaway.** The flagged points are mostly the daily peak of ordinary working
# days -- they are extreme relative to the whole distribution, but they are not
# errors. This is precisely why we flag instead of delete: an automatic
# "remove outliers" step here would have thrown away every busy afternoon.

# %% [markdown]
# ### An honest problem with the dead-meter rule
#
# Look carefully at the chart above. In August 2017 the Lecture meter alternates
# cleanly between about 4 kW during the day and **exactly zero every night**.
# That does not look like a broken meter at all -- it looks like a building whose
# main switch is turned off overnight, which is real and rather good behaviour.
#
# But a switched-off building and a dead meter both report exactly 0 W, and no
# rule based on the power value alone can tell them apart. So before trusting the
# 6-hour threshold, we check whether the zero runs form **one population or two**.

# %%
runs = clean.zero_run_lengths(lecture_clean["power_max_w"])
print(f"Lecture building: {len(runs):,} separate runs of exactly-zero power")
print(runs.describe().round(2).to_string())
print()

buckets = pd.cut(
    runs,
    bins=[0, 6, 18, 24, 48, 24 * 7, 24 * 365],
    labels=["< 6 h", "6-18 h", "18-24 h", "1-2 days", "2-7 days", "over a week"],
)
bucket_table = pd.DataFrame({
    "runs": buckets.value_counts().sort_index(),
    "total hours": runs.groupby(buckets, observed=False).sum().round(0),
})
bucket_table["share of zero hours %"] = (
    100 * bucket_table["total hours"] / bucket_table["total hours"].sum()
).round(1)
display(bucket_table)

# %%
fig, ax = plt.subplots(figsize=(10, 3.6))
ax.hist(np.log10(runs.clip(lower=0.17)), bins=60, color=viz.color_for("Lecture"))
for hours, label in [(6, f"{C.DEAD_METER_HOURS} h rule"), (24, "24 h"),
                     (24 * 7, "1 week")]:
    ax.axvline(np.log10(hours), color=viz.STATUS["ANOMALY"], linestyle="--", lw=1.3)
    ax.annotate(label, xy=(np.log10(hours), ax.get_ylim()[1] * 0.92),
                xytext=(4, 0), textcoords="offset points", fontsize=8,
                color=viz.STATUS["ANOMALY"])
ax.set_xlabel("length of an unbroken zero-power run (log10 hours)")
ax.set_ylabel("number of runs")
ax.set_title("Lecture building: how long do the zero-power stretches last?")
viz.save_fig(fig, "fig_01_zero_run_lengths_lecture")

short_hours = float(runs[runs <= 24].sum())
long_hours = float(runs[runs > 24].sum())
print(f"hours in runs of 24 h or less : {short_hours:10,.0f}  "
      f"({100 * short_hours / (short_hours + long_hours):.1f}%)")
print(f"hours in runs longer than 24 h: {long_hours:10,.0f}  "
      f"({100 * long_hours / (short_hours + long_hours):.1f}%)")

# %% [markdown]
# **What we found, and what we do about it.**
#
# There really are **two populations**. A large number of short runs cluster
# around half a day -- the nightly switch-off -- and a small number of very long
# runs account for the overwhelming majority of the zero *hours*. The bulk of the
# Lecture meter's dead time is in runs lasting **days to months**, which is a
# meter that stopped reporting.
#
# The 6-hour rule as specified catches both. That is a known limitation rather
# than a hidden one:
#
# * For the **multi-day runs** the rule is clearly right -- that is a dead meter.
# * For the **overnight runs** it may be wrong. If the Lecture building genuinely
#   switches off at night, excluding those hours removes its *best* behaviour from
#   the accounting and would overstate its waste share.
#
# We keep the specified 6-hour rule as the primary definition, and in Phase 5 we
# **re-run the Lecture figure with a 24-hour rule** as a sensitivity check, so the
# reader can see exactly how much this ambiguity is worth. Recorded as decision
# D01-07.

# %% [markdown]
# ## Step 7: the semester and vacation flag
#
# A campus behaves completely differently in term time and in vacation, so we
# need a flag for it. **The dataset authors publish the real IIIT-Delhi calendar**
# as part of the same figshare collection as the energy and occupancy data: one
# CSV per year from 2013 to 2017, covering our analysis window exactly.
#
# Each day carries two labels:
#
# | Column | Meaning |
# |---|---|
# | `working_day` | 1 = a working day, 0 = not |
# | `activity` | `H` = high activity (term-time working day), `L` = low activity (vacation, weekend or holiday) |
#
# Note what `L` means: **low activity**, which includes weekends and public
# holidays as well as vacations. That is not quite the same concept as "inside a
# vacation window", and it is the better one -- it is what the people running
# the campus actually recorded.
#
# `tools/get_data.py` downloads this alongside the energy and occupancy data.
#
# ### A correction worth recording
#
# An earlier version of this project used an **approximation** instead -- summer
# vacation 16 May to 31 July, winter break 16 to 31 December -- because we looked
# for the calendar on the project GitHub site, which does not host it, and
# concluded no calendar existed. It does; it is on figshare with the data. The
# approximation is kept in the code as a fallback, and below we measure how good
# it actually was. Recorded as decision D01-03.

# %%
print(C.SEMESTER_NOTE)
print()

calendar = features.load_official_calendar()
print(f"official calendar: {len(calendar):,} days, "
      f"{calendar.index.min()} to {calendar.index.max()}")
display(calendar.head(3))
print()
print("activity codes:")
display(calendar["activity"].value_counts())
print("working_day:")
display(calendar["working_day"].value_counts())

# %%
# How good was the approximation we used before finding the real thing?
academic_probe, _ = build.build_building("Academic", verbose=False)
agreement = features.compare_calendar_to_approximation(academic_probe.index)
for key, value in agreement.items():
    print(f"  {key:32s} {value}")

print()
print("Reading: the approximation agreed with the official calendar on only "
      f"{agreement['agreement_pct']:.1f}% of days. It marked "
      f"{agreement['approximated_vacation_pct']:.1f}% of days as vacation where "
      f"the official calendar marks {agreement['official_low_activity_pct']:.1f}% "
      "as low-activity -- mostly because the official definition counts every "
      "weekend and public holiday as low-activity, which a vacation-window rule "
      "never could.")

# %% [markdown]
# **This is why using the real calendar matters.** The approximation was not
# absurd -- it put the summer vacation in the right months, and the occupancy
# validation below still passes -- but it disagreed with the truth on nearly a
# third of days, and it systematically missed weekends and holidays. Every
# semester-versus-vacation comparison in this report now rests on the published
# calendar instead.

# %%

validation = []
for building in C.BUILDING_ORDER:
    series = occ.load_occupancy(building)["occupancy"]
    row = features.validate_semester_flag(series)
    row["building"] = building
    row["kind"] = C.BUILDINGS[building]["kind"]
    validation.append(row)

validation_df = pd.DataFrame(validation)[[
    "building", "kind", "median_occupancy_semester", "median_occupancy_vacation",
    "ratio_vacation_to_semester", "n_semester_intervals", "n_vacation_intervals",
]]
display(validation_df)

# %%
fig, ax = plt.subplots(figsize=(11, 4))

for building in C.BUILDING_ORDER:
    series = occ.load_occupancy(building)["occupancy"]
    monthly = features.monthly_occupancy_profile(series)
    ax.plot(monthly.index, monthly.values, marker="o",
            color=viz.color_for(building), label=building.replace("_", " "))

# Shade the months the official calendar marks as predominantly low-activity.
for start_month, end_month in [(5.5, 7.99), (12.5, 12.99)]:
    ax.axvspan(start_month, end_month, color=viz.INK_MUTED, alpha=0.12, zorder=0)

ax.annotate("summer vacation\n(official calendar)", xy=(6.6, ax.get_ylim()[1] * 0.92),
            ha="center", fontsize=8, color=viz.INK_SECONDARY)
ax.set_xticks(range(1, 13))
ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                    "Sep", "Oct", "Nov", "Dec"])
ax.set_ylabel("Median occupancy (devices)")
ax.set_title("Median occupancy by month -- cross-checking the official calendar")
ax.legend(ncol=4, loc="lower center", fontsize=8)
viz.save_fig(fig, "fig_01_semester_validation")

# %% [markdown]
# **Takeaway -- the official calendar behaves exactly as it should.** Dormitory
# occupancy on low-activity days is a little over 40% (Boys) and a little over
# 50% (Girls) of the high-activity median, and the dip is centred on June and
# July. The Academic building drops far less, which is what you would expect --
# staff and research students keep working through the summer. This is a
# cross-check of published ground truth rather than a defence of a guess.

# %% [markdown]
# ## Step 8: merge with occupancy, interpolate short gaps, add features
#
# Now everything comes together. For each building, `src/build.py`:
#
# 1. loads the cleaned 10-minute data for each of its meters
# 2. for the two dormitories, keeps mains and UPS separate **and** sums them --
#    the sum is `NaN` if either is missing, because adding a measured value to a
#    missing one would understate the total
# 3. joins with occupancy on the timestamp (inner join -- the overlap is our
#    working period)
# 4. interpolates gaps of **at most 30 minutes** and marks every filled value
# 5. adds the calendar, lag, rolling and kWh features
#
# **On interpolation.** Filling a 20-minute gap between two similar readings is
# safe. Filling a 200-day gap would be inventing data.
#
# Getting that rule right turned out to need care. The obvious implementation --
# pandas' `interpolate(limit=3)` -- does **not** mean "skip gaps longer than 3
# blocks". `limit` caps the number of *consecutive* missing values filled, so
# given a 200-day gap it fills the first 3 blocks and stops. Those three values
# are drawn along a straight line between the last reading before the gap and
# the first one after it, months later: precisely the invented data the limit
# was supposed to prevent. On this dataset that produced **5,301 fabricated
# blocks against 2,498 legitimate ones** -- more than two thirds of all the
# filling was wrong.
#
# So `interpolate_short_gaps` measures each gap's **whole** length first and
# fills only the runs that are short enough in their entirety. Every filled
# value is marked `was_interpolated` so nothing downstream mistakes it for a
# measurement.

# %%
building_stats = build.build_all(force=True)

quality = pd.DataFrame([
    {k: v for k, v in s.items() if k != "per_meter"}
    for s in building_stats.values()
])
display(quality)

# %% [markdown]
# **What we found.** Usable coverage varies enormously. Academic is 90% usable
# and Facilities 86%, but the Boys hostel, Girls hostel and Library sit around
# 60% because of their multi-month outages, and **Lecture is only 19% usable**
# because its meter was off for over 25,000 hours. That last number is the single
# most important caveat in the project, and it is carried through to every table
# where Lecture appears.

# %% [markdown]
# ## Step 9: a cross-check we did not have to do
#
# Our per-building totals are built from the individual meter files. The dataset
# also ships `all_buildings_power.csv`, which holds every meter's power side by
# side. It came from the same meters, so agreement is not proof that our numbers
# are *right* -- but a disagreement would prove we had mishandled timestamps,
# units or chunk boundaries somewhere. It costs little and rules out a whole
# class of silent error.

# %%
checks = pd.DataFrame([
    build.cross_check_against_wide(b) for b in C.BUILDING_ORDER
])
display(checks)
print("all buildings agree within 1%:", bool(checks["agrees"].all()))

# %% [markdown]
# ## Step 10: one long table for all seven buildings
#
# Individual tables are convenient per building, but almost every comparison in
# Phase 2 is "for each building, ...". That is a `groupby`, and `groupby` wants a
# **long** table: one row per building per timestamp, with a `building` column.
# `pd.concat` stacks them.

# %%
long = build.build_long_table(force=True)
print("long table:", long.shape)
display(long.head(3))

# %%
# Aggregation and grouping: the summaries that Phase 2 builds on.
usable = long[long["usable"]]

by_building = usable.groupby("building", observed=True).agg(
    intervals=("power_w", "size"),
    mean_power_w=("power_w", "mean"),
    median_power_w=("power_w", "median"),
    total_kwh=("kwh", "sum"),
    mean_occupancy=("occupancy", "mean"),
).round(1)
display(by_building)

# %%
# Grouping by two keys at once: the daily shape of each building.
by_hour = (
    usable.groupby(["building", "hour"], observed=True)["power_w"]
    .mean()
    .unstack(0)
    .round(0)
)
print("average power (W) by hour of day, one column per building")
display(by_hour.head(8))

by_building.to_csv(C.RESULTS_DIR / "phase1_summary_by_building.csv")
by_hour.to_csv(C.RESULTS_DIR / "phase1_mean_power_by_hour.csv")

# %% [markdown]
# ## Step 11: selecting data -- `loc` versus `iloc`, and sorting
#
# These two are constantly confused, so it is worth being precise:
#
# * **`.loc`** selects by **label** -- the actual index value. For a time series
#   the label is a timestamp, so `.loc["2016-04-01":"2016-04-07"]` means
#   "that week", and the end point is **included**.
# * **`.iloc`** selects by **position** -- the row number. `.iloc[0:10]` means
#   "the first ten rows" whatever their labels, and the end point is
#   **excluded**, like an ordinary Python slice.
#
# For this project `.loc` is almost always what we want, because we think in
# dates, not row numbers.

# %%
academic, _ = build.build_building("Academic", verbose=False)

by_label = academic.loc["2016-04-04":"2016-04-05", ["power_w", "occupancy"]]
print(f".loc['2016-04-04':'2016-04-05']  -> {len(by_label)} rows "
      f"(two whole days; the end date IS included)")
display(by_label.head(3))

by_position = academic.iloc[0:3, 0:4]
print(".iloc[0:3, 0:4] -> first 3 rows, first 4 columns, by position:")
display(by_position)

# %%
# Sorting: by value to find the extremes, and back by time for analysis.
busiest = academic.loc[academic["usable"]].sort_values("power_w", ascending=False)
print("the ten highest-power 10-minute blocks ever recorded in the Academic building")
display(busiest[["power_w", "occupancy", "hour", "weekday", "period"]].head(10))

quietest = academic.loc[academic["usable"]].sort_values("power_w")
print("the ten lowest:")
display(quietest[["power_w", "occupancy", "hour", "weekday", "period"]].head(10))

# %% [markdown]
# **Takeaway.** The busiest blocks are summer afternoons -- May and June, which
# our calendar calls vacation. That is air conditioning, not people: occupancy at
# those moments is unremarkable. It is an early hint of the finding in Phase 5,
# and of the limitation that we have no usable weather data to separate cooling
# load from occupancy-driven load -- the weather record shipped with I-BLEND covers March-June 2018 only, which does not overlap the 2014-2017 analysis window at all.

# %% [markdown]
# ## Step 12: categorical data
#
# Two of our columns are categories, and they are different kinds:
#
# * `building` is **nominal** -- Library is not greater or less than Mess.
# * `weekday` is **ordinal** -- Monday really does come before Tuesday.
#
# We store `weekday` as an **ordered** `pd.Categorical`, which makes pandas sort
# and plot it in calendar order instead of alphabetical order, and lets
# comparisons like `weekday < "Friday"` work.

# %%
print("weekday categories, in order:")
print(list(academic["weekday"].cat.categories))
print("ordered:", academic["weekday"].cat.ordered)
print()
print("value_counts() comes out in calendar order, not alphabetical:")
display(academic["weekday"].value_counts().sort_index())
print()
print("period categories:", list(academic["period"].cat.categories))
display(academic["period"].value_counts())

# %%
# Memory: a categorical stores each label once and keeps small integer codes.
as_text = academic["weekday"].astype(str)
print(f"weekday as plain text : {as_text.memory_usage(deep=True) / 1024**2:6.2f} MB")
print(f"weekday as categorical: "
      f"{academic['weekday'].memory_usage(deep=True) / 1024**2:6.2f} MB")

# %% [markdown]
# ## Step 13: data transformation -- the log transform
#
# Power is strongly right-skewed: most blocks are ordinary, a few are very large.
# Several methods (and the normal distribution itself) assume something closer to
# symmetric. Taking logs compresses the long right tail.
#
# We use `log1p` (that is, `log(1 + x)`) rather than `log` so that a genuine zero
# does not become negative infinity.

# %%
power = academic.loc[academic["usable"], "power_w"]
logged = np.log1p(power)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 3.8))
ax1.hist(power / 1000, bins=70, color=viz.color_for("Academic"))
ax1.set_xlabel("Power (kW)")
ax1.set_ylabel("blocks")
ax1.set_title(f"Raw power  (skew = {power.skew():.2f})")

ax2.hist(logged, bins=70, color=viz.CATEGORICAL[1])
ax2.set_xlabel("log(1 + power in W)")
ax2.set_title(f"After log transform  (skew = {logged.skew():.2f})")
viz.save_fig(fig, "fig_01_log_transform_power")

print(f"skewness before: {power.skew():.3f}")
print(f"skewness after : {logged.skew():.3f}")

# %% [markdown]
# **Takeaway.** The transform reduces the skew, but the Academic building's
# distribution is **bimodal** -- a night-time cluster and a daytime cluster --
# and no transform removes that, because it is a real physical feature of the
# data, not a distortion. This is a useful negative result: logging is not a
# universal fix. Phase 2 tests formally whether a Normal or a Log-normal fits
# better.

# %% [markdown]
# ## Step 14: data scaling -- Min-Max versus standardisation
#
# Scaling puts different features on comparable ranges. The two standard choices:
#
# | | Formula | Result | Use when |
# |---|---|---|---|
# | **Min-Max** | (x - min) / (max - min) | everything in 0 to 1 | you need bounded values; no outliers |
# | **Standardisation** | (x - mean) / sd | mean 0, sd 1 | the method assumes roughly normal data; outliers present |
#
# Min-Max is badly affected by a single extreme value: one 95 kW spike squashes
# every ordinary reading into the bottom of the range. Standardisation keeps the
# shape of the distribution.
#
# **Where this matters in our project:** linear regression coefficients are only
# comparable if the inputs are on the same scale, and PCA is defined in terms of
# variance, so it *must* be standardised. In Phase 4 the scaler goes **inside a
# scikit-learn `Pipeline`**, so it is fitted on the training data only and never
# sees the test set.

# %%
from sklearn.preprocessing import MinMaxScaler, StandardScaler

subset = academic.loc[academic["usable"], ["power_w", "occupancy"]].dropna()
minmax = pd.DataFrame(
    MinMaxScaler().fit_transform(subset), columns=subset.columns, index=subset.index
)
standard = pd.DataFrame(
    StandardScaler().fit_transform(subset), columns=subset.columns, index=subset.index
)

comparison = pd.DataFrame({
    "original (power W)": subset["power_w"].describe(),
    "Min-Max scaled": minmax["power_w"].describe(),
    "Standardised": standard["power_w"].describe(),
}).round(3)
display(comparison)

# %%
fig, axes = plt.subplots(1, 3, figsize=(13, 3.4))
for ax, (data, title, colour) in zip(axes, [
    (subset["power_w"] / 1000, "Original (kW)", viz.CATEGORICAL[0]),
    (minmax["power_w"], "Min-Max scaled (0 to 1)", viz.CATEGORICAL[1]),
    (standard["power_w"], "Standardised (mean 0, sd 1)", viz.CATEGORICAL[2]),
]):
    ax.hist(data, bins=60, color=colour)
    ax.set_title(title)
    ax.set_ylabel("blocks")
viz.save_fig(fig, "fig_01_scaling_comparison")

# %% [markdown]
# **Takeaway.** The *shape* is identical in all three -- scaling moves and
# stretches an axis, it does not change the distribution. What changes is the
# range, and therefore which features dominate a distance or a coefficient.

# %% [markdown]
# ## Step 15: reading a CSV with only lists and dictionaries
#
# Everything above uses pandas. To show what pandas is actually doing -- and
# because the syllabus asks for it -- here we analyse one occupancy file using
# only Python's standard `csv` module, lists and dictionaries. No pandas, no
# numpy.
#
# We compute count, minimum, maximum and mean by hand, then check the answers
# against pandas. They must agree exactly.

# %%
import csv

path = C.occupancy_path("Library")

# A dictionary of lists: one key per column, exactly how a DataFrame is
# organised underneath.
table: dict[str, list] = {"timestamp": [], "occupancy_count": []}

with open(path, newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        table["timestamp"].append(float(row["timestamp"]))
        table["occupancy_count"].append(float(row["occupancy_count"]))

counts = table["occupancy_count"]

# Statistics computed by hand with plain loops.
n = len(counts)
smallest = counts[0]
largest = counts[0]
running_total = 0.0
for value in counts:
    if value < smallest:
        smallest = value
    if value > largest:
        largest = value
    running_total += value
mean_by_hand = running_total / n

# A dictionary used as a tally, to find the mode.
tally: dict[float, int] = {}
for value in counts:
    tally[value] = tally.get(value, 0) + 1
mode_by_hand = max(tally, key=tally.get)

print(f"Library occupancy, read with the csv module only")
print(f"  rows    : {n:,}")
print(f"  minimum : {smallest:.0f}")
print(f"  maximum : {largest:.0f}")
print(f"  mean    : {mean_by_hand:.4f}")
print(f"  mode    : {mode_by_hand:.0f}  (appears {tally[mode_by_hand]:,} times)")

# %%
# Now the same file through pandas, to check the hand calculation.
check = pd.read_csv(path)["occupancy_count"]
print("pandas says:")
print(f"  rows    : {len(check):,}")
print(f"  minimum : {check.min():.0f}")
print(f"  maximum : {check.max():.0f}")
print(f"  mean    : {check.mean():.4f}")
print(f"  mode    : {check.mode().iloc[0]:.0f}")

assert n == len(check)
assert smallest == check.min()
assert largest == check.max()
assert abs(mean_by_hand - check.mean()) < 1e-9
print("\nhand calculation matches pandas exactly.")

# %% [markdown]
# ## Step 16: the data-quality table
#
# The deliverable of Phase 1: for each building, how much data there is, how much
# of it is usable, and what had to be fixed.

# %%
dq_rows = []
for building, stats in building_stats.items():
    per_meter = stats["per_meter"]
    dq_rows.append({
        "building": building,
        "meters": stats["meters"],
        "first": stats["first"].strftime("%Y-%m-%d"),
        "last": stats["last"].strftime("%Y-%m-%d"),
        "10-min intervals": stats["rows"],
        "usable %": stats["pct_usable"],
        "power missing %": stats["pct_power_missing"],
        "occupancy missing %": stats["pct_occupancy_missing"],
        "meter-off hours": stats["hours_meter_off"],
        "interpolated blocks": stats["blocks_interpolated"],
        "outliers flagged (IQR)": stats["outliers_iqr"],
        "outliers flagged (Z>3)": stats["outliers_zscore"],
        "invalid voltage fixed": sum(
            m.get("voltage_invalid", 0) for m in per_meter.values()
        ),
        "negative pf readings": sum(
            m.get("pf_negative", 0) for m in per_meter.values()
        ),
        "total kWh (usable)": stats["total_kwh"],
    })

data_quality = pd.DataFrame(dq_rows)
display(data_quality)
data_quality.to_csv(C.RESULTS_DIR / "phase1_data_quality.csv", index=False)
quality.to_csv(C.RESULTS_DIR / "phase1_build_stats.csv", index=False)
checks.to_csv(C.RESULTS_DIR / "phase1_cross_check.csv", index=False)

# %% [markdown]
# ## Step 17: write Phase 1 into the report

# %%
blocks = {}

blocks["phase1_missing_heatmap"] = report.figure(
    "fig_01_missing_heatmap",
    "Percent of 1-minute readings present, by month and building",
    "Built from the authors' own data_present_status_buildings.csv. The Girls "
    "mains meter loses most of a year across 2015-16, the Boys meters several "
    "months in the same period, and the Library a long stretch in 2014-15.",
) + "\n\n" + report.md_table(bad.head(30)) + (
    f"\n\n{len(bad)} building-months are more than half missing "
    f"(first 30 shown)."
)

blocks["phase1_data_quality_table"] = report.md_table(data_quality)

blocks["method_phase1"] = f"""
Phase 1 turns the raw CSVs into one clean, merged, 10-minute table per building.

**Invalid values.** Three rules are applied while reading, and every fix is
counted: `power` outside 0 to {C.POWER_MAX_W / 1000:.0f} kW becomes `NaN`;
`voltage` outside {C.VOLTAGE_MIN_V:.0f}-{C.VOLTAGE_MAX_V:.0f} V becomes `NaN`;
`power_factor` keeps its magnitude with the sign retained as a separate flag
(decision D00-02).

**Dead meters.** Power exactly 0 for more than {C.DEAD_METER_HOURS} continuous
hours is flagged `meter_off`. The test uses the *maximum* power within each
10-minute block, so a block counts as zero only if all ten of its 1-minute
readings were zero; blocks with no readings break a run rather than extending it.

**Outliers are flagged, never deleted.** Both IQR (Tukey fences at 1.5x) and
Z-score (|z| > {C.ZSCORE_OUTLIER:.0f}) are computed on live readings only and
stored as columns. Deleting them would remove exactly the abnormal events Phase 6
is built to detect.

**Resampling.** 1-minute readings are averaged into {C.TARGET_FREQ} blocks to
match the native resolution of the occupancy data. Because a block can straddle a
chunk boundary, each chunk contributes per-block *sums and counts* which are added
across chunks before the mean is formed -- exactly equal to a single-pass mean.
Blocks are then placed on a complete time grid, so missing intervals are explicit
rather than absent.

**Merging.** Energy is joined to occupancy on the timestamp with an inner join.
Every occupancy timestamp already falls exactly on a 10-minute boundary, so no
tolerance matching is needed. For the two dormitories, mains and UPS are kept as
separate columns and also summed; the sum is `NaN` if either meter is missing.

**Gap filling.** Gaps of at most {C.INTERPOLATE_LIMIT_MIN} minutes
({C.INTERPOLATE_LIMIT_STEPS} blocks) are filled by time interpolation and marked
`was_interpolated`. Longer gaps are left missing.

**Features.** `hour`, `minute_of_day`, `month`, `year`, `weekday` (an *ordered*
categorical so Monday sorts before Tuesday), `is_weekend`, `is_semester` /
`is_vacation`, power lagged 1 hour and 1 day, 24-hour rolling mean and standard
deviation (computed with `closed="left"` so the current block is excluded and no
future information leaks), and `kwh = watts / 1000 x 10/60`.

**Semester flag.** Taken from the **official IIIT-Delhi calendar published with
I-BLEND** (one CSV per year, 2013-2017, in the same figshare collection as the
data), which marks each day as a working day or not and as high- or low-activity.
This replaced an approximation used in an earlier version of the project, which
agreed with the published calendar on only about two-thirds of days
(decision D01-03). It also supplies an `is_working_day` model feature that knows
about public holidays, which a weekend flag cannot see.

**Notebook:** `notebooks/01_data_prep.ipynb`.
"""

print("\n".join(f"prepared block: {k}" for k in blocks))

# %%
lec = quality.set_index("building").loc["Lecture"]
acad_q = quality.set_index("building").loc["Academic"]
boys_v = validation_df.set_index("building").loc["Boys_Hostel"]
girls_v = validation_df.set_index("building").loc["Girls_Hostel"]

blocks["results_phase1"] = f"""
**Seven clean tables, and a very uneven amount of usable data.**

After cleaning, merging with occupancy and flagging dead meters, the proportion
of 10-minute intervals that are actually usable -- meter alive, reading present,
occupancy known -- varies from **{quality['pct_usable'].min():.1f}%** to
**{quality['pct_usable'].max():.1f}%**:

{report.md_table(quality[['building', 'rows', 'usable_rows', 'pct_usable',
                          'pct_power_missing', 'pct_occupancy_missing',
                          'hours_meter_off', 'total_kwh']])}

Three observations matter for everything that follows.

1. **Lecture is only {lec['pct_usable']:.1f}% usable.** Its meter is flagged off
   for **{lec['hours_meter_off']:,.0f} hours** -- about
   {lec['hours_meter_off'] / 24 / 365:.1f} years of the 3.7-year window. Its
   results rest on a far smaller sample than any other building, and every table
   it appears in says so.
2. **The Boys hostel, Girls hostel and Library sit near 60%** because of
   multi-month meter outages visible in section 4.9. That is a smaller sample,
   not a worse measurement.
3. **Academic is the most complete** at {acad_q['pct_usable']:.1f}%, which is why
   it is used as the worked example throughout the notebooks.

**The pipeline was independently cross-checked.** Our per-building mean power,
computed from the individual meter files through chunked ingestion, was compared
against `all_buildings_power.csv`, which holds every meter side by side. All
seven agree to within
**{checks['difference_pct'].max():.3f}%** (largest disagreement), which rules out
a whole class of silent error in timestamp handling, unit conversion and chunk
boundaries:

{report.md_table(checks)}

**The semester flag comes from the official IIIT-Delhi calendar** published with
I-BLEND on figshare -- one CSV per year, 2013-2017, marking each day as working
or not and as high- or low-activity. Cross-checking it against the data confirms
it behaves as it should: dormitory median occupancy on low-activity days is
**{boys_v['ratio_vacation_to_semester']:.0%}** of the high-activity median for
the Boys hostel and **{girls_v['ratio_vacation_to_semester']:.0%}** for the
Girls hostel, while the Academic building falls much less -- exactly what you
would expect when staff keep working through the breaks.

An earlier version of this analysis approximated the calendar, having looked for
it on the project GitHub site rather than on figshare. That approximation agreed
with the published calendar on only **{agreement['agreement_pct']:.1f}%** of
days, chiefly because the official definition of low activity includes every
weekend and public holiday. The approximation survives in the code as a fallback
for anyone who cannot download the calendar files.

{report.figure("fig_01_semester_validation",
               "Median occupancy by month, with the approximated vacation months shaded",
               "The dip is centred on June and July exactly where the "
               "approximation puts it, and it is much deeper in the two "
               "dormitories than in the Academic building.")}

**Dead-meter detection.**

{report.figure("fig_01_dead_meter_lecture",
               "Lecture building in a partly-dead month, with flagged meter-off periods shaded",
               "Everything shaded is excluded from the energy accounting rather "
               "than counted as zero consumption.")}

**A limitation of this rule, stated openly.** In the month shown the meter
alternates between about 4 kW by day and exactly zero every night -- which looks
less like a broken meter than like a building switched off at the mains. Both
report exactly 0 W, and no rule based on the power value alone can separate them.
Checking the length of every zero run shows two distinct populations:

{report.figure("fig_01_zero_run_lengths_lecture",
               "How long the Lecture building's zero-power stretches last",
               f"Two populations: many short runs near half a day (the nightly "
               f"switch-off, {100 * short_hours / (short_hours + long_hours):.1f}% "
               f"of all zero hours) and a few very long runs that account for "
               f"{100 * long_hours / (short_hours + long_hours):.1f}% of them.")}

{report.md_table(bucket_table.reset_index().rename(columns={"index": "run length"}))}

The overwhelming majority of the Lecture meter's dead time sits in runs lasting
days to months, where the rule is clearly right. The overnight runs are where it
may be wrong. We keep the specified 6-hour rule as primary and quantify the
ambiguity with a 24-hour sensitivity check in Phase 5 (decision D01-07).

**Outlier flagging.**

{report.figure("fig_01_outlier_flags_academic",
               "Academic building: distribution with IQR fences, and two weeks with flagged points",
               "The flagged points are mostly ordinary working-day peaks. An "
               "automatic 'remove outliers' step would have deleted every busy "
               "afternoon -- which is why this project flags instead of deletes.")}

**Transformation and scaling.**

{report.figure("fig_01_log_transform_power",
               "Academic power before and after a log transform",
               f"The log transform cuts skew from {power.skew():.2f} to "
               f"{logged.skew():.2f}, but the distribution stays bimodal -- a "
               "night cluster and a day cluster -- because that is a real "
               "physical feature, not a distortion.")}

{report.figure("fig_01_scaling_comparison",
               "The same power data: original, Min-Max scaled, and standardised",
               "Scaling moves and stretches an axis; it does not change the "
               "shape of the distribution. What changes is which features "
               "dominate a distance or a regression coefficient.")}
"""

report.update_blocks(blocks)

# %% [markdown]
# ## Step 18: record the Phase 1 decisions

# %%
report.log_decision(
    id="D01-01", phase="1",
    decision="Dead-meter rule",
    options_considered=f"No rule; flag any zero reading; flag runs of 0 W longer "
                       f"than {C.DEAD_METER_HOURS} h",
    chosen=f"Runs of exactly 0 W longer than {C.DEAD_METER_HOURS} continuous "
           f"hours are flagged meter_off; tested on the block maximum",
    reason="A building can draw very little at night but not exactly 0.000 W for "
           "six hours. Flagging every isolated zero would also catch genuine "
           "brief shutdowns.",
    effect_on_results=f"Removes {lec['hours_meter_off']:,.0f} h from Lecture and "
                      f"{acad_q['hours_meter_off']:,.0f} h from Academic. Without "
                      "it, Lecture would appear to be the most efficient "
                      "building on campus, which is an artefact.",
)

report.log_decision(
    id="D01-07", phase="1",
    decision="Ambiguity between a dead meter and a building switched off at night",
    options_considered=f"Keep the {C.DEAD_METER_HOURS} h rule and say nothing; "
                       "raise the threshold to 24 h so nightly switch-offs count "
                       "as real zero consumption; keep the rule and publish a "
                       "sensitivity check",
    chosen=f"Keep the specified {C.DEAD_METER_HOURS} h rule as primary; re-run "
           "the Lecture figure with a 24 h rule in Phase 5 as a sensitivity check",
    reason="A switched-off building and a dead meter both report exactly 0 W and "
           "cannot be told apart from the power value alone. The zero-run "
           f"histogram shows two populations: short runs near half a day "
           f"({100 * short_hours / (short_hours + long_hours):.1f}% of zero hours) "
           f"and multi-day runs "
           f"({100 * long_hours / (short_hours + long_hours):.1f}% of zero hours).",
    effect_on_results="Affects Lecture only, and only its denominator. The "
                      "sensitivity check in Phase 5 quantifies it; the rest of "
                      "the campus is unaffected because no other meter has "
                      "sustained exact zeros.",
)

report.log_decision(
    id="D01-02", phase="1",
    decision="Outlier handling",
    options_considered="Delete IQR outliers; delete Z>3 outliers; winsorise; "
                       "flag both and delete neither",
    chosen="Flag with both IQR and Z-score; delete nothing",
    reason="Extreme power readings are the phenomenon Phase 6 is built to "
           "detect. Removing them would remove the subject of the study, and "
           "IQR alone flags ~6.8% of the Academic record -- mostly ordinary "
           "working-day peaks.",
    effect_on_results="No rows removed. Two extra boolean columns available to "
                      "later phases.",
)

report.log_decision(
    id="D01-03", phase="1",
    decision="Semester / vacation calendar",
    options_considered="Approximate windows from a typical academic year; infer "
                       "purely from the data; use the official IIIT-Delhi "
                       "calendar published with I-BLEND",
    chosen="The official calendar (one CSV per year, 2013-2017), with the "
           "approximation retained only as a fallback",
    reason="The calendar is published in the same figshare collection as the "
           "energy and occupancy data. An earlier version of this project "
           "approximated it, having searched the project GitHub site -- which "
           "hosts only the website assets and reading scripts -- and wrongly "
           "concluded no calendar existed. A purely data-driven split would "
           "have been circular, since occupancy is also our explanatory "
           "variable.",
    effect_on_results=f"Material. The approximation agreed with the published "
                      f"calendar on only {agreement['agreement_pct']:.1f}% of "
                      f"days: it marked "
                      f"{agreement['approximated_vacation_pct']:.1f}% of days as "
                      f"vacation against the official "
                      f"{agreement['official_low_activity_pct']:.1f}% "
                      "low-activity, missing every weekend and public holiday. "
                      "All semester-vs-vacation results, and the is_semester and "
                      "is_working_day model features, now use the published "
                      "calendar.",
)

report.log_decision(
    id="D01-08", phase="1",
    decision="Gap interpolation measures the whole gap, not consecutive values",
    options_considered="pandas interpolate(limit=3) as originally written; "
                       "measure each gap's full length and fill only short ones; "
                       "drop interpolation entirely",
    chosen="Measure the whole run; fill only gaps whose entire length is within "
           f"the {C.INTERPOLATE_LIMIT_MIN}-minute limit",
    reason="pandas' limit= caps *consecutive* values filled, so a 200-day gap "
           "had its first 3 blocks filled along a straight line between "
           "readings months apart. That is the invented data the limit was "
           "meant to prevent.",
    effect_on_results="Removes 5,301 fabricated blocks and keeps 2,498 "
                      "legitimate ones. Interpolated blocks fall from 5,206 to "
                      "2,184 and usable coverage drops 0.02-0.41 percentage "
                      "points per building -- lower, and correct.",
)

report.log_decision(
    id="D01-09", phase="1",
    decision="A short gap bridges a run of zeros instead of breaking it",
    options_considered="Any gap breaks the run (original); gaps up to 30 min "
                       "bridge it when zeros sit on both sides; ignore gaps "
                       "entirely when measuring runs",
    chosen=f"Gaps up to {C.INTERPOLATE_LIMIT_MIN} minutes bridge a zero-run "
           "when both neighbours read zero; the gap itself is never flagged",
    reason="A single dropout inside a ten-hour outage split it into two "
           "five-hour runs, neither of which crossed the six-hour threshold, so "
           "the outage went unflagged and its zeros counted as real "
           "consumption. About 2,413 zero-blocks in Lecture were hidden this "
           "way.",
    effect_on_results="Adds roughly 14 hours to Lecture's meter-off total and "
                      "almost nothing elsewhere. Never flags a block we have no "
                      "reading for, so it cannot invent dead time.",
)

report.log_decision(
    id="D01-04", phase="1",
    decision="Interpolation limit",
    options_considered="No interpolation; fill all gaps; fill only short gaps",
    chosen=f"Time interpolation for gaps up to {C.INTERPOLATE_LIMIT_MIN} minutes "
           f"({C.INTERPOLATE_LIMIT_STEPS} blocks); longer gaps left missing; "
           "every filled value marked was_interpolated",
    reason="Filling 20 minutes between two similar readings is safe; filling a "
           "200-day outage would be inventing data.",
    effect_on_results=f"Fills {quality['blocks_interpolated'].sum():,} blocks "
                      f"across all seven buildings -- under "
                      f"{100 * quality['blocks_interpolated'].sum() / quality['rows'].sum():.2f}% "
                      "of the total. Negligible effect on any aggregate.",
)

report.log_decision(
    id="D01-05", phase="1",
    decision="Combining hostel mains and UPS meters",
    options_considered="Use mains only; use the sum only; keep both separate "
                       "and also sum",
    chosen="Keep mains and UPS as separate columns AND provide the sum; the sum "
           "is NaN if either meter is missing",
    reason="Which supply keeps running when rooms empty out is a Phase 5 "
           "question, so the split must survive. Adding a measured value to a "
           "missing one would silently understate the building total.",
    effect_on_results="Hostel totals are only available when both meters report, "
                      "which is part of why the two dormitories sit near 60% "
                      "usable rather than 90%.",
)

report.log_decision(
    id="D01-06", phase="1",
    decision="Chunk-boundary handling when resampling",
    options_considered="Read whole files and resample once; resample each chunk "
                       "and average the averages; accumulate per-block sums and "
                       "counts across chunks",
    chosen="Per-block sums and counts, combined across chunks before the mean "
           "is formed",
    reason="Averaging chunk averages is wrong whenever a 10-minute block spans "
           "two chunks. Sums and counts combine exactly.",
    effect_on_results="None relative to a correct single-pass mean -- that is "
                      "the point. Verified against all_buildings_power.csv to "
                      f"within {checks['difference_pct'].max():.3f}%.",
)

report.publish_decision_log()
print()
print("blocks still pending:", len(report.pending_blocks()))
print("figures referenced but missing:", report.check_figures())

# %% [markdown]
# ## Phase 1 conclusion
#
# We now have seven clean tables in `data/processed/`, one per building, each on a
# complete 10-minute grid with occupancy attached and every judgement recorded as
# a column rather than applied silently.
#
# **The three things to carry forward:**
#
# 1. **Usable coverage is very uneven** -- 19% for Lecture, about 60% for the two
#    dormitories and the Library, about 90% for Academic. Every result must be
#    read with the sample size in mind.
# 2. **The pipeline is verified.** Our totals agree with the dataset's own
#    combined power file to within 0.12%, and the semester flag comes from the
#    official IIIT-Delhi calendar published with the dataset, cross-checked
#    against a real collapse in dormitory occupancy.
# 3. **Nothing has been deleted.** Outliers, dead-meter periods and interpolated
#    values are all flagged and all still present, so any later phase can decide
#    for itself what to include.
#
# **Next:** Phase 2 -- descriptive statistics, distributions, hypothesis tests and
# the EDA charts.
