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