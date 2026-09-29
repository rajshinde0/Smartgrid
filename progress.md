# SMARTGRID-X — progress log

Three lines per phase: what was done, what we found, what is next.
If work is picked up again after a break, read this file and
`docs/PROJECT_REPORT.md` first, then continue from the first unfinished phase.

---

## Setup — done

**Done.** Git repo initialised and pointed at `rajshinde0/Smartgrid`. `.gitignore`
written before the first `git add`, so `Dataset/`, `data/` and every `*.parquet`
are excluded; `tools/check_no_data.py` enforces it (also fails on any file over
50 MB). Installed the notebook execution stack (nbformat, nbconvert, nbclient,
ipykernel) on Python 3.14.3 and registered the `python3` kernel. Built the
reusable `src/` layer: `config.py` (paths, building registry, every threshold),
`ingest.py` (chunked CSV → 10-minute parquet), `explore.py`, `viz.py`,
`report.py`, `nbbuild.py`, plus `tools/build_and_run.py`.

**Found.** Python 3.14 was a real risk — most of the scientific stack was already
present (pandas 3.0.3, numpy 2.4.3, sklearn 1.8.0) and the Jupyter stack installed
as clean wheels, so there is no blocker. The `jupyter` console script is not on
PATH on this machine; `python -m nbconvert` is used instead and works.

**Next.** Phase 1.

---

## Phase 0 — Explore — done

**Done.** `notebooks/00_explore.ipynb` opens every file in `Dataset/`, reads both
readmes and the ISA-Tab provenance metadata, prints head/tail of all 9 energy
meters and all 7 occupancy files, and profiles each for coverage, gaps and
data-quality counts. Produced `figures/fig_00_coverage_timeline.png` (monthly
completeness heatmap), three `results/phase0_*.csv` tables, and the
`docs/PROJECT_REPORT.md` skeleton with section 4 filled from executed code.
Eight Phase 0 decisions logged.

**Found.**
- **Occupancy never reaches zero** — minimum is 1 in all seven buildings. The main
  question had to be re-specified around a *relative* low-occupancy threshold
  (≤5% of each building's 95th-percentile occupancy).
- **Facilities (SRB)**: that threshold is 0.9, below its own minimum of 1, so
  **no reading qualifies**. Rule kept uniform; reported honestly and read off the
  Phase 5 sensitivity curve instead.
- **Lecture (LCB)**: meter reads exactly 0 W for **81.7%** of the record — a dead
  meter, not an idle building. Waste computed over alive periods only.
- **Negative `power_factor` is a sign convention, not corruption** — 0.01–67.6% of
  rows per meter, range exactly −0.999..+1.000 while power is never negative.
  Dropping those rows would have destroyed 58% of the Library record.
- **Coverage is much worse than row counts suggest**: 71.5%–99.6% row coverage,
  with single gaps up to 5,311 hours (221 days) in Girls mains. Boys hostel,
  Girls mains and Library each lose several consecutive months.
- Working period is **2014-02-16 → 2017-11-03**, set by occupancy.

**Next.** Phase 1 — data preparation: build the 10-minute parquet cache for all 9
meters, missing-data heatmap from `data_present_status_buildings.csv`, dead-meter
flagging, outlier flagging, merge with occupancy, feature engineering, and the
post-cleaning data-quality table.

---

## Phase 1 — Data preparation — done

**Done.** `notebooks/01_data_prep.ipynb` does the full inspection
(head/tail/info/describe), builds the missing-data heatmap from
`data_present_status_buildings.csv`, applies the invalid-value rules, flags dead
meters and outliers (flag, never delete), resamples to 10 min, merges with
occupancy, interpolates gaps <= 30 min, adds all features, and stacks everything
into one long table (1,347,027 rows). Also covers `loc`/`iloc`, sorting, ordered
categoricals, the log transform, Min-Max vs standardisation, and one occupancy
file analysed with the stdlib `csv` module using only lists and dicts (checked
against pandas with asserts). Seven decisions logged. Five figures.

**Found.**
- **Usable coverage is very uneven**: Academic 90.4%, Facilities 85.5%, Mess
  80.5%, Boys 60.9%, Library 60.8%, Girls 60.0%, **Lecture 18.9%**.
- **Lecture meter is off for 25,488 hours** (~2.9 years of the 3.7-year window).
- **Pipeline independently verified**: our per-building mean power agrees with
  `all_buildings_power.csv` to within **0.113%** across all seven buildings.
- **Approximate academic calendar validated**: Boys hostel vacation occupancy is
  42% of its semester median, Girls 53%, Academic 83% (staff keep working).
- **New problem found and documented (D01-07):** a building switched off at the
  mains overnight and a dead meter both read exactly 0 W. The zero-run histogram
  for Lecture shows two populations — median run 13.7 h (nightly switch-off),
  max 1,123 h (46 days). 34.5% of Lecture's zero hours sit in runs of <= 24 h.
  The specified 6 h rule catches both; Phase 5 will re-run Lecture with a 24 h
  rule as a sensitivity check.
- The highest-power blocks in the Academic building are **summer afternoons**
  during vacation — air conditioning, not people. Early hint for Phase 5 and
  for the no-weather-data limitation.

**Next.** Phase 2 — attribute-type table, descriptive statistics (manual NumPy
vs pandas), population-vs-sample simulation, distribution fitting with Q-Q and
KS, hypothesis tests, and the EDA chart set.

## Phase 2 — Statistics and EDA — done

**Done.** `notebooks/02_stats_eda.ipynb`: attribute-type table (including the
asymmetric binary flags), descriptive statistics per building, the same
statistics recomputed by hand with NumPy and asserted equal to pandas,
population-vs-sample simulation (1,000 samples of 30 days), Normal vs Log-normal
fitting with Q-Q and KS, hypothesis tests with effect sizes, and ten charts.
Four decisions logged. New module `src/stats.py`.

**Found.**
- **Occupancy explains only 7%-45% of the variation in power.** Best: Academic
  r = 0.67 (R2 = 0.45). Worst: Facilities r = 0.27 (R2 = 0.08). Most of what
  drives consumption is not how many people are present.
- **Every building has a large base load.** The Academic building still draws
  ~20 kW at 3 a.m. against a 41 kW midday peak. Facilities is almost perfectly
  flat across the whole day (~10-13 kW).
- **Log-normal beats Normal** (KS 0.083 vs 0.172) but **neither fits** — power
  is bimodal (night cluster + day cluster). So MAE goes beside RMSE in Phase 4.
- **Manual NumPy statistics match pandas to 4.5e-15** (assertion in the notebook).
- **Response to occupation is very uneven, and that is the key finding.**
  Semester vs vacation: Lecture d = 1.24 and Boys hostel d = 0.89 (large), but
  Academic d = -0.08 and Mess d = 0.09 (negligible), and **Facilities uses 17%
  MORE in vacation** (d = -0.45) because Delhi's summer break is its hottest
  season. Weekday vs weekend: Library -64%, Academic -45% (medium), both
  hostels flat. Buildings *can* respond — so the ones that do not are making a
  choice.
- With n = 37k-177k every p-value is < 1e-300; only effect sizes are informative.
  Recorded as decision D02-01.

**Next.** Phase 3 — PCA on daily load profiles (NumPy day matrix, eigen-PCA by
hand checked against sklearn, scree plot, PC scatter, 3D plot, k-means day types).

## Phase 3 — PCA — done

**Done.** `notebooks/03_pca.ipynb` plus new module `src/pca.py`. Day matrix built
by a genuine NumPy `reshape` (1,356 days x 144 blocks), indexing/slicing/matrix
subsetting demonstrated, vectorized vs looped hourly aggregation timed, PCA
computed by hand (covariance + `np.linalg.eig`) and asserted equal to sklearn,
scree plot, component-shape plots, PC1-PC2 scatter, 3D PC1-PC3 plot, k-means day
types, reconstruction-error anomaly score, and the same analysis repeated on the
Boys hostel. Four decisions logged. Eight figures.

**Found.**
- **Three numbers describe a day.** PC1 = 55.0%, PC1-3 = 86.9% of variance for
  the Academic building. PC1 is overall level (all weights one sign), PC2 is
  day-vs-night contrast (weights change sign), PC3 is peak timing.
- **PCA rediscovered the calendar without being told it.** Weekends separate
  along PC2 (flatter days); semester/vacation separates along PC1, less cleanly,
  because some vacation days are among the highest-consuming in the record.
- **Hand-computed PCA matches sklearn exactly** (after sign alignment, atol 1e-8).
- **Vectorized aggregation is ~97x faster** than the equivalent nested loops,
  with bit-identical results (max difference 0.00e+00).
- **The Academic night floor is 53% of its midday level** — the Phase 5
  question stated in one number.
- **Facilities has an almost flat daily shape**, so its consumption is nearly
  independent of the time of day.
- **Lecture has too few complete days (<30) to contribute an average daily
  shape** and is excluded from the shape chart — stated in the chart and the
  report rather than silently dropped.

**Next.** Phase 4 — regression models A-D, chronological 70/15/15 split,
TimeSeriesSplit CV, feature selection, overfitting curve, MAE/RMSE/R2 per
building. Model A gives the base load *a* and slope *b* that Phase 5 needs.

## Phase 4 — Regression — not started

## Phase 5 — Wasted energy (headline) — not started

## Phase 6 — Anomaly experiment — not started

## Phase 7 — Delivery — not started
