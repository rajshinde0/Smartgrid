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

## Phase 2 — Statistics and EDA — not started

## Phase 3 — PCA — not started

## Phase 4 — Regression — not started

## Phase 5 — Wasted energy (headline) — not started

## Phase 6 — Anomaly experiment — not started

## Phase 7 — Delivery — not started
