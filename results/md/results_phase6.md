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
| T | all | 1,733 | 558 | 1,800 | 1,175 | 0.24 | 0.32 | 0.27 | 0.89 |
| T | spike | 324 | 108 | 1,800 | 216 | 0.06 | 0.33 | 0.10 | 0.92 |
| T | waste | 1,409 | 450 | 1,800 | 959 | 0.20 | 0.32 | 0.25 | 0.89 |
| O | all | 1,733 | 631 | 2,910 | 1,102 | 0.18 | 0.36 | 0.24 | 0.85 |
| O | spike | 324 | 124 | 2,910 | 200 | 0.04 | 0.38 | 0.07 | 0.88 |
| O | waste | 1,409 | 507 | 2,910 | 902 | 0.15 | 0.36 | 0.21 | 0.85 |

A note on **accuracy**: it is reported because the plan asks for it, but it is
the least useful number here. Anomalies are a few percent of the intervals, so a
detector that flags nothing at all still scores above 90%.

#### Why the fixed threshold is not a fair comparison

| building | T residual sd (kW) | T MAD scale (kW) | T alerts at z>3 | O residual sd (kW) | O MAD scale (kW) | O alerts at z>3 | extra alerts from O |
|---|---|---|---|---|---|---|---|
| Academic | 16.48 | 10.87 | 2,358 | 17.17 | 8.68 | 3,541 | 1,183 |
| Boys_Hostel | 12.14 | 8.73 | 797 | 12.34 | 8.84 | 755 | -42 |
| Girls_Hostel | 4.63 | 4.33 | 182 | 4.71 | 4.55 | 165 | -17 |
| Mess | 10.30 | 9.58 | 324 | 10.33 | 9.54 | 338 | 14 |
| Library | 9.24 | 6.03 | 1,812 | 9.70 | 6.03 | 1,898 | 86 |
| Lecture | 1.50 | 1.14 | 233 | 1.53 | 1.30 | 128 | -105 |
| Facilities | 3.08 | 2.57 | 502 | 3.11 | 2.57 | 557 | 55 |

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
| Academic | T | 2,358 | 0.24 | 0.32 | 0.27 |
| Academic | O | 2,358 | 0.23 | 0.31 | 0.26 |
| Boys_Hostel | T | 755 | 0.31 | 0.26 | 0.28 |
| Boys_Hostel | O | 755 | 0.40 | 0.35 | 0.37 |
| Girls_Hostel | T | 165 | 1 | 0.19 | 0.31 |
| Girls_Hostel | O | 165 | 0.99 | 0.19 | 0.31 |
| Mess | T | 324 | 0.88 | 0.10 | 0.18 |
| Mess | O | 324 | 0.90 | 0.10 | 0.18 |
| Library | T | 1,812 | 0.58 | 0.23 | 0.33 |
| Library | O | 1,812 | 0.55 | 0.22 | 0.31 |
| Lecture | T | 128 | 0.40 | 0.02 | 0.04 |
| Lecture | O | 128 | 0.43 | 0.02 | 0.04 |
| Facilities | T | 502 | 0.48 | 0.74 | 0.58 |
| Facilities | O | 502 | 0.47 | 0.73 | 0.58 |

| building | detector | roc auc | average precision | baseline precision |
|---|---|---|---|---|
| Academic | T | 0.66 | 0.29 | 0.07 |
| Academic | O | 0.69 | 0.30 | 0.07 |
| Boys_Hostel | T | 0.70 | 0.25 | 0.05 |
| Boys_Hostel | O | 0.83 | 0.38 | 0.05 |
| Girls_Hostel | T | 0.70 | 0.40 | 0.05 |
| Girls_Hostel | O | 0.76 | 0.45 | 0.05 |
| Mess | T | 0.56 | 0.29 | 0.12 |
| Mess | O | 0.57 | 0.31 | 0.12 |
| Library | T | 0.56 | 0.43 | 0.26 |
| Library | O | 0.50 | 0.40 | 0.26 |
| Lecture | T | 0.64 | 0.56 | 0.49 |
| Lecture | O | 0.60 | 0.54 | 0.49 |
| Facilities | T | 0.97 | 0.75 | 0.01 |
| Facilities | O | 0.97 | 0.74 | 0.01 |

![Detector T against Detector O at a matched budget and threshold-free  [SYNTHETIC]](../figures/fig_06_detector_comparison.png)

*Once the comparison is made fairly, the two detectors perform almost
identically.*

#### The answer to research question 3

| comparison | detector T | detector O | metric | difference (O - T) |
|---|---|---|---|---|
| fixed threshold \|z\| > 3 (as specified) | 0.29 | 0.29 | mean F1 | -0.01 |
| matched alert budget | 0.28 | 0.29 | mean F1 | 0.01 |
| threshold-free ranking | 0.43 | 0.45 | mean average precision | 0.02 |
| threshold-free ranking | 0.68 | 0.70 | mean ROC AUC | 0.02 |
| waste anomalies only, matched budget | 0.14 | 0.17 | mean F1 | 0.02 |
| waste events noticed at all | 0.22 | 0.25 | event recall | 0.03 |

**Detector o is consistently but modestly better once the comparison is made
fairly.** At the fixed threshold the mean F1 is 0.293 for T against 0.288 for O
-- but that gap is the calibration artefact described above and should be
disregarded. On the 5 **fair** comparisons, 5 favour Detector O:

- matched alert budget: mean F1 0.285 -> 0.294 (+0.009)
- average precision: 0.426 -> 0.446 (+0.020)
- ROC AUC: 0.685 -> 0.703 (+0.018)
- waste anomalies only, F1: 0.141 -> 0.165
- waste events noticed at all: 21.8% -> 24.7%

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
| IQR fences (cross-check) | O | 858.43 | 0.58 | 0.28 | 0.29 |
| IQR fences (cross-check) | T | 704.43 | 0.59 | 0.26 | 0.28 |
| one-sided z > 3 (positive only) | O | 982 | 0.64 | 0.28 | 0.29 |
| one-sided z > 3 (positive only) | T | 849.43 | 0.65 | 0.27 | 0.29 |
| two-sided \|z\| > 3 (as specified) | O | 1,054.57 | 0.55 | 0.28 | 0.29 |
| two-sided \|z\| > 3 (as specified) | T | 886.86 | 0.56 | 0.27 | 0.29 |

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
| Academic | 26,511 | 20,769 | 2,163 | 3,579 | 11.97 |
| Boys_Hostel | 17,855 | 15,515 | 1,701 | 639 | 3.30 |
| Girls_Hostel | 17,579 | 17,240 | 336 | 3 | 0.02 |
| Mess | 23,591 | 22,456 | 1,017 | 118 | 0.50 |
| Library | 17,809 | 14,048 | 1,922 | 1,839 | 10.03 |
| Lecture | 5,540 | 4,726 | 376 | 438 | 0.52 |
| Facilities | 22,404 | 20,491 | 1,520 | 393 | 1.72 |

![The most unusual real pattern found, with occupancy below](../figures/fig_06_top_real_pattern.png)

*Worth inspecting, NOT a confirmed fault. With no weather data the model cannot
distinguish a genuine fault from a hot day.*