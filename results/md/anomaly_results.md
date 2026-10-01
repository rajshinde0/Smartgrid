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
| Academic | 26,522 | 199 | 63 | 324 | 1,362 | 6.36 | 772 |
| Boys_Hostel | 18,138 | 198 | 31 | 326 | 582 | 5.01 | 544 |
| Girls_Hostel | 17,627 | 198 | 26 | 325 | 552 | 4.98 | 393 |
| Mess | 23,630 | 198 | 123 | 326 | 2,509 | 12 | 1,255 |
| Library | 17,832 | 198 | 200 | 326 | 4,217 | 25.48 | 4,420 |
| Lecture | 5,548 | 190 | 131 | 304 | 2,344 | 47.73 | 2,740 |
| Facilities | 22,483 | 199 | 0 | 324 | 0 | 1.44 | 0 |

#### Confusion matrices and scores, at the specified |z| > 3 threshold

| detector | anomaly type | n anomaly intervals | true positives | false positives | false negatives | true negatives | precision | recall | f1 | accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| T | all | 1,686 | 547 | 1,514 | 1,139 | 23,322 | 0.27 | 0.32 | 0.29 | 0.90 |
| T | spike | 324 | 106 | 1,514 | 218 | 23,322 | 0.07 | 0.33 | 0.11 | 0.93 |
| T | waste | 1,362 | 441 | 1,514 | 921 | 23,322 | 0.23 | 0.32 | 0.27 | 0.91 |
| O | all | 1,686 | 646 | 2,883 | 1,040 | 21,953 | 0.18 | 0.38 | 0.25 | 0.85 |
| O | spike | 324 | 123 | 2,883 | 201 | 21,953 | 0.04 | 0.38 | 0.07 | 0.88 |
| O | waste | 1,362 | 523 | 2,883 | 839 | 21,953 | 0.15 | 0.38 | 0.22 | 0.86 |

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
| fixed threshold \|z\| > 3 (as specified) | 0.29 | 0.28 | mean F1 | -0.01 |
| matched alert budget | 0.29 | 0.29 | mean F1 | -0.00 |
| threshold-free ranking | 0.41 | 0.42 | mean average precision | 0.01 |
| threshold-free ranking | 0.68 | 0.70 | mean ROC AUC | 0.02 |
| waste anomalies only, matched budget | 0.15 | 0.16 | mean F1 | 0.01 |
| waste events noticed at all | 0.20 | 0.23 | event recall | 0.03 |

![Detector T against Detector O at a matched budget and threshold-free  [SYNTHETIC]](../figures/fig_06_detector_comparison.png)

*Compared fairly, the two detectors perform almost identically.*

**Answer to research question 3: a qualified yes -- occupancy helps
consistently, but only a little.** The fixed-threshold comparison is discarded
as a calibration artefact. On the 5 fair comparisons, 4 favour Detector O:
matched-budget F1 0.289 -> 0.287, average precision 0.414 -> 0.423, ROC AUC
0.675 -> 0.696, and waste-event recall 19.5% -> 22.9%.

Every margin is one to three percentage points, and the one comparison that does
not favour Detector O sits essentially on zero, so the direction is not
unanimous. What gives the result weight is **where** the gains fall: the largest
are on the waste anomalies specifically -- the case where occupancy ought to
matter, because a sustained modest lift only looks wrong if you know the
building was empty. Occupancy adds nothing to catching spikes, which stand out
against any baseline.

This modest result is consistent with everything else the project found:
occupancy explains only 8-44% of power variation (Phase 2), adds +0.109 to
validation R-squared on average (Phase 4), and several buildings have a nearly
flat daily profile (Phase 3). **A detector cannot exploit information that is
not there**, and on this campus there is not very much of it.

#### Rule variants

| rule | detector | alerts | precision | recall | f1 |
|---|---|---|---|---|---|
| IQR fences (cross-check) | O | 859.86 | 0.56 | 0.27 | 0.28 |
| IQR fences (cross-check) | T | 658.29 | 0.57 | 0.25 | 0.27 |
| one-sided z > 3 (positive only) | O | 963.14 | 0.63 | 0.27 | 0.28 |
| one-sided z > 3 (positive only) | T | 784.86 | 0.65 | 0.26 | 0.29 |
| two-sided \|z\| > 3 (as specified) | O | 1,035.29 | 0.53 | 0.27 | 0.28 |
| two-sided \|z\| > 3 (as specified) | T | 806.29 | 0.56 | 0.26 | 0.29 |

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
| 1 | Academic | 2017-09-14 03:30:00+05:30 | 2017-09-14 10:30:00+05:30 | 7 | 8.40 | 37.37 | 261.61 |
| 2 | Academic | 2017-09-15 03:20:00+05:30 | 2017-09-15 11:10:00+05:30 | 8 | 7.78 | 34.41 | 275.24 |
| 3 | Academic | 2017-10-09 03:20:00+05:30 | 2017-10-09 10:10:00+05:30 | 7 | 7.23 | 38.73 | 271.08 |
| 4 | Academic | 2017-10-04 03:20:00+05:30 | 2017-10-04 11:10:00+05:30 | 7.50 | 7.15 | 36.86 | 276.42 |
| 5 | Academic | 2017-09-25 03:20:00+05:30 | 2017-09-25 09:50:00+05:30 | 6.33 | 6.96 | 35.43 | 224.36 |
| 6 | Academic | 2017-08-17 03:40:00+05:30 | 2017-08-17 10:40:00+05:30 | 6.83 | 6.93 | 35.80 | 244.64 |
| 7 | Academic | 2017-10-03 03:30:00+05:30 | 2017-10-03 11:10:00+05:30 | 7.83 | 6.92 | 37.19 | 291.31 |
| 8 | Academic | 2017-10-06 03:20:00+05:30 | 2017-10-06 11:20:00+05:30 | 8.17 | 6.89 | 36.99 | 302.06 |
| 9 | Academic | 2017-08-18 03:30:00+05:30 | 2017-08-18 11:10:00+05:30 | 7.67 | 6.88 | 35.15 | 269.48 |
| 10 | Academic | 2017-09-12 03:20:00+05:30 | 2017-09-12 11:10:00+05:30 | 7.67 | 6.87 | 34.11 | 261.51 |

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
| Academic | 2017-09-14 03:30:00+05:30 | 7 | 8.40 | 37.37 | 261.61 | 103 |
| Boys_Hostel | 2017-10-10 14:00:00+05:30 | 5.17 | 6.75 | 38.43 | 198.55 | 64 |
| Library | 2017-10-06 04:30:00+05:30 | 4.67 | 5 | 22.44 | 104.74 | 87 |
| Lecture | 2017-08-14 04:50:00+05:30 | 0.17 | 4.66 | 3.06 | 0.51 | 8 |
| Facilities | 2017-06-05 15:00:00+05:30 | 1.33 | 4.53 | 8.83 | 11.77 | 113 |
| Mess | 2017-07-25 07:50:00+05:30 | 1.83 | 4.29 | 32.50 | 59.58 | 43 |
| Girls_Hostel | 2017-10-10 17:40:00+05:30 | 0.17 | 3.07 | 12.42 | 2.07 | 2 |