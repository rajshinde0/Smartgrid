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
> notebooks to follow it. [`docs/README.md`](docs/README.md) says where to enter
> it depending on what you want.

## What we found

**When these buildings are at their emptiest, they still draw 62%–85% of their
average power.** In every one of the seven, the base load — the part drawn
whether or not anyone is present — is the larger share of consumption.

As an external check, applying the clock-based definition used by Masoso &
Grobler (2010) to this data gives 55.2% for the Academic building and 55.0% for
the Library, against their published 56%.

**Almost none of that is air conditioning.** Delhi airport weather for the exact
analysis window lets us split low-occupancy power into the part that responds to
heat and the part that does not. In the four buildings where the split can be
identified at all, cooling accounts for **1%–9%** of it. So the waste is a
controls and scheduling problem — equipment left running on a timetable nobody
revisits — rather than a thermostat problem, and the remedy is correspondingly
cheaper.

Two secondary results, both modest and both reported honestly:

- **Occupancy is a weak predictor of power**, and weaker than it first looked.
  It adds +0.107 validation R² over a time-only model — but only **+0.078** once
  outdoor temperature is also known, a 27% shrinkage. Occupancy and heat are
  both seasonal, and this campus empties in exactly the months Delhi is hottest.
- **An occupancy-aware anomaly detector is better, but only just** — ahead on
  all five fair comparisons by one to three percentage points each, with the
  gains concentrated on sustained waste rather than spikes.

We also found, without looking for it, that **campus consumption grew 32%–48%
between 2014 and 2017**.

---

## Repository layout

```
.
├── Dataset/                    # I-BLEND source data — READ-ONLY, never committed
├── notebooks/
│   ├── 00_explore.ipynb        # the executed notebooks: the graded artefacts
│   ├── 01_data_prep.ipynb      #   00 profile · 01 build · 02 stats · 03 PCA
│   ├── ...                     #   04 regression · 05 waste · 06 anomaly
│   ├── 08_weather.ipynb        #   07 report · 08 weather
│   └── src_py/                 # percent-format source of each notebook
│
├── src/                        # reusable logic, imported by every notebook
│   ├── config.py               # paths, building registry, EVERY threshold
│   │
│   ├── ingest.py               # chunked CSV -> 10-minute parquet cache
│   ├── occupancy.py            # WiFi counts, and what "low occupancy" means
│   ├── weather.py              # Delhi METAR, cooling degree hours, base temp
│   │
│   ├── clean.py                # dead meters, outliers, which gaps may be filled
│   ├── features.py             # calendar features, semester flag, lags
│   ├── build.py                # assembles one merged table per building
│   │
│   ├── explore.py              # Phase 0 profiling without loading everything
│   ├── stats.py                # descriptives, distribution fits, hypothesis tests
│   ├── pca.py                  # daily load profiles and their components
│   ├── models.py               # the regression models (RQ2)
│   ├── waste.py                # the headline calculation (RQ1)
│   ├── anomaly.py              # the detector experiment (RQ3)
│   │
│   ├── viz.py                  # chart style, palette, the no-dual-axis rule
│   ├── report.py               # writes generated tables into the report
│   ├── dashboard.py            # scores every interval once, saves for Streamlit
│   └── nbbuild.py              # percent-format .py -> .ipynb
│
├── dashboard/app.py            # Streamlit dashboard
├── docs/
│   ├── PROJECT_REPORT.md       # the master document
│   ├── README.md               # index: where to enter the report
│   ├── bugFix1.md, bugFix2.md  # two rounds of code review, written up
│   └── planning/               # the original brief, kept unedited
├── tools/                      # fetch data, build+execute a notebook, leak guard
├── results/                    # 50 CSV tables the report and dashboard read
├── figures/                    # all 47 charts used in the report
├── data/                       # parquet + weather cache — generated, not committed
└── progress.md                 # running log: done / found / next
```

`src/__init__.py` carries the same map with the dependency order, if you are
reading the package rather than this file.

## Setup

```bash
python -m pip install -r requirements.txt
python -m ipykernel install --user --name python3
```

Then fetch the data (about 1.6 GB, deliberately **not** in this repository):

```bash
python tools/get_data.py          # energy, occupancy and semester calendar
python tools/get_data.py --all    # also the 2018 campus weather file
```

This pulls the I-BLEND collection from figshare
(<https://doi.org/10.6084/m9.figshare.c.3893581>) and unpacks it into
`Dataset/`. To do it by hand instead, download the collection and unzip it so
that `Dataset/energy_dataset/` and `Dataset/IIITD_occupancy_dataset/` exist.

Outdoor weather for the analysis window is a separate source — Delhi airport
METAR, fetched on first use by `src/weather.py` and cached to `data/weather/`.
The analysis runs without it; the Phase 8 sections are simply skipped.

## Running the notebooks

Run them in order; each one caches its outputs so later phases are fast.

```bash
python tools/build_and_run.py 00_explore
python tools/build_and_run.py 01_data_prep
...
python tools/build_and_run.py 08_weather
```

`tools/build_and_run.py` converts the percent-format source in
`notebooks/src_py/` into a notebook and executes it end to end with
`nbconvert`, failing loudly if any cell raises. A notebook is never committed
unless that command exits 0.

Phase 1 takes a few minutes on first run and seconds afterwards. To execute an
existing notebook directly:

```bash
python -m nbconvert --to notebook --execute --inplace notebooks/00_explore.ipynb
```

## Dashboard

```bash
streamlit run dashboard/app.py
```

Pick a building and a date range to get power, occupancy and outdoor temperature
on one shared clock, with anomalies flagged and low-occupancy periods shaded.
It reads the saved parquet and `results/` tables, and retrains nothing — so
every number on screen matches the report exactly.

If the parquet files are missing:

```bash
python -c "import sys; sys.path.insert(0, '.'); from src import dashboard; dashboard.export_all()"
```

## Rules this project follows

- **`Dataset/` is read-only.** Nothing writes to it, and it is never committed.
  `python tools/check_no_data.py` fails the build if any data file, parquet, or
  file over 50 MB gets staged.
- **Every number in the report comes from executed code.** The report contains
  named blocks that the notebooks fill via `src/report.py`; nothing is typed by
  hand. Anything not yet computed reads "pending Phase N", and `07_final`
  asserts that none remain.
- **Never load all 1.6 GB at once.** One meter at a time, in chunks, cached to
  10-minute parquet and reused.
- **Every judgement call is logged.** Section 7 of the report is a 46-row
  decision log: the options considered, the one chosen, why, and what it did to
  the results — including the decisions that made a finding smaller.
- **Notebooks are committed only after they execute cleanly end to end.**

## Data sources

Rashid, H., Singh, P. & Singh, A. (2019). *I-BLEND, a campus-scale commercial and
residential buildings electrical energy dataset.* **Scientific Data** 6, 190015.
<https://www.nature.com/articles/sdata201915>

Outdoor weather: METAR observations for Delhi IGI (VIDP) from the Iowa
Environmental Mesonet ASOS archive, <https://mesonet.agron.iastate.edu/ASOS/>.
The airport is about 25 km from campus, so this is a measured proxy for campus
weather rather than a measurement of it — stated wherever a weather number
appears.
