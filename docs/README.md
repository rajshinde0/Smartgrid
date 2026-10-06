# Documentation index

Five kinds of document live here. Start with the summary — the others exist to
answer questions it deliberately does not stop to answer.

## The summary

**[`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md)** — the whole project in ~5,800
words: the findings, how they were produced, what went wrong on the way, and
what not to conclude from them.

This is the one to hand someone. It carries the eleven figures that matter and
links through to the full report wherever the detail lives there. The same
document is also published as a page at
<https://claude.ai/code/artifact/21d8c3a5-34b9-4961-b9a6-344d4a76ca88>.

## The report

**[`PROJECT_REPORT.md`](PROJECT_REPORT.md)** — the master document, ~30,900
words in 14 sections plus an appendix. Everything the summary states, with the
workings.

It is written to be read on its own. A teammate or an examiner who has never
opened a notebook should be able to follow it start to finish, and every number
in it was produced by executed code: the file contains named placeholder blocks
that the notebooks fill through `src/report.py`, so nothing is typed by hand.

Where to enter it, depending on what you want:

| You want | Read |
|---|---|
| The finding, in one page | §1 Abstract, then §8 Headline findings |
| Whether to believe it | §4 Data quality, §10 Limitations |
| Why it was done this way | §7 Decision log — 46 entries, every judgement call |
| To run it yourself | §13 How to reproduce |
| The anomaly experiment | §9 |
| Course mapping (Units I–VI, Tutorials 1–8) | §12 |

The decision log in §7 is the part worth knowing about. Each row names the
options considered, the one chosen, the reason, and the effect on the results —
including the decisions that made a finding smaller.

## The bug write-ups

Two rounds of outside-eye code review, written up as narrative rather than as a
changelog. Each entry follows the same four beats: **what the code did**, **why
it was wrong**, **why nothing caught it**, and **the fix**.

- **[`bugFix1.md`](bugFix1.md)** — the first 12 issues, including the one that
  mattered most: interpolated power was being computed and then silently
  discarded, so 5,206 blocks used raw readings instead. The cross-check against
  the published totals passed anyway, because both sides of the check used raw
  power — it had been validating ingestion, not the build step.
- **[`bugFix2.md`](bugFix2.md)** — 6 more, found after the first round was
  fixed. Several were only reachable *because* the first round was fixed: with
  interpolation finally live, `pandas.interpolate(limit=3)` turned out to cap
  consecutive NaNs rather than whole gaps, fabricating the first three blocks
  of every long outage.

They are kept because the second-round pattern is the useful lesson: fixing a
real bug is what exposed the next one.

## The planning documents

**[`planning/`](planning/)** — the original brief, written before any code
existed. Kept unedited, as the record of what was planned versus what the data
turned out to allow.

- `Project Overview.md` — the pitch, the dataset, the three research questions
- `Implementation Plan.md` — the phase-by-phase build plan
- `ds_cp_plan.docx` — the same plan as submitted

Read these against §7 of the report to see where the plan bent. The headline
definition of "low occupancy" is the clearest case: the plan assumed an absolute
occupancy cutoff, and the data forced a per-building relative one.

## Not in this folder

- **[`../progress.md`](../progress.md)** — the running log, newest phase last:
  what was done, what was found, what is next.
- **[`../README.md`](../README.md)** — setup, how to run the notebooks, the
  rules the project follows.
- **`../results/`** — 50 CSV tables, the machine-readable form of everything in
  §6 and §8. `decision_log.csv` is §7.
- **`../figures/`** — all 47 figures. Every one is referenced by the report, and
  `07_final.ipynb` fails if a reference is ever broken.
