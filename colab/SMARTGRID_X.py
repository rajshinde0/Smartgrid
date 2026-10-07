"""Colab runner. Percent-format source; build with src/nbbuild.py.

    python src/nbbuild.py colab/SMARTGRID_X.py colab/SMARTGRID_X.ipynb

Authored as a .py like every other notebook in this project, so the source is
diffable and the .ipynb is a build artefact rather than hand-edited JSON.
"""

# %% [markdown]
# # SMARTGRID-X on Google Colab
#
# **Occupancy-aware energy-waste and anomaly analysis of the I-BLEND campus
# dataset** — IIIT Delhi, 7 buildings, Feb 2014 to Nov 2017.
#
# This notebook runs the project end to end on a free Colab runtime and then
# walks through everything it produced. Nothing needs to be installed or
# downloaded by hand.
#
# ---
#
# ### What it does
#
# | Step | What happens |
# |---|---|
# | 1 | Clone the repository and install dependencies |
# | 2 | Fetch the data |
# | 3 | Execute the analysis phases |
# | 4 | Walk the whole project, phase by phase, with its figures and tables |
# | 5 | **Check the numbers against the published ones** |
# | 6 | *(optional)* Serve the dashboard on a public URL |
#
# ### Two ways to run it
#
# **`fast`** (default, ~10–15 min) downloads the saved output of Phase 1 and
# executes Phases 2–8 live. Phase 1 is the slow step: it reads 1.6 GB of raw
# 1-minute meter readings and boils them down to 10-minute tables. Skipping it
# means everything else still runs for real.
#
# **`full`** (~30–60 min) fetches the raw 1.6 GB from figshare and runs all nine
# phases, proving the whole thing works from nothing.
#
# > **Step 5 is the one to watch.** Every number in this project's report was
# > produced on an exactly-pinned software stack. Colab's is different, so the
# > results *could* shift. Rather than hope, step 5 compares every regenerated
# > table against the committed one and reports what moved.

# %% [markdown]
# ## 1. Clone and install
#
# The dataset is not in the repository — it is 1.6 GB and lives on figshare
# under its own DOI, so the clone is small and quick.

# %%
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_URL = "https://github.com/rajshinde0/Smartgrid.git"
REPO_DIR = Path("/content/Smartgrid")

if not REPO_DIR.exists():
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(REPO_DIR)], check=True)

os.chdir(REPO_DIR)
sys.path.insert(0, str(REPO_DIR))

print("repository:", REPO_DIR)
print("commit    :", subprocess.run(
    ["git", "rev-parse", "--short", "HEAD"],
    capture_output=True, text=True).stdout.strip())
print("python    :", sys.version.split()[0])

# %% [markdown]
# Dependencies come from `requirements-portable.txt`, not `requirements.txt`.
#
# The pinned file requires Python 3.13+ and exact versions, because that is the
# stack every published number was produced on. Colab runs an older Python, so
# the portable file expresses the same stack as lower bounds. The floors are
# real: the analysis uses no syntax newer than 3.10 and no pandas API that
# changed between 2.2 and 3.0.

# %%
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements-portable.txt"],
    check=True,
)

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import sklearn

print(f"pandas       {pd.__version__}")
print(f"numpy        {np.__version__}")
print(f"scikit-learn {sklearn.__version__}")
print()
print("Published results were produced with pandas 3.0.3 / numpy 2.4.3 / "
      "scikit-learn 1.8.0 on Python 3.14.3.")
print("Step 5 checks whether that difference changed anything.")

# %% [markdown]
# ## 2. Choose how to run, and fetch the data
#
# Change `RUN_MODE` to `"full"` for the complete cold run.

# %%
RUN_MODE = "fast"        # "fast" or "full"

assert RUN_MODE in {"fast", "full"}, "RUN_MODE must be 'fast' or 'full'"

started = time.time()

if RUN_MODE == "fast":
    print("fast mode: fetching Phase 1 output from the GitHub Release\n")
    subprocess.run([sys.executable, "tools/get_cache.py", "--full"], check=True)
    PHASES = ["02_stats_eda", "03_pca", "04_regression",
              "05_waste", "06_anomaly", "07_final", "08_weather"]
else:
    print("full mode: fetching 1.6 GB of raw data from figshare\n")
    subprocess.run([sys.executable, "tools/get_data.py", "--all"], check=True)
    PHASES = ["00_explore", "01_data_prep", "02_stats_eda", "03_pca",
              "04_regression", "05_waste", "06_anomaly", "07_final", "08_weather"]

print(f"\nfetch took {time.time() - started:.0f}s")
print(f"will run {len(PHASES)} phases: {', '.join(PHASES)}")

# %% [markdown]
# ### Keep a copy of the published results before we overwrite them
#
# The phases rewrite `results/*.csv` as they run. Step 5 needs the committed
# versions to compare against, so they are copied aside first.

# %%
import shutil

PUBLISHED = Path("/content/published_results")
if PUBLISHED.exists():
    shutil.rmtree(PUBLISHED)
shutil.copytree("results", PUBLISHED)

print(f"kept {len(list(PUBLISHED.glob('*.csv')))} published CSVs for comparison")

# %% [markdown]
# ## 3. Execute the phases
#
# Each phase is built from its percent-format source and executed end to end
# with `nbconvert`, exactly as it is locally. A phase that raises stops the run
# and prints the offending cell — a broken notebook is never passed over.
#
# This is the slow cell. Phase 6 (the anomaly experiment) and Phase 4 (the
# random forest) take the longest.

# %%
run_started = time.time()
timings = []

for phase in PHASES:
    phase_started = time.time()
    print(f"\n{'=' * 70}\n  {phase}\n{'=' * 70}")

    result = subprocess.run(
        [sys.executable, "tools/build_and_run.py", phase],
        capture_output=True, text=True,
    )
    elapsed = time.time() - phase_started
    timings.append((phase, elapsed, result.returncode))

    tail = [ln for ln in result.stdout.splitlines() if ln.strip()][-6:]
    print("\n".join(tail))

    if result.returncode != 0:
        print(f"\nFAILED after {elapsed:.0f}s\n")
        print(result.stdout[-4000:])
        print(result.stderr[-2000:])
        raise RuntimeError(f"{phase} exited {result.returncode}")

    print(f"\n  OK  {elapsed:.0f}s")

print(f"\n{'=' * 70}")
print(f"all {len(PHASES)} phases passed in {(time.time() - run_started) / 60:.1f} min")

# %%
pd.DataFrame(timings, columns=["phase", "seconds", "exit code"]).style.format(
    {"seconds": "{:.0f}"}
)

# %% [markdown]
# ## 4. The project, phase by phase
#
# Everything below was produced by the cells above — these are this run's own
# figures and tables, read off disk, not pictures pasted in.

# %%
from IPython.display import Image, Markdown, display


def figure(name: str, caption: str = "") -> None:
    """Show a figure this run produced, with a caption."""
    display(Image(f"figures/{name}"))
    if caption:
        display(Markdown(f"*{caption}*"))


def table(name: str, note: str = "", **kw) -> None:
    """Print a result table this run produced."""
    frame = pd.read_csv(f"results/{name}")
    print(frame.to_string(index=False, **kw))
    if note:
        display(Markdown(f"*{note}*"))


print("helpers ready")

# %% [markdown]
# ### Phases 0 and 1 — the data, and what is wrong with it
#
# Seven buildings, 1-minute meters, Feb 2014 to Nov 2017, paired with
# WiFi-derived occupancy counts. The buildings are **not** equally trustworthy
# and the analysis says so per building rather than averaging the problem away.

# %%
table("phase1_data_quality.csv")

# %%
figure("fig_01_missing_heatmap.png",
       "Missing data by building and month. Coverage is the first thing to "
       "establish, because every later number is conditional on it.")

# %% [markdown]
# **Lecture is the problem case, and it is kept deliberately.** Its meter reads
# zero for 25,501 hours. A dead meter and a genuinely switched-off building look
# identical in the data and mean opposite things for a waste analysis.

# %%
figure("fig_01_zero_run_lengths_lecture.png",
       "How long Lecture's zero-runs are. The classification was logged as a "
       "decision and checked against a 24-hour alternative threshold.")

# %% [markdown]
# **The guiding rule is flag, never delete.** An outlier in an energy meter
# might be an error — or exactly the abnormal event Phase 6 exists to detect.
# Deleting it would delete the thing being studied, so every judgement becomes
# an extra column and the original value stays.

# %%
figure("fig_01_outlier_flags_academic.png",
       "Outliers flagged by IQR and Z-score on the Academic building. Flagged, "
       "counted, reported -- none removed.")

# %% [markdown]
# ### Phase 2 — statistics and exploratory analysis
#
# Descriptive statistics first, computed with pandas and then again by hand in
# NumPy with the two asserted equal.

# %%
table("phase2_descriptive_statistics.csv")

# %% [markdown]
# Two hypothesis tests, each reporting an **effect size** beside its p-value.
# With 170,000 intervals a tiny p-value means "we have a lot of data", not
# "this matters", so the effect size leads.

# %%
table("phase2_test_weekday_weekend.csv")
print()
table("phase2_test_semester_vacation.csv")

# %%
figure("fig_02_hourly_profile_all.png",
       "Mean power by hour of day. The overnight floor never reaches zero in "
       "any building -- that floor is the whole subject of this project.")

# %%
figure("fig_02_scatter_power_occupancy.png",
       "Power against occupancy. The relationship is real but loose, which "
       "Phase 4 then quantifies.")

# %%
figure("fig_02_distribution_fit.png",
       "Fitting a distribution to power: Normal against Log-normal, with Q-Q "
       "plots and a KS test.")

# %% [markdown]
# ### Phase 3 — principal component analysis
#
# Each day becomes a 144-point vector (10-minute blocks), giving a days x 144
# matrix. PCA is computed by hand with `np.linalg.eig` and verified against
# scikit-learn.

# %%
figure("fig_03_scree_academic.png",
       "Scree plot. A handful of components carry most of the variation in "
       "daily load shape.")

# %%
figure("fig_03_day_types_academic.png",
       "Day types found by clustering in component space.")

# %%
table("phase3_day_types_academic.csv",
      "Each cluster described by what it actually is -- note the night floor "
      "column, which never approaches zero.")

# %% [markdown]
# ### Phase 4 — regression (RQ2)
#
# Four models. **A** is power on occupancy alone, and its intercept is the base
# load RQ1 needs. **B** is time-only. **C** adds occupancy to B. **D** is a
# random forest on C's features, checking whether non-linearity matters.

# %%
table("phase4_model_scores.csv")

# %%
figure("fig_04_model_comparison.png",
       "Validation scores by building. Negative R-squared means worse than "
       "predicting the mean -- real information, left visible.")

# %%
table("phase4_occupancy_contribution.csv",
      "What occupancy is worth over a time-only baseline. It helps in the "
      "dormitories and the Library, barely anywhere else, and makes Facilities "
      "actively worse -- which Phase 8 later explains.")

# %% [markdown]
# **Why there are no lag features.** Power an hour ago correlates with current
# power at about r = 0.95, and adding it lifts validation R-squared from 0.55 to
# 0.83. The project refuses it anyway: a lag model would *track* waste instead
# of flagging it, since lights on since 2 a.m. would simply be predicted to stay
# on. The low R-squared is the price of a baseline that can still see waste.

# %%
figure("fig_04_overfitting_curves.png",
       "Training against validation error as model complexity rises -- where "
       "the forest depth was fixed, and why.")

# %%
table("phase4_concept_drift.csv",
      "Consumption grew 32-48% across the record, so a model fitted on "
      "2014-2016 is genuinely stale by late 2017. Measured, not assumed.")

# %% [markdown]
# ### Phase 5 — wasted energy (RQ1, the headline)
#
# What share of each building's energy is spent while it is nearly empty, and
# how hard is it still working when nobody is there?

# %%
headline = pd.read_csv("results/phase5_headline.csv")

view = headline[[
    "building", "low-occupancy energy share %", "intensity ratio",
    "base load a (kW)", "mean power overall (kW)",
]].copy()
view["intensity ratio"] = (view["intensity ratio"] * 100).round(1)
view = view.rename(columns={
    "low-occupancy energy share %": "energy at low occupancy %",
    "intensity ratio": "power when empty, % of average",
})
view.sort_values("power when empty, % of average", ascending=False)

# %%
figure("fig_05_headline.png",
       "Left: share of energy spent at low occupancy. Right: power when nearly "
       "empty as a share of that building's own average.")

# %% [markdown]
# **When these buildings are at their emptiest they still draw 62–85% of their
# average power.** In every one of them the base load — drawn whether or not
# anyone is present — is the larger share of consumption.
#
# Facilities is blank: its low-occupancy threshold works out below its own
# minimum observed occupancy, so it has no qualifying interval. The rule was
# kept identical for every building rather than bent for one.

# %% [markdown]
# **Does the finding depend on where the threshold was drawn?** "Low occupancy"
# is defined relative to each building — at or below 5% of its own
# 95th-percentile. That choice is the most consequential definition in the
# project, so it is swept across its whole range rather than asserted.

# %%
figure("fig_05_sensitivity_curve.png",
       "The headline across every threshold from 0% to 20%. The finding holds "
       "across the range; it does not balance on one cutoff.")

# %% [markdown]
# **The external check.** A 2010 study (Masoso & Grobler) measured out-of-hours
# consumption in commercial buildings and reported 56%. Running *their*
# clock-based definition on *our* data tests whether this pipeline measures what
# it claims to.

# %%
table("phase5_published_comparison.csv",
      "55.2% for Academic and 55.0% for Library against a published 56%.")

# %% [markdown]
# ### Phase 6 — the anomaly experiment (RQ3)
#
# Real faults are not labelled in I-BLEND, so anomalies of known shape are
# injected into the held-out test period: **spikes**, and **waste events** —
# sustained elevated consumption while a building is nearly empty, which is the
# thing the project actually cares about.

# %%
figure("fig_06_injected_waste_example.png",
       "An injected waste event against the expected-power baseline.")

# %% [markdown]
# Two detectors read two models' residuals. **Detector T** uses model B (time
# only); **Detector O** uses model C (time + occupancy).

# %%
table("phase6_pooled_answer.csv")

# %% [markdown]
# **The first row is the interesting one.** On the comparison this project
# originally specified — a fixed z > 3 cutoff — the occupancy-aware detector
# comes out **worse**. That is reported first rather than buried, then
# explained: a fixed threshold lets the two detectors fire at different rates,
# so it measures how *often* each alarms as much as how well it ranks.
#
# Fix the comparison rather than the threshold — same alert budget, or no
# threshold at all — and Detector O wins every time. By one to three points, and
# by **5.5** on whether a sustained waste event is noticed at all. That last row
# is the one worth keeping: occupancy does little for spikes, but it is exactly
# what distinguishes a steady 20 kW draw at 2 p.m. from the same draw at 2 a.m.

# %%
figure("fig_06_detector_comparison.png",
       "Detector T against Detector O across all four framings.")

# %% [markdown]
# ### Phase 8 — how much of the waste is just air conditioning?
#
# This phase exists to close the project's largest caveat. The physics check
# came first: cooled buildings should climb above roughly 25 °C, and a building
# that is mostly switched off should not.

# %%
figure("fig_08_temperature_response.png",
       "Facilities climbs +62% from mild to hot weather; Lecture falls -12%. "
       "That is the negative control working.")

# %%
table("phase8_temperature_response.csv")

# %% [markdown]
# Within low-occupancy intervals only, power is regressed on **cooling degree
# hours** with hour of day controlled for. The intercept is consumption drawn
# regardless of weather — a controls problem. The slope times the degree hours
# is cooling an empty building — a setpoint problem.

# %%
figure("fig_08_waste_decomposition.png")
table("phase8_waste_decomposition.csv")

# %% [markdown]
# **Cooling accounts for only 1–9%** of the power drawn while a building is
# nearly empty, in the four buildings where the split can be identified at all.
# So the waste is a scheduling and controls problem — equipment running on a
# timetable nobody revisits — rather than a thermostat problem, and the remedy
# is correspondingly cheaper.
#
# Library and Lecture report "not identifiable" rather than a number: both are
# shut during the hot months, so within their low-occupancy sample season and
# usage are confounded and the fitted slope goes negative. A negative cooling
# share would be nonsense, so it is not reported as one.

# %% [markdown]
# **And it sharpened RQ2.** Occupancy and heat are both seasonal, and this
# campus empties in exactly the months Delhi is hottest — so part of what looked
# like an occupancy effect was summer in disguise.

# %%
figure("fig_08_occupancy_vs_weather.png",
       "Occupancy is worth +0.107 validation R-squared when the weather is "
       "unknown, and only +0.078 once it is known -- a 27% shrinkage.")

# %% [markdown]
# ### Every judgement call, logged
#
# Section 7 of the report is a table with one row per decision: the options
# considered, the one chosen, the reason, and the effect on the results. Logging
# all of them — including the dull ones — removes the option of quietly picking
# whichever choice made a finding look better. Several entries record decisions
# that made the result *smaller*.

# %%
decisions = pd.read_csv("results/decision_log.csv")
print(f"{len(decisions)} decisions logged across {decisions['phase'].nunique()} phases\n")
print(decisions.groupby("phase").size().to_string())
print("\nA sample:\n")
for _, row in decisions.sample(3, random_state=0).iterrows():
    print(f"  [{row['id']}] {row['decision']}")
    print(f"      chosen: {row['chosen']}")
    print()

# %% [markdown]
# ## 5. Did running on a different stack change any number?
#
# This is the step that matters most.
#
# The project's central claim is that **every number in its report came from
# executed code** on a known stack. This notebook just re-ran that code on a
# different pandas, numpy and scikit-learn. If the results moved, that has to be
# visible rather than quietly published.
#
# Every regenerated table is compared against the committed one, cell by cell,
# with floats compared to a tolerance rather than by exact equality.

# %%
import numpy as np


def compare(published: Path, regenerated: Path, tol: float = 1e-6) -> tuple[str, str]:
    """Compare two CSVs. Returns (verdict, detail)."""
    a = pd.read_csv(published)
    b = pd.read_csv(regenerated)

    if list(a.columns) != list(b.columns):
        return "COLUMNS", f"{len(a.columns)} -> {len(b.columns)}"
    if len(a) != len(b):
        return "ROWS", f"{len(a)} -> {len(b)}"

    worst, where = 0.0, ""
    for col in a.columns:
        if pd.api.types.is_numeric_dtype(a[col]) and pd.api.types.is_numeric_dtype(b[col]):
            x, y = a[col].to_numpy(dtype="float64"), b[col].to_numpy(dtype="float64")
            both_nan = np.isnan(x) & np.isnan(y)
            diff = np.where(both_nan, 0.0, np.abs(x - y))
            if np.isnan(diff).any():
                return "NaN", f"{col}: NaN pattern differs"
            if diff.max() > worst:
                worst, where = float(diff.max()), col
        else:
            if not a[col].astype(str).equals(b[col].astype(str)):
                return "TEXT", f"{col} differs"

    if worst == 0:
        return "IDENTICAL", ""
    if worst <= tol:
        return "IDENTICAL", f"max |diff| {worst:.2e} in {where}"
    return "MOVED", f"max |diff| {worst:.6g} in {where}"


rows = []
for published in sorted(PUBLISHED.glob("*.csv")):
    regenerated = Path("results") / published.name
    if not regenerated.is_file():
        rows.append((published.name, "MISSING", "not regenerated"))
        continue
    verdict, detail = compare(published, regenerated)
    rows.append((published.name, verdict, detail))

drift = pd.DataFrame(rows, columns=["file", "verdict", "detail"])

counts = drift["verdict"].value_counts()
print(f"compared {len(drift)} result tables against the published copies\n")
for verdict, n in counts.items():
    print(f"  {verdict:10s} {n}")

# %%
moved = drift[~drift["verdict"].isin(["IDENTICAL"])]

if moved.empty:
    print("Every regenerated table matches the published one.")
    print()
    print("That is a real portability result: the findings do not depend on the")
    print("exact library versions they were produced with.")
else:
    print("These tables differ from the published copies:")
    print()
    print(moved.to_string(index=False))
    print()
    print("Not necessarily an error -- library versions change how ties are")
    print("broken, how floats accumulate, and how some estimators initialise.")
    print("What matters is that the difference is named rather than hidden.")
    print("requirements.txt remains the canonical stack for the report.")

# %% [markdown]
# ## 6. (Optional) Run the dashboard
#
# This serves the Streamlit app from the Colab runtime and opens a temporary
# public URL through a Cloudflare tunnel. The URL lives only as long as this
# runtime does.
#
# A permanent deployment is linked from the repository's README.
#
# Set `RUN_DASHBOARD = True` and run the cell to start it.

# %%
RUN_DASHBOARD = False

if RUN_DASHBOARD:
    subprocess.run(
        "wget -q -O /tmp/cloudflared "
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-linux-amd64 && chmod +x /tmp/cloudflared",
        shell=True, check=True,
    )

    subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
         "--server.port", "8501", "--server.headless", "true"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(8)

    tunnel = subprocess.Popen(
        ["/tmp/cloudflared", "tunnel", "--url", "http://localhost:8501"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    print("starting tunnel...\n")
    for line in tunnel.stdout:
        if "trycloudflare.com" in line:
            print(line.strip())
            break
else:
    print("Set RUN_DASHBOARD = True above to serve the dashboard.")

# %% [markdown]
# ## Where to read more
#
# | | |
# |---|---|
# | **The summary** | [`docs/PROJECT_SUMMARY.md`](https://github.com/rajshinde0/Smartgrid/blob/main/docs/PROJECT_SUMMARY.md) — the whole project in ~5,800 words |
# | **The full report** | [`docs/PROJECT_REPORT.md`](https://github.com/rajshinde0/Smartgrid/blob/main/docs/PROJECT_REPORT.md) — 14 sections, every number generated from code |
# | **What went wrong** | [`docs/bugFix1.md`](https://github.com/rajshinde0/Smartgrid/blob/main/docs/bugFix1.md) and [`bugFix2.md`](https://github.com/rajshinde0/Smartgrid/blob/main/docs/bugFix2.md) — two rounds of code review |
# | **Every judgement call** | Section 7 of the report: a 46-row decision log |
#
# **Data source.** Rashid, H., Singh, P. & Singh, A. (2019). *I-BLEND, a
# campus-scale commercial and residential buildings electrical energy dataset.*
# Scientific Data 6, 190015.
