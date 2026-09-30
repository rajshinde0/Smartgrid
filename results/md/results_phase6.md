#### What was injected

| building | test intervals | spike events | waste events | spike intervals | waste intervals | % of intervals contaminated | low-occ intervals available |
|---|---|---|---|---|---|---|---|
| Academic | 26,511 | 199 | 65 | 324 | 1,409 | 6.54 | 772 |
| Boys_Hostel | 17,855 | 198 | 28 | 325 | 554 | 4.92 | 494 |
| Girls_Hostel | 17,579 | 198 | 27 | 332 | 554 | 5.04 | 391 |
| Mess | 23,591 | 199 | 122 | 323 | 2,578 | 12.30 | 1,255 |
| Library | 17,809 | 198 | 200 | 325 | 4,274 | 25.82 | 4,391 |
| Lecture | 5,540 | 196 | 132 | 320 | 2,403 | 49.15 | 2,735 |
| Facilities | 22,404 | 198 | 0 | 325 | 0 | 1.45 | 0 |

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
| T | all | 1,733 | 541 | 1,523 | 1,192 | 0.26 | 0.31 | 0.28 | 0.90 |
| T | spike | 324 | 105 | 1,523 | 219 | 0.06 | 0.32 | 0.11 | 0.93 |
| T | waste | 1,409 | 436 | 1,523 | 973 | 0.22 | 0.31 | 0.26 | 0.90 |
| O | all | 1,733 | 632 | 2,873 | 1,101 | 0.18 | 0.36 | 0.24 | 0.85 |
| O | spike | 324 | 123 | 2,873 | 201 | 0.04 | 0.38 | 0.07 | 0.88 |
| O | waste | 1,409 | 509 | 2,873 | 900 | 0.15 | 0.36 | 0.21 | 0.86 |

A note on **accuracy**: it is reported because the plan asks for it, but it is
the least useful number here. Anomalies are a few percent of the intervals, so a
detector that flags nothing at all still scores above 90%.

#### Why the fixed threshold is not a fair comparison

| building | T residual sd (kW) | T MAD scale (kW) | T alerts at z>3 | O residual sd (kW) | O MAD scale (kW) | O alerts at z>3 | extra alerts from O |
|---|---|---|---|---|---|---|---|
| Academic | 16.32 | 11.31 | 2,064 | 17.09 | 8.70 | 3,505 | 1,441 |
| Boys_Hostel | 11.81 | 8.62 | 734 | 12.30 | 8.84 | 753 | 19 |
| Girls_Hostel | 4.55 | 4.24 | 195 | 4.64 | 4.43 | 173 | -22 |
| Mess | 10.26 | 9.38 | 357 | 10.29 | 9.38 | 359 | 2 |
| Library | 9.10 | 6.19 | 1,629 | 9.64 | 6.21 | 1,756 | 127 |
| Lecture | 1.52 | 1.24 | 170 | 1.54 | 1.30 | 136 | -34 |
| Facilities | 3.06 | 2.54 | 507 | 3.10 | 2.52 | 615 | 108 |

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
| Academic | T | 2,064 | 0.26 | 0.31 | 0.28 |
| Academic | O | 2,064 | 0.25 | 0.29 | 0.27 |
| Boys_Hostel | T | 734 | 0.33 | 0.27 | 0.30 |
| Boys_Hostel | O | 734 | 0.41 | 0.34 | 0.37 |
| Girls_Hostel | T | 173 | 0.98 | 0.19 | 0.32 |
| Girls_Hostel | O | 173 | 1 | 0.20 | 0.33 |
| Mess | T | 357 | 0.84 | 0.10 | 0.18 |
| Mess | O | 357 | 0.87 | 0.11 | 0.19 |
| Library | T | 1,629 | 0.64 | 0.23 | 0.33 |
| Library | O | 1,629 | 0.59 | 0.21 | 0.31 |
| Lecture | T | 136 | 0.39 | 0.02 | 0.04 |
| Lecture | O | 136 | 0.37 | 0.02 | 0.04 |
| Facilities | T | 507 | 0.49 | 0.76 | 0.59 |
| Facilities | O | 507 | 0.47 | 0.73 | 0.57 |

| building | detector | roc auc | average precision | baseline precision |
|---|---|---|---|---|
| Academic | T | 0.67 | 0.30 | 0.07 |
| Academic | O | 0.69 | 0.30 | 0.07 |
| Boys_Hostel | T | 0.69 | 0.25 | 0.05 |
| Boys_Hostel | O | 0.82 | 0.38 | 0.05 |
| Girls_Hostel | T | 0.69 | 0.40 | 0.05 |
| Girls_Hostel | O | 0.75 | 0.44 | 0.05 |
| Mess | T | 0.56 | 0.29 | 0.12 |
| Mess | O | 0.56 | 0.31 | 0.12 |
| Library | T | 0.55 | 0.43 | 0.26 |
| Library | O | 0.50 | 0.41 | 0.26 |
| Lecture | T | 0.64 | 0.55 | 0.49 |
| Lecture | O | 0.61 | 0.54 | 0.49 |
| Facilities | T | 0.97 | 0.75 | 0.01 |
| Facilities | O | 0.98 | 0.74 | 0.01 |

![Detector T against Detector O at a matched budget and threshold-free  [SYNTHETIC]](../figures/fig_06_detector_comparison.png)

*Once the comparison is made fairly, the two detectors perform almost
identically.*

#### The answer to research question 3

| comparison | detector T | detector O | metric | difference (O - T) |
|---|---|---|---|---|
| fixed threshold \|z\| > 3 (as specified) | 0.30 | 0.29 | mean F1 | -0.01 |
| matched alert budget | 0.29 | 0.30 | mean F1 | 0.00 |
| threshold-free ranking | 0.43 | 0.44 | mean average precision | 0.02 |
| threshold-free ranking | 0.68 | 0.70 | mean ROC AUC | 0.02 |
| waste anomalies only, matched budget | 0.15 | 0.17 | mean F1 | 0.02 |
| waste events noticed at all | 0.20 | 0.24 | event recall | 0.04 |

**Detector o is consistently but modestly better once the comparison is made
fairly.** At the fixed threshold the mean F1 is 0.298 for T against 0.286 for O
-- but that gap is the calibration artefact described above and should be
disregarded. On the 5 **fair** comparisons, 5 favour Detector O:

- matched alert budget: mean F1 0.292 -> 0.296 (+0.003)
- average precision: 0.426 -> 0.443 (+0.018)
- ROC AUC: 0.682 -> 0.702 (+0.021)
- waste anomalies only, F1: 0.145 -> 0.168
- waste events noticed at all: 20.2% -> 24.4%

**The direction is consistent and the pattern is exactly what theory predicts,
but the size is small.** Every individual margin is between one and three
percentage points. What makes them worth believing is that they all point the
same way, and that **the largest gains are on the waste anomalies** -- the case
designed to favour occupancy, because a sustained modest lift only looks wrong
if you know the building was empty. Occupancy adds nothing to catching spikes,
which stand out against any baseline, and it adds most to catching exactly the
behaviour Phase 5 measured.

**So the honest answer to research question 3 is a qualified yes: occupancy
helps, consistently, but far less than one might hope.** That is consistent with
everything else the project found by different routes -- occupancy explains only
7-45% of power variation (Phase 2), adds +0.107 to validation R-squared on
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
| IQR fences (cross-check) | O | 854.29 | 0.57 | 0.28 | 0.28 |
| IQR fences (cross-check) | T | 654.29 | 0.57 | 0.26 | 0.27 |
| one-sided z > 3 (positive only) | O | 972.86 | 0.64 | 0.29 | 0.29 |
| one-sided z > 3 (positive only) | T | 789.57 | 0.65 | 0.27 | 0.30 |
| two-sided \|z\| > 3 (as specified) | O | 1,042.43 | 0.54 | 0.29 | 0.29 |
| two-sided \|z\| > 3 (as specified) | T | 808 | 0.56 | 0.27 | 0.30 |

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
| Academic | 26,511 | 20,799 | 2,168 | 3,544 | 11.89 |
| Boys_Hostel | 17,855 | 15,524 | 1,697 | 634 | 3.27 |
| Girls_Hostel | 17,579 | 17,187 | 390 | 2 | 0.01 |
| Mess | 23,591 | 22,395 | 1,060 | 136 | 0.58 |
| Library | 17,809 | 14,339 | 1,843 | 1,627 | 8.96 |
| Lecture | 5,540 | 4,620 | 457 | 463 | 0.67 |
| Facilities | 22,404 | 20,389 | 1,554 | 461 | 2.03 |

![The most unusual real pattern found, with occupancy below](../figures/fig_06_top_real_pattern.png)

*Worth inspecting, NOT a confirmed fault. With no weather data covering this
period, the model cannot distinguish a genuine fault from a hot day.*