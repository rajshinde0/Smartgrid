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
  Academic d = -0.08 and Mess d = 0.09 (negligible), and **Facilities is the only
  building that uses MORE on low-activity days** (+3.5%, d = -0.08) -- every
  other falls 13-50%. Phase 8 later showed this is outdoor temperature. (The
  original +17% predated the official calendar, whose low-activity label
  includes weekends year-round.) Weekday vs weekend: Library -64%, Academic -45% (medium), both
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

## Phase 4 — Regression — done

**Done.** `notebooks/04_regression.ipynb` plus new module `src/models.py`.
Chronological 70/15/15 split, TimeSeriesSplit CV, one-hot encoding of cyclic
time features, scaling inside a Pipeline, feature selection (correlation +
SelectKBest), models A-D for all 7 buildings, actual-vs-predicted week,
overfitting curves (polynomial degree 1-10 and RF depth), feature importances,
residual analysis. Six decisions logged. Seven figures. Runtime ~4 min.

**Found.**
- **The campus grew 32%-48% in mean power from 2014 to 2017** (six of seven
  buildings; Lecture -7% but unreliable). A major finding in its own right, and
  it forced explicit handling of concept drift: the test split is 2017, the
  highest-consuming period, so a model fitted on 2014-16 under-predicts it.
  Handled with a validation-calibrated offset (no leakage: validation precedes
  test) and both corrected and uncorrected metrics reported. Decision D04-02.
- **The power-occupancy correlation itself weakened over time** in the Academic
  building: r fell from 0.71 (2014) to 0.45 (2017).
- **RQ2 answered: occupancy helps in 6 of 7 buildings, mean +0.099
  validation R2** (recomputed after the official calendar was adopted).** Helps most where people drive the load (Girls
  hostel +0.444, Library +0.205); slightly hurts where equipment schedules and
  weather do (Mess -0.007, Facilities -0.063). Matches the published LBNL result.
- **Base load is 52%-86% of mean power in every building** (Facilities 85.7%,
  Mess 83.2%, Girls hostel 75.1%, Academic 62.3%). This is the quantitative
  core of the headline finding, and the model-A intercepts agree with an
  independent night-time-median check.
- **The lag-feature trap demonstrated, not just asserted:** adding power-1h
  lifts validation R2 from 0.29 to 0.91, but such a model absorbs waste into its
  expectation and would never flag lights left on. Excluded deliberately (D04-03).
- Random forest at unlimited depth shows the textbook overfitting gap.

**Next.** Phase 5 — the headline: low-occupancy energy share per building,
sensitivity curve over thresholds 0-20%, base load vs night minimum,
responsiveness ranking, semester vs vacation, hostel mains vs UPS, comparison
with Masoso & Grobler (56%) and Anderson et al. (27.5-31.5%). Plus the two
sensitivity checks owed from earlier phases: Lecture under a 24 h dead-meter
rule (D01-07) and the corrected-occupancy robustness run (D00-06).

## Phase 5 — Wasted energy (headline) — done

**Done.** `notebooks/05_waste.ipynb` plus new module `src/waste.py`. Headline
table, sensitivity curve (0-20%), base load vs night minimum, responsiveness
ranking, semester vs vacation, hostel mains vs UPS, commercial vs residential,
comparison with the published literature, and the two sensitivity checks owed
from earlier phases. Four decisions logged. Eight figures.

**HEADLINE FINDING.** *When these buildings are at their emptiest they still
draw 62%-85% of their average power.* Per building, low-occupancy energy share /
intensity ratio: Lecture 19.1% / 85%, Library 17.4% / 62%, Mess 9.3% / 74%,
Girls hostel 5.0% / 79%, Academic 4.8% / 74%, Boys hostel 4.5% / 75%,
Facilities no qualifying interval at the standard threshold.

**Found.**
- **Strongest external check in the project:** applying Masoso & Grobler's own
  clock-based definition (outside 08:00-18:00 weekdays) to our data gives
  Academic **55.2%** and Library **55.0%** against their published **56%**.
  Different continent, fifteen years apart, within a percentage point.
- The clock rule and the occupancy rule are **not measuring the same thing** and
  differ by an order of magnitude; our occupancy figure is a conservative lower
  bound, which the corrected-occupancy check confirms independently.
- **The intensity ratio was added** (D05-01) because the energy share depends on
  how *often* a building is empty — a fact about the timetable, not the building.
- **Two base-load estimates disagree where extrapolation is unsafe.** Model A's
  intercept sits 52% below the measured night median for the Boys hostel, 46%
  below for Lecture, 31% below for Girls hostel — dormitory occupancy never
  approaches zero, so the intercept is extrapolated far outside the data.
  Responsiveness is therefore ranked on the *measured* intensity ratio, with the
  modelled value flagged unreliable. Conclusion unchanged either way.
- **The Facilities sensitivity curve is a staircase**, not a smooth rise: its
  occupancy is a small integer (1-47), so a sliding threshold only ever crosses
  whole numbers. Same fact that makes the standard threshold unreachable there.
- **Lecture 24 h dead-meter check (D01-07 settled):** share moves 19.06% -> 17.76%,
  a difference of 1.30 pp, while usable intervals more than double. Ambiguity
  real but small.
- **Corrected-occupancy check (D00-06 settled):** subtracting the idle-device
  baseline raises the share everywhere, confirming the raw headline is a lower
  bound. For Facilities the correction is not credible (subtracting 20 from a
  building whose p95 is 18), which is why it was never the headline.

**Next.** Phase 6 — anomaly experiment: Detector T (model B residuals) vs
Detector O (model C residuals), injected spikes and waste anomalies on a copy of
the test data with seed 42, confusion matrices and precision/recall/F1 per
detector x anomaly type, then Detector O on real data for the top 10 unusual
patterns.

## Phase 6 — Anomaly experiment — done

**Done.** `notebooks/06_anomaly.ipynb` plus new module `src/anomaly.py`.
Detector T (model B residuals) vs Detector O (model C residuals), synthetic
anomaly injection on a copy of the test data with seed 42, confusion matrices,
precision/recall/F1/accuracy per detector x anomaly type, event-level recall,
one-sided and IQR variants, and Detector O on the real data. Five decisions
logged (D06-01..05). Four figures.

**Found.**
- **RQ3 answered: a qualified yes.** Occupancy helps consistently but only a
  little. All 5 fair comparisons favour Detector O: matched-budget F1
  0.292->0.296, average precision 0.426->0.443, ROC AUC 0.682->0.702,
  waste-only F1 0.141->0.165, waste-event recall 21.8%->24.7%. Every margin is
  1-3 percentage points, but they all point the same way and **the largest
  gains land on the waste anomalies**, exactly where theory predicts.
- **The specified fixed |z|>3 threshold is NOT a fair test** (D06-02). Model C
  fits better, so its residuals are tighter, so its MAD is smaller, so the same
  deviation in watts scores a larger Z and it simply fires more often. At that
  threshold O looked *worse* (F1 0.288 vs 0.293). Reporting only the planned
  comparison would have drawn a conclusion about scale calibration and called it
  a finding about occupancy. Added matched-alert-budget and threshold-free
  (ROC AUC, average precision) comparisons.
- **Robust z-scores (median/MAD) instead of mean/SD** (D06-01): the SD is
  inflated by the anomalies being hunted, so they raise the bar and hide
  themselves.
- **One-sided detection is a clear win** (D06-05): all injected and all real
  waste is additive, so the two-sided rule spends ~half its alerts on
  under-consumption, which cannot be a true positive.
- **Fewer waste events land than requested** (D06-04): they run 2-6 h and must
  fit inside low-occupancy periods. Academic fits 65 of 200; Facilities fits
  **0** because its threshold is unreachable. All scores use achieved counts.
- **Real-data finding: the top 10 is one finding ten times.** 29 of the 30 most
  extreme real episodes are the Academic building starting ~03:20, lasting 7-8 h,
  Aug-Nov 2017, ~35-38 kW excess, repeating daily. That is a **change of
  operating schedule** the 2014-16 model keeps re-reporting — concept drift
  returning as false alarms. Added a deduplicated per-building view, and the
  lesson that a fixed historical baseline needs periodic refitting.

**Next.** Phase 7 — Streamlit dashboard reading saved outputs only, then
finalise PROJECT_REPORT.md: rewrite the abstract with real findings, limitations,
conclusion & future scope, full syllabus coverage table (Units I-VI, Tutorials
1-8), how to reproduce, and the presentation outline appendix.

## Phase 7 — Delivery — done  —  PROJECT COMPLETE

**Done.** `notebooks/07_final.ipynb` plus `src/dashboard.py` and
`dashboard/app.py`. Exported per-building scored parquet for the dashboard;
wrote the remaining report sections (abstract rewritten with real findings,
limitations, conclusion & future scope, syllabus coverage for Units I-VI and
Tutorials 1-8, how to reproduce, presentation outline); ran the final checks.
Two decisions logged (D07-01/02). 40 decisions total.

**Final state.**
- 8 notebooks, all executing end to end from a cold start (verified)
- 44 figures, 46 result tables, 15 src modules
- `docs/PROJECT_REPORT.md`: 27,383 words, 0 sections pending, 0 broken figure
  links
- dashboard verified by executing every code path with a stubbed Streamlit:
  8 metrics, 2 charts, 4 tables, and the Facilities unreachable-threshold branch
  correctly warns

**Found while finishing.**
- The report checker had two false positives, both caught by the assertions:
  `pending_blocks()` matched any block *mentioning* the placeholder phrase (now
  matches only blocks that *start* with it), and `check_figures()` matched the
  text documenting the figure-link format. Both fixed.
- Generated sub-headings sat at the same level as the sections containing them,
  flattening a 27k-word outline. `report._fix_heading_levels()` now demotes each
  block's headings to sit below its section, skipping fenced code.

**Nothing left outstanding.** All three research questions answered, all
sensitivity checks owed by earlier decisions discharged (D00-06, D01-07).

---

## Post-completion correction — the official calendar and the weather file

**Trigger.** While writing `tools/get_data.py` (a one-command downloader, so the
1.6 GB dataset need not — and cannot — live in git: five files exceed GitHub's
100 MB hard limit), querying the figshare API revealed the collection holds
**four** articles, not two.

**What was wrong.**
- **The IIIT-Delhi semester calendar is published with the dataset.** Phase 1
  approximated it, having searched the project GitHub site — which hosts only
  website assets and reading scripts — and wrongly concluded none existed. The
  brief said to use the real calendar "if reachable, else approximate"; it was
  reachable, just on figshare.
- **A weather file exists**, contradicting the report's claim that "I-BLEND
  contains no temperature or humidity".

**What was done.**
- Adopted the official calendar (`calender_year_2013..2017_.csv`, 1,614 days
  covering our window exactly): `working_day` 0/1 and `activity` H/L. Added
  `is_working_day` as a model feature — it knows about public holidays, which a
  weekend flag cannot see. The approximation survives as a documented fallback.
- Measured the damage: the approximation agreed with the published calendar on
  only **68.5%** of days, marking 26.5% of days as vacation against the official
  57.4% low-activity, because the official definition includes weekends and
  holidays. D01-03 rewritten.
- Corrected the weather claim rather than deleting it. The file
  (`IIITD_and_airport_data.csv`) covers **1 Mar – 29 Jun 2018** and has **zero
  rows** overlapping our Feb 2014 – Nov 2017 window — it is a sensor-comparison
  record, not a weather history. The limitation stands, now stated precisely.
- Re-ran all eight notebooks.

**Effect on results.** The headline is **unchanged** — it never depended on the
calendar. Model B improved (Academic val R2 0.473 → 0.509) because the official
calendar is a better feature, so occupancy's marginal contribution fell slightly
(+0.107 → +0.099). RQ3 conclusions hold: all five fair comparisons still favour
Detector O, and waste-event recall improved (+0.029 → +0.041).

**Lesson.** "We checked and it does not exist" was true of the place we looked
and false of the dataset. Worth checking the data repository itself, not just
the project website.

---

## Second code review (2 Oct 2026) - 6 issues found, all fixed

**Trigger.** A fresh read of the pipeline with no prior context, after the first
review round (commit `c703e30`). Documented in `docs/bugFix1.md` (round 1) and
`docs/bugFix2.md` (round 2).

**The one that mattered.** `interpolate_short_gaps` used pandas'
`interpolate(limit=3)`, which caps *consecutive* NaNs rather than skipping long
gaps - so a 200-day gap had its first 3 blocks filled along a straight line
between readings months apart. **5,301 fabricated blocks against 2,498
legitimate ones: 68% of all interpolation was invented data.** It had been
harmless while round 1's bug discarded the column; fixing that discard made this
one live. **A fix promoted a latent bug to a live one** - the best argument for
reviewing twice. Interpolated blocks now 5,206 -> 2,184.

**Also fixed.**
- A single dropout split a zero-run, so a 10 h outage became two 5 h runs and
  neither crossed the 6 h threshold. Hid 2,413 zero-blocks (~402 h) in Lecture.
  Short gaps now bridge a run when both sides read zero; the gap itself is never
  flagged. D01-09.
- `low_occupancy_share` returned 3 keys on the empty path and 11 on the normal
  one - a KeyError waiting for any building with no usable rows.
- `power_missing` was counted after invalidation, double-counting with
  `power_invalid` (harmless today: power_invalid is 0 everywhere).
- `load_occupancy` reindexed without flooring, so an off-grid timestamp would
  vanish silently. Now floored with a warning.
- Removed `peek`, `tail_rows`, `count_rows` from ingest.py - zero call sites.

**Result movement.** Headline unchanged to within 0.01pp. Usable coverage fell
0.02-0.41pp per building (correctly - those blocks were fabricated). Lecture
meter-off +14 h. Decisions now 42 (D01-08, D01-09 added).

**A recurring failure mode, now fixed properly.** The RQ3 comparison count
flipped 5/5 -> 4/5 -> 5/5 across these fixes. Each time the report's *generated*
count updated itself and the hand-written sentence beside it did not. Those
sentences are now generated from the count too, so they cannot contradict it.
Also fixed a `.capitalize()` that was rendering "Detector o".

**Next.** Nothing outstanding. Team names in docs/PROJECT_REPORT.md are still
placeholders.

---

## Phase 8 - Weather integration (6 Oct 2026) - done

**Why.** Closing the project's largest limitation: no weather data covered the
analysis window, so we could measure that nearly-empty buildings draw 62-85% of
average power but not say how much of it was air conditioning.

**Data.** I-BLEND's own weather file covers Mar-Jun 2018, zero overlap. Used
METAR for Delhi IGI (VIDP) from the Iowa State archive instead: 58,639
observations, 2014-02-16 to 2017-11-02, 0.06% missing, 2-49 C. Reaches 96.1% of
analysis intervals. Fetched not committed; `src/weather.py` pulls it on
first use.
**VIDP is 25 km from campus - a measured proxy, not campus weather.**

**Found.**
- **Physics check passed first.** Facilities +64% and Academic +52% hot-vs-mild;
  **Lecture -16%**, the negative control working (a switched-off building cannot
  respond to heat). Nothing downstream would have been reported had this failed.
- **Cooling is only 1.1%-9.0% of low-occupancy consumption** (mean ~4%) where
  identifiable. **The empty hours are the cool hours** - 46% of low-occupancy
  intervals fall between midnight and 6 a.m. So the waste is overwhelmingly a
  **controls and scheduling problem**, not a cooling artefact. The limitation
  turned out milder than feared, which strengthens the main finding.
- **A quarter of occupancy's apparent value was summer heat.** Fitted on
  identical rows: occupancy worth +0.107 validation R2 with weather unknown,
  **+0.078** once known (27% shrinkage). Weather alone worth +0.070.
- **Facilities is a weather-driven building.** Occupancy worth -0.118 there once
  temperature is known; weather alone +0.176. That explains at last why adding
  occupancy made its model *worse* in Phase 4.
- **Library and Lecture cannot be decomposed** - both are shut in the hot months,
  so season and usage are confounded within their low-occupancy sample and the
  fitted slope goes negative. Reported as not identifiable rather than given a
  nonsensical negative cooling share.
- **Hour-of-day must be controlled for** (D08-03): without it the fit confuses
  "cooler at night" with "needs less cooling". R2 roughly trebles with it
  (Academic 0.07 -> 0.19).

**Stale number caught.** "Facilities uses 17% more in vacation" (quoted in 4
files) predated the official calendar, whose low-activity label includes
weekends year-round. The real current figure is **+3.5%** (d = -0.08), and
Facilities is the only building that rises at all - every other falls 13-50%.
Corrected everywhere and the report blocks now compute it.

**Published results untouched.** Models B and C kept their definitions (D08-02),
so `phase4_occupancy_contribution.csv`, `phase5_headline.csv` and
`phase6_pooled_answer.csv` are **bit-identical** after the full re-run. Verified
by diff, not assumption.

**State.** 9 notebooks, 47 figures, 50 result tables, 45 decisions, 30,319-word
report, 0 pending sections, 0 broken figure links.

## Dashboard - outdoor temperature (7 Oct 2026) - done

**Why.** Phase 8's weather work existed only in the report. The dashboard is
what actually gets demonstrated, so the temperature belonged there too.

**What.** A third stacked panel on the shared clock - never a second y-axis
(D08-04), because watts, people and degrees are three different quantities and
one shared axis would let a reader take a correlation off the crossing points.
The panel carries a dashed line at the building's own fitted base temperature,
so it answers "was it hot enough to matter *here*", not just "how hot was it".
Alongside it, a fifth headline metric for the cooling share, and an expander
with the full decomposition and temperature-response tables.

**Two bugs caught in verification.** `decomposition` was bound inside the
`if not row.empty` guard but read later in the chart block - so Facilities, the
one building with no qualifying interval, would have raised `NameError` on
exactly the page most worth looking at. And the "cooling starts" label was
pinned to the panel floor, where it collided with its own line in buildings
with a low base. Both fixed before commit.

**Verified** with a stubbed-Streamlit harness over Academic, Facilities and
Boys_Hostel, panel on and off: six runs, no errors.

## Documentation tidy-up (7 Oct 2026) - done

**Why.** The code was documented but the *navigation* was not, and several
pointers had quietly gone stale as the project grew past them.

**Done.**
- `src/__init__.py` was empty; it now carries a map of all 18 modules grouped
  by pipeline layer, with the dependency order. The package has no cycles and
  the map says so.
- Docstring coverage is now complete: every module and every public top-level
  function in `src/` and `tools/` (7 were missing, including `make_linear_model`
  and `feature_columns` in a 549-line module).
- README rewritten: it had no mention of Phase 8 at all, listed 6 of 18 `src`
  modules, and still told the reader to download 1.6 GB by hand when
  `tools/get_data.py` had automated it.
- New `docs/README.md` index, and the three planning documents moved from the
  repo root into `docs/planning/` (`git mv`, history preserved).

**Three stale or wrong things found while tidying.**
1. **A model-name collision.** Phase 4 prose called the lag-feature
   demonstration "model E"; Phase 8 then published E and F as the weather
   models. Two different models, one letter. It never reached the report or any
   result table - the lag demo is only a local variable - so the fix was to
   drop the letter from the prose.
2. **`get_data.py --all` help was wrong.** It claimed to fetch "weather data
   and the semester calendar", but the calendar is in `CORE` and always
   fetched. progress.md also cited a `--weather` flag that does not exist.
3. **The decision log's order was not deterministic** - the real find.
   `log_decision` sorted on `["phase", "id"]`, but `phase` is passed as a
   string and comes back from `read_csv` as int64, so the column held mixed
   types and the sort silently fell back to insertion order. Re-running
   notebook 04 alone moved D04-06 below D08-04 in the published table. Now
   sorted on `id` as text, which is canonical because every id is a zero-padded
   `D<phase>-<n>`. The report's table is bit-identical again, and stays that
   way whichever notebook is re-run.

**State.** 9 notebooks, 47 figures, 50 result tables, 46 decisions,
30,853-word report, 0 pending sections, 0 broken figure links. Every module and
public function documented.

**Possible next.** Team names in docs/PROJECT_REPORT.md are still placeholders.

