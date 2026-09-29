# SMARTGRID-X
## Occupancy-aware energy-waste and anomaly analysis of the I-BLEND campus dataset

**Course:** MD3135 — Data Science
**Programme:** T.Y. B.Tech, Vishwakarma Institute of Technology, Pune
**Academic year:** 2025–26

**Team**

| Role | Owns | Name |
|---|---|---|
| Data lead | Phase 1: loading, merging, cleaning, data-quality summary | *(add name)* |
| Analysis lead | Phases 2–3: statistics, EDA, PCA | *(add name)* |
| Modelling lead | Phase 4: regression and evaluation | *(add name)* |
| Insight lead | Phases 5–6: wasted energy, anomaly experiment | *(add name)* |
| Delivery lead | Phase 7: dashboard, report, presentation | *(add name)* |

---

> **How to read this report.** It is written to stand on its own. You do not need
> to open the notebooks to follow it. Every number, table and chart in it was
> produced by code in `notebooks/`, and anything not yet computed says
> "pending Phase N" rather than being guessed at.

---

## 1. Abstract

<!-- BEGIN:abstract -->
pending Phase 7 — the abstract is rewritten at the end of the project with the
real findings, so that it reports results rather than intentions.

*Provisional statement of intent:* this project measures how much electricity
seven buildings on the IIIT-Delhi campus consume while they are close to empty,
using the public I-BLEND dataset of 1-minute electrical readings paired with
10-minute WiFi-derived occupancy counts over February 2014 – November 2017. It
then tests whether an anomaly detector that knows about occupancy outperforms one
that only knows the time of day.
<!-- END:abstract -->

---

## 2. Introduction

### 2.1 What data science is

Data science is the practice of turning recorded observations into decisions. It
sits on three legs: the **domain** the data comes from, the **statistics** needed
to say what the data does and does not support, and the **computing** needed to
handle data at a size no person could read. A data scientist's job is not to
produce a model; it is to answer a question in a way that survives scrutiny —
which means being as clear about the data's flaws as about the result.

This project is a small but complete example of that cycle: a real question
(*how much electricity does a near-empty building use?*), a real and imperfect
dataset, cleaning that has to be justified, a measurement, a model, an experiment,
and an honest account of what the answer does not cover.

### 2.2 Big data, the hype, and getting past it

For most of the 2010s "big data" was sold as a promise that volume itself creates
insight — collect everything, and answers will emerge. The reality is duller and
more useful. Our dataset is about 1.6 GB, which is large enough to break a naive
script on a laptop but far too small to be interesting merely for its size. What
makes it valuable is not the volume but the **resolution and the pairing**: a
reading every minute, for four years, alongside a count of how many devices were
in the building.

Getting past the hype means three practical commitments, all visible in this
project:

- **Size is an engineering problem, not a source of insight.** We handle 1.6 GB by
  reading one building at a time and caching a 10-minute summary. That is
  plumbing, and it is not the contribution.
- **More rows do not fix a biased measurement.** Our occupancy sensor counts WiFi
  devices, not people. Four years of it is still four years of a biased count, and
  no amount of data corrects that — only stating it does.
- **The question comes before the method.** Everything in this report that does
  not serve one of the three research questions below was cut.

### 2.3 Datafication, with smart meters as the example

**Datafication** is the process by which an activity that was previously invisible
becomes a stream of records that can be counted, compared and acted on. Electricity
is the textbook case. For a century, a building's energy use was a single number
read off a dial once a month by a person with a clipboard: enough to send a bill,
useless for understanding behaviour.

A smart meter datafies the same activity. Reading the same feeder every minute
turns "the campus used 40,000 units last month" into a time series in which you can
see the lights come on, a chiller cycle, an exam week, a vacation. The activity has
not changed; its *visibility* has. The I-BLEND dataset is exactly this: campus
electricity use, datafied at 1-minute resolution for 4.4 years.

The second datafication in this project is subtler and more debatable. IIIT-Delhi's
WiFi access points log which devices are associated with them. That log was created
for network operations, but it can be re-read as a **proxy for occupancy** — turning
"who is in the building" into data as a by-product of a system built for something
else. This is characteristic of datafication, and so is its characteristic flaw:
the proxy is not the thing. A phone left charging in an empty room is still counted.
Section 10 treats this as a limitation rather than a detail.

Datafication is what makes this project possible, and its imperfection is what makes
the project honest.

### 2.4 The current landscape, and where energy analytics sits in it

Contemporary data science runs on cheap storage, mature open-source tooling
(`pandas`, `scikit-learn`), and a shift from bespoke statistics toward reusable
pipelines. Energy analytics has followed the same path: from monthly billing
analysis, to load forecasting, to non-intrusive load monitoring and automated
fault detection in buildings. Public benchmark datasets — I-BLEND among them —
are the infrastructure of that shift, because they let different groups test
different methods on the same data. This project is a user of that infrastructure:
standard methods, applied to a dataset in a way it has not been applied before.

### 2.5 Problem statement

Buildings consume electricity when nobody is using them. Lights, air conditioning,
idle equipment and always-on infrastructure continue to draw power through nights,
weekends and vacations. On a university campus this is plausibly a large fraction
of total consumption, but it is rarely measured, because measuring it requires two
things at once: fine-grained energy data **and** some knowledge of whether anyone
was there.

The I-BLEND dataset has both. It has not, as far as we can find, been used to ask
this question.

### 2.6 Research questions

1. **MAIN — Waste.** What percentage of each building's energy is consumed during
   low-occupancy periods?
2. **Prediction.** How well do occupancy and time of day predict a building's
   power, using simple and multiple linear regression?
3. **Detection.** Does an anomaly detector that uses time *and* occupancy beat one
   that uses time alone, tested on injected anomalies with known locations?

### 2.7 Novelty claim

> **This is the first occupancy-aware energy-waste and anomaly analysis of I-BLEND.**

We state this precisely, because it is a modest claim and overstating it would be
dishonest. The *methods* used here — threshold-based low-occupancy accounting,
linear regression baselines, residual Z-score anomaly detection, PCA day
clustering — are all standard and none is invented here. Measuring energy used in
unoccupied buildings has been done before, in other buildings (Section 3).

What we could not find published is the **application to this dataset**: using
I-BLEND's own WiFi occupancy stream to quantify, per building, how much of the
campus's electricity is consumed while it is close to empty, together with a
threshold-sensitivity curve and a controlled test of whether occupancy improves
automated anomaly detection. That combination is the contribution.

---

## 3. Related work

**Rashid, Singh & Singh (2019), *I-BLEND, a campus-scale commercial and residential
buildings electrical energy dataset*, Scientific Data 6:190015.**
The dataset paper. It describes the collection setup — Schneider EM6400 panel
meters at building level, Cisco access points for occupancy — documents the file
formats, and validates the data. Its purpose is to publish a resource, not to
analyse waste. *How we differ:* we use the dataset it publishes to answer a
question it does not ask, and we quantify the data-quality problems it flags
(Section 4) rather than only noting them.

**Rashid & Singh (2018), *Monitor: an abnormality detection approach in buildings
energy consumption*.**
Prior work on this same campus. It clusters daily load profiles and detects days
whose shape is abnormal, using energy data alone. *How we differ:* our detector
question is explicitly comparative — does adding occupancy help? — and is evaluated
against injected anomalies with known ground-truth locations, which lets us report
precision and recall rather than only illustrative examples. Our PCA day-clustering (Phase 3)
overlaps with this work and is therefore presented as *supporting analysis, not as
a novelty claim*.

**Mishra, Lone & Mishra (2024), *DECODE: Data-driven Energy Consumption Prediction
leveraging Historical Data and Environmental Factors in Buildings*.**
Forecasts consumption on I-BLEND, including occupancy among its inputs. *How we
differ:* DECODE's objective is predictive accuracy. Ours is accounting and
detection — we use regression as a *baseline of expected consumption* against which
waste and anomalies are measured, not as an end in itself.

**Masoso & Grobler (2010), *The dark side of occupants' behaviour on building
energy use*, Energy and Buildings 42(2).**
Audited commercial buildings in Botswana and South Africa and found that **56% of
total energy was consumed outside working hours**, more than during them. *How we
differ:* their "unoccupied" is defined by the clock (outside office hours); ours is
defined by a measured occupancy signal, which catches an empty building at 3 p.m.
on a vacation day that a clock-based rule would call occupied. Their figure is our
main external comparison point for commercial buildings.

**Anderson, Song, Lee & Tian (2015), *Longitudinal analysis of normalized energy
consumption in university dormitories*, Energy and Buildings.**
Found **27.5–31.5% of dormitory energy consumed while unoccupied**. *How we
differ:* same measurement idea, different campus and climate (Delhi, with heavy
summer cooling), and a measured rather than assumed occupancy signal. This is our
comparison point for the two hostel buildings.

**Lawrence Berkeley National Laboratory (2016), baseline energy models using
occupancy data.**
Tested whether adding occupancy information improves building energy baseline
models, and found the improvement modest. *How we differ:* we run the equivalent
comparison on I-BLEND (models B versus C in Phase 4) and report the result
whichever way it falls — a null result here is a genuine finding, not a failure,
and it directly informs research question 3.

---

## 4. Dataset and data quality

### 4.1 Source

The **I-BLEND** dataset (Rashid, Singh & Singh, *Scientific Data*, 2019) records
electricity use across the IIIT-Delhi campus. It is published on figshare under
DOI [10.6084/m9.figshare.c.3893581](https://doi.org/10.6084/m9.figshare.c.3893581).
It contains two parts, which this project joins together:

- **Energy** — 1-minute readings from Schneider EM6400 panel meters on nine
  building feeders and three transformers, August 2013 to December 2017. Columns:
  `timestamp` (UNIX seconds), `power` (W), `current` (A), `voltage` (V),
  `frequency` (Hz), `power_factor`.
- **Occupancy** — 10-minute counts of devices associated with each building's Cisco
  WiFi access points, February 2014 to November 2017. Columns: `timestamp`,
  `occupancy_count`.

The dataset readme is explicit that UNIX timestamps must be converted using the
`Asia/Kolkata` timezone (UTC+05:30); every notebook in this project does so.

### 4.2 Buildings and the meter-to-occupancy mapping

Joining the two halves of the dataset depends entirely on this mapping, which comes
from the two `Readme.txt` files shipped with the data. Both dormitories have two
meters — a mains supply and a UPS (backup) supply — which we keep separate as well
as summing, because which supply keeps running when rooms empty out is one of the
questions in Phase 5.

<!-- BEGIN:phase0_mapping -->
| building | label | occupancy file | energy meters | kind |
|---|---|---|---|---|
| Academic | Academic Building | ACB.csv | acad_build_mains.csv | commercial |
| Boys_Hostel | Boys Dormitory | BH.csv | boys_hostel_mains.csv, boys_hostel_ups.csv | residential |
| Girls_Hostel | Girls Dormitory | GH.csv | girls_hostel_mains.csv, girls_hostel_ups.csv | residential |
| Mess | Dining Building (Mess) | DB.csv | mess_build_mains.csv | commercial |
| Library | Library Building | LB.csv | library_build_mains.csv | commercial |
| Lecture | Lecture Building | LCB.csv | lecture_build_mains.csv | commercial |
| Facilities | Facilities Building | SRB.csv | facilities_build_mains.csv | commercial |
<!-- END:phase0_mapping -->

### 4.3 What is in the folder

<!-- BEGIN:phase0_file_inventory -->
| folder | file | size mb |
|---|---|---|
| energy_dataset | all_buildings_power.csv | 187.81 |
| energy_dataset | acad_build_mains.csv | 125.16 |
| energy_dataset | girls_hostel_ups.csv | 123.82 |
| energy_dataset | mess_build_mains.csv | 111.26 |
| energy_dataset | facilities_build_mains.csv | 110.70 |
| energy_dataset | transformer_2.csv | 95.68 |
| energy_dataset | transformer_3.csv | 95.17 |
| energy_dataset | boys_hostel_ups.csv | 93.18 |
| energy_dataset | library_build_mains.csv | 92.70 |
| energy_dataset | girls_hostel_mains.csv | 89.95 |
| energy_dataset | boys_hostel_mains.csv | 86.46 |
| energy_dataset | all_transformer_power.csv | 85.74 |
| energy_dataset | data_present_status_buildings.csv | 83.76 |
| energy_dataset | lecture_build_mains.csv | 72.76 |
| energy_dataset | transformer_1.csv | 66.01 |
| energy_dataset | data_present_status_transformers.csv | 53.45 |
| energy_dataset | .DS_Store | 0.01 |
| energy_dataset | Readme.txt | 0 |
| IIITD_occupancy_dataset | BH.csv | 3.22 |
| IIITD_occupancy_dataset | GH.csv | 3.16 |
| IIITD_occupancy_dataset | ACB.csv | 3.12 |
| IIITD_occupancy_dataset | DB.csv | 3.07 |
| IIITD_occupancy_dataset | LB.csv | 2.94 |
| IIITD_occupancy_dataset | SRB.csv | 2.59 |
| IIITD_occupancy_dataset | LCB.csv | 2.54 |
| IIITD_occupancy_dataset | .DS_Store | 0.01 |
| IIITD_occupancy_dataset | Readme.txt | 0 |

Total: **1,594 MB** across 27 files.
<!-- END:phase0_file_inventory -->

### 4.4 Coverage of each energy meter

A file having 2.2 million rows does not mean it has 2.2 million consecutive
minutes of data. For each meter we compare the readings actually present against
the number that should exist between its first and last timestamp.

<!-- BEGIN:phase0_energy_profile -->
| meter | label | rows | first | last | span days | row coverage pct | gaps over 1min | largest gap hours |
|---|---|---|---|---|---|---|---|---|
| acad_mains | Academic | 2,269,530 | 2013-08-10 00:00:00+05:30 | 2017-12-31 23:59:00+05:30 | 1,605 | 98.20 | 489 | 254.70 |
| boys_mains | Boys_Hostel | 1,671,546 | 2013-08-10 00:00:00+05:30 | 2017-12-31 23:59:00+05:30 | 1,605 | 72.32 | 9,149 | 4,987.80 |
| boys_ups | Boys_Hostel | 1,688,044 | 2013-08-10 00:00:00+05:30 | 2017-12-31 23:59:00+05:30 | 1,605 | 73.04 | 9,783 | 4,987.80 |
| girls_mains | Girls_Hostel | 1,653,053 | 2013-08-10 00:00:00+05:30 | 2017-12-31 23:59:00+05:30 | 1,605 | 71.52 | 616 | 5,311 |
| girls_ups | Girls_Hostel | 2,300,745 | 2013-08-10 00:00:00+05:30 | 2017-12-31 23:59:00+05:30 | 1,605 | 99.55 | 563 | 32.10 |
| library_mains | Library | 1,713,637 | 2013-08-10 00:00:00+05:30 | 2017-12-31 23:59:00+05:30 | 1,605 | 74.14 | 639 | 4,890.80 |
| mess_mains | Mess | 2,013,090 | 2013-09-24 00:00:00+05:30 | 2017-12-31 23:59:00+05:30 | 1,560 | 89.61 | 1,074 | 1,465.20 |
| lecture_mains | Lecture | 2,269,309 | 2013-08-10 00:00:00+05:30 | 2017-12-31 23:59:00+05:30 | 1,605 | 98.19 | 719 | 254.70 |
| facilities_mains | Facilities | 2,048,910 | 2013-11-15 00:00:00+05:30 | 2017-12-31 23:59:00+05:30 | 1,508 | 94.35 | 3,191 | 1,054.80 |
<!-- END:phase0_energy_profile -->

### 4.5 Data-quality measurements per meter

<!-- BEGIN:phase0_energy_quality -->
| meter | power mean w | power max w | power zero pct | pf negative pct | pf min | pf max | voltage min | voltage max | voltage out of range pct | current na pct |
|---|---|---|---|---|---|---|---|---|---|---|
| acad_mains | 27,785.80 | 95,786.30 | 0.29 | 13.78 | -1.00 | 1 | 0 | 269.17 | 0.00 | 9.29 |
| boys_mains | 17,488 | 97,663.90 | 0.01 | 43.64 | -1.00 | 1 | 0 | 281.76 | 0.01 | 12.56 |
| boys_ups | 13,927.40 | 47,212.10 | 0 | 47.46 | -1.00 | 1 | 0 | 277.74 | 0.08 | 12.45 |
| girls_mains | 7,315.90 | 20,895.90 | 0 | 67.55 | -1.00 | 1 | 0 | 280.90 | 0.00 | 11.38 |
| girls_ups | 6,881.30 | 18,126.80 | 0.01 | 66.05 | -1.00 | 1 | 0 | 277.68 | 0.02 | 9.12 |
| library_mains | 9,074.70 | 99,208.90 | 0 | 58.08 | -1.00 | 1 | 0 | 270.41 | 0.00 | 12.34 |
| mess_mains | 22,195.30 | 142,442.10 | 0 | 0.05 | -1.00 | 1 | 209.60 | 270.45 | 0 | 7.19 |
| lecture_mains | 641.70 | 26,703.10 | 81.70 | 0.01 | -1.00 | 1 | 119.51 | 254.17 | 0 | 9.29 |
| facilities_mains | 10,458.90 | 139,437.10 | 0 | 3.14 | -1.00 | 1 | 0 | 268.56 | 0.00 | 3.24 |
<!-- END:phase0_energy_quality -->

### 4.6 Coverage of each occupancy file

<!-- BEGIN:phase0_occupancy_profile -->
| building | file | rows | first | last | span days | row coverage pct | aligned to 10min |
|---|---|---|---|---|---|---|---|
| Academic | ACB.csv | 179,701 | 2014-02-16 00:20:00+05:30 | 2017-11-03 23:50:00+05:30 | 1,357 | 91.96 | True |
| Boys_Hostel | BH.csv | 179,849 | 2014-02-16 00:10:00+05:30 | 2017-11-03 23:50:00+05:30 | 1,357 | 92.04 | True |
| Girls_Hostel | GH.csv | 179,681 | 2014-02-16 00:20:00+05:30 | 2017-11-03 23:50:00+05:30 | 1,357 | 91.95 | True |
| Mess | DB.csv | 178,427 | 2014-02-16 00:30:00+05:30 | 2017-11-03 23:50:00+05:30 | 1,357 | 91.31 | True |
| Library | LB.csv | 173,006 | 2014-02-16 00:20:00+05:30 | 2017-11-03 23:50:00+05:30 | 1,357 | 88.54 | True |
| Lecture | LCB.csv | 151,516 | 2014-02-16 01:50:00+05:30 | 2017-11-03 23:50:00+05:30 | 1,357 | 77.54 | True |
| Facilities | SRB.csv | 157,649 | 2014-07-10 12:00:00+05:30 | 2017-11-03 23:50:00+05:30 | 1,213 | 90.29 | True |
<!-- END:phase0_occupancy_profile -->

### 4.7 Occupancy distribution — and why "empty" is not measurable

<!-- BEGIN:phase0_occupancy_distribution -->
| building | occ min | occ p05 | occ median | occ mean | occ p95 | occ max | low occ threshold | pct rows at or below threshold |
|---|---|---|---|---|---|---|---|---|
| Academic | 1 | 11 | 44 | 78.40 | 257 | 505 | 12.85 | 6.51 |
| Boys_Hostel | 1 | 29 | 221 | 222.10 | 421 | 614 | 21.05 | 4.13 |
| Girls_Hostel | 1 | 11 | 97 | 95.70 | 178 | 275 | 8.90 | 4.02 |
| Mess | 1 | 4 | 44 | 58.50 | 174 | 340 | 8.70 | 12.23 |
| Library | 1 | 2 | 21 | 41.70 | 160 | 498 | 8 | 27.30 |
| Lecture | 1 | 1 | 6 | 39.90 | 209 | 498 | 10.45 | 60.39 |
| Facilities | 1 | 1 | 5 | 6.60 | 18 | 47 | 0.90 | 0 |
<!-- END:phase0_occupancy_distribution -->

<!-- BEGIN:phase0_occupancy_note -->
**The single most important finding in exploration: occupancy never reaches zero.**
The minimum count in every one of the seven buildings is **1**, not 0. This is the
WiFi over-counting the dataset authors warn about -- idle phones and laptops stay
associated with an access point long after their owner has left. The consequence is
structural, not cosmetic: *the main research question cannot be phrased as "energy
used while the building is empty", because no such reading exists in this dataset.*

It must instead be "energy used while occupancy is **low**", against a threshold we
state openly. We use a threshold relative to each building's own scale:
**low occupancy = occupancy at or below 5% of that building's
95th-percentile occupancy.** An absolute cut-off would be
meaningless across buildings whose normal populations differ by a factor of twenty.

Two buildings do not fit the standard recipe, and both are reported rather than
quietly dropped:

- **Facilities (SRB)** is small: its occupancy runs 1 to
  47 with a 95th percentile of 18, so the
  threshold works out to **0.90** -- below its own
  minimum observed count of 1. **No reading qualifies**
  (0.00% of rows). We keep the identical
  rule for every building rather than bending the definition for one, report this
  cell honestly as "no qualifying intervals", and read Facilities off the
  threshold-sensitivity curve in Phase 5 instead.
- **Lecture (LCB)** has 60.4% of its
  readings under the threshold, and its meter reads exactly 0 W for
  81.7% of the record. Its waste figure is therefore computed only
  over the periods when the meter was demonstrably alive, with the coverage
  reported alongside.

Reassuringly, **every occupancy timestamp sits exactly on a 10-minute boundary**,
so energy and occupancy line up without any fuzzy time matching.
<!-- END:phase0_occupancy_note -->

### 4.8 Completeness over time

<!-- BEGIN:phase0_coverage_figure -->
![Monthly completeness of every energy meter and occupancy file](../figures/fig_00_coverage_timeline.png)

*The record is far patchier than the row counts suggest: the Boys hostel, Girls mains and Library meters each lose several consecutive months entirely, and the occupancy block (below the black line) exists only between the two dashed lines.*
<!-- END:phase0_coverage_figure -->

### 4.9 Missing-data heatmap from the authors' own status file

<!-- BEGIN:phase1_missing_heatmap -->
![Percent of 1-minute readings present, by month and building](../figures/fig_01_missing_heatmap.png)

*Built from the authors' own data_present_status_buildings.csv. The Girls mains meter loses most of a year across 2015-16, the Boys meters several months in the same period, and the Library a long stretch in 2014-15.*

| building | month | pct present |
|---|---|---|
| Boys_main | 2015-06 | 0 |
| Boys_main | 2015-07 | 0 |
| Boys_main | 2015-08 | 0 |
| Boys_main | 2015-09 | 44.30 |
| Boys_main | 2015-10 | 16.40 |
| Boys_main | 2015-11 | 45.60 |
| Boys_main | 2015-12 | 0 |
| Boys_main | 2016-01 | 0 |
| Boys_main | 2016-02 | 0 |
| Boys_main | 2016-03 | 0 |
| Boys_main | 2016-04 | 0 |
| Boys_main | 2016-05 | 0 |
| Boys_main | 2017-06 | 22.80 |
| Boys_main | 2017-07 | 4 |
| Boys_backup | 2015-06 | 0 |
| Boys_backup | 2015-07 | 0 |
| Boys_backup | 2015-08 | 0 |
| Boys_backup | 2015-09 | 44.30 |
| Boys_backup | 2015-10 | 16.40 |
| Boys_backup | 2015-11 | 45.60 |
| Boys_backup | 2015-12 | 0 |
| Boys_backup | 2016-01 | 0 |
| Boys_backup | 2016-02 | 0 |
| Boys_backup | 2016-03 | 0 |
| Boys_backup | 2016-04 | 0 |
| Boys_backup | 2016-05 | 0 |
| Boys_backup | 2017-06 | 38.70 |
| Boys_backup | 2017-07 | 5.20 |
| Facilities | 2013-08 | 0 |
| Facilities | 2013-09 | 0 |

68 building-months are more than half missing (first 30 shown).
<!-- END:phase1_missing_heatmap -->

### 4.10 Data-quality issues found, and what we do about each

<!-- BEGIN:phase0_data_quality_issues -->
| issue | where | evidence | reading | phase 1 action | phase 1 / 5 action |
|---|---|---|---|---|---|
| Negative power_factor | all 9 meters, 14-66% of rows | range exactly -0.999..+1.000 while power is never negative | sign convention (leading/lagging), not bad data | keep abs(power_factor); keep a pf_was_negative flag | - |
| Dead meter (0 W for months) | Lecture building, 81.7% of rows | exact zeros in long unbroken runs | meter stopped reporting, not zero consumption | flag runs of 0 W longer than 6 h as meter_off | - |
| Missing current | all meters, 9-13% of rows, early period | NA in the first rows of every file; readme confirms | instrument not configured yet | leave as NaN; we do not model current | - |
| Out-of-range voltage | all meters, under 0.1% of rows | values at 0 V and above 270 V on a 230 V feeder | momentary meter artefact | set outside 180-270 V to NaN | - |
| Long gaps | Library and both hostels, up to ~208 days | largest_gap_hours column above | extended outage in data collection | put data on a complete time grid; interpolate only gaps <= 30 min | - |
| Staggered start dates | Mess (Sep 2013), Facilities (Nov 2013) | first column above | meters installed later | per-building coverage reported; no back-filling | - |
| Occupancy never reaches zero | all 7 buildings, minimum count = 1 | occ_min column above | WiFi counts idle devices, not people | - | relative low-occupancy threshold + sensitivity curve |
| Threshold unreachable for Facilities | Facilities (SRB) | 5% of p95 = 0.9 < minimum observed count of 1 | small building, occupancy range 1-47 | - | keep the rule; report the cell honestly; use the sensitivity curve |
<!-- END:phase0_data_quality_issues -->

### 4.11 Working period

<!-- BEGIN:phase0_working_period -->
Energy recording runs from **2013-08-10** to
**2017-12-31**, but occupancy only exists from
**2014-02-16** to **2017-11-03**.
Every research question in this project needs both, so the working period is the
overlap:

> **16 February 2014 to 03 November 2017** -- 1,356 days,
> 195,406 ten-minute intervals.

The roughly six months of energy data that precede the occupancy record are not
used. They are not deleted, simply out of scope for questions that require knowing
whether anyone was in the building.
<!-- END:phase0_working_period -->

### 4.12 Data-quality table after cleaning

<!-- BEGIN:phase1_data_quality_table -->
| building | meters | first | last | 10-min intervals | usable % | power missing % | occupancy missing % | meter-off hours | interpolated blocks | outliers flagged (IQR) | outliers flagged (Z>3) | invalid voltage fixed | negative pf readings | total kWh (usable) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Academic | 1 | 2014-02-16 | 2017-11-03 | 195,406 | 90.44 | 1.94 | 8.04 | 10.50 | 89 | 13,195 | 1,538 | 0 | 0 | 849,596.90 |
| Boys_Hostel | 2 | 2014-02-16 | 2017-11-03 | 195,407 | 60.91 | 31.21 | 7.96 | 0 | 2,654 | 5,499 | 1,909 | 0 | 0 | 651,028.10 |
| Girls_Hostel | 2 | 2014-02-16 | 2017-11-03 | 195,406 | 59.97 | 32.45 | 8.05 | 0 | 385 | 1,296 | 578 | 0 | 0 | 293,037.10 |
| Mess | 1 | 2014-02-16 | 2017-11-03 | 195,405 | 80.48 | 11.24 | 8.69 | 0 | 281 | 3,464 | 1,632 | 0 | 0 | 616,561.30 |
| Library | 1 | 2014-02-16 | 2017-11-03 | 195,406 | 60.76 | 30.42 | 11.46 | 0 | 166 | 10,002 | 2,350 | 0 | 0 | 201,059.60 |
| Lecture | 1 | 2014-02-16 | 2017-11-03 | 195,397 | 18.90 | 1.94 | 22.46 | 25,487.50 | 2,269 | 125 | 119 | 0 | 0 | 18,581.90 |
| Facilities | 1 | 2014-07-10 | 2017-11-03 | 174,600 | 85.54 | 4.82 | 9.71 | 0 | 537 | 7,208 | 190 | 0 | 0 | 281,274.10 |
<!-- END:phase1_data_quality_table -->

---

## 5. Methodology

### 5.1 Phase 0 — Exploration

<!-- BEGIN:method_phase0 -->
Exploration was done before any cleaning, to find out what the data actually
contains rather than what the documentation promises.

**What we did.** We listed every file with its size; read both `Readme.txt` files
and the ISA-Tab metadata that records the instruments used; printed the first and
last rows of all 9 energy meters and all 7 occupancy
files; and profiled each file for coverage, gaps and data-quality counts.

**How we handled the size.** The energy folder is about 1.5 GB, so no step ever
loads it all. Files are read one at a time, in chunks of 500,000 rows, keeping
only the needed columns. Reading the last rows of a 125 MB file, for example, is
done by streaming through it and keeping only the final chunk.

**Timestamps.** All UNIX timestamps are converted with
`pd.to_datetime(..., unit="s", utc=True).dt.tz_convert("Asia/Kolkata")`, which is
what the dataset readme requires. Getting this wrong by 5.5 hours would put every
"night-time" reading in the afternoon and silently invalidate the entire project.

**Coverage measurement.** Rather than drawing a bar from each meter's first to its
last timestamp -- which makes a meter that went silent for 200 days look
continuous -- we counted readings per calendar month and divided by how many that
month should contain (1440 per day for the 1-minute energy files, 144 per day for
the 10-minute occupancy files). That is what the heatmap in section 4.8 shows.

**Notebook:** `notebooks/00_explore.ipynb`.
<!-- END:method_phase0 -->

### 5.2 Phase 1 — Data preparation

<!-- BEGIN:method_phase1 -->
Phase 1 turns the raw CSVs into one clean, merged, 10-minute table per building.

**Invalid values.** Three rules are applied while reading, and every fix is
counted: `power` outside 0 to 200 kW becomes `NaN`;
`voltage` outside 180-270 V becomes `NaN`;
`power_factor` keeps its magnitude with the sign retained as a separate flag
(decision D00-02).

**Dead meters.** Power exactly 0 for more than 6 continuous
hours is flagged `meter_off`. The test uses the *maximum* power within each
10-minute block, so a block counts as zero only if all ten of its 1-minute
readings were zero; blocks with no readings break a run rather than extending it.

**Outliers are flagged, never deleted.** Both IQR (Tukey fences at 1.5x) and
Z-score (|z| > 3) are computed on live readings only and
stored as columns. Deleting them would remove exactly the abnormal events Phase 6
is built to detect.

**Resampling.** 1-minute readings are averaged into 10min blocks to
match the native resolution of the occupancy data. Because a block can straddle a
chunk boundary, each chunk contributes per-block *sums and counts* which are added
across chunks before the mean is formed -- exactly equal to a single-pass mean.
Blocks are then placed on a complete time grid, so missing intervals are explicit
rather than absent.

**Merging.** Energy is joined to occupancy on the timestamp with an inner join.
Every occupancy timestamp already falls exactly on a 10-minute boundary, so no
tolerance matching is needed. For the two dormitories, mains and UPS are kept as
separate columns and also summed; the sum is `NaN` if either meter is missing.

**Gap filling.** Gaps of at most 30 minutes
(3 blocks) are filled by time interpolation and marked
`was_interpolated`. Longer gaps are left missing.

**Features.** `hour`, `minute_of_day`, `month`, `year`, `weekday` (an *ordered*
categorical so Monday sorts before Tuesday), `is_weekend`, `is_semester` /
`is_vacation`, power lagged 1 hour and 1 day, 24-hour rolling mean and standard
deviation (computed with `closed="left"` so the current block is excluded and no
future information leaks), and `kwh = watts / 1000 x 10/60`.

**Semester flag.** The I-BLEND project site publishes no academic calendar -- we
verified that the repository holds only the website assets and reading scripts --
so the windows are an approximation of a typical IIIT-Delhi year, validated
against observed dormitory occupancy (decision D01-03).

**Notebook:** `notebooks/01_data_prep.ipynb`.
<!-- END:method_phase1 -->

### 5.3 Phase 2 — Statistics and exploratory data analysis

<!-- BEGIN:method_phase2 -->
pending Phase 2
<!-- END:method_phase2 -->

### 5.4 Phase 3 — Principal component analysis of daily load profiles

<!-- BEGIN:method_phase3 -->
pending Phase 3
<!-- END:method_phase3 -->

### 5.5 Phase 4 — Regression models

<!-- BEGIN:method_phase4 -->
pending Phase 4
<!-- END:method_phase4 -->

### 5.6 Phase 5 — Wasted-energy analysis

<!-- BEGIN:method_phase5 -->
pending Phase 5
<!-- END:method_phase5 -->

### 5.7 Phase 6 — Anomaly detection experiment

<!-- BEGIN:method_phase6 -->
pending Phase 6
<!-- END:method_phase6 -->

### 5.8 Phase 7 — Delivery

<!-- BEGIN:method_phase7 -->
pending Phase 7
<!-- END:method_phase7 -->

---

## 6. Results

### 6.1 Phase 0 — What exploration told us

<!-- BEGIN:results_phase0 -->
Exploration produced four findings that shaped everything after it.

1. **The working period is set by occupancy, not energy.** Energy covers
   Aug 2013 – Dec 2017,
   occupancy only Feb 2014 – Nov 2017.
   The project analyses the overlap.

2. **"Empty" is not measurable in this dataset.** Minimum occupancy is 1 in all
   seven buildings (section 4.7). The main question had to be re-specified around a
   relative low-occupancy threshold, with a sensitivity curve to show how much the
   answer depends on where that threshold is put.

3. **Negative `power_factor` is a sign convention, not corrupt data.** It affects
   0.01%–67.55% of readings depending on the meter. The decisive
   evidence is that the range is exactly −0.999 to +1.000 *while `power` itself is
   never negative*: if current were genuinely flowing backwards, power would be
   negative too. Treating these as invalid would have deleted more than half of the
   Library record. We keep the magnitude and retain the sign as a separate flag.

4. **Coverage is much worse than row counts suggest.** Row coverage ranges from
   71.5% to
   99.5%, and the worst meters lose
   whole months at a time -- the largest single gap is
   5,311 hours
   (221 days). The Lecture meter
   additionally reads exactly 0 W for 81.7% of its record, which is a
   dead meter rather than an idle building.
<!-- END:results_phase0 -->

### 6.2 Phase 1 — Cleaning and preparation

<!-- BEGIN:results_phase1 -->
**Seven clean tables, and a very uneven amount of usable data.**

After cleaning, merging with occupancy and flagging dead meters, the proportion
of 10-minute intervals that are actually usable -- meter alive, reading present,
occupancy known -- varies from **18.9%** to
**90.4%**:

| building | rows | usable rows | pct usable | pct power missing | pct occupancy missing | hours meter off | total kwh |
|---|---|---|---|---|---|---|---|
| Academic | 195,406 | 176,730 | 90.44 | 1.94 | 8.04 | 10.50 | 849,596.90 |
| Boys_Hostel | 195,407 | 119,024 | 60.91 | 31.21 | 7.96 | 0 | 651,028.10 |
| Girls_Hostel | 195,406 | 117,186 | 59.97 | 32.45 | 8.05 | 0 | 293,037.10 |
| Mess | 195,405 | 157,266 | 80.48 | 11.24 | 8.69 | 0 | 616,561.30 |
| Library | 195,406 | 118,720 | 60.76 | 30.42 | 11.46 | 0 | 201,059.60 |
| Lecture | 195,397 | 36,930 | 18.90 | 1.94 | 22.46 | 25,487.50 | 18,581.90 |
| Facilities | 174,600 | 149,353 | 85.54 | 4.82 | 9.71 | 0 | 281,274.10 |

Three observations matter for everything that follows.

1. **Lecture is only 18.9% usable.** Its meter is flagged off
   for **25,488 hours** -- about
   2.9 years of the 3.7-year window. Its
   results rest on a far smaller sample than any other building, and every table
   it appears in says so.
2. **The Boys hostel, Girls hostel and Library sit near 60%** because of
   multi-month meter outages visible in section 4.9. That is a smaller sample,
   not a worse measurement.
3. **Academic is the most complete** at 90.4%, which is why
   it is used as the worked example throughout the notebooks.

**The pipeline was independently cross-checked.** Our per-building mean power,
computed from the individual meter files through chunked ingestion, was compared
against `all_buildings_power.csv`, which holds every meter side by side. All
seven agree to within
**0.122%** (largest disagreement), which rules out
a whole class of silent error in timestamp handling, unit conversion and chunk
boundaries:

| building | mean power from wide file w | mean power from our cache w | difference pct | agrees |
|---|---|---|---|---|
| Academic | 27,785.80 | 27,788.80 | 0.01 | True |
| Boys_Hostel | 31,418.80 | 31,383.20 | 0.11 | True |
| Girls_Hostel | 14,180.60 | 14,181.70 | 0.01 | True |
| Mess | 22,195.30 | 22,194.90 | 0.00 | True |
| Library | 9,074.70 | 9,075.90 | 0.01 | True |
| Lecture | 641.70 | 642 | 0.05 | True |
| Facilities | 10,458.90 | 10,471.70 | 0.12 | True |

**The approximate academic calendar was validated against the data.** If the
vacation windows were roughly right, dormitory occupancy should collapse inside
them -- and it does. Boys hostel median occupancy in vacation is
**42%** of its semester median, Girls
hostel **53%**. The Academic building
falls much less, which is what you would expect when staff keep working through
the summer.

![Median occupancy by month, with the approximated vacation months shaded](../figures/fig_01_semester_validation.png)

*The dip is centred on June and July exactly where the approximation puts it, and it is much deeper in the two dormitories than in the Academic building.*

**Dead-meter detection.**

![Lecture building in a partly-dead month, with flagged meter-off periods shaded](../figures/fig_01_dead_meter_lecture.png)

*Everything shaded is excluded from the energy accounting rather than counted as zero consumption.*

**A limitation of this rule, stated openly.** In the month shown the meter
alternates between about 4 kW by day and exactly zero every night -- which looks
less like a broken meter than like a building switched off at the mains. Both
report exactly 0 W, and no rule based on the power value alone can separate them.
Checking the length of every zero run shows two distinct populations:

![How long the Lecture building's zero-power stretches last](../figures/fig_01_zero_run_lengths_lecture.png)

*Two populations: many short runs near half a day (the nightly switch-off, 34.5% of all zero hours) and a few very long runs that account for 65.5% of them.*

| hours | runs | total hours | share of zero hours % |
|---|---|---|---|
| < 6 h | 418 | 408 | 1.30 |
| 6-18 h | 574 | 7,997 | 26.10 |
| 18-24 h | 106 | 2,152 | 7 |
| 1-2 days | 95 | 3,642 | 11.90 |
| 2-7 days | 88 | 7,504 | 24.50 |
| over a week | 22 | 8,928 | 29.10 |

The overwhelming majority of the Lecture meter's dead time sits in runs lasting
days to months, where the rule is clearly right. The overnight runs are where it
may be wrong. We keep the specified 6-hour rule as primary and quantify the
ambiguity with a 24-hour sensitivity check in Phase 5 (decision D01-07).

**Outlier flagging.**

![Academic building: distribution with IQR fences, and two weeks with flagged points](../figures/fig_01_outlier_flags_academic.png)

*The flagged points are mostly ordinary working-day peaks. An automatic 'remove outliers' step would have deleted every busy afternoon -- which is why this project flags instead of deletes.*

**Transformation and scaling.**

![Academic power before and after a log transform](../figures/fig_01_log_transform_power.png)

*The log transform cuts skew from 1.16 to 0.02, but the distribution stays bimodal -- a night cluster and a day cluster -- because that is a real physical feature, not a distortion.*

![The same power data: original, Min-Max scaled, and standardised](../figures/fig_01_scaling_comparison.png)

*Scaling moves and stretches an axis; it does not change the shape of the distribution. What changes is which features dominate a distance or a regression coefficient.*
<!-- END:results_phase1 -->

### 6.3 Phase 2 — Statistics and EDA

<!-- BEGIN:results_phase2 -->
pending Phase 2
<!-- END:results_phase2 -->

### 6.4 Phase 3 — PCA

<!-- BEGIN:results_phase3 -->
pending Phase 3
<!-- END:results_phase3 -->

### 6.5 Phase 4 — Regression

<!-- BEGIN:results_phase4 -->
pending Phase 4
<!-- END:results_phase4 -->

### 6.6 Phase 5 — Wasted energy

<!-- BEGIN:results_phase5 -->
pending Phase 5
<!-- END:results_phase5 -->

### 6.7 Phase 6 — Anomaly experiment

<!-- BEGIN:results_phase6 -->
pending Phase 6
<!-- END:results_phase6 -->

---

## 7. Decision log

Every judgement call made anywhere in this project is recorded here: thresholds,
how invalid values were treated, what was dropped, which models were chosen, and
the random seed. Each row states what else was considered and what difference the
choice makes to the results, so a reader can disagree with a decision and know
exactly what it would change.

<!-- BEGIN:decision_log -->
| # | Phase | Decision | Options considered | Chosen | Reason | Effect on results |
|---|---|---|---|---|---|---|
| 1 | 0 | Analysis window | Use the full energy record (Aug 2013 - Dec 2017); use only the energy/occupancy overlap | Overlap only: 2014-02-16 to 2017-11-03 | All three research questions need occupancy. Energy-only months cannot answer any of them. | Drops ~6 months of energy data at the start and ~2 months at the end. Reduces sample size; does not bias it. |
| 2 | 0 | Interpretation of negative power_factor | Treat as invalid and drop the rows; set to NaN; take the absolute value and keep a sign flag | abs(power_factor), plus a retained pf_was_negative flag | Affects 0.01-67.55% of rows. The range is exactly -0.999..+1.000 while power is never negative, so the sign is a leading/lagging convention, not reverse power flow. | Preserves 58% of the Library record that dropping would have destroyed. Power itself is untouched, so energy totals are unaffected either way. |
| 3 | 0 | Definition of low occupancy | occupancy == 0 (impossible: minimum is 1); a fixed absolute count for all buildings; a per-building fraction of its own 95th percentile | occupancy <= 5% of the building's 95th percentile | WiFi never reads zero, and building populations differ by ~20x, so an absolute cut-off is not comparable across buildings. | This threshold IS the main result's definition. A sensitivity curve over 0-20% is published in Phase 5 so the reader can see how much the headline depends on it. |
| 4 | 0 | Facilities (SRB), where no reading meets the threshold | Add a percentile floor for all buildings; use an absolute rule for SRB only; keep the uniform rule and report the empty cell | Keep the uniform rule; report 'no qualifying intervals'; quote SRB from the sensitivity curve instead | 5% of its 95th percentile is 0.90, below its own minimum count of 1. Changing the definition for one building would make it non-comparable. | Facilities has no headline waste percentage at the standard threshold. Its behaviour is reported from the sensitivity curve, clearly labelled as such. |
| 5 | 0 | Lecture building, whose meter reads 0 W for most of the record | Exclude the building; treat the zeros as genuine zero consumption; compute over alive periods only | Include it, computing over periods where the meter was alive, with coverage reported alongside | 81.7% of readings are exactly 0 W in long unbroken runs -- a meter that stopped reporting, not a building using no electricity. Treating them as real would produce a near-zero waste figure that is an artefact. | Lecture keeps a place in the headline table, but its figure rests on a much smaller sample than the other six buildings, and is flagged as such. |
| 6 | 0 | WiFi over-count of idle devices | Ignore it; subtract the documented idle baseline before thresholding and use that as the headline; use raw counts for the headline and report a corrected variant | Raw counts for the headline; corrected-occupancy run reported as a robustness check in Phase 5 | The over-count (~20 devices, ~50 in Academic) is an approximate constant from the dataset paper, not a measurement. Building the headline on it would rest the main result on an estimate. | Headline is conservative (raw counts make buildings look more occupied than they are, so waste is understated). The corrected run quantifies by how much. |
| 7 | 0 | Analysis resolution | Keep 1-minute energy and forward-fill occupancy; average energy into 10-minute blocks to match occupancy | 10min blocks | Occupancy is natively 10-minute. Up-sampling it to 1 minute would invent ten times more data than was measured. Every occupancy timestamp already falls exactly on a 10-minute boundary. | Reduces ~2.3M rows per meter to ~231k, which is what makes the whole project run on a laptop. No loss of information relative to the occupancy signal. |
| 8 | 0 | Random seed | Unseeded; a fixed seed | seed = 42 everywhere (sampling, k-means, anomaly injection, random forest) | Results must be reproducible by a teammate or an examiner running the notebooks again. | None on the substance; makes every reported number exactly reproducible. |
| 9 | 1 | Dead-meter rule | No rule; flag any zero reading; flag runs of 0 W longer than 6 h | Runs of exactly 0 W longer than 6 continuous hours are flagged meter_off; tested on the block maximum | A building can draw very little at night but not exactly 0.000 W for six hours. Flagging every isolated zero would also catch genuine brief shutdowns. | Removes 25,488 h from Lecture and 10 h from Academic. Without it, Lecture would appear to be the most efficient building on campus, which is an artefact. |
| 10 | 1 | Outlier handling | Delete IQR outliers; delete Z>3 outliers; winsorise; flag both and delete neither | Flag with both IQR and Z-score; delete nothing | Extreme power readings are the phenomenon Phase 6 is built to detect. Removing them would remove the subject of the study, and IQR alone flags ~6.8% of the Academic record -- mostly ordinary working-day peaks. | No rows removed. Two extra boolean columns available to later phases. |
| 11 | 1 | Semester / vacation calendar | Use the I-BLEND published calendar; infer purely from the data; approximate from the academic year and validate against the data | Approximate windows (16 May - 31 Jul, 16 - 31 Dec), validated against dormitory occupancy | The I-BLEND project repository publishes no calendar file -- verified, it contains only website assets and reading scripts. A purely data-driven split would be circular, since occupancy is also our explanatory variable. | Validated: Boys hostel vacation occupancy is 42% of its semester median, Girls 53%. Good enough for coarse semester-vs-vacation comparisons; boundaries are accurate to within days, not hours. |
| 12 | 1 | Interpolation limit | No interpolation; fill all gaps; fill only short gaps | Time interpolation for gaps up to 30 minutes (3 blocks); longer gaps left missing; every filled value marked was_interpolated | Filling 20 minutes between two similar readings is safe; filling a 200-day outage would be inventing data. | Fills 6,381 blocks across all seven buildings -- under 0.47% of the total. Negligible effect on any aggregate. |
| 13 | 1 | Combining hostel mains and UPS meters | Use mains only; use the sum only; keep both separate and also sum | Keep mains and UPS as separate columns AND provide the sum; the sum is NaN if either meter is missing | Which supply keeps running when rooms empty out is a Phase 5 question, so the split must survive. Adding a measured value to a missing one would silently understate the building total. | Hostel totals are only available when both meters report, which is part of why the two dormitories sit near 60% usable rather than 90%. |
| 14 | 1 | Chunk-boundary handling when resampling | Read whole files and resample once; resample each chunk and average the averages; accumulate per-block sums and counts across chunks | Per-block sums and counts, combined across chunks before the mean is formed | Averaging chunk averages is wrong whenever a 10-minute block spans two chunks. Sums and counts combine exactly. | None relative to a correct single-pass mean -- that is the point. Verified against all_buildings_power.csv to within 0.122%. |
| 15 | 1 | Ambiguity between a dead meter and a building switched off at night | Keep the 6 h rule and say nothing; raise the threshold to 24 h so nightly switch-offs count as real zero consumption; keep the rule and publish a sensitivity check | Keep the specified 6 h rule as primary; re-run the Lecture figure with a 24 h rule in Phase 5 as a sensitivity check | A switched-off building and a dead meter both report exactly 0 W and cannot be told apart from the power value alone. The zero-run histogram shows two populations: short runs near half a day (34.5% of zero hours) and multi-day runs (65.5% of zero hours). | Affects Lecture only, and only its denominator. The sensitivity check in Phase 5 quantifies it; the rest of the campus is unaffected because no other meter has sustained exact zeros. |
<!-- END:decision_log -->

---

## 8. Headline findings

<!-- BEGIN:headline_findings -->
pending Phase 5
<!-- END:headline_findings -->

---

## 9. Anomaly experiment results

<!-- BEGIN:anomaly_results -->
pending Phase 6
<!-- END:anomaly_results -->

---

## 10. Limitations

<!-- BEGIN:limitations -->
pending Phase 7
<!-- END:limitations -->

---

## 11. Conclusion and future scope

<!-- BEGIN:conclusion -->
pending Phase 7
<!-- END:conclusion -->

---

## 12. Syllabus coverage

Every topic in MD3135 Units I–VI and every tutorial, mapped to the notebook and
section where it is implemented.

### 12.1 Units I–VI

<!-- BEGIN:syllabus_units -->
pending Phase 7
<!-- END:syllabus_units -->

### 12.2 Tutorials 1–8

<!-- BEGIN:syllabus_tutorials -->
pending Phase 7
<!-- END:syllabus_tutorials -->

---

## 13. How to reproduce

<!-- BEGIN:how_to_reproduce -->
pending Phase 7
<!-- END:how_to_reproduce -->

---

## 14. References

1. Rashid, H., Singh, P. & Singh, A. (2019). *I-BLEND, a campus-scale commercial and
   residential buildings electrical energy dataset.* **Scientific Data** 6, 190015.
   <https://www.nature.com/articles/sdata201915> ·
   data: <https://doi.org/10.6084/m9.figshare.c.3893581>
2. Rashid, H. & Singh, P. (2018). *Monitor: an abnormality detection approach in
   buildings energy consumption.* IEEE CIC.
   <https://loneharoon.github.io/files/monitor.pdf>
3. Mishra, A., Lone, S. A. & Mishra, A. (2024). *DECODE: Data-driven Energy
   Consumption Prediction leveraging Historical Data and Environmental Factors in
   Buildings.* <https://arxiv.org/abs/2309.02908>
4. Masoso, O. T. & Grobler, L. J. (2010). *The dark side of occupants' behaviour on
   building energy use.* **Energy and Buildings** 42(2), 173–177.
   <https://www.osti.gov/etdeweb/biblio/21341871>
5. Anderson, K., Song, K., Lee, S. & Tian, W. (2015). *Longitudinal analysis of
   normalized energy consumption in university dormitories.* **Energy and Buildings**.
   <https://www.sciencedirect.com/science/article/abs/pii/S0378778814010299>
6. Lawrence Berkeley National Laboratory (2016). *Assessing the value of occupancy
   data in building energy baseline models.*
   <https://www.researchgate.net/publication/388952602>
7. Arjunan, P. et al. (2015). *Multi-user energy consumption monitoring and anomaly
   detection with partial context information.* **BuildSys '15**.
   <https://www.samy101.com/projects/energy-anomaly-detection/>
8. Martani, C. et al. (2012). *ENERNET: studying the dynamic relationship between
   building occupancy and energy consumption.* **Energy and Buildings** 47, 584–591.
9. Zhan, S. & Chong, A. (2021). *Building occupancy and energy consumption:
   case studies across building types.* **Energy and Built Environment** 2(2).
   <https://www.sciencedirect.com/science/article/pii/S2666123320300829>
10. I-BLEND project site (reading scripts and documentation).
    <https://github.com/i-blend/i-blend.github.io>

---

## Appendix A — Presentation outline

<!-- BEGIN:presentation_outline -->
pending Phase 7
<!-- END:presentation_outline -->
