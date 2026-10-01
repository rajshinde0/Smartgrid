# bugFix2 — the second review

**Project:** SMARTGRID-X
**Review date:** 2 October 2026
**Companion to:** [`bugFix1.md`](bugFix1.md)

A second pass over the pipeline, read cold. Six issues found. **One was live and
contaminating published numbers — and it was live precisely because of a fix
made in the first round.** Every suspicion was verified against the real data
before anything was changed.

---

## Summary

| # | Where | Issue | Severity |
|---|---|---|---|
| 1 | `src/clean.py` | Interpolation filled the gaps it promised to skip | **Live** |
| 2 | `src/clean.py` | A single dropout could hide a dead meter | Live, under-counted |
| 3 | `src/waste.py` | Two return paths with different keys | Latent crash |
| 4 | `src/ingest.py` | `power_missing` double-counted invalidated readings | Reporting |
| 5 | `src/occupancy.py` | Off-grid timestamps dropped silently | Latent data loss |
| 6 | `src/ingest.py` | Three functions with no callers | Dead code |

---

## 1. The interpolation filled the gaps it promised to leave alone

**What the code did.**

```python
filled = series.interpolate(method="time", limit=limit_steps, limit_area="inside")
```

The docstring, the method section and the decision log all said the same thing:
*gaps of at most 30 minutes are filled, longer gaps are left missing.*

**Why it was wrong.** That is not what pandas' `limit=` means. It caps the number
of **consecutive** NaNs filled — so given a 200-day gap it fills the **first
three blocks** and stops, rather than skipping the gap. Those three values are
drawn along a straight line between the last reading before the gap and the
first one after it, which may be months later.

Minimal reproduction:

```
input : 1 real value, then a 17-block gap, then real values
filled inside that long gap : 3 blocks
values invented             : [144.4, 188.9, 233.3]
```

Measured across all nine meters:

```
blocks in genuinely short gaps (<=30 min, legitimate) : 2,498
blocks filled at the head of long gaps (fabricated)   : 5,301
```

**68% of every interpolated value in the project was invented data**, sitting at
the edge of gaps the method explicitly claimed not to touch.

**Why it only mattered now.** Until the first review, `build.py` summed the raw
column and discarded `power_filled_w` entirely (bugFix1 #1), so these fabricated
values went nowhere. Fixing *that* switched the build onto `power_filled_w` —
which promoted this bug from latent to live. **The first fix was correct and
necessary; it also activated a second bug.** That interaction is the single best
argument for reviewing twice.

**The fix.** Measure each gap's whole length first, then fill only the runs that
are short enough in their entirety:

```python
missing = series.isna()
short_gap = missing & (gap_runs(series) <= limit_steps)
candidate = series.interpolate(method="time", limit_area="inside")  # no limit
filled = series.where(~short_gap, candidate)
```

**Effect.** Interpolated blocks fell from **5,206 to 2,184** — the fabricated
ones are gone and the legitimate ones remain. Usable coverage fell 0.02–0.41
percentage points per building, which is lower *and correct*. The headline moved
by at most 0.01 percentage points.

---

## 2. A single missing block could hide a dead meter

**What the code did.** `flag_meter_off` grouped unbroken runs of exactly-zero
power, and any missing block broke the run.

**Why it was wrong.** A ten-hour outage containing one dropout became two
five-hour runs, **neither** of which crossed the six-hour threshold. The whole
outage went unflagged and its zeros were counted as genuine zero consumption.

Measured: **2,413 zero-blocks (about 402 hours)** sat in sub-threshold runs in
the Lecture building; 4 in Academic, 2 in Library.

**The fix.** A gap of up to 30 minutes — the same limit used for interpolation —
now bridges a zero-run when both neighbours read zero. Longer gaps still break
it: at that length the absence is its own event rather than a dropout. The flag
is never set on a missing block, so the rule can never invent dead time from
absent data.

**Effect.** Adds about 14 hours to Lecture's meter-off total and almost nothing
elsewhere. Recorded as decision D01-09.

---

## 3. One function, two incompatible contracts

**What the code did.** `low_occupancy_share` returned 11 keys normally, but its
empty-input early return gave 3:

```python
if usable.empty:
    return {"threshold": np.nan, "share_pct": np.nan, "reachable": False}
```

**Why it was wrong.** `05_waste.py` indexes all eleven directly. A building with
no usable rows would raise `KeyError` several lines later, far from the cause.

**Why it did not fire.** No building in this dataset is empty. It would fire on a
shorter extract, or on one building whose meter was dead throughout.

**The fix.** A `SHARE_KEYS` tuple and an `_empty_share_result()` helper, so both
paths return the same keys with NaN where nothing was measured.

---

## 4. A quality statistic double-counted

**What the code did.** `_clean_chunk` set out-of-range power to `NaN`, then
counted `power_missing` afterwards — so any reading rejected by the range rule
appeared in **both** `power_invalid` and `power_missing` in the Phase 1
data-quality table.

**Honest scope.** `power_invalid == 0` for all nine meters, so the two counts
never actually overlap on this data. It is a reporting trap waiting for the first
dataset that does contain an out-of-range reading.

**The fix.** Capture `power_missing_in_source` before invalidation and keep
`power_missing` as the post-cleaning total, so the two are distinguishable and
the table adds up.

---

## 5. Off-grid occupancy timestamps vanished without a word

**What the code did.** `load_occupancy` reindexed onto a 10-minute grid without
flooring the index first.

**Why it was wrong.** Any timestamp not already on a boundary is simply absent
from the new index — **dropped with no error and no warning**. Fewer rows, no
sign anything was lost, which is the worst way for data to disappear.

**Why it did not fire.** Phase 0 verified all seven occupancy files sit exactly
on 10-minute boundaries.

**The fix.** Floor the index before reindexing, and warn with a count if flooring
moved anything — turning silent loss into a visible message.

---

## 6. Dead code

`peek`, `tail_rows` and `count_rows` in `src/ingest.py` had **zero call sites**;
the notebooks use `explore.head_tail`. `tail_rows` also read the entire file
despite a docstring implying otherwise. All three removed.

---

## What this round added to the lessons

**A fix can promote a latent bug to a live one.** Finding #1 existed before the
first review and was harmless while its output was discarded. Repairing the
discard made it live. Neither fix was wrong; the interaction between them was
invisible from either one alone.

**Generated prose needs generating too.** Fixing #1 moved a Phase 6 comparison
across zero — the fifth of five fair comparisons flipped against Detector O,
then back again after the dead-meter fix. Each time the report's generated
*count* updated itself correctly while the hand-written sentence beside it
("they all point the same way") did not. Those sentences are now built from the
count, so they cannot contradict it. A `.capitalize()` call that had been
quietly rendering "Detector **o**" was fixed in the same pass.

**Most bugs were invisible on this dataset.** Four of six could not fire on the
I-BLEND download as published. They would all fire on a shorter extract, a
single building, or a re-published archive.
