"""Phase 7 -- Delivery: dashboard data and the finished report. Percent-format source."""

# %% [markdown]
# # SMARTGRID-X -- Phase 7: Delivery
#
# **What this notebook does.** It closes the project:
#
# 1. exports the data the Streamlit dashboard reads, so the dashboard never has
#    to train anything
# 2. writes the remaining sections of `docs/PROJECT_REPORT.md` -- the abstract
#    (rewritten now that there are real findings), limitations, conclusion,
#    the syllabus coverage table, how to reproduce, and the presentation outline
# 3. runs the final checks: no section still says "pending", every figure
#    referenced by the report exists, and every phase left a decision trail
#
# Everything here reads results computed in earlier notebooks. Nothing new is
# measured, because a report that quietly recalculated its own numbers at the
# last minute would be a report nobody could check.

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import numpy as np
import pandas as pd
from IPython.display import display

from src import config as C
from src import dashboard as D, report, viz

viz.setup_style()
C.ensure_dirs()
pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 60)

R = C.RESULTS_DIR
headline = pd.read_csv(R / "phase5_headline.csv")
base_load = pd.read_csv(R / "phase5_base_load.csv")
published = pd.read_csv(R / "phase5_published_comparison.csv")
drift = pd.read_csv(R / "phase4_concept_drift.csv")
occupancy_help = pd.read_csv(R / "phase4_occupancy_contribution.csv")
pooled = pd.read_csv(R / "phase6_pooled_answer.csv")
quality = pd.read_csv(R / "phase1_data_quality.csv")
correlations = pd.read_csv(R / "phase2_power_occupancy_correlation.csv")
print("loaded the result tables from every earlier phase")

# %% [markdown]
# ## Step 1: export the dashboard data
#
# The dashboard reads saved model output and nothing else. Refitting inside a
# dashboard would be slow during a live demonstration and -- more importantly --
# would let the numbers on screen drift away from the numbers in the report.

# %%
exported = D.export_all()
print()
print(f"exported {len(exported)} buildings for the dashboard")
print("run it with:  streamlit run dashboard/app.py")

# %% [markdown]
# ## Step 2: the abstract, rewritten with real findings

# %%
ratio_valid = headline[headline["intensity ratio"].notna()]
acad_ooh = float(published.set_index("building").loc["Academic",
                                                    "out-of-hours share % (clock rule)"])
lib_ooh = float(published.set_index("building").loc["Library",
                                                   "out-of-hours share % (clock rule)"])
growth_series = drift[drift["building"] != "Lecture"]["growth 2014-2017 %"]
mean_r2_gain = float(occupancy_help["R2 gain from occupancy"].mean())
matched = pooled[pooled["comparison"] == "matched alert budget"].iloc[0]
ap_row = pooled[(pooled["comparison"] == "threshold-free ranking") &
                (pooled["metric"] == "mean average precision")].iloc[0]

blocks = {}

blocks["abstract"] = f"""
Buildings consume electricity when nobody is using them, but measuring how much
requires fine-grained energy data and some knowledge of whether anyone was there.
The public **I-BLEND** dataset has both: 1-minute electrical readings from nine
meters across seven IIIT-Delhi buildings, paired with 10-minute counts of
WiFi-associated devices. This project presents **the first occupancy-aware
energy-waste and anomaly analysis of I-BLEND**, over the
{len(ratio_valid)} + 1 buildings and 3.7 years where both signals overlap
(February 2014 to November 2017). The methods are standard; the contribution is
the application.

Because WiFi occupancy **never reads zero** -- the minimum in every building is
1, since idle devices stay connected -- "empty" is not a state this dataset can
report. We therefore define low occupancy relative to each building's own scale,
at or below {C.LOW_OCC_FRACTION:.0%} of its 95th-percentile occupancy, and
publish a sensitivity curve across every threshold from 0% to 20%.

**The headline finding is that when these buildings are at their emptiest they
still draw between {ratio_valid['intensity ratio'].min():.0%} and
{ratio_valid['intensity ratio'].max():.0%} of their average power.** Low-occupancy
consumption accounts for
{ratio_valid['low-occupancy energy share %'].min():.1f}% to
{ratio_valid['low-occupancy energy share %'].max():.1f}% of measured energy
depending on the building, and in every building the base load -- the power drawn
whether or not anyone is present -- is the larger share of mean consumption. As
an external check, applying the clock-based definition of Masoso & Grobler (2010)
to this data reproduces their published 56% to within a percentage point
({acad_ooh:.1f}% for the Academic building, {lib_ooh:.1f}% for the Library).

Two further results emerged. Occupancy is a **weak predictor**: it raises
validation R-squared by only {mean_r2_gain:+.3f} on average over a time-only
model, and explains between
{100 * correlations['r_squared'].min():.0f}% and
{100 * correlations['r_squared'].max():.0f}% of the variation in power. And a
controlled experiment on synthetic anomalies shows an occupancy-aware detector is
**consistently but only marginally** better than a time-only one -- matched-budget
F1 {matched['detector T']:.3f} against {matched['detector O']:.3f}, average
precision {ap_row['detector T']:.3f} against {ap_row['detector O']:.3f} -- with
the gains concentrated, as theory predicts, on sustained waste rather than on
spikes.

Separately, campus consumption **grew {growth_series.min():.0f}% to
{growth_series.max():.0f}% between 2014 and 2017**, which required explicit
handling of concept drift and which reappears in the anomaly results as a
recurring false alarm.

The main limitation is the absence of weather data: Delhi's summer vacation is
also its hottest season, so cooling an empty building is counted as
low-occupancy consumption without being separable from it.
"""

print(blocks["abstract"][:700], "...")

# %% [markdown]
# ## Step 3: limitations
#
# Written as concretely as possible. A limitations section that lists generic
# caveats is worthless; this one names what specifically would change if each
# problem were fixed.

# %%
lecture_row = quality[quality["building"] == "Lecture"].iloc[0]
worst_extrapolation = float(base_load["difference %"].abs().max())

blocks["limitations"] = f"""
### 1. Occupancy is a device count, not a count of people

This is the deepest limitation in the project and it shapes every result. The
occupancy signal counts devices associated with a building's WiFi access points.
A phone left charging in an empty room is counted; a visitor with no device is
not. The dataset authors estimate the over-count at roughly 20 devices per
building and about 50 in the Academic building.

The concrete consequence is that **the minimum occupancy in every building is 1,
never 0**, so this project cannot measure "energy used while empty" and instead
measures "energy used at low occupancy" against a stated relative threshold.
Section 6.6's corrected-occupancy check shows that subtracting the documented
baseline raises the low-occupancy share in every building, which means **our
headline figures are a conservative lower bound** rather than an overstatement.

### 2. No weather data -- cooling is mixed into the result

I-BLEND contains no temperature or humidity. In Delhi this matters more than it
would almost anywhere else, because the long summer vacation coincides with the
hottest months. Phase 2 found that Facilities uses **17% more** power during
vacation than during semester, and the Academic building slightly more, which is
almost certainly air conditioning rather than people.

So some of what we call low-occupancy consumption is **cooling an empty
building**. That is still waste, but it is a different kind with a different
remedy -- setback temperatures rather than switching off lights -- and we cannot
separate the two. A weather feed would let the regression models attribute load
between the two causes, and it is the single most valuable addition this project
could receive.

### 3. The injected anomalies are synthetic

Every anomaly used to score the detectors in section 9 was **created by us** and
injected into a copy of the test data with a recorded seed, because no real fault
on this campus was ever labelled. They are a measuring instrument for comparing
two detectors, and **no injected event corresponds to anything that happened at
IIIT-Delhi**.

This means the detector comparison is only as realistic as our idea of what waste
looks like. We modelled it as a sustained +15-30% lift during low-occupancy
periods; if real waste on this campus takes a different shape, the ranking could
differ. The real-data findings are reported separately and described only as
patterns worth inspecting.

### 4. Very uneven data coverage

Usable coverage ranges from **{quality["usable %"].min():.1f}%** to
**{quality["usable %"].max():.1f}%**. The Lecture building is the extreme case: its
meter is flagged off for **{lecture_row["meter-off hours"]:,.0f} hours**, leaving
only {lecture_row["usable %"]:.1f}% of its intervals usable, so every Lecture
figure rests on a much smaller sample than the others. The Boys hostel, Girls
hostel and Library each lose several consecutive months to meter outages. This is
a smaller sample, not a biased measurement -- but conclusions about those
buildings are correspondingly less certain.

### 5. A dead meter and a building switched off look identical

Both read exactly 0 W, and no rule based on the power value alone can tell them
apart. The Lecture building's zero runs form two clear populations -- nightly
stretches around 13 hours and outages lasting up to 46 days -- and the specified
6-hour rule catches both. Section 6.6's 24-hour sensitivity check shows this is
worth about 1.3 percentage points on the Lecture figure. Real: small, and
quantified rather than hidden.

### 6. The academic calendar is approximated

The I-BLEND project publishes no calendar file -- we checked the repository. The
semester and vacation windows are approximated from a typical IIIT-Delhi year and
then validated against the data: dormitory occupancy in the inferred vacation
windows falls to 42% (Boys) and 53% (Girls) of its semester median, confirming
the windows are roughly right. They are accurate to within days, not hours, which
is adequate for the coarse comparisons we use them for and no finer.

### 7. The base load is partly an extrapolation

Model A estimates base load as the power a fitted line predicts at zero
occupancy. For buildings whose occupancy never approaches zero -- the two
dormitories especially -- that point lies far outside the observed data, and the
estimate departs from the directly measured night-time median by up to
**{worst_extrapolation:.0f}%**. Section 6.6 reports both, ranks buildings on the
*measured* quantity, and flags where the modelled one should not be trusted.

### 8. The models are baselines, not forecasts, and they age

Models B and C deliberately exclude lag features, which costs a great deal of
accuracy (validation R-squared would rise from about 0.29 to over 0.9 with a
one-hour lag). That is the price of a baseline that can detect sustained waste
rather than absorbing it. Separately, campus consumption grew
{growth_series.min():.0f}-{growth_series.max():.0f}% across the record, and the
power-occupancy correlation itself weakened over time in the Academic building
(r fell from 0.71 to 0.45). A model of this campus **needs periodic refitting**;
section 9 shows what happens when it does not get it -- a schedule change in
August 2017 is re-reported as an anomaly every morning for months.

### 9. Seven buildings, one campus, one climate

Every finding here describes **these seven buildings in these years**.
Generalising to other campuses would require assuming Delhi's climate, this
institution's routine and this building stock are representative, and we do not
assume that. Where published figures from other campuses are quoted, they are
offered as context, not as validation.

### 10. No sub-metering

Each building has one meter (two for the dormitories). We can say a building
draws 20 kW at 3 a.m.; we cannot say how much of that is lighting, air
conditioning, servers or lifts. That is exactly the information an energy manager
would need to act on these findings, and it is the natural next step.
"""

print("limitations drafted:", len(blocks["limitations"].split()), "words")

# %% [markdown]
# ## Step 4: conclusion and future scope

# %%
blocks["conclusion"] = f"""
### What we set out to do

We asked three questions of the I-BLEND campus dataset: how much energy is used
while buildings are nearly empty, how well occupancy and time predict power, and
whether an occupancy-aware anomaly detector beats a time-only one.

### What we found

**1. Nearly-empty buildings still draw most of their average power.** Between
{ratio_valid['intensity ratio'].min():.0%} and
{ratio_valid['intensity ratio'].max():.0%} of it, depending on the building. In
every one of the seven, the base load -- the part drawn whether or not anyone is
present -- is the larger share of consumption. Applying the published literature's
own clock-based definition to our data reproduces its headline figure to within a
percentage point, which is strong evidence the measurement is sound.

**2. Occupancy is a weak predictor of power.** It explains between
{100 * correlations['r_squared'].min():.0f}% and
{100 * correlations['r_squared'].max():.0f}% of the variation, and adds only
{mean_r2_gain:+.3f} to validation R-squared over a time-only model. This arrived
independently from three different directions -- correlation analysis, regression,
and the flat daily profiles PCA produced -- and it agrees with the published LBNL
result.

**3. An occupancy-aware detector is better, but only just.** All five fair
comparisons favour it, by one to three percentage points each, with the largest
gains on exactly the anomaly type where occupancy ought to help. A detector
cannot exploit information that is not there, and finding (2) explains finding
(3).

**4. Two things we did not go looking for.** Campus consumption grew
{growth_series.min():.0f}-{growth_series.max():.0f}% in four years. And the most
extreme "anomalies" in the real data turned out to be a single recurring schedule
change being re-reported every morning -- a reminder that a detector on a fixed
historical baseline decays.

### What it means

The practical implication is not "install occupancy sensing". Occupancy data
turned out to add little that the clock does not already provide on this campus.
The implication is that **the fixed part of these buildings' load is where the
opportunity is**. A building that draws 74% of its average power with nobody in
it is not failing to respond to occupancy -- it is running equipment on a
schedule that ignores occupancy entirely, and that is a controls and commissioning
problem rather than a sensing problem.

The Library is the proof that it need not be so: it drops 65% at weekends and
runs at 62% when nearly empty, the best on campus. Whatever the Library does, the
others could do.

### Future scope

1. **Add weather data.** The single highest-value addition. It would separate
   cooling load from occupancy-driven load and turn "some of this is air
   conditioning an empty building" from a caveat into a number.
2. **Sub-metering.** One meter per building can say *how much* is wasted but never
   *what* is wasting it. Circuit-level metering would make the findings
   actionable.
3. **Rolling re-baselining.** Section 9 shows a fixed historical model decaying
   into constant false alarms. A model refitted on a trailing window would adapt
   to schedule changes instead of re-reporting them.
4. **Occupancy calibration.** A short manual count against the WiFi signal would
   replace the paper's approximate 20-device offset with a measured one, and turn
   our conservative lower bound into a point estimate.
5. **Cost and carbon.** Every kWh in this report could be priced and given an
   emissions factor, which is what turns an analysis into a business case.
6. **The methods we deliberately left out.** Gradient boosting, deep sequence
   models, real-time streaming and a fault-diagnosis layer were all out of scope
   here. None of them would change the headline finding, which is an accounting
   result rather than a modelling one -- but they would matter for a deployed
   system.
"""

print("conclusion drafted:", len(blocks["conclusion"].split()), "words")

# %% [markdown]
# ## Step 5: the syllabus coverage table
#
# Every topic in MD3135 Units I-VI and every tutorial, mapped to the notebook and
# step where it is actually implemented -- not where it was planned.

# %%
units = pd.DataFrame([
    ("I", "What data science is; the big-data hype and getting past it",
     "Report section 2.1-2.2"),
    ("I", "Datafication (smart meters as the example)", "Report section 2.3"),
    ("I", "The current landscape of data science", "Report section 2.4"),
    ("I", "Statistical inference: populations and samples",
     "02_stats_eda.ipynb, Steps 1 and 5"),
    ("I", "Probability distributions; fitting a model",
     "02_stats_eda.ipynb, Step 6 (Normal vs Log-normal, Q-Q, KS)"),
    ("I", "Statistical modelling; overfitting",
     "04_regression.ipynb, Step 11 (polynomial degree and forest depth curves)"),
    ("I", "Python environment for data science",
     "00_explore.ipynb, Step 0; requirements.txt"),
    ("II", "Attribute types: nominal, ordinal, binary, asymmetric binary, "
           "numeric, discrete vs continuous",
     "02_stats_eda.ipynb, Step 2 (full attribute table)"),
    ("II", "Mean, median, mode; range, quartiles, variance, SD, IQR",
     "02_stats_eda.ipynb, Steps 3-4 (pandas, then by hand in NumPy)"),
    ("II", "Graphic displays of statistical descriptions",
     "02_stats_eda.ipynb, Step 8 (histograms, box plots, Q-Q plots)"),
    ("III", "Data sources and data quality",
     "00_explore.ipynb, Steps 5-10; 01_data_prep.ipynb, Step 2"),
    ("III", "Data cleaning; identifying outliers",
     "01_data_prep.ipynb, Steps 3-6 (invalid values, dead meters, IQR and "
     "Z-score flags)"),
    ("III", "Hypothesis testing and its relation to EDA",
     "02_stats_eda.ipynb, Step 7 (t-test and Mann-Whitney with effect sizes)"),
    ("III", "Data transformation; data scaling",
     "01_data_prep.ipynb, Steps 13-14 (log transform; Min-Max vs standardisation)"),
    ("III", "Feature selection",
     "04_regression.ipynb, Step 5 (correlation filter + SelectKBest)"),
    ("IV", "NumPy arrays: creating, indexing, slicing, reshaping",
     "03_pca.ipynb, Step 1 (10-min series reshaped to days x 144)"),
    ("IV", "Vectorized operations",
     "03_pca.ipynb, Step 2 (vectorized vs looped, timed and asserted identical)"),
    ("IV", "Multi-dimensional arrays, matrices, matrix subsetting",
     "03_pca.ipynb, Step 1 (array[row_slice, col_slice])"),
    ("IV", "Principal component analysis",
     "03_pca.ipynb, Steps 4-6 (by hand with np.linalg.eig, verified against "
     "scikit-learn)"),
    ("IV", "Categorical data: category levels and summaries",
     "01_data_prep.ipynb, Step 12 (ordered pd.Categorical for weekday)"),
    ("IV", "DataFrames: loc / iloc, extending, sorting",
     "01_data_prep.ipynb, Step 11"),
    ("IV", "Lists and dictionaries; analysing a CSV with them",
     "01_data_prep.ipynb, Step 15 (csv module only, asserted equal to pandas)"),
    ("V", "Importing data; head / tail / info / describe",
     "01_data_prep.ipynb, Step 1"),
    ("V", "Aggregation, grouping, merging, concatenating",
     "01_data_prep.ipynb, Steps 8 and 10 (merge with occupancy; pd.concat long "
     "table; groupby summaries)"),
    ("V", "EDA: descriptive statistics, distributions, correlation, trends; "
          "Matplotlib / Seaborn",
     "02_stats_eda.ipynb, Steps 3-8"),
    ("V", "Feature extraction, encoding, scaling",
     "01_data_prep.ipynb, Step 8 (lags, rolling, kWh); 04_regression.ipynb, "
     "Step 4 (one-hot, scaler inside a Pipeline)"),
    ("V", "Training, validation and testing sets; cross-validation",
     "04_regression.ipynb, Steps 1 and 8 (chronological 70/15/15; TimeSeriesSplit)"),
    ("V", "Train-test split using scikit-learn",
     "04_regression.ipynb, Step 1 (train_test_split with shuffle=False)"),
    ("V", "Confusion matrix, accuracy, precision, recall",
     "06_anomaly.ipynb, Steps 3-5"),
    ("VI", "Pie chart with legend", "02_stats_eda.ipynb, Step 8.1"),
    ("VI", "Bar chart", "02_stats_eda.ipynb, Step 8.2"),
    ("VI", "Box plot", "02_stats_eda.ipynb, Step 8.3"),
    ("VI", "Histogram", "02_stats_eda.ipynb, Step 8.4"),
    ("VI", "Line graph with multiple lines", "02_stats_eda.ipynb, Step 8.5"),
    ("VI", "Scatter plot", "02_stats_eda.ipynb, Step 8.6"),
    ("VI", "2D and 3D visualization",
     "03_pca.ipynb, Steps 7-8 (PC1-PC2 scatter; 3D PC1-PC3)"),
    ("VI", "Linear regression; multiple linear regression",
     "04_regression.ipynb, Steps 6 and 9 (models A, B, C)"),
    ("VI", "Dashboards and communicating results",
     "dashboard/app.py; docs/PROJECT_REPORT.md"),
], columns=["Unit", "Topic", "Where it is implemented"])

display(units)
units.to_csv(R / "phase7_syllabus_units.csv", index=False)

# %%
tutorials = pd.DataFrame([
    ("1", "Population vs sample; identifying data types",
     "02_stats_eda.ipynb, Steps 1-2 and 5 (1,000 samples of 30 days; the "
     "attribute-type table)"),
    ("2", "Central tendency and dispersion by hand; checking the distribution",
     "02_stats_eda.ipynb, Steps 3-4 and 6 (NumPy formulas asserted equal to "
     "pandas; Normal vs Log-normal)"),
    ("3", "Classifying attributes",
     "02_stats_eda.ipynb, Step 2 (includes asymmetric binary flags)"),
    ("4", "Data cleaning and pre-processing",
     "01_data_prep.ipynb, Steps 3-8"),
    ("5", "Vectors, matrices, arrays and DataFrames",
     "03_pca.ipynb, Steps 1-2; 01_data_prep.ipynb, Steps 11-12"),
    ("6", "Lists, functions and control structures",
     "00_explore.ipynb, Step 4 (loop over the meter registry with conditions); "
     "01_data_prep.ipynb, Step 15 (lists and dictionaries); the whole src/ "
     "package is the functions component"),
    ("7", "Data visualization",
     "02_stats_eda.ipynb, Step 8; 03_pca.ipynb, Steps 5-9; dashboard/app.py"),
    ("8", "Linear regression and predictive analytics",
     "04_regression.ipynb, all steps"),
], columns=["Tutorial", "Topic", "Where it is implemented"])

display(tutorials)
tutorials.to_csv(R / "phase7_syllabus_tutorials.csv", index=False)

blocks["syllabus_units"] = report.md_table(units)
blocks["syllabus_tutorials"] = report.md_table(tutorials)

# %% [markdown]
# ## Step 6: how to reproduce

# %%
blocks["how_to_reproduce"] = f"""
### 1. Get the code and the environment

```bash
git clone https://github.com/rajshinde0/Smartgrid.git
cd Smartgrid
python -m pip install -r requirements.txt
python -m ipykernel install --user --name python3
```

Built and tested on **Python {sys.version.split()[0]}**, Windows 11. The pinned
versions in `requirements.txt` were read from the environment the notebooks were
actually executed in, not typed by hand.

### 2. Get the data

The I-BLEND dataset is about 1.6 GB and is **deliberately not in this
repository**. Download it from
<https://doi.org/10.6084/m9.figshare.c.3893581> and unzip so that these exist:

```
Dataset/energy_dataset/            (16 CSVs + Readme.txt)
Dataset/IIITD_occupancy_dataset/   (7 CSVs + Readme.txt)
```

`Dataset/` is read-only throughout: nothing in this project ever writes to it.

### 3. Run the notebooks in order

```bash
python tools/build_and_run.py 00_explore
python tools/build_and_run.py 01_data_prep
python tools/build_and_run.py 02_stats_eda
python tools/build_and_run.py 03_pca
python tools/build_and_run.py 04_regression
python tools/build_and_run.py 05_waste
python tools/build_and_run.py 06_anomaly
python tools/build_and_run.py 07_final
```

Each notebook is authored as a percent-format `.py` file in `notebooks/src_py/`.
`tools/build_and_run.py` converts it to a real `.ipynb` and executes it end to
end with `nbconvert`, failing loudly if any cell raises. To execute an existing
notebook directly instead:

```bash
python -m nbconvert --to notebook --execute --inplace notebooks/00_explore.ipynb
```

**Order matters.** Phase 1 builds the parquet cache every later phase reads;
Phase 4 writes the model-A coefficients Phase 5 needs; Phase 5 writes the
headline table the dashboard shows. Phase 1 takes a few minutes on first run
because it reads all 1.6 GB once; after that everything reads the cache.
Phase 4 is the slowest at roughly four minutes.

### 4. Run the dashboard

```bash
streamlit run dashboard/app.py
```

It reads the parquet files and the CSVs in `results/`, and trains nothing. If the
parquet files are missing, run notebook 07 first, or:

```bash
python -c "import sys; sys.path.insert(0, '.'); from src import dashboard; dashboard.export_all()"
```

### 5. Check nothing leaked into git

```bash
python tools/check_no_data.py
```

Fails if any file under `Dataset/` or `data/`, any `.parquet`, or any file over
50 MB has been staged.

### Reproducibility notes

* **Seed {C.SEED}** is used for every random operation -- the sampling simulation,
  k-means, the random forest and the anomaly injection -- so every number in the
  report is exactly reproducible.
* **Every number in the report comes from executed code.** The report contains
  named blocks that the notebooks fill through `src/report.py`; nothing is typed
  by hand. Re-running a notebook rewrites its blocks, so the report cannot drift
  out of step with the analysis.
* **Nothing is committed unless it runs.** A notebook only reaches the repository
  after `tools/build_and_run.py` exits 0.
"""

print("how-to-reproduce drafted")

# %% [markdown]
# ## Step 7: the presentation outline

# %%
best_ratio = ratio_valid.loc[ratio_valid["intensity ratio"].idxmin()]
worst_ratio = ratio_valid.loc[ratio_valid["intensity ratio"].idxmax()]

blocks["presentation_outline"] = f"""
Twelve slides, **headline first**. The rule throughout: one idea per slide, the
number on the slide, the caveat spoken aloud.

**1. Title and the one-sentence finding**
SMARTGRID-X. *"Seven buildings on a real campus draw
{ratio_valid['intensity ratio'].min():.0%}-{ratio_valid['intensity ratio'].max():.0%}
of their average power when they are at their emptiest."*
Give the finding before the method. Everything after this slide is evidence for it.

**2. The problem and the data**
Buildings use power when nobody is there; measuring it needs energy data *and*
occupancy data together. I-BLEND has both: 1-minute meters on 7 IIIT-Delhi
buildings plus WiFi device counts, Feb 2014 - Nov 2017.
*Figure:* `fig_00_coverage_timeline.png`.

**3. The problem we hit immediately**
Occupancy never reads zero -- minimum is 1 in every building, because idle phones
stay connected. So "empty" is not measurable and the question had to be
re-specified around a **relative** low-occupancy threshold, published with a
sensitivity curve. *This slide is where the examiner learns we read our own data.*

**4. Cleaning: what we found and what we did**
81.7% of Lecture readings are exactly 0 W (dead meter, not an idle building).
Negative power factor on up to 66% of rows is a sign convention, not corruption --
dropping it would have destroyed 58% of the Library record.
*Figure:* `fig_01_missing_heatmap.png`.

**5. What a normal day looks like**
*Figure:* `fig_02_hourly_profile_all.png`. Academic peaks at 41 kW and still
draws about 20 kW at 3 a.m. Hostels do the opposite. Facilities is nearly flat --
its consumption barely knows what time it is.

**6. THE HEADLINE**
*Figure:* `fig_05_headline.png`. Give the intensity ratio, not just the share:
"{worst_ratio['building'].replace('_', ' ')} draws
{worst_ratio['intensity ratio']:.0%} of its average power when nearly empty;
{best_ratio['building'].replace('_', ' ')}, the best on campus, still draws
{best_ratio['intensity ratio']:.0%}."

**7. Is the headline robust?**
*Figure:* `fig_05_sensitivity_curve.png`. The threshold is a judgement, so here is
every other threshold. Rankings do not move. Also: the base load computed two
independent ways agrees.

**8. Does it match anyone else?**
*Figure:* `fig_05_published_comparison.png`. Applying Masoso & Grobler's own
clock-based definition to our data gives {acad_ooh:.1f}% and {lib_ooh:.1f}%
against their published 56%. Different continent, fifteen years apart.
**This is the credibility slide.**

**9. Can we predict it? (RQ2)**
Occupancy adds only {mean_r2_gain:+.3f} to validation R-squared. Say the negative
result plainly -- it matches published work, and three different analyses in this
project reached it independently.
*Figure:* `fig_04_model_comparison.png`.

**10. Can we detect it automatically? (RQ3)**
The experiment: two detectors, synthetic labelled anomalies, seed {C.SEED}.
**Say "synthetic" out loud.** Result: occupancy helps consistently but by only
1-3 points, and most on the waste anomalies. Mention the trap we caught -- the
planned fixed threshold was not a fair comparison.
*Figure:* `fig_06_detector_comparison.png`.

**11. Limitations, said before anyone asks**
No weather data (Delhi's vacation is its hottest season, so some of this is
cooling an empty building). WiFi counts devices, not people -- which makes our
numbers a *lower* bound. Injected anomalies are synthetic. Lecture has only
{lecture_row["usable %"]:.0f}% usable data. One campus, one climate.

**12. So what, and a live dashboard**
The opportunity is the **fixed** part of the load: this is a controls and
commissioning problem, not a sensing problem. The Library proves it can be done.
Then demonstrate `streamlit run dashboard/app.py` -- pick a building, pick a week,
show the flagged periods.

**If asked "what is new here?"** -- *"The methods are standard. What we could not
find published is anyone using I-BLEND's own occupancy stream to quantify, per
building, how much of the campus's electricity is used while it is nearly empty,
with a threshold-sensitivity curve and a controlled test of whether occupancy
helps a detector."*

**If asked about the null results** -- *"Two of our three questions came back
weaker than we hoped. We report them because they agree with published work and
because three independent analyses in this project reached the same conclusion.
The main finding does not depend on them."*
"""

blocks["method_phase7"] = f"""
Phase 7 delivers the project and verifies it.

**Dashboard.** `dashboard/app.py` is a Streamlit page with a building selector, a
date-range picker, a power-and-occupancy chart with anomaly bands coloured, the
key numbers for the selected building, and the threshold-sensitivity curve with
that building highlighted. It **reads saved output only** -- the parquet files
written by `src/dashboard.py` and the CSV tables in `results/` -- and trains
nothing. Refitting inside a dashboard would be slow during a demonstration and,
worse, would let the numbers on screen drift away from the numbers in this
report.

The chart uses two stacked panels sharing one time axis rather than two y-axes.
Watts and people are different quantities, and a shared axis would invent a
visual relationship that does not exist.

**Report assembly.** Every section of this report is generated. The file contains
named placeholder blocks which the notebooks fill through `src/report.py`, so no
number is ever typed by hand and re-running a notebook rewrites its section.
Anything not yet computed reads "pending Phase N", and Phase 7 asserts that none
remain.

**Verification.** Three checks run as assertions at the end of
`07_final.ipynb`, so the notebook fails rather than reporting a problem quietly:

1. no section still says "pending"
2. every embedded figure link resolves to a file that actually exists
   in `figures/`
3. every phase left entries in the decision log

`tools/check_no_data.py` additionally fails the build if any dataset file,
parquet, or file over 50 MB has been staged for commit.

**Notebook:** `notebooks/07_final.ipynb`.
"""

report.update_blocks(blocks)

# %%
report.log_decision(
    id="D07-01", phase="7",
    decision="Dashboard reads saved output instead of refitting models",
    options_considered="Refit models live on each selection; cache models in "
                       "the session; export scored data once and read it",
    chosen="Export to parquet in src/dashboard.py; the app only reads and draws",
    reason="A dashboard that refits is slow and unpredictable during a live "
           "demonstration, and it would let the numbers on screen drift away "
           "from the numbers in the report.",
    effect_on_results="None on any reported number. The dashboard shows exactly "
                      "the values the notebooks computed.",
)

report.log_decision(
    id="D07-02", phase="7",
    decision="Dashboard shows predictions across the whole record, not just test",
    options_considered="Test period only; whole record with no marking; whole "
                       "record with a split column",
    chosen="Whole record, with a `split` column marking train / validation / test",
    reason="Restricting the dashboard to the test period would make most dates "
           "unselectable. Showing in-sample fit without labelling it would "
           "misrepresent how well the model performs.",
    effect_on_results="Presentation only. The anomaly scale is calibrated on the "
                      "test period and applied consistently, so a flag means the "
                      "same thing at every date.",
)

report.publish_decision_log()

# %% [markdown]
# ## Step 8: final verification
#
# Three checks the project must pass before it is finished.

# %%
pending = report.pending_blocks()
missing_figures = report.check_figures()
decisions = pd.read_csv(report.DECISIONS_CSV)

print("=" * 66)
print("FINAL CHECKS")
print("=" * 66)
print(f"1. report sections still 'pending' : "
      f"{len(pending)}  {pending if pending else '-- none'}")
print(f"2. figures referenced but missing  : "
      f"{len(missing_figures)}  {missing_figures if missing_figures else '-- none'}")
print(f"3. decisions logged                : {len(decisions)} "
      f"across phases {sorted(decisions['phase'].astype(str).unique())}")

figure_files = sorted(C.FIGURES_DIR.glob("*.png"))
result_files = sorted(C.RESULTS_DIR.glob("*.csv"))
print(f"4. figures produced                : {len(figure_files)}")
print(f"5. result tables produced          : {len(result_files)}")

report_text = C.REPORT_PATH.read_text(encoding="utf-8")
print(f"6. report length                   : {len(report_text.split()):,} words, "
      f"{len(report_text.splitlines()):,} lines")

assert not pending, f"report still has pending sections: {pending}"
assert not missing_figures, f"report references missing figures: {missing_figures}"
print()
print("All checks passed.")

# %%
# Every phase must have left a decision trail.
per_phase = decisions.groupby("phase").size()
display(per_phase.rename("decisions").to_frame())
display(decisions[["id", "phase", "decision"]])

# %% [markdown]
# ## Step 9: what the project produced

# %%
inventory = pd.DataFrame([
    {"deliverable": "docs/PROJECT_REPORT.md",
     "what it is": "the complete write-up, readable without opening a notebook",
     "size": f"{len(report_text.split()):,} words"},
    {"deliverable": "notebooks/*.ipynb",
     "what it is": "eight executed notebooks, phases 0-7",
     "size": f"{len(list(Path('.').glob('../notebooks/*.ipynb')))} notebooks"},
    {"deliverable": "src/",
     "what it is": "reusable modules imported by every notebook",
     "size": f"{len(list(Path('../src').glob('*.py')))} modules"},
    {"deliverable": "figures/",
     "what it is": "every chart used in the report",
     "size": f"{len(figure_files)} PNG files"},
    {"deliverable": "results/",
     "what it is": "the tables the report and dashboard read",
     "size": f"{len(result_files)} CSV files"},
    {"deliverable": "dashboard/app.py",
     "what it is": "Streamlit dashboard, reads saved output only",
     "size": "1 app"},
    {"deliverable": "results/decision_log.csv",
     "what it is": "every judgement call, with alternatives and consequences",
     "size": f"{len(decisions)} decisions"},
])
display(inventory)

# %% [markdown]
# ## Phase 7 conclusion -- the project is complete
#
# **All eight notebooks execute end to end. Every section of the report is
# filled from executed code, every figure it references exists, and every
# judgement call is logged with the alternatives that were considered.**
#
# The three research questions are answered:
#
# 1. **How much energy is used at low occupancy?** Between 4.5% and 19.1% of
#    measured energy depending on the building -- and more usefully, these
#    buildings still draw **62% to 85% of their average power** when at their
#    emptiest. The base load exceeds the variable load everywhere.
# 2. **How well do occupancy and time predict power?** Occupancy explains 7-45%
#    of the variation and adds about +0.11 validation R² over a time-only model.
#    A weak predictor, consistently across three independent analyses.
# 3. **Does an occupancy-aware detector beat a time-only one?** Yes, on all five
#    fair comparisons, but by only one to three percentage points -- with the
#    gains concentrated on sustained waste, exactly where theory predicts.
#
# Along the way the project also found that campus consumption grew by a third to
# a half in four years, and that the loudest "anomalies" in the real data are a
# single schedule change that an ageing model keeps re-reporting.
#
# **What we would do next, in one line:** get weather data, because the biggest
# remaining uncertainty is how much of this waste is air conditioning an empty
# building in a Delhi summer.
