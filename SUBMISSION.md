# SMARTGRID-X — submission

**Occupancy-aware energy-waste and anomaly analysis of the I-BLEND campus dataset**

MD3135 Data Science · T.Y. B.Tech · Vishwakarma Institute of Technology, Pune
Rajwardhan Shinde

---

## Links

| | |
|---|---|
| **GitHub repository** | <https://github.com/rajshinde0/Smartgrid> |
| **Run it in Google Colab** | <https://colab.research.google.com/github/rajshinde0/Smartgrid/blob/main/colab/SMARTGRID_X.ipynb> |

The Colab notebook needs nothing installed. It clones the repository, fetches
the data, runs the analysis, shows every figure and table it produced, and then
checks its own numbers against the published ones. A Google login is the only
requirement.

Every individual phase also opens on its own in Colab — the links are in the
[repository README](https://github.com/rajshinde0/Smartgrid#readme).

---

## The finding, in one sentence

**When these seven campus buildings are at their emptiest, they still draw
62–85% of their average power — and only 1–9% of that is air conditioning.**

So the waste is a scheduling and controls problem, not a thermostat problem.

---

## What is in this submission

| Path | What it is |
|---|---|
| `docs/PROJECT_SUMMARY.md` | **Start here.** The whole project in ~5,800 words, with the figures. |
| `docs/PROJECT_REPORT.md` | The master document: 14 sections, ~30,900 words, every number generated from executed code. |
| `presentation/SMARTGRID-X.pptx` | The 12-slide deck. |
| `notebooks/` | Nine executed notebooks — the analysis itself. |
| `notebooks/src_py/` | The percent-format source each notebook is built from. |
| `src/` | 17 analysis modules imported by every notebook. |
| `tests/` | 78 regression tests. |
| `figures/` | All 47 charts. |
| `results/` | 50 result tables, including the 50-row decision log. |
| `dashboard/` | The Streamlit dashboard. |
| `docs/bugFix1.md`, `bugFix2.md` | Two rounds of code review, written up. |

**The dataset is not included.** I-BLEND is 1.6 GB and is published under its own
DOI; `python tools/get_data.py` fetches it. Nothing data-shaped is in this
archive, and `python tools/check_no_data.py` enforces that.

---

## Running it locally

```bash
python -m pip install -r requirements.txt
python tools/get_data.py                      # the 1.6 GB dataset, from figshare
python tools/build_and_run.py 00_explore      # ... through 08_weather
streamlit run dashboard/app.py
```

One `requirements.txt` works on any Python from 3.10 up. Each package is
declared twice behind a version marker: the exact pinned version on 3.13+,
which is the stack every published number was produced on, and a floor below
that so the project still installs on Colab.

To skip the slow ingest step, `python tools/get_cache.py --full` downloads
Phase 1's saved output and the analysis runs from there.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -q                    # 78 tests, no data needed
```

---

## Three things worth a marker's attention

**Every number came from executed code.** The report contains named placeholder
blocks the notebooks fill; nothing is typed by hand. Re-running a notebook
rewrites its section. A full rebuild from raw on 31 October reproduced every
result table and figure bit-for-bit.

**Every judgement call is logged.** Section 7 of the report is a 50-row decision
log: options considered, the one chosen, the reason, and the effect on the
results — including the decisions that made a finding *smaller*, and one that
was later superseded.

**The results that went against us are reported first.** On the anomaly
comparison this project originally specified, the occupancy-aware detector comes
out *worse*; that row leads the table, and the explanation follows it. The one
building whose coverage embarrasses the method is kept in every table with its
18.9% visible.
