> **All anomalies used to score the detectors in this section are SYNTHETIC.**
> They were injected into a copy of the test data with a recorded seed
> (42) purely so that the two detectors could be compared against known
> labels. No injected event corresponds to anything that happened on the
> IIIT-Delhi campus. The real-data table at the end of this section is kept
> separate, and its entries are **candidates for inspection, not confirmed
> faults**.

#### The experiment

Detector **T** scores the residuals of a time-only model; Detector **O** scores
the residuals of a time-and-occupancy model. Everything else about them is
identical.

| building | test intervals | spike events | waste events | spike intervals | waste intervals | % of intervals contaminated | low-occ intervals available |
|---|---|---|---|---|---|---|---|
| Academic | 26,511 | 199 | 65 | 324 | 1,409 | 6.54 | 772 |
| Boys_Hostel | 17,855 | 198 | 28 | 325 | 554 | 4.92 | 494 |
| Girls_Hostel | 17,579 | 198 | 27 | 332 | 554 | 5.04 | 391 |
| Mess | 23,591 | 199 | 122 | 323 | 2,578 | 12.30 | 1,255 |
| Library | 17,809 | 198 | 200 | 325 | 4,274 | 25.82 | 4,391 |
| Lecture | 5,540 | 196 | 132 | 320 | 2,403 | 49.15 | 2,735 |
| Facilities | 22,404 | 198 | 0 | 325 | 0 | 1.45 | 0 |

#### Confusion matrices and scores, at the specified |z| > 3 threshold

| detector | anomaly type | n anomaly intervals | true positives | false positives | false negatives | true negatives | precision | recall | f1 | accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| T | all | 1,733 | 541 | 1,523 | 1,192 | 23,255 | 0.26 | 0.31 | 0.28 | 0.90 |
| T | spike | 324 | 105 | 1,523 | 219 | 23,255 | 0.06 | 0.32 | 0.11 | 0.93 |
| T | waste | 1,409 | 436 | 1,523 | 973 | 23,255 | 0.22 | 0.31 | 0.26 | 0.90 |
| O | all | 1,733 | 632 | 2,873 | 1,101 | 21,905 | 0.18 | 0.36 | 0.24 | 0.85 |
| O | spike | 324 | 123 | 2,873 | 201 | 21,905 | 0.04 | 0.38 | 0.07 | 0.88 |
| O | waste | 1,409 | 509 | 2,873 | 900 | 21,905 | 0.15 | 0.36 | 0.21 | 0.86 |

![Confusion matrices for both detectors, Academic building  [SYNTHETIC]](../figures/fig_06_confusion_matrices.png)

*Detector O has higher recall and lower precision at this threshold -- but see
the fairness correction below.*

#### The fair comparison

A fixed threshold does not put the two detectors on equal terms: model C fits
better, so its residuals are tighter, so its MAD is smaller, so the same
deviation in watts scores a larger Z and it raises more alerts. Comparing at
that threshold measures scale calibration rather than the value of the
information.

| comparison | detector T | detector O | metric | difference (O - T) |
|---|---|---|---|---|
| fixed threshold \|z\| > 3 (as specified) | 0.30 | 0.29 | mean F1 | -0.01 |
| matched alert budget | 0.29 | 0.30 | mean F1 | 0.00 |
| threshold-free ranking | 0.43 | 0.44 | mean average precision | 0.02 |
| threshold-free ranking | 0.68 | 0.70 | mean ROC AUC | 0.02 |
| waste anomalies only, matched budget | 0.15 | 0.17 | mean F1 | 0.02 |
| waste events noticed at all | 0.20 | 0.24 | event recall | 0.04 |

![Detector T against Detector O at a matched budget and threshold-free  [SYNTHETIC]](../figures/fig_06_detector_comparison.png)

*Compared fairly, the two detectors perform almost identically.*

**Answer to research question 3: a qualified yes -- occupancy helps
consistently, but only a little.** The fixed-threshold comparison is discarded
as a calibration artefact. On the 5 fair comparisons, 5 favour Detector O:
matched-budget F1 0.292 -> 0.296, average precision 0.426 -> 0.443, ROC AUC
0.682 -> 0.702, and waste-event recall 20.2% -> 24.4%.

Every margin is one to three percentage points. What makes them credible is that
they all point the same way and that **the largest gains fall on the waste
anomalies specifically** -- the case where occupancy ought to matter, because a
sustained modest lift only looks wrong if you know the building was empty.
Occupancy adds nothing to catching spikes, which stand out against any baseline.

This modest result is consistent with everything else the project found:
occupancy explains only 7-45% of power variation (Phase 2), adds +0.107 to
validation R-squared on average (Phase 4), and several buildings have a nearly
flat daily profile (Phase 3). **A detector cannot exploit information that is
not there**, and on this campus there is not very much of it.

#### Rule variants

| rule | detector | alerts | precision | recall | f1 |
|---|---|---|---|---|---|
| IQR fences (cross-check) | O | 854.29 | 0.57 | 0.28 | 0.28 |
| IQR fences (cross-check) | T | 654.29 | 0.57 | 0.26 | 0.27 |
| one-sided z > 3 (positive only) | O | 972.86 | 0.64 | 0.29 | 0.29 |
| one-sided z > 3 (positive only) | T | 789.57 | 0.65 | 0.27 | 0.30 |
| two-sided \|z\| > 3 (as specified) | O | 1,042.43 | 0.54 | 0.29 | 0.29 |
| two-sided \|z\| > 3 (as specified) | T | 808 | 0.56 | 0.27 | 0.30 |

One-sided detection -- flagging only *excess* consumption -- improves precision
substantially at almost no cost in recall, because every real or injected waste
event adds power rather than removing it. The IQR cross-check flags far more and
scores worse, as expected for heavy-tailed residuals.

#### Top 10 unusual patterns in the real data

**These are candidates for inspection, not confirmed faults.** Each is a period
where a building drew considerably more power than a model of time and occupancy
expected. Ordinary explanations are available for all of them -- an event in the
building, a maintenance test, a commissioning run, or simply a hot day, and the
project has **no weather data covering this period** with which to rule the last
one out (the weather record shipped with I-BLEND covers March-June 2018 only,
which does not overlap the 2014-2017 analysis window at all). Consecutive
flagged intervals are grouped into episodes, so a four-hour deviation appears
once rather than twenty-four times.

| # | building | start | end | duration hours | peak z | mean excess kW | total excess kWh |
|---|---|---|---|---|---|---|---|
| 1 | Academic | 2017-09-14 03:30:00+05:30 | 2017-09-14 10:30:00+05:30 | 7 | 8.41 | 37.38 | 261.69 |
| 2 | Academic | 2017-09-15 03:20:00+05:30 | 2017-09-15 11:10:00+05:30 | 8 | 7.78 | 34.41 | 275.28 |
| 3 | Academic | 2017-10-09 03:20:00+05:30 | 2017-10-09 10:10:00+05:30 | 7 | 7.23 | 38.72 | 271.05 |
| 4 | Academic | 2017-10-04 03:20:00+05:30 | 2017-10-04 11:10:00+05:30 | 7.50 | 7.15 | 36.85 | 276.41 |
| 5 | Academic | 2017-09-25 03:20:00+05:30 | 2017-09-25 09:50:00+05:30 | 6.33 | 6.97 | 35.43 | 224.41 |
| 6 | Academic | 2017-08-17 03:40:00+05:30 | 2017-08-17 10:40:00+05:30 | 6.83 | 6.94 | 35.80 | 244.63 |
| 7 | Academic | 2017-10-03 03:30:00+05:30 | 2017-10-03 11:10:00+05:30 | 7.83 | 6.93 | 37.19 | 291.28 |
| 8 | Boys_Hostel | 2017-10-10 14:00:00+05:30 | 2017-10-10 18:50:00+05:30 | 4.83 | 6.90 | 39.37 | 190.27 |
| 9 | Academic | 2017-10-06 03:20:00+05:30 | 2017-10-06 11:20:00+05:30 | 8.17 | 6.89 | 36.98 | 302.03 |
| 10 | Academic | 2017-09-12 03:20:00+05:30 | 2017-09-12 11:10:00+05:30 | 7.67 | 6.88 | 34.12 | 261.56 |

**Read that table with care: it is not ten findings, it is one finding ten
times.** Almost every one of the most extreme episodes on the campus is the
Academic building, starting around 03:20, running seven to eight hours, between
August and November 2017, at an excess of roughly 35-38 kW -- repeating day
after day.

A repeating daily pattern is not what a fault looks like; it is what a **change
of schedule** looks like. Something in that building began switching on in the
small hours in the second half of 2017, and a model fitted on 2014-2016 does not
know about it, so it reports the same surprise every morning. This is the
concept drift of section 6.5 resurfacing as false alarms -- the same drift
measured there as a 42% rise in Academic consumption across the record.

The practical lesson is worth stating: **a detector built on a fixed historical
baseline will eventually spend all of its alerts re-reporting a change it should
have absorbed.** A deployed version of this would need periodic refitting. A
more useful operator view takes the most unusual episode per building, so one
recurring pattern occupies one row:

| building | start | duration hours | peak z | mean excess kW | total excess kWh | total episodes |
|---|---|---|---|---|---|---|
| Academic | 2017-09-14 03:30:00+05:30 | 7 | 8.41 | 37.38 | 261.69 | 103 |
| Boys_Hostel | 2017-10-10 14:00:00+05:30 | 4.83 | 6.90 | 39.37 | 190.27 | 61 |
| Library | 2017-10-06 04:30:00+05:30 | 4.67 | 5.03 | 22.44 | 104.74 | 86 |
| Lecture | 2017-08-14 04:50:00+05:30 | 0.17 | 4.67 | 3.06 | 0.51 | 8 |
| Facilities | 2017-06-05 15:00:00+05:30 | 1.33 | 4.53 | 8.84 | 11.78 | 117 |
| Mess | 2017-07-25 07:50:00+05:30 | 1.83 | 4.29 | 32.48 | 59.54 | 43 |
| Girls_Hostel | 2017-10-10 17:40:00+05:30 | 0.17 | 3.07 | 12.44 | 2.07 | 2 |