# bugFix1 — the first code review and what it found

**Project:** SMARTGRID-X
**Review date:** 30 September 2026
**Fixed in:** commit `c703e30`

An external review of the repository raised 15 points. Each was checked against
the actual code and the actual data before anything was changed. **Twelve were
real and are fixed below. Three did not hold**, and are recorded at the end with
the evidence, because "we checked and it was fine" is as much a result as a fix.

---

## Summary

| # | Where | Issue | Severity |
|---|---|---|---|
| 1 | `src/build.py` | Gap interpolation computed, then discarded | **Live — affected published numbers** |
| 2 | `src/models.py` | One 0 W reading turned a whole building's MAPE into NaN | Live, unreported metric |
| 3 | `src/stats.py` | `describe_manual` crashed on empty / all-NaN input | Latent |
| 4 | `src/stats.py` | `describe_manual` gave a silent NaN variance for n = 1 | Latent |
| 5 | `src/stats.py` | `cohens_d` divided by zero degrees of freedom | Latent |
| 6 | `src/anomaly.py` | Injection crashed when a split was shorter than the event | Latent |
| 7 | `src/anomaly.py` | Episode duration disagreed with wall-clock span | Reporting |
| 8 | `tools/check_no_data.py` | Raw traceback outside a git worktree | Tooling |
| 9 | `tools/get_data.py` | Assumed every download was a `.zip` | Latent |
| 10 | `src/config.py` | Calendar glob matched only one spelling | Robustness |
| 11 | `src/features.py` | Calendar fallback happened silently | Robustness |
| 12 | `dashboard/app.py` | Timezone-naive slicing of a tz-aware index | Hardening |

---

## 1. The interpolation was computed and then thrown away

**Severity: the only one that changed published numbers.**

**What the code did.** `src/clean.py` filled gaps of up to 30 minutes and put the
result in `power_filled_w`. `src/build.py` then added up each building's meters —
and summed `power_w`, the *raw* column, instead.

```python
power_cols = [f"power_w_{r}" for r in roles]          # raw, gaps intact
combined["power_w"] = combined[power_cols].sum(axis=1, min_count=len(power_cols))
```

**Why it was wrong.** Every gap the pipeline filled was discarded one step later.
**5,206 ten-minute blocks (0.386% of all rows)** were affected — 3,330 of them in
the Boys hostel alone. The method section of the report described interpolation
as part of the pipeline, and the data-quality table printed a
`blocks_interpolated` count, so the documentation described behaviour the code
did not have.

**Why nothing caught it.** Every available signal said it was working:

- Nothing raised. Summing the raw column is perfectly valid code.
- `build.py` *did* list `power_filled_w` among the columns it carried across, so
  on a read-through the column looked used.
- The reported `blocks_interpolated` count was real — it came from genuine
  interpolation that then went nowhere.
- **The cross-check passed.** Per-building totals were validated against the
  dataset's own `all_buildings_power.csv` and agreed to 0.113%. But *both sides
  of that comparison used raw power*. The check validated ingestion, not the
  build step, and was structurally incapable of catching this.

That last point is the real lesson: a verification only covers the step it
actually crosses. This one looked rigorous and had a blind spot exactly where
the bug was.

**The fix.** Sum the filled series, with a comment explaining why so nobody
"simplifies" it back:

```python
power_cols = [f"power_filled_w_{r}" for r in roles]
combined["power_w"] = combined[power_cols].sum(axis=1, min_count=len(power_cols))
```

**Effect.** Usable data rose 0.02–0.97 percentage points per building, energy
totals 0.04%–1.55%. The headline moved by at most 0.02 percentage points.

---

## 2. A single zero reading destroyed MAPE for an entire building

**What the code did.**

```python
"MAPE_pct": float(
    np.mean(np.abs((y_true - y_pred) / np.where(y_true == 0, np.nan, y_true))) * 100
),
```

**Why it was wrong.** Putting `NaN` in the denominator correctly marks intervals
where MAPE is undefined — but `np.mean` over an array containing any `NaN`
returns `NaN`. So one interval at 0 W made the whole building's MAPE `NaN`. On
this data that happens whenever a meter is briefly off for less than the 6-hour
dead-meter threshold.

**Why nothing caught it.** The project reports MAE, RMSE and R², so nobody read
the MAPE column. A metric nothing depends on is a metric nothing tests.

**The fix.** `np.nanmean`, so undefined intervals are excluded rather than
poisoning the average, plus a guard for the case where *every* interval is
undefined:

```python
mape = float(np.nanmean(relative) * 100) if np.isfinite(relative).any() else float("nan")
```

---

## 3–5. Statistics functions on degenerate input

**3. `describe_manual` on an empty or all-NaN array.** After filtering to finite
values, `n` could be 0 and the code went straight to `squared_deviations / (n - 1)`
→ `ZeroDivisionError`, with `ordered[0]` waiting behind it.

**4. `describe_manual` with a single value.** Sample variance needs `n - 1`
degrees of freedom. With `n = 1` it produced `NaN` *and* a `RuntimeWarning`,
rather than saying plainly that one observation has no spread to estimate.

**5. `cohens_d` with one observation per group.** `(na - 1) * var + (nb - 1) * var`
over `na + nb - 2` divides by zero when both groups have one member.

**Why none of them fired.** All three are only ever called on arrays of 100,000+
rows. They were landmines for anyone running the code on a short extract, a
single building, or a filtered subgroup — which is the first thing a marker or a
teammate would do.

**The fixes.** Return NaNs with `n = 0` for empty input; return `NaN` variance
explicitly for `n = 1`; return `NaN` from `cohens_d` when degrees of freedom are
non-positive or the pooled standard deviation is zero. All three now degrade
instead of crashing.

---

## 6. Anomaly injection crashed on short data

**What the code did.**

```python
start = int(rng.integers(0, n - length))
```

**Why it was wrong.** When the split is no longer than the event, `n - length`
is zero or negative and NumPy raises `ValueError: high <= 0`. Reproduced at
**n ≤ 3**.

**Why it did not fire.** Test splits are thousands of rows and spike events are
at most 3 blocks. The guard was simply never exercised.

**The fix.** Skip any event that cannot fit:

```python
if length >= n:
    continue
```

---

## 7. Episode duration did not mean what it looked like

**What the code did.** `group_into_episodes` merged consecutive flagged
intervals, bridging small gaps, then reported
`duration_hours = len(group) / 6` — the count of flagged blocks.

**Why it was ambiguous.** When an episode bridges a gap, that number is the time
actually flagged, not the wall-clock span from first flag to last. The two
disagree, and only one label was shown, so a reader could not tell which they
were getting. The reviewer's suggested replacement (`end - start`) would have
been wrong in the other direction — it undercounts a contiguous run by one
interval, because the index stores each interval's *start*.

**The fix.** Report both, and say what each means:

- `flagged_hours` — time actually flagged
- `span_hours` — first flag to end of the last one

---

## 8. The safety guard crashed instead of explaining itself

**What the code did.** `check_no_data.py` called
`subprocess.run(["git", "ls-files"], check=True)`. Outside a git worktree, or
with git absent from PATH, it died with a raw `CalledProcessError` traceback.

**Why it mattered.** This script exists to stop the 1.6 GB dataset reaching
GitHub. A guard that fails confusingly is worse than one that says plainly why
it could not check.

**The fix.** A `NotAGitRepo` exception carrying git's own message, caught in
`main()`, printed as a readable sentence, exit code 2.

---

## 9. The downloader assumed everything was a zip

**What the code did.** `get_data.py` called `unzip_into_dataset()` on every
download and then deleted the file.

**Why it was a risk.** A non-zip would hit `zipfile.BadZipFile` — *and then be
deleted by the cleanup step*, so the thing just downloaded would be destroyed.

**Honest scope.** The reviewer reported this as a live crash on the calendar
files. It is not: querying the figshare API confirms **all four** files in the
collection are `.zip`, the calendar arriving as `iiitd_calender_schedule.zip`.
The script had already run successfully. It is a latent robustness gap, not a
live bug — figshare records do get reorganised.

**The fix.** Test with `zipfile.is_zipfile()` first; keep non-archives as plain
files, and only delete a download that was actually extracted.

---

## 10–11. The calendar could be missed, and the fallback was silent

**10. Spelling.** `CALENDAR_GLOB = "calender_year_*.csv"` — the dataset authors
misspell "calendar", so this is correct for the real files. But a corrected
re-publication, or a hand-renamed file, would match nothing.

**11. Silence.** If no calendar was found, the pipeline fell back to approximate
vacation windows and said nothing. Those windows agree with the published
calendar on only about **68%** of days, so every semester-versus-vacation result
would have quietly rested on an approximation with nothing flagging it.

**The fixes.** Accept both spellings; emit a `RuntimeWarning` naming the
directory searched, the agreement rate, and the command that fetches the real
file.

---

## 12. Timezone-naive slicing of a timezone-aware index

**What the code did.** `data.loc[str(start) : str(...)]` on an `Asia/Kolkata`
index, with bounds built from naive timestamps.

**Honest scope.** This one **works**. Tested on pandas 3.0.3 it returns the
correct 433 rows — pandas localises the strings to the index timezone. It was
hardened anyway because the behaviour is an implementation detail rather than a
guarantee, and being explicit costs nothing:

```python
tz = data.index.tz
lower = pd.Timestamp(start).tz_localize(tz)
upper = (pd.Timestamp(end) + pd.Timedelta(days=1)).tz_localize(tz)
window = data.loc[lower:upper]
```

---

## Three claims that did not survive checking

**"`requirements.txt` pins versions that do not exist on PyPI."** They exist.
`pip index versions pandas` lists 3.0.3 among many, with 3.0.6 current, and all
pins match what the notebooks actually ran on. The reviewer was most likely on
an older Python, where those wheels are unavailable. **No change to the pins** —
instead a header now states the real constraint (Python 3.13+) and explains how
to relax them.

**"Timezone-naive slicing raises `TypeError`."** It returns the correct rows.
Hardened anyway (#12), but it was not broken.

**"`nbbuild` silently discards lines before the first cell marker."**
Documented and deliberate — it is what allows a module docstring above the first
cell. Behaving as designed.

---

## What the episode actually taught

**A verification only covers the step it crosses.** The `all_buildings_power.csv`
cross-check was the strongest check in the project and it passed while the build
step was wrong, because both sides of the comparison used raw power. Strength of
a check is not the same as coverage.

**"It works on this dataset" is not "it works."** Six of the twelve could not
fire on this specific download. They would all fire on a shorter extract, a
single building, or a re-published archive — which is what anyone else running
the code would hit first.

**Fixing a bug can activate another.** Fix #1 switched the build onto
`power_filled_w`. That column was itself being filled incorrectly — pandas'
`interpolate(limit=)` caps *consecutive* values rather than skipping long gaps,
so it had been fabricating data at the head of every long gap. While the column
was discarded this was harmless; the moment it was used it became live. A second
review caught it, and it is documented in `bugFix2`.

**Generated numbers stay in sync; generated prose does not.** The report fills
its numbers from executed code, so when fix #1 changed a Phase 6 comparison the
count updated itself from "5 favour" to "4 favour" automatically. The sentence
beside it still read *"they all point the same way."* The design protects
figures, not claims — so the sentences that depend on a count are now generated
from that count too.
