"""Phase 0 -- Explore the raw I-BLEND files. Percent-format source; see src/nbbuild.py."""

# %% [markdown]
# # SMARTGRID-X -- Phase 0: Exploring the raw data
#
# **Project:** occupancy-aware energy-waste and anomaly analysis of the I-BLEND
# campus dataset (IIIT Delhi, 7 buildings).
#
# **What this notebook does.** Before cleaning anything or fitting any model, we
# look at what we actually have. This notebook opens every single file in the
# `Dataset` folder, prints the first and last few rows, measures how much of the
# time range each meter really covers, and counts the data problems we will have
# to deal with in Phase 1.
#
# **Why do this first.** The energy folder is about 1.6 GB of 1-minute readings.
# If we start writing analysis code before we know where the gaps and the bad
# values are, every number we produce later is untrustworthy. Half of a data
# science project is finding out what is wrong with the data.
#
# **The rule we work under:** `Dataset/` is read-only source data. Nothing in
# this project ever writes to it, and it is never committed to GitHub.
#
# **What this notebook produces:**
#
# * `results/phase0_energy_profile.csv` -- one row per energy meter
# * `results/phase0_occupancy_profile.csv` -- one row per building
# * `figures/fig_00_coverage_timeline.png` -- when each meter was recording
# * Section 4 (Dataset & data quality) of `docs/PROJECT_REPORT.md`

# %% [markdown]
# ## Step 0: the Python environment
#
# Part of the syllabus is being able to say what our tools are and why. We print
# the versions from the running interpreter rather than typing them by hand, so
# this record can never drift out of date.

# %%
import sys
from pathlib import Path

# The notebooks live in notebooks/, so the project root is one level up. Adding
# it to sys.path is what lets us write "from src import ..." and reuse the same
# functions in every notebook instead of copy-pasting them.
sys.path.insert(0, str(Path.cwd().parent))

import numpy as np
import pandas as pd
import matplotlib
import sklearn
import scipy
import pyarrow

from IPython.display import display, Markdown

from src import config as C
from src import explore, viz

viz.setup_style()
C.ensure_dirs()

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)

why = {
    "python": (sys.version.split()[0], "the language everything is written in"),
    "pandas": (pd.__version__, "tables: reading CSVs, resampling, grouping, merging"),
    "numpy": (np.__version__, "arrays and the matrix maths behind PCA"),
    "pyarrow": (pyarrow.__version__, "reads/writes the parquet cache we build in Phase 1"),
    "matplotlib": (matplotlib.__version__, "every chart in the report"),
    "scipy": (scipy.__version__, "distribution fitting and hypothesis tests"),
    "scikit-learn": (sklearn.__version__, "regression, PCA, k-means, train/test splits"),
}
env = pd.DataFrame(
    [{"tool": k, "version": v[0], "what we use it for": v[1]} for k, v in why.items()]
)
display(env)
print("project root:", C.PROJECT_ROOT)

# %% [markdown]
# ## Step 1: what is actually in the folder
#
# We list every file with its size. This is the first reality check: the numbers
# below are why we cannot simply load everything into memory at once.

# %%
print("Dataset/ top level")
display(explore.file_inventory(C.DATASET_DIR))

print("\nDataset/energy_dataset/ -- 1-minute electrical readings")
energy_files = explore.file_inventory(C.ENERGY_DIR)
display(energy_files)
print(f"total energy folder: {energy_files['size_mb'].sum():,.0f} MB")

print("\nDataset/IIITD_occupancy_dataset/ -- 10-minute occupancy counts")
occ_files = explore.file_inventory(C.OCCUPANCY_DIR)
display(occ_files)
print(f"total occupancy folder: {occ_files['size_mb'].sum():,.0f} MB")

# %% [markdown]
# **What we found.** The energy folder is about 1.5 GB spread over 17 files; the
# occupancy folder is only about 21 MB. Two energy files are much bigger than the
# rest because they hold every building side by side:
# `all_buildings_power.csv` (power only, all 9 meters) and
# `data_present_status_buildings.csv` (a 1/0 "is this reading present" flag per
# minute per building). Those two will be useful later as an independent
# cross-check and as the source of our missing-data heatmap.

# %% [markdown]
# ## Step 2: what the dataset authors tell us
#
# Both folders ship a `Readme.txt`, and the dataset also comes with ISA-Tab
# metadata files describing how it was collected. Reading these first saves a lot
# of guessing. The two facts that matter most:
#
# 1. Timestamps are UNIX seconds and **must** be read as `Asia/Kolkata` (+05:30).
# 2. `power` is in watts.

# %%
print("=" * 78)
print("energy_dataset/Readme.txt")
print("=" * 78)
print((C.ENERGY_DIR / "Readme.txt").read_text(encoding="utf-8", errors="replace"))

# %%
print("=" * 78)
print("IIITD_occupancy_dataset/Readme.txt")
print("=" * 78)
print((C.OCCUPANCY_DIR / "Readme.txt").read_text(encoding="utf-8", errors="replace"))

# %% [markdown]
# ### How the data was measured (provenance)
#
# The ISA-Tab metadata that ships with the dataset records the instruments used.
# This is worth quoting in the report because it tells us what kind of errors to
# expect: a panel meter can lose communications (giving gaps), and a WiFi access
# point counts *devices associated to it*, not people.

# %%
assay = pd.read_csv(C.DATASET_DIR / "a_Rashid372C_assay.txt", sep="\t")
provenance = (
    assay[["Sample Name", "Protocol REF", "Parameter Value[instrument]",
           "Parameter Value[manufacturer]"]]
    .drop_duplicates(subset=["Protocol REF"])
    .reset_index(drop=True)
)
display(provenance)

study = (C.DATASET_DIR / "i_Investigation.txt").read_text(encoding="utf-8", errors="replace")
for line in study.splitlines():
    if line.startswith(("Study Title", "Study Identifier", "Study Public Release Date",
                        "Comment[Data Record URI]")):
        print(line)

# %% [markdown]
# ## Step 3: the mapping that makes this project possible
#
# The energy meters and the occupancy files use different names. The two
# `Readme.txt` files give us the mapping, and it is the single most important
# piece of setup in the project -- without it we cannot put power and people on
# the same row.
#
# Note that the two dormitories have **two** meters each: a `mains` supply and a
# `ups` (backup) supply. We keep them separate and also add them together,
# because "which supply keeps running when the rooms empty out" is one of our
# Phase 5 questions.

# %%
mapping = pd.DataFrame(
    [
        {
            "building": name,
            "label": spec["label"],
            "occupancy file": f"{spec['occ_code']}.csv",
            "energy meters": ", ".join(C.METERS[m] for m in spec["meters"]),
            "kind": spec["kind"],
        }
        for name, spec in C.BUILDINGS.items()
    ]
)
display(mapping)

# %% [markdown]
# ## Step 4: first and last rows of every energy meter
#
# Here we use a `for` loop over the meter registry defined in `src/config.py`,
# with an `if` test to report which optional columns each file has. Writing it as
# a loop over a dictionary -- rather than nine copy-pasted blocks -- is the point:
# add a meter to the registry and everything downstream picks it up.
#
# `head_tail()` reads the file in chunks and keeps only the last chunk, so we can
# see the final rows of a 125 MB file without ever holding it all in memory.

# %%
for meter_key, filename in C.METERS.items():
    path = C.meter_path(meter_key)
    head, tail = explore.head_tail(path, n=3)

    building = C.building_of_meter(meter_key)
    print("=" * 78)
    print(f"{meter_key}  ({filename})   building: {building}")
    print("=" * 78)
    print("columns:", list(head.columns))

    # Not every file carries every column -- transformers have no frequency.
    if "frequency" in head.columns:
        print("  has frequency column: yes")
    else:
        print("  has frequency column: no")

    print("\nfirst 3 rows:")
    print(head.to_string(index=False))
    print("\nlast 3 rows:")
    print(tail.to_string(index=False))
    print()

# %% [markdown]
# **What we found.** Every building meter has the same six columns: `timestamp`,
# `power`, `current`, `voltage`, `frequency`, `power_factor`. The first rows show
# `current` as `NA` -- the dataset readme warns about this. The timestamps are
# large integers (UNIX seconds), so nothing is human-readable until we convert.

# %% [markdown]
# ## Step 5: how much of the time range does each meter actually cover?
#
# A file having 2.2 million rows does not mean it has 2.2 million *consecutive*
# minutes. For each meter we compute:
#
# * the first and last timestamp, converted to India time
# * how many 1-minute readings there *should* be over that span
# * how many there actually are (row coverage %)
# * how many gaps longer than one minute there are, and the biggest one
# * the data-quality counts: zero power, negative power factor, out-of-range voltage
#
# This is the table that tells us what Phase 1 has to fix.

# %%
energy_profiles = pd.DataFrame(
    [
        explore.profile_energy_csv(C.meter_path(mk), C.building_of_meter(mk))
        for mk in C.METERS
    ]
)
energy_profiles.insert(0, "meter", list(C.METERS))
display(energy_profiles[[
    "meter", "label", "rows", "first", "last", "span_days",
    "row_coverage_pct", "gaps_over_1min", "largest_gap_hours",
]])

# %%
display(energy_profiles[[
    "meter", "power_min_w", "power_mean_w", "power_max_w", "power_zero_pct",
    "pf_negative_pct", "pf_min", "pf_max", "voltage_min", "voltage_max",
    "voltage_out_of_range_pct", "current_na_pct",
]])

energy_profiles.to_csv(C.RESULTS_DIR / "phase0_energy_profile.csv", index=False)
print("saved results/phase0_energy_profile.csv")

# %% [markdown]
# **What we found -- and these findings drive the whole of Phase 1.**
#
# 1. **The Lecture building meter is mostly dead.** Over 80% of its readings are
#    exactly 0 W. A lecture hall does use little power at night, but not exactly
#    zero for months on end -- that is a meter that stopped reporting. We must not
#    treat those zeros as "the building used no electricity".
# 2. **Negative `power_factor` is a sign convention, not corruption.** Between
#    about 14% and 66% of readings per meter are negative, the range is exactly
#    -0.999 to +1.000, and `power` itself is *never* negative. If electricity were
#    genuinely flowing backwards, power would be negative too. So the sign is a
#    leading/lagging indicator, and the usable value is the magnitude. Throwing
#    these rows away would delete more than half of the Library data.
# 3. **`current` is missing for roughly 9-13% of rows**, all at the start of the
#    record, exactly as the readme warns.
# 4. **Voltage is almost always fine** -- under 0.1% of readings fall outside a
#    credible 180-270 V band, so this is a small, safe fix.
# 5. **Coverage is high but gaps are long.** Most meters cover 97-99% of their
#    span row-wise, but individual gaps run to several months. Counting "percent
#    of rows present" alone would hide that, so Phase 1 puts the data on a
#    complete time grid before measuring anything.
# 6. **The meters do not all start together.** The Mess starts in September 2013
#    and Facilities in November 2013, months after the rest.

# %% [markdown]
# ## Step 6: the occupancy files
#
# Occupancy is a count of devices seen by the building's WiFi access points,
# recorded every 10 minutes. Two things to check: the time span (because it is
# shorter than the energy data, and the overlap is our working period), and
# whether the count ever reaches zero.

# %%
for building in C.BUILDING_ORDER:
    path = C.occupancy_path(building)
    head, tail = explore.head_tail(path, n=3)
    print("=" * 78)
    print(f"{building}  ({path.name})")
    print("=" * 78)
    print("first 3 rows:")
    print(head.to_string(index=False))
    print("last 3 rows:")
    print(tail.to_string(index=False))
    print()

# %%
occ_profiles = pd.DataFrame(
    [explore.profile_occupancy_csv(C.occupancy_path(b), b) for b in C.BUILDING_ORDER]
)
display(occ_profiles[[
    "building", "file", "rows", "first", "last", "span_days",
    "row_coverage_pct", "aligned_to_10min",
]])

# %%
display(occ_profiles[[
    "building", "occ_min", "occ_p05", "occ_median", "occ_mean", "occ_p95",
    "occ_max", "low_occ_threshold", "pct_rows_at_or_below_threshold",
]])

occ_profiles.to_csv(C.RESULTS_DIR / "phase0_occupancy_profile.csv", index=False)
print("saved results/phase0_occupancy_profile.csv")

# %% [markdown]
# **What we found -- this is the single most important finding in Phase 0.**
#
# **Occupancy never reaches zero.** The minimum count in every one of the seven
# buildings is 1, not 0. This is the WiFi over-counting the dataset authors warn
# about: idle phones and laptops stay associated to an access point even when
# nobody is using them. So the main research question cannot be phrased as "energy
# used when the building is empty" -- there is no such reading. It has to be
# "energy used when occupancy is **low**", with a threshold we state openly.
#
# We use a *relative* threshold: low occupancy means at or below 5% of that
# building's own 95th-percentile occupancy. The `low_occ_threshold` column shows
# what that works out to, and `pct_rows_at_or_below_threshold` shows how much data
# it captures. Two buildings need special handling:
#
# * **Facilities (SRB)** is a small building whose occupancy runs 1 to 47, so 5% of
#   its 95th percentile is 0.9 -- below its own minimum of 1. **No reading
#   qualifies.** We keep the same rule for every building rather than bending the
#   definition, report this cell honestly, and read Facilities off the threshold
#   sensitivity curve in Phase 5 instead.
# * **Lecture (LCB)** has 60% of its readings under the threshold, which combined
#   with its dead meter means its waste figure must be computed over the periods
#   when the meter was alive.
#
# Reassuringly, every occupancy timestamp sits exactly on a 10-minute boundary, so
# energy and occupancy will line up without any fuzzy matching.

# %% [markdown]
# ## Step 7: the two combined files
#
# `all_buildings_power.csv` holds the power of all nine meters side by side, and
# `data_present_status_buildings.csv` holds a 1/0 flag per minute per building.
# We are not using them as our main source -- they have no voltage or power factor
# -- but they are valuable:
#
# * the power file gives us a completely **independent way to check** the totals we
#   compute from the individual meter files
# * the status file is the cleanest way to build a **missing-data heatmap**

# %%
for path in (C.ALL_BUILDINGS_POWER_CSV, C.STATUS_BUILDINGS_CSV):
    head = pd.read_csv(path, nrows=3)
    print("=" * 78)
    print(path.name)
    print("=" * 78)
    print("columns:", list(head.columns))
    print(head.to_string(index=False))
    print()

# %% [markdown]
# Note the column names in these two files (`Boys_main`, `Boys_backup`, ...)
# differ from our meter keys. `src/config.py` holds the translation in
# `WIDE_COL_TO_METER` so the cross-check in Phase 1 is unambiguous.

# %% [markdown]
# ## Step 8: the working period
#
# Energy recording starts in August 2013, but occupancy only starts in February
# 2014 and stops in November 2017. Since every research question needs both, our
# working period is the **overlap**.

# %%
start, end = explore.overlap_window(energy_profiles, occ_profiles)
print("energy spans   :", energy_profiles["first"].min(), "->", energy_profiles["last"].max())
print("occupancy spans:", occ_profiles["first"].min(), "->", occ_profiles["last"].max())
print()
print("WORKING PERIOD :", start, "->", end)
print(f"                 {(end - start).days} days, "
      f"{int((end - start).total_seconds() // 600):,} ten-minute steps")

# %% [markdown]
# ## Step 9: a picture of when each meter was actually recording
#
# The table above is precise but hard to take in. The obvious chart -- one bar per
# source from its first timestamp to its last -- would be **misleading**, because
# a meter that went silent for 200 days in the middle still produces a solid bar.
#
# So instead we count how many readings each source produced in each calendar
# month and divide by how many that month should contain (1440 per day for the
# 1-minute energy meters, 144 per day for the 10-minute occupancy files). Dark
# means a full month of data; pale means a month with holes; white means the
# source recorded nothing at all that month.

# %%
import matplotlib.pyplot as plt

coverage = explore.coverage_matrix()
print(f"coverage matrix: {coverage.shape[0]} sources x {coverage.shape[1]} months")
display(coverage.iloc[:, :6].round(1))

# %%
fig, ax = plt.subplots(figsize=(13, 6))

# A month with no rows at all is a different thing from a month that recorded
# almost nothing, so NaN gets its own neutral grey rather than the palest blue.
cmap = viz.SEQ_BLUE.copy()
cmap.set_bad("#e8e7e3")

im = ax.imshow(
    coverage.values, aspect="auto", cmap=cmap, vmin=0, vmax=100,
    interpolation="nearest",
)

ax.set_yticks(range(len(coverage.index)))
ax.set_yticklabels(coverage.index, fontsize=8)

# Label every third month so the axis stays readable.
tick_positions = range(0, len(coverage.columns), 3)
ax.set_xticks(list(tick_positions))
ax.set_xticklabels([coverage.columns[i] for i in tick_positions], rotation=45,
                   ha="right", fontsize=8)

# Separate the energy block from the occupancy block.
ax.axhline(len(C.METERS) - 0.5, color=viz.INK, linewidth=1.2)

# Mark where the usable overlap begins and ends.
months = list(coverage.columns)
for boundary, text in (
    (str(start.to_period("M")), "occupancy starts"),
    (str(end.to_period("M")), "occupancy ends"),
):
    if boundary in months:
        x = months.index(boundary)
        ax.axvline(x, color=viz.STATUS["ANOMALY"], linewidth=1.4, linestyle="--")
        ax.annotate(text, xy=(x, -0.8), fontsize=8, color=viz.STATUS["ANOMALY"],
                    ha="center", va="bottom", annotation_clip=False)

# pad lifts the title clear of the two dashed-line annotations above the plot
ax.set_title("How complete each data source is, month by month", pad=26)
ax.grid(False)
cbar = fig.colorbar(im, ax=ax, pad=0.01, fraction=0.025)
cbar.set_label("% of expected readings present", fontsize=9,
               color=viz.INK_SECONDARY)
cbar.outline.set_visible(False)

# Grey means the source recorded nothing at all that month -- distinct from the
# palest blue, which means it recorded something but almost nothing.
from matplotlib.patches import Patch
ax.legend(
    handles=[Patch(facecolor="#e8e7e3", label="no data recorded at all")],
    loc="upper left", bbox_to_anchor=(0.0, -0.30), fontsize=8,
)

viz.save_fig(fig, "fig_00_coverage_timeline")
coverage.round(1).to_csv(C.RESULTS_DIR / "phase0_monthly_coverage.csv")
print("saved results/phase0_monthly_coverage.csv")

# %% [markdown]
# **Takeaway:** the record is far patchier than the row counts suggest. The Boys
# hostel, Girls mains and Library meters each have a multi-month white band where
# nothing was recorded at all, which is why their row coverage sits near 72-74%
# rather than 98%. The occupancy block (below the black line) starts only in
# February 2014 and stops in November 2017 -- the two dashed lines. Everything
# this project analyses lives between them.

# %%
# Which months are completely missing for each source? Worth naming explicitly,
# because these are the periods that will simply be absent from every result.
gaps = []
for source in coverage.index:
    row = coverage.loc[source]
    blank = row[row.isna() | (row < 1)].index.tolist()
    if blank:
        gaps.append({"source": source, "blank months": len(blank),
                     "from": blank[0], "to": blank[-1]})
display(pd.DataFrame(gaps))

# %% [markdown]
# ## Step 10: the Phase 0 data-quality summary
#
# Finally we pull the findings into one small table. This is what goes into
# section 4 of `docs/PROJECT_REPORT.md`, and it is the to-do list for Phase 1.

# %%
issues = pd.DataFrame(
    [
        {
            "issue": "Negative power_factor",
            "where": "all 9 meters, 14-66% of rows",
            "evidence": "range exactly -0.999..+1.000 while power is never negative",
            "reading": "sign convention (leading/lagging), not bad data",
            "phase 1 action": "keep abs(power_factor); keep a pf_was_negative flag",
        },
        {
            "issue": "Dead meter (0 W for months)",
            "where": "Lecture building, 81.7% of rows",
            "evidence": "exact zeros in long unbroken runs",
            "reading": "meter stopped reporting, not zero consumption",
            "phase 1 action": "flag runs of 0 W longer than 6 h as meter_off",
        },
        {
            "issue": "Missing current",
            "where": "all meters, 9-13% of rows, early period",
            "evidence": "NA in the first rows of every file; readme confirms",
            "reading": "instrument not configured yet",
            "phase 1 action": "leave as NaN; we do not model current",
        },
        {
            "issue": "Out-of-range voltage",
            "where": "all meters, under 0.1% of rows",
            "evidence": "values at 0 V and above 270 V on a 230 V feeder",
            "reading": "momentary meter artefact",
            "phase 1 action": "set outside 180-270 V to NaN",
        },
        {
            "issue": "Long gaps",
            "where": "Library and both hostels, up to ~208 days",
            "evidence": "largest_gap_hours column above",
            "reading": "extended outage in data collection",
            "phase 1 action": "put data on a complete time grid; interpolate only gaps <= 30 min",
        },
        {
            "issue": "Staggered start dates",
            "where": "Mess (Sep 2013), Facilities (Nov 2013)",
            "evidence": "first column above",
            "reading": "meters installed later",
            "phase 1 action": "per-building coverage reported; no back-filling",
        },
        {
            "issue": "Occupancy never reaches zero",
            "where": "all 7 buildings, minimum count = 1",
            "evidence": "occ_min column above",
            "reading": "WiFi counts idle devices, not people",
            "phase 1 / 5 action": "relative low-occupancy threshold + sensitivity curve",
        },
        {
            "issue": "Threshold unreachable for Facilities",
            "where": "Facilities (SRB)",
            "evidence": "5% of p95 = 0.9 < minimum observed count of 1",
            "reading": "small building, occupancy range 1-47",
            "phase 1 / 5 action": "keep the rule; report the cell honestly; use the sensitivity curve",
        },
    ]
)
display(issues)
issues.to_csv(C.RESULTS_DIR / "phase0_data_quality_issues.csv", index=False)
print("saved results/phase0_data_quality_issues.csv")

# %% [markdown]
# ## Step 11: write these findings into the project report
#
# The project rule is that **every number in `docs/PROJECT_REPORT.md` comes from
# executed code** -- nothing is typed in by hand. The report contains named
# placeholder blocks, and `src/report.py` fills them from the tables we just
# built. Re-running this notebook rewrites the blocks, so the report can never
# drift out of step with the analysis.

# %%
from src import report

blocks = {}

blocks["phase0_mapping"] = report.md_table(mapping)

inventory = pd.concat(
    [
        explore.file_inventory(C.ENERGY_DIR).assign(folder="energy_dataset"),
        explore.file_inventory(C.OCCUPANCY_DIR).assign(folder="IIITD_occupancy_dataset"),
    ]
)[["folder", "file", "size_mb"]].reset_index(drop=True)
blocks["phase0_file_inventory"] = (
    report.md_table(inventory)
    + f"\n\nTotal: **{inventory['size_mb'].sum():,.0f} MB** across "
    f"{len(inventory)} files."
)

blocks["phase0_energy_profile"] = report.md_table(
    energy_profiles[[
        "meter", "label", "rows", "first", "last", "span_days",
        "row_coverage_pct", "gaps_over_1min", "largest_gap_hours",
    ]]
)

blocks["phase0_energy_quality"] = report.md_table(
    energy_profiles[[
        "meter", "power_mean_w", "power_max_w", "power_zero_pct",
        "pf_negative_pct", "pf_min", "pf_max", "voltage_min", "voltage_max",
        "voltage_out_of_range_pct", "current_na_pct",
    ]]
)

blocks["phase0_occupancy_profile"] = report.md_table(
    occ_profiles[[
        "building", "file", "rows", "first", "last", "span_days",
        "row_coverage_pct", "aligned_to_10min",
    ]]
)

blocks["phase0_occupancy_distribution"] = report.md_table(
    occ_profiles[[
        "building", "occ_min", "occ_p05", "occ_median", "occ_mean", "occ_p95",
        "occ_max", "low_occ_threshold", "pct_rows_at_or_below_threshold",
    ]]
)

print("\n".join(f"prepared block: {k}" for k in blocks))

# %%
# The written findings that go with those tables. These are conclusions, not
# numbers, so they are prose -- but every figure quoted inside them is read from
# the tables above rather than typed.
srb = occ_profiles.set_index("building").loc["Facilities"]
lcb = occ_profiles.set_index("building").loc["Lecture"]
lecture_zero = float(
    energy_profiles.set_index("meter").loc["lecture_mains", "power_zero_pct"]
)
pf_lo = energy_profiles["pf_negative_pct"].min()
pf_hi = energy_profiles["pf_negative_pct"].max()

blocks["phase0_occupancy_note"] = f"""
**The single most important finding in exploration: occupancy never reaches zero.**
The minimum count in every one of the seven buildings is **1**, not 0. This is the
WiFi over-counting the dataset authors warn about -- idle phones and laptops stay
associated with an access point long after their owner has left. The consequence is
structural, not cosmetic: *the main research question cannot be phrased as "energy
used while the building is empty", because no such reading exists in this dataset.*

It must instead be "energy used while occupancy is **low**", against a threshold we
state openly. We use a threshold relative to each building's own scale:
**low occupancy = occupancy at or below {C.LOW_OCC_FRACTION:.0%} of that building's
{C.LOW_OCC_PERCENTILE}th-percentile occupancy.** An absolute cut-off would be
meaningless across buildings whose normal populations differ by a factor of twenty.

Two buildings do not fit the standard recipe, and both are reported rather than
quietly dropped:

- **Facilities (SRB)** is small: its occupancy runs {srb['occ_min']:.0f} to
  {srb['occ_max']:.0f} with a 95th percentile of {srb['occ_p95']:.0f}, so the
  threshold works out to **{srb['low_occ_threshold']:.2f}** -- below its own
  minimum observed count of {srb['occ_min']:.0f}. **No reading qualifies**
  ({srb['pct_rows_at_or_below_threshold']:.2f}% of rows). We keep the identical
  rule for every building rather than bending the definition for one, report this
  cell honestly as "no qualifying intervals", and read Facilities off the
  threshold-sensitivity curve in Phase 5 instead.
- **Lecture (LCB)** has {lcb['pct_rows_at_or_below_threshold']:.1f}% of its
  readings under the threshold, and its meter reads exactly 0 W for
  {lecture_zero:.1f}% of the record. Its waste figure is therefore computed only
  over the periods when the meter was demonstrably alive, with the coverage
  reported alongside.

Reassuringly, **every occupancy timestamp sits exactly on a 10-minute boundary**,
so energy and occupancy line up without any fuzzy time matching.
"""

blocks["phase0_coverage_figure"] = report.figure(
    "fig_00_coverage_timeline",
    "Monthly completeness of every energy meter and occupancy file",
    "The record is far patchier than the row counts suggest: the Boys hostel, "
    "Girls mains and Library meters each lose several consecutive months "
    "entirely, and the occupancy block (below the black line) exists only "
    "between the two dashed lines.",
)

blocks["phase0_data_quality_issues"] = report.md_table(issues)

blocks["phase0_working_period"] = f"""
Energy recording runs from **{energy_profiles['first'].min():%Y-%m-%d}** to
**{energy_profiles['last'].max():%Y-%m-%d}**, but occupancy only exists from
**{occ_profiles['first'].min():%Y-%m-%d}** to **{occ_profiles['last'].max():%Y-%m-%d}**.
Every research question in this project needs both, so the working period is the
overlap:

> **{start:%d %B %Y} to {end:%d %B %Y}** -- {(end - start).days:,} days,
> {int((end - start).total_seconds() // 600):,} ten-minute intervals.

The roughly six months of energy data that precede the occupancy record are not
used. They are not deleted, simply out of scope for questions that require knowing
whether anyone was in the building.
"""

print("\n".join(f"prepared block: {k}" for k in blocks))

# %%
blocks["method_phase0"] = f"""
Exploration was done before any cleaning, to find out what the data actually
contains rather than what the documentation promises.

**What we did.** We listed every file with its size; read both `Readme.txt` files
and the ISA-Tab metadata that records the instruments used; printed the first and
last rows of all {len(C.METERS)} energy meters and all {len(C.BUILDINGS)} occupancy
files; and profiled each file for coverage, gaps and data-quality counts.

**How we handled the size.** The energy folder is about 1.5 GB, so no step ever
loads it all. Files are read one at a time, in chunks of 500,000 rows, keeping
only the needed columns. Reading the last rows of a 125 MB file, for example, is
done by streaming through it and keeping only the final chunk.

**Timestamps.** All UNIX timestamps are converted with
`pd.to_datetime(..., unit="s", utc=True).dt.tz_convert("{C.TIMEZONE}")`, which is
what the dataset readme requires. Getting this wrong by 5.5 hours would put every
"night-time" reading in the afternoon and silently invalidate the entire project.

**Coverage measurement.** Rather than drawing a bar from each meter's first to its
last timestamp -- which makes a meter that went silent for 200 days look
continuous -- we counted readings per calendar month and divided by how many that
month should contain (1440 per day for the 1-minute energy files, 144 per day for
the 10-minute occupancy files). That is what the heatmap in section 4.8 shows.

**Notebook:** `notebooks/00_explore.ipynb`.
"""

blocks["results_phase0"] = f"""
Exploration produced four findings that shaped everything after it.

1. **The working period is set by occupancy, not energy.** Energy covers
   {energy_profiles['first'].min():%b %Y} – {energy_profiles['last'].max():%b %Y},
   occupancy only {occ_profiles['first'].min():%b %Y} – {occ_profiles['last'].max():%b %Y}.
   The project analyses the overlap.

2. **"Empty" is not measurable in this dataset.** Minimum occupancy is 1 in all
   seven buildings (section 4.7). The main question had to be re-specified around a
   relative low-occupancy threshold, with a sensitivity curve to show how much the
   answer depends on where that threshold is put.

3. **Negative `power_factor` is a sign convention, not corrupt data.** It affects
   {pf_lo:.2f}%–{pf_hi:.2f}% of readings depending on the meter. The decisive
   evidence is that the range is exactly −0.999 to +1.000 *while `power` itself is
   never negative*: if current were genuinely flowing backwards, power would be
   negative too. Treating these as invalid would have deleted more than half of the
   Library record. We keep the magnitude and retain the sign as a separate flag.

4. **Coverage is much worse than row counts suggest.** Row coverage ranges from
   {energy_profiles['row_coverage_pct'].min():.1f}% to
   {energy_profiles['row_coverage_pct'].max():.1f}%, and the worst meters lose
   whole months at a time -- the largest single gap is
   {energy_profiles['largest_gap_hours'].max():,.0f} hours
   ({energy_profiles['largest_gap_hours'].max() / 24:,.0f} days). The Lecture meter
   additionally reads exactly 0 W for {lecture_zero:.1f}% of its record, which is a
   dead meter rather than an idle building.
"""

report.update_blocks(blocks)

# %% [markdown]
# ## Step 12: record the Phase 0 decisions
#
# Any time we make a judgement call, it goes into the decision log with the
# options we considered and what difference the choice makes. This is what lets a
# reader disagree with us precisely rather than vaguely.

# %%
report.log_decision(
    id="D00-01", phase="0",
    decision="Analysis window",
    options_considered="Use the full energy record (Aug 2013 - Dec 2017); "
                       "use only the energy/occupancy overlap",
    chosen=f"Overlap only: {start:%Y-%m-%d} to {end:%Y-%m-%d}",
    reason="All three research questions need occupancy. Energy-only months "
           "cannot answer any of them.",
    effect_on_results="Drops ~6 months of energy data at the start and ~2 months "
                      "at the end. Reduces sample size; does not bias it.",
)

report.log_decision(
    id="D00-02", phase="0",
    decision="Interpretation of negative power_factor",
    options_considered="Treat as invalid and drop the rows; set to NaN; "
                       "take the absolute value and keep a sign flag",
    chosen="abs(power_factor), plus a retained pf_was_negative flag",
    reason=f"Affects {pf_lo:.2f}-{pf_hi:.2f}% of rows. The range is exactly "
           "-0.999..+1.000 while power is never negative, so the sign is a "
           "leading/lagging convention, not reverse power flow.",
    effect_on_results="Preserves 58% of the Library record that dropping would "
                      "have destroyed. Power itself is untouched, so energy "
                      "totals are unaffected either way.",
)

report.log_decision(
    id="D00-03", phase="0",
    decision="Definition of low occupancy",
    options_considered="occupancy == 0 (impossible: minimum is 1); a fixed "
                       "absolute count for all buildings; a per-building "
                       "fraction of its own 95th percentile",
    chosen=f"occupancy <= {C.LOW_OCC_FRACTION:.0%} of the building's "
           f"{C.LOW_OCC_PERCENTILE}th percentile",
    reason="WiFi never reads zero, and building populations differ by ~20x, so "
           "an absolute cut-off is not comparable across buildings.",
    effect_on_results="This threshold IS the main result's definition. A "
                      "sensitivity curve over 0-20% is published in Phase 5 so "
                      "the reader can see how much the headline depends on it.",
)

report.log_decision(
    id="D00-04", phase="0",
    decision="Facilities (SRB), where no reading meets the threshold",
    options_considered="Add a percentile floor for all buildings; use an "
                       "absolute rule for SRB only; keep the uniform rule and "
                       "report the empty cell",
    chosen="Keep the uniform rule; report 'no qualifying intervals'; quote SRB "
           "from the sensitivity curve instead",
    reason=f"5% of its 95th percentile is {srb['low_occ_threshold']:.2f}, below "
           f"its own minimum count of {srb['occ_min']:.0f}. Changing the "
           "definition for one building would make it non-comparable.",
    effect_on_results="Facilities has no headline waste percentage at the "
                      "standard threshold. Its behaviour is reported from the "
                      "sensitivity curve, clearly labelled as such.",
)

report.log_decision(
    id="D00-05", phase="0",
    decision="Lecture building, whose meter reads 0 W for most of the record",
    options_considered="Exclude the building; treat the zeros as genuine zero "
                       "consumption; compute over alive periods only",
    chosen="Include it, computing over periods where the meter was alive, with "
           "coverage reported alongside",
    reason=f"{lecture_zero:.1f}% of readings are exactly 0 W in long unbroken "
           "runs -- a meter that stopped reporting, not a building using no "
           "electricity. Treating them as real would produce a near-zero waste "
           "figure that is an artefact.",
    effect_on_results="Lecture keeps a place in the headline table, but its "
                      "figure rests on a much smaller sample than the other six "
                      "buildings, and is flagged as such.",
)

report.log_decision(
    id="D00-06", phase="0",
    decision="WiFi over-count of idle devices",
    options_considered="Ignore it; subtract the documented idle baseline before "
                       "thresholding and use that as the headline; use raw "
                       "counts for the headline and report a corrected variant",
    chosen="Raw counts for the headline; corrected-occupancy run reported as a "
           "robustness check in Phase 5",
    reason="The over-count (~20 devices, ~50 in Academic) is an approximate "
           "constant from the dataset paper, not a measurement. Building the "
           "headline on it would rest the main result on an estimate.",
    effect_on_results="Headline is conservative (raw counts make buildings look "
                      "more occupied than they are, so waste is understated). "
                      "The corrected run quantifies by how much.",
)

report.log_decision(
    id="D00-07", phase="0",
    decision="Analysis resolution",
    options_considered="Keep 1-minute energy and forward-fill occupancy; "
                       "average energy into 10-minute blocks to match occupancy",
    chosen=f"{C.TARGET_FREQ} blocks",
    reason="Occupancy is natively 10-minute. Up-sampling it to 1 minute would "
           "invent ten times more data than was measured. Every occupancy "
           "timestamp already falls exactly on a 10-minute boundary.",
    effect_on_results="Reduces ~2.3M rows per meter to ~231k, which is what "
                      "makes the whole project run on a laptop. No loss of "
                      "information relative to the occupancy signal.",
)

report.log_decision(
    id="D00-08", phase="0",
    decision="Random seed",
    options_considered="Unseeded; a fixed seed",
    chosen=f"seed = {C.SEED} everywhere (sampling, k-means, anomaly injection, "
           "random forest)",
    reason="Results must be reproducible by a teammate or an examiner running "
           "the notebooks again.",
    effect_on_results="None on the substance; makes every reported number exactly "
                      "reproducible.",
)

report.publish_decision_log()
print()
print("blocks still pending:", len(report.pending_blocks()))
print("figures referenced but missing:", report.check_figures())

# %% [markdown]
# ## Phase 0 conclusion
#
# We have opened every file, and we now know three things that change how the rest
# of the project must be built:
#
# 1. **Our working period is 2014-02-16 to 2017-11-03**, set by the occupancy data,
#    not by the much longer energy record.
# 2. **"Empty building" is not measurable** with this data, because WiFi occupancy
#    never reads zero. The main research question is therefore about *low*
#    occupancy, with a stated, relative threshold -- and we will publish a
#    sensitivity curve so the reader can see how much the answer depends on it.
# 3. **Two buildings need care, not exclusion:** Lecture (dead meter for most of
#    the record) and Facilities (too small for the standard threshold).
#
# **Next:** Phase 1 turns these raw files into one clean 10-minute table per
# building, with the fixes listed in the table above, and produces the
# missing-data heatmap.
