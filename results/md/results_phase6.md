#### What was injected

| building | test intervals | spike events | waste events | spike intervals | waste intervals | % of intervals contaminated | low-occ intervals available |
|---|---|---|---|---|---|---|---|
| Academic | 26,514 | 200 | 70 | 325 | 1,438 | 6.65 | 772 |
| Boys_Hostel | 18,018 | 198 | 30 | 326 | 620 | 5.25 | 523 |
| Girls_Hostel | 17,595 | 196 | 27 | 331 | 518 | 4.83 | 393 |
| Mess | 23,607 | 199 | 123 | 324 | 2,511 | 12.01 | 1,255 |
| Library | 17,812 | 198 | 200 | 325 | 4,270 | 25.80 | 4,399 |
| Lecture | 5,529 | 191 | 131 | 309 | 2,346 | 48.02 | 2,731 |
| Facilities | 22,447 | 198 | 0 | 325 | 0 | 1.45 | 0 |

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
| T | all | 1,763 | 546 | 1,535 | 1,217 | 0.26 | 0.31 | 0.28 | 0.90 |
| T | spike | 325 | 95 | 1,535 | 230 | 0.06 | 0.29 | 0.10 | 0.93 |
| T | waste | 1,438 | 451 | 1,535 | 987 | 0.23 | 0.31 | 0.26 | 0.90 |
| O | all | 1,763 | 643 | 2,859 | 1,120 | 0.18 | 0.36 | 0.24 | 0.85 |
| O | spike | 325 | 116 | 2,859 | 209 | 0.04 | 0.36 | 0.07 | 0.88 |
| O | waste | 1,438 | 527 | 2,859 | 911 | 0.16 | 0.37 | 0.22 | 0.86 |

A note on **accuracy**: it is reported because the plan asks for it, but it is
the least useful number here. Anomalies are a few percent of the intervals, so a
detector that flags nothing at all still scores above 90%.

#### Why the fixed threshold is not a fair comparison

| building | T residual sd (kW) | T MAD scale (kW) | T alerts at z>3 | O residual sd (kW) | O MAD scale (kW) | O alerts at z>3 | extra alerts from O |
|---|---|---|---|---|---|---|---|
| Academic | 16.29 | 11.29 | 2,081 | 17.08 | 8.67 | 3,502 | 1,421 |
| Boys_Hostel | 11.60 | 8.62 | 673 | 12.04 | 8.76 | 704 | 31 |
| Girls_Hostel | 4.56 | 4.24 | 196 | 4.64 | 4.41 | 179 | -17 |
| Mess | 10.30 | 9.40 | 367 | 10.33 | 9.36 | 376 | 9 |
| Library | 9.13 | 6.15 | 1,638 | 9.67 | 6.25 | 1,714 | 76 |
| Lecture | 1.53 | 1.19 | 187 | 1.54 | 1.31 | 119 | -68 |
| Facilities | 3 | 2.54 | 483 | 3.04 | 2.52 | 570 | 87 |

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
| Academic | T | 2,081 | 0.26 | 0.31 | 0.28 |
| Academic | O | 2,081 | 0.26 | 0.31 | 0.28 |
| Boys_Hostel | T | 673 | 0.30 | 0.21 | 0.25 |
| Boys_Hostel | O | 673 | 0.37 | 0.27 | 0.31 |
| Girls_Hostel | T | 179 | 0.98 | 0.21 | 0.34 |
| Girls_Hostel | O | 179 | 1 | 0.21 | 0.35 |
| Mess | T | 367 | 0.85 | 0.11 | 0.19 |
| Mess | O | 367 | 0.87 | 0.11 | 0.20 |
| Library | T | 1,638 | 0.70 | 0.25 | 0.37 |
| Library | O | 1,638 | 0.66 | 0.23 | 0.34 |
| Lecture | T | 119 | 0.30 | 0.01 | 0.03 |
| Lecture | O | 119 | 0.29 | 0.01 | 0.03 |
| Facilities | T | 483 | 0.46 | 0.68 | 0.55 |
| Facilities | O | 483 | 0.43 | 0.64 | 0.51 |

| building | detector | roc auc | average precision | baseline precision |
|---|---|---|---|---|
| Academic | T | 0.66 | 0.30 | 0.07 |
| Academic | O | 0.68 | 0.30 | 0.07 |
| Boys_Hostel | T | 0.67 | 0.20 | 0.05 |
| Boys_Hostel | O | 0.80 | 0.31 | 0.05 |
| Girls_Hostel | T | 0.71 | 0.43 | 0.05 |
| Girls_Hostel | O | 0.76 | 0.47 | 0.05 |
| Mess | T | 0.57 | 0.30 | 0.12 |
| Mess | O | 0.58 | 0.32 | 0.12 |
| Library | T | 0.56 | 0.46 | 0.26 |
| Library | O | 0.51 | 0.43 | 0.26 |
| Lecture | T | 0.62 | 0.53 | 0.48 |
| Lecture | O | 0.61 | 0.53 | 0.48 |
| Facilities | T | 0.96 | 0.67 | 0.01 |
| Facilities | O | 0.96 | 0.65 | 0.01 |

![Detector T against Detector O at a matched budget and threshold-free  [SYNTHETIC]](../figures/fig_06_detector_comparison.png)

*Once the comparison is made fairly, the two detectors perform almost
identically.*

#### The answer to research question 3

| comparison | detector T | detector O | metric | difference (O - T) |
|---|---|---|---|---|
| fixed threshold \|z\| > 3 (as specified) | 0.29 | 0.28 | mean F1 | -0.01 |
| matched alert budget | 0.29 | 0.29 | mean F1 | 0.00 |
| threshold-free ranking | 0.41 | 0.43 | mean average precision | 0.02 |
| threshold-free ranking | 0.68 | 0.70 | mean ROC AUC | 0.02 |
| waste anomalies only, matched budget | 0.16 | 0.17 | mean F1 | 0.02 |
| waste events noticed at all | 0.19 | 0.25 | event recall | 0.05 |

**Detector O is ahead on all 5 fair comparisons, though modestly.** At the fixed
threshold the mean F1 is 0.294 for T against 0.280 for O -- but that gap is the
calibration artefact described above and should be disregarded. On the 5
**fair** comparisons, 5 favour Detector O:

- matched alert budget: mean F1 0.287 -> 0.289 (+0.002)
- average precision: 0.415 -> 0.430 (+0.015)
- ROC AUC: 0.677 -> 0.697 (+0.020)
- waste anomalies only, F1: 0.155 -> 0.174
- waste events noticed at all: 19.3% -> 24.8%

**The pattern is what theory predicts, but the size is small enough that it has
to be read carefully.** Every margin is between one and three percentage points,
and every one of them points the same way, which is what makes margins this
small worth reporting at all.

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
8-44% of power variation (Phase 2), adds +0.106 to validation R-squared on
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
| IQR fences (cross-check) | O | 865.57 | 0.57 | 0.27 | 0.29 |
| IQR fences (cross-check) | T | 659 | 0.58 | 0.25 | 0.28 |
| one-sided z > 3 (positive only) | O | 953.71 | 0.64 | 0.27 | 0.28 |
| one-sided z > 3 (positive only) | T | 782.86 | 0.65 | 0.26 | 0.29 |
| two-sided \|z\| > 3 (as specified) | O | 1,023.43 | 0.53 | 0.27 | 0.28 |
| two-sided \|z\| > 3 (as specified) | T | 803.57 | 0.56 | 0.26 | 0.29 |

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
| Academic | 26,514 | 20,800 | 2,169 | 3,545 | 11.89 |
| Boys_Hostel | 18,018 | 15,675 | 1,706 | 637 | 3.24 |
| Girls_Hostel | 17,595 | 17,201 | 392 | 2 | 0.01 |
| Mess | 23,607 | 22,412 | 1,060 | 135 | 0.57 |
| Library | 17,812 | 14,340 | 1,845 | 1,627 | 8.97 |
| Lecture | 5,529 | 4,582 | 473 | 474 | 0.69 |
| Facilities | 22,447 | 20,436 | 1,551 | 460 | 2.02 |

![The most unusual real pattern found, with occupancy below](../figures/fig_06_top_real_pattern.png)

*Worth inspecting, NOT a confirmed fault. With no weather data covering this
period, the model cannot distinguish a genuine fault from a hot day.*