Phase 7 delivers the project and verifies it.

**Dashboard.** `dashboard/app.py` is a Streamlit page with a building selector,
a date-range picker, a power-occupancy-temperature chart with anomaly bands
coloured, the key numbers for the selected building, and the
threshold-sensitivity curve with that building highlighted. It **reads saved
output only** -- the parquet files written by `src/dashboard.py` and the CSV
tables in `results/` -- and trains nothing. Refitting inside a dashboard would
be slow during a demonstration and, worse, would let the numbers on screen drift
away from the numbers in this report.

The chart uses stacked panels sharing one time axis rather than shared y-axes.
Watts, people and degrees are different quantities, and putting them on one axis
would invent visual relationships that are not in the data. The temperature
panel is optional and carries a dashed line at the building's fitted base
temperature, so the reader sees not just how hot it was but whether it was hot
enough to matter in that building. Alongside it, a fifth headline metric reports
the Phase 8 cooling share of low-occupancy consumption, and an expander carries
the full decomposition and temperature-response tables. Buildings whose cooling
response is not identifiable say so rather than showing a number.

**Report assembly.** Every section of this report is generated. The file
contains named placeholder blocks which the notebooks fill through
`src/report.py`, so no number is ever typed by hand and re-running a notebook
rewrites its section. Anything not yet computed reads "pending Phase N", and
Phase 7 asserts that none remain.

**Verification.** Three checks run as assertions at the end of `07_final.ipynb`,
so the notebook fails rather than reporting a problem quietly:

1. no section still says "pending"
2. every embedded figure link resolves to a file that actually exists
   in `figures/`
3. every phase left entries in the decision log

`tools/check_no_data.py` additionally fails the build if any dataset file,
parquet, or file over 50 MB has been staged for commit.

**Notebook:** `notebooks/07_final.ipynb`.