Phase 6 is set up as a controlled experiment, not a pipeline. Two detectors, the
same data, the same procedure, one difference: **Detector T** scores the
residuals of model B (time features only) and **Detector O** scores the residuals
of model C (time and occupancy).

**Why anomalies are injected.** Nobody labelled the real faults on this campus,
so there is no ground truth to score against. A **copy** of the test period is
taken and anomalies with recorded locations are added; those locations are the
labels. **Everything injected is synthetic** and corresponds to nothing that
happened on the IIIT-Delhi campus.

**What is injected**, with seed 42 so the whole thing is reproducible:

| Type | Change | Duration | Placement |
|---|---|---|---|
| spike | +50% to +100% | 10-30 minutes | anywhere |
| waste | +15% to +30% | 2-6 hours | low-occupancy periods only |

Only `power_w` is altered; the time and occupancy columns are untouched, so both
detectors make identical predictions on contaminated and clean data and any
difference in what they catch comes from the models rather than from the
injection disturbing their inputs. Events are never allowed to overlap. Fewer
waste events land than are requested, because multi-hour events must fit inside
low-occupancy periods that are only 6-28% of the record; **every number uses the
count achieved, never the count requested**.

**Scoring.** Residuals are standardised with the **median and median absolute
deviation** rather than the mean and standard deviation, because the standard
deviation is inflated by the very anomalies being hunted -- a few large events
would raise the bar and hide themselves. The 1.4826 factor rescales the MAD so
the thresholds of 2 and 3 keep their usual meaning. Bands are NORMAL below
2, WARNING from 2 to 3, ANOMALY
above 3, cross-checked against Tukey IQR fences.

**Three comparisons rather than one.** A fixed threshold turned out not to be a
fair test (section 6.7), so the detectors are also compared at a **matched alert
budget** and with **threshold-free** measures (ROC AUC and average precision).

**Notebook:** `notebooks/06_anomaly.ipynb`.