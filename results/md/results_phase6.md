#### What was injected

| building | test intervals | spike events | waste events | spike intervals | waste intervals | % of intervals contaminated | low-occ intervals available |
|---|---|---|---|---|---|---|---|
| Academic | 26,522 | 199 | 63 | 324 | 1,362 | 6.36 | 772 |
| Boys_Hostel | 18,138 | 198 | 31 | 326 | 582 | 5.01 | 544 |
| Girls_Hostel | 17,627 | 198 | 26 | 325 | 552 | 4.98 | 393 |
| Mess | 23,630 | 198 | 123 | 326 | 2,509 | 12 | 1,255 |
| Library | 17,832 | 198 | 200 | 326 | 4,217 | 25.48 | 4,420 |
| Lecture | 5,548 | 190 | 131 | 304 | 2,344 | 47.73 | 2,740 |
| Facilities | 22,483 | 199 | 0 | 324 | 0 | 1.44 | 0 |

Spikes are short and can go anywhere, so nearly all 200 are placed. Waste events
run 2-6 hours and must start inside a low-occupancy period, and those are only
6% of the Academic building's record -- there is no room for 200 non-overlapping
multi-hour events inside them, so placement saturates. That is a property of the
campus, not a fault in the method, and every score below uses the achieved
count.

![A single injected waste event, with occupancy below  [SYNTHETIC]](../figures/fig_06_injected_waste_example.png)

*Deliberately subtle: a modest lift sustained for hours while the building is
nearly empty. A spike stands out against any baseline; slow waste looks like a
slightly busier night unless the detector knows nobody was there.*

#### The fixed threshold specified in the plan

![Confusion matrices for both detectors, Academic building  [SYNTHETIC]](../figures/fig_06_confusion_matrices.png)

*At a fixed |z| > 3 threshold Detector O has higher recall and lower precision
than Detector T.*

| detector | anomaly type | n anomaly intervals | true positives | false positives | false negatives | precision | recall | f1 | accuracy |
|---|---|---|---|---|---|---|---|---|---|
| T | all | 1,686 | 547 | 1,514 | 1,139 | 0.27 | 0.32 | 0.29 | 0.90 |
| T | spike | 324 | 106 | 1,514 | 218 | 0.07 | 0.33 | 0.11 | 0.93 |
| T | waste | 1,362 | 441 | 1,514 | 921 | 0.23 | 0.32 | 0.27 | 0.91 |
| O | all | 1,686 | 646 | 2,883 | 1,040 | 0.18 | 0.38 | 0.25 | 0.85 |
| O | spike | 324 | 123 | 2,883 | 201 | 0.04 | 0.38 | 0.07 | 0.88 |
| O | waste | 1,362 | 523 | 2,883 | 839 | 0.15 | 0.38 | 0.22 | 0.86 |

A note on **accuracy**: it is reported because the plan asks for it, but it is
the least useful number here. Anomalies are a few percent of the intervals, so a
detector that flags nothing at all still scores above 90%.

#### Why the fixed threshold is not a fair comparison

| building | T residual sd (kW) | T MAD scale (kW) | T alerts at z>3 | O residual sd (kW) | O MAD scale (kW) | O alerts at z>3 | extra alerts from O |
|---|---|---|---|---|---|---|---|
| Academic | 16.33 | 11.32 | 2,061 | 17.10 | 8.67 | 3,529 | 1,468 |
| Boys_Hostel | 11.59 | 8.59 | 665 | 11.95 | 8.78 | 682 | 17 |
| Girls_Hostel | 4.51 | 4.21 | 193 | 4.59 | 4.41 | 178 | -15 |
| Mess | 10.30 | 9.34 | 370 | 10.34 | 9.30 | 378 | 8 |
| Library | 9.16 | 6.18 | 1,681 | 9.69 | 6.26 | 1,746 | 65 |
| Lecture | 1.52 | 1.21 | 185 | 1.54 | 1.27 | 154 | -31 |
| Facilities | 3.01 | 2.54 | 489 | 3.05 | 2.53 | 580 | 91 |

**Detector O raises far more alerts than Detector T at the same threshold, and
that is an artefact of the threshold.** Model C is the better model, so its
residuals cluster more tightly, so its MAD is smaller, so the same deviation in
watts produces a larger Z-score. At a fixed cut-off the better model fires more
often -- buying recall and losing precision for reasons that have nothing to do
with occupancy. Comparing the two at that threshold measures the calibration of
the scale, not the usefulness of the information.

So the detectors are also compared two fairer ways: at a **matched alert
budget** (same number of alerts each -- which 500 intervals should an operator
investigate?) and with **threshold-free** measures.

| building | detector | alert budget | precision | recall | f1 |
|---|---|---|---|---|---|
| Academic | T | 2,061 | 0.27 | 0.32 | 0.29 |
| Academic | O | 2,061 | 0.25 | 0.30 | 0.27 |
| Boys_Hostel | T | 665 | 0.29 | 0.21 | 0.25 |
| Boys_Hostel | O | 665 | 0.36 | 0.26 | 0.31 |
| Girls_Hostel | T | 178 | 0.98 | 0.20 | 0.33 |
| Girls_Hostel | O | 178 | 1 | 0.20 | 0.34 |
| Mess | T | 370 | 0.84 | 0.11 | 0.19 |
| Mess | O | 370 | 0.87 | 0.11 | 0.20 |
| Library | T | 1,681 | 0.70 | 0.26 | 0.38 |
| Library | O | 1,681 | 0.63 | 0.23 | 0.34 |
| Lecture | T | 154 | 0.40 | 0.02 | 0.04 |
| Lecture | O | 154 | 0.35 | 0.02 | 0.04 |
| Facilities | T | 489 | 0.45 | 0.68 | 0.54 |
| Facilities | O | 489 | 0.43 | 0.65 | 0.52 |

| building | detector | roc auc | average precision | baseline precision |
|---|---|---|---|---|
| Academic | T | 0.68 | 0.31 | 0.06 |
| Academic | O | 0.71 | 0.31 | 0.06 |
| Boys_Hostel | T | 0.66 | 0.21 | 0.05 |
| Boys_Hostel | O | 0.80 | 0.30 | 0.05 |
| Girls_Hostel | T | 0.67 | 0.40 | 0.05 |
| Girls_Hostel | O | 0.73 | 0.43 | 0.05 |
| Mess | T | 0.57 | 0.30 | 0.12 |
| Mess | O | 0.57 | 0.31 | 0.12 |
| Library | T | 0.55 | 0.46 | 0.25 |
| Library | O | 0.51 | 0.42 | 0.25 |
| Lecture | T | 0.63 | 0.53 | 0.48 |
| Lecture | O | 0.61 | 0.52 | 0.48 |
| Facilities | T | 0.97 | 0.69 | 0.01 |
| Facilities | O | 0.97 | 0.67 | 0.01 |

![Detector T against Detector O at a matched budget and threshold-free  [SYNTHETIC]](../figures/fig_06_detector_comparison.png)

*Once the comparison is made fairly, the two detectors perform almost
identically.*

#### The answer to research question 3

| comparison | detector T | detector O | metric | difference (O - T) |
|---|---|---|---|---|
| fixed threshold \|z\| > 3 (as specified) | 0.29 | 0.28 | mean F1 | -0.01 |
| matched alert budget | 0.29 | 0.29 | mean F1 | -0.00 |
| threshold-free ranking | 0.41 | 0.42 | mean average precision | 0.01 |
| threshold-free ranking | 0.68 | 0.70 | mean ROC AUC | 0.02 |
| waste anomalies only, matched budget | 0.15 | 0.16 | mean F1 | 0.01 |
| waste events noticed at all | 0.20 | 0.23 | event recall | 0.03 |

**Detector o is ahead on 4 of the 5 fair comparisons, by margins small enough
that the remaining one sits essentially on zero.** At the fixed threshold the
mean F1 is 0.293 for T against 0.279 for O -- but that gap is the calibration
artefact described above and should be disregarded. On the 5 **fair**
comparisons, 4 favour Detector O:

- matched alert budget: mean F1 0.289 -> 0.287 (-0.002)
- average precision: 0.414 -> 0.423 (+0.009)
- ROC AUC: 0.675 -> 0.696 (+0.021)
- waste anomalies only, F1: 0.151 -> 0.164
- waste events noticed at all: 19.5% -> 22.9%

**The pattern is what theory predicts, but the size is small enough that it has
to be read carefully.** Every margin is between one and three percentage points,
and 1 of the 5 comparisons sits on the other side of zero -- close enough to
nothing that it would be wrong to call the direction unanimous.

What gives the result what weight it has is **where** the gains fall: the
largest are on the **waste** anomalies, the case designed to favour occupancy,
because a sustained modest lift only looks wrong if you know the building was
empty. Occupancy adds nothing to catching spikes, which stand out against any
baseline, and most to catching exactly the behaviour Phase 5 measured. A benefit
that appears precisely where the mechanism predicts it is more believable than
the same-sized benefit appearing at random.

**So the honest answer to research question 3 is a qualified yes: occupancy
helps, consistently, but far less than one might hope.** That is consistent with
everything else the project found by different routes -- occupancy explains only
8-44% of power variation (Phase 2), adds +0.109 to validation R-squared on
average (Phase 4), and several buildings have nearly flat daily profiles (Phase
3). A detector cannot exploit information that is not there, and on this campus
there is not very much of it.

The practical reading: if you are building an anomaly detector for a campus like
this one, a WiFi occupancy feed will improve it slightly and will not transform
it. That sits comfortably with the published LBNL finding for baseline models,
and extends it from prediction to detection.

#### Two variants worth reporting

| rule | detector | alerts | precision | recall | f1 |
|---|---|---|---|---|---|
| IQR fences (cross-check) | O | 859.86 | 0.56 | 0.27 | 0.28 |
| IQR fences (cross-check) | T | 658.29 | 0.57 | 0.25 | 0.27 |
| one-sided z > 3 (positive only) | O | 963.14 | 0.63 | 0.27 | 0.28 |
| one-sided z > 3 (positive only) | T | 784.86 | 0.65 | 0.26 | 0.29 |
| two-sided \|z\| > 3 (as specified) | O | 1,035.29 | 0.53 | 0.27 | 0.28 |
| two-sided \|z\| > 3 (as specified) | T | 806.29 | 0.56 | 0.26 | 0.29 |

**One-sided detection is a clear improvement.** Every injected anomaly is
additive, and real waste is too -- lights left on add power, they never subtract
it. The specified two-sided rule spends about half its alerts on buildings using
*less* power than predicted, which cannot be a fault against these labels.
Flagging only positive deviations raises precision substantially at almost no
cost in recall.

**The IQR cross-check** flags far more intervals than the Z-score rule and has
much lower precision. Tukey fences assume a roughly symmetric distribution, and
Phase 2 established that these residuals are heavy-tailed.

#### Detector O on the real data

| building | test intervals | NORMAL | WARNING | ANOMALY | % flagged |
|---|---|---|---|---|---|
| Academic | 26,522 | 20,811 | 2,167 | 3,544 | 11.89 |
| Boys_Hostel | 18,138 | 15,790 | 1,716 | 632 | 3.16 |
| Girls_Hostel | 17,627 | 17,228 | 397 | 2 | 0.01 |
| Mess | 23,630 | 22,435 | 1,057 | 138 | 0.58 |
| Library | 17,832 | 14,348 | 1,866 | 1,618 | 8.91 |
| Lecture | 5,548 | 4,622 | 469 | 457 | 0.67 |
| Facilities | 22,483 | 20,476 | 1,548 | 459 | 2.01 |

![The most unusual real pattern found, with occupancy below](../figures/fig_06_top_real_pattern.png)

*Worth inspecting, NOT a confirmed fault. With no weather data covering this
period, the model cannot distinguish a genuine fault from a hot day.*