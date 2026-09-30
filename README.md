# SMARTGRID-X

**Occupancy-aware energy-waste and anomaly analysis of the I-BLEND campus dataset.**

MD3135 Data Science course project — T.Y. B.Tech, Vishwakarma Institute of
Technology, Pune.

We pair four years of 1-minute electricity readings from seven IIIT-Delhi
buildings with WiFi-derived occupancy counts, and ask three questions:

1. **Main —** what percentage of each building's energy is used during
   low-occupancy periods?
2. How well do occupancy and time of day predict power?
3. Does an anomaly detector that knows about occupancy beat one that only knows
   the time?

> **The whole project is written up in [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md).**
> That file is designed to be read on its own — you do not need to open the
> notebooks to follow it.

## What we found

**When these buildings are at their emptiest, they still draw 62%–85% of their
average power.** In every one of the seven, the base load — the part drawn
whether or not anyone is present — is the larger share of consumption.

As an external check, applying the clock-based definition used by Masoso &
Grobler (2010) to this data gives 55.2% for the Academic building and 55.0% for
the Library, against their published 56%.

Two secondary results, both modest and both reported honestly:

- **Occupancy is a weak predictor of power.** It explains 7%–45% of the
  variation and adds only +0.11 validation R² over a time-only model.
- **An occupancy-aware anomaly detector is better, but only just** — ahead on
  all five fair comparisons by one to three percentage points each, with the
  gains concentrated on sustained waste rather than spikes.

We also found, without looking for it, that **campus consumption grew 32%–48%
between 2014 and 2017**.

---

## Repository layout

```
.
├── Dataset/                  # I-BLEND source data — READ-ONLY, never committed
├── notebooks/
│   ├── 00_explore.ipynb      # executed notebooks (the graded artefacts)
│   ├── 01_data_prep.ipynb
│   ├── ...
│   └── src_py/               # percent-format source of each notebook
├── src/                      # reusable code, imported by every notebook
│   ├── config.py             # paths, building registry, every threshold
│   ├── ingest.py             # chunked CSV -> 10-minute parquet cache
│   ├── explore.py            # profiling helpers
│   ├── viz.py                # chart style and palette
│   ├── report.py             # writes generated tables into the report
│   └── nbbuild.py            # percent-format .py -> .ipynb
├── data/processed/           # parquet cache — generated, not committed
├── figures/                  # every chart used in the report
├── results/                  # small CSV tables the report and dashboard read
├── dashboard/app.py          # Streamlit dashboard
├── docs/PROJECT_REPORT.md    # the master document
├── tools/                    # build/execute a notebook, data-leak guard
└── progress.md               # running log: done / found / next
```

## Setup

```bash
python -m pip install -r requirements.txt
python -m ipykernel install --user --name python3
```

Then download the I-BLEND dataset from
<https://doi.org/10.6084/m9.figshare.c.3893581> and unzip it into `Dataset/` so
that `Dataset/energy_dataset/` and `Dataset/IIITD_occupancy_dataset/` exist.
The data is about 1.6 GB and is deliberately **not** in this repository.

## Running the notebooks

Run them in order; each one caches its outputs so later phases are fast.

```bash
python tools/build_and_run.py 00_explore
python tools/build_and_run.py 01_data_prep
...
```

`tools/build_and_run.py` converts the percent-format source in
`notebooks/src_py/` into a notebook and executes it end to end with
`nbconvert`, failing loudly if any cell raises. A notebook is never committed
unless that command exits 0.

To execute an existing notebook directly:

```bash
python -m nbconvert --to notebook --execute --inplace notebooks/00_explore.ipynb
```

## Dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard reads the saved parquet and `results/` tables. It does not retrain
anything.

## Rules this project follows

- **`Dataset/` is read-only.** Nothing writes to it, and it is never committed.
  `python tools/check_no_data.py` fails the build if any data file, parquet, or
  file over 50 MB gets staged.
- **Every number in the report comes from executed code.** The report contains
  named blocks that the notebooks fill via `src/report.py`; nothing is typed by
  hand. Anything not yet computed reads "pending Phase N".
- **Never load all 1.6 GB at once.** One meter at a time, in chunks, cached to
  10-minute parquet and reused.
- **Notebooks are committed only after they execute cleanly end to end.**

## Data source

Rashid, H., Singh, P. & Singh, A. (2019). *I-BLEND, a campus-scale commercial and
residential buildings electrical energy dataset.* **Scientific Data** 6, 190015.
<https://www.nature.com/articles/sdata201915>
