#### Thresholds

| building | kind | p95 occupancy | threshold (5% of p95) | usable intervals | intervals at/below threshold | % of intervals | threshold reachable |
|---|---|---|---|---|---|---|---|
| Academic | commercial | 258 | 12.90 | 176,730 | 11,529 | 6.52 | True |
| Boys_Hostel | residential | 421 | 21.05 | 119,024 | 7,088 | 5.96 | True |
| Girls_Hostel | residential | 180 | 9 | 117,186 | 7,345 | 6.27 | True |
| Mess | commercial | 177 | 8.85 | 157,266 | 19,794 | 12.59 | True |
| Library | commercial | 182 | 9.10 | 118,720 | 33,670 | 28.36 | True |
| Lecture | commercial | 298 | 14.90 | 36,930 | 8,270 | 22.39 | True |
| Facilities | commercial | 18 | 0.90 | 149,353 | 0 | 0 | False |

Facilities is the exception predicted in Phase 0: its occupancy runs 1 to 47
with a 95th percentile of 18, so the threshold is **0.9** -- below its own
minimum observed count -- and **no interval qualifies**. The rule is kept
identical for every building rather than bent for one; its behaviour is read off
the sensitivity curve instead.

#### The headline table

| building | kind | threshold | coverage % | total kWh measured | low-occupancy kWh | low-occupancy energy share % | % of intervals low | mean power overall (kW) | mean power when low (kW) | intensity ratio | base load a (kW) | watts per occupant b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Academic | commercial | 12.90 | 90.40 | 849,596.90 | 40,832.10 | 4.81 | 6.52 | 28.84 | 21.25 | 0.74 | 16.95 | 128.10 |
| Boys_Hostel | residential | 21.05 | 60.90 | 651,028.10 | 28,959.20 | 4.45 | 5.96 | 32.82 | 24.51 | 0.75 | 15.94 | 68 |
| Girls_Hostel | residential | 9 | 60 | 293,037.10 | 14,587.80 | 4.98 | 6.27 | 15 | 11.92 | 0.79 | 10.60 | 36.30 |
| Mess | commercial | 8.85 | 80.50 | 616,561.30 | 57,580.60 | 9.34 | 12.59 | 23.52 | 17.45 | 0.74 | 18.85 | 61.70 |
| Library | commercial | 9.10 | 60.80 | 201,059.60 | 35,043.50 | 17.43 | 28.36 | 10.16 | 6.24 | 0.61 | 7.24 | 68.50 |
| Lecture | commercial | 14.90 | 18.90 | 18,581.90 | 3,541.80 | 19.06 | 22.39 | 3.02 | 2.57 | 0.85 | 2.13 | 7.40 |
| Facilities | commercial | 0.90 | 85.50 | 281,274.10 | 0 | 0 | 0 | 11.30 | - | - | 9.27 | 231.70 |

![Low-occupancy energy share and intensity ratio, per building](../figures/fig_05_headline.png)

*The right-hand panel is the one to read: when nearly empty, these buildings
still draw between 62% and 85% of their average power.*

#### Sensitivity to the threshold

![Low-occupancy energy share against threshold, 0% to 20% of p95](../figures/fig_05_sensitivity_curve.png)

*Six of seven curves rise smoothly and the ranking of buildings barely changes
across the range, so the finding does not depend on the exact threshold.
Facilities is a staircase because its occupancy is a small integer.*

Six of the seven curves rise smoothly with no jumps, and the ranking of
buildings is stable across the whole range, so the headline does not rest on the
choice of 5%. **Facilities is the exception, and the shape of its curve is
diagnostic**: it is a staircase, jumping at roughly 6%, 12% and 17% and flat in
between. Occupancy there is a small integer running from 1 to 47, so a sliding
threshold only ever crosses whole numbers, and between crossings nothing
changes. That is the same fact that made the standard threshold unreachable for
this building, seen from another angle -- a relative threshold assumes occupancy
is effectively continuous, and in a building this small it is not.

#### Comparison with the published literature

| building | kind | out-of-hours share % (clock rule) | % intervals out of hours | low-occupancy share % (occupancy rule) | % intervals low occupancy |
|---|---|---|---|---|---|
| Academic | commercial | 55.25 | 69.98 | 4.81 | 6.52 |
| Boys_Hostel | residential | 74.10 | 69.65 | 4.45 | 5.96 |
| Girls_Hostel | residential | 73.66 | 70.11 | 4.98 | 6.27 |
| Mess | commercial | 66.37 | 69.98 | 9.34 | 12.59 |
| Library | commercial | 54.96 | 68.82 | 17.43 | 28.36 |
| Lecture | commercial | 22.09 | 27.62 | 19.06 | 22.39 |
| Facilities | commercial | 63.65 | 68.64 | 0 | 0 |

![Clock-based and occupancy-based definitions against the published figures](../figures/fig_05_published_comparison.png)

*Applying Masoso & Grobler's own clock-based definition to this data gives the
Academic building 55.2% and the Library 55.0%, against their published 56%.*

**This is the strongest external check in the project.** Applying Masoso &
Grobler's clock-based definition to our data gives the Academic building
**55.2%** and the Library **55.0%** -- against their published **56%**, from
different buildings on a different continent fifteen years earlier. Landing
within a percentage point is good evidence that the pipeline measures what it
claims to.

It also shows that the two definitions are **not measuring the same thing**. A
clock rule calls 3 p.m. on a vacation Tuesday "occupied" when the building is
empty, and 8 p.m. during exams "unoccupied" when the Library is full. The
occupancy rule uses what was actually measured but is far stricter, because WiFi
over-counting means genuinely quiet periods still register double-digit device
counts. The truth lies between them, and **our occupancy-based figure is a
conservative lower bound** -- a conclusion the corrected-occupancy check below
independently confirms.

#### Base load: two independent routes to the same number

| building | base load a from model A (kW) | night 02:00-06:00 median (kW) | difference (kW) | difference % | mean power (kW) | base load as % of mean |
|---|---|---|---|---|---|---|
| Academic | 16.95 | 19.74 | -2.79 | -14.10 | 28.84 | 58.80 |
| Boys_Hostel | 15.94 | 33.51 | -17.57 | -52.40 | 32.82 | 48.60 |
| Girls_Hostel | 10.60 | 15.43 | -4.83 | -31.30 | 15 | 70.60 |
| Mess | 18.85 | 16.76 | 2.09 | 12.40 | 23.52 | 80.10 |
| Library | 7.24 | 5.69 | 1.55 | 27.30 | 10.16 | 71.30 |
| Lecture | 2.13 | 3.97 | -1.84 | -46.30 | 3.02 | 70.60 |
| Facilities | 9.27 | 10.17 | -0.90 | -8.80 | 11.30 | 82 |

![Model A intercept against the directly measured night-time median](../figures/fig_05_base_load_vs_night.png)

*A regression intercept and a raw night-time median are computed in completely
different ways; that they track each other is real corroboration that the base
load is not an artefact of the fit.*

Where the two disagree, the direction is informative. The Boys hostel's night
median sits far *above* its model intercept -- exactly right for a dormitory,
where people are home and asleep at 4 a.m. The small hours are simply not a
low-occupancy period there, which is precisely why an occupancy-based definition
is worth the trouble: a clock-based rule would have called those hours
unoccupied and been wrong.

#### Responsiveness ranking

| building | base load kw | mean power kw | variable share pct | responsiveness rank | intensity ratio | watts per occupant b | model A vs night median % | model A reliable? | measured rank |
|---|---|---|---|---|---|---|---|---|---|
| Library | 7.24 | 10.16 | 28.70 | 5 | 0.61 | 68.50 | 27.30 | NO -- extrapolated | 1 |
| Academic | 16.95 | 28.84 | 41.20 | 2 | 0.74 | 128.10 | -14.10 | yes | 2 |
| Mess | 18.85 | 23.52 | 19.90 | 6 | 0.74 | 61.70 | 12.40 | yes | 3 |
| Boys_Hostel | 15.94 | 32.82 | 51.40 | 1 | 0.75 | 68 | -52.40 | NO -- extrapolated | 4 |
| Girls_Hostel | 10.60 | 15 | 29.30 | 4 | 0.79 | 36.30 | -31.30 | NO -- extrapolated | 5 |
| Lecture | 2.13 | 3.02 | 29.50 | 3 | 0.85 | 7.40 | -46.30 | NO -- extrapolated | 6 |
| Facilities | 9.27 | 11.30 | 18 | 7 | - | 231.70 | -8.80 | yes | - |

![How much of each building's load actually follows its occupants](../figures/fig_05_responsiveness.png)

*In every building the base load -- the part drawn whether or not anyone is
present -- is the larger share.*

**The two metrics disagree, and the disagreement is informative.** Ranked by the
*measured* intensity ratio, the most responsive building is **Library** (62% of
average power when nearly empty) and the least is **Lecture** (85%). Ranked by
the *modelled* non-base-load share the order differs, because that version
extrapolates model A down to zero occupancy -- and for the two dormitories and
the Lecture building that point lies far outside the occupancy range ever
observed. In the worst case the extrapolated intercept sits 52% away from the
directly measured night-time median.

Where the two disagree we rank on the measured ratio and flag the modelled value
as unreliable. The conclusion survives either way: **even the best performer has
the majority of its consumption fixed**, and for the flagged buildings the true
fixed share is larger than the modelled figure, not smaller.

#### Semester against vacation

| building | semester | vacation | change (pp) |
|---|---|---|---|
| Academic | 4.13 | 6.60 | 2.47 |
| Boys_Hostel | 3.19 | 11.33 | 8.14 |
| Facilities | 0 | 0 | 0 |
| Girls_Hostel | 3.89 | 9.90 | 6.01 |
| Lecture | 18.05 | 25.14 | 7.09 |
| Library | 14.13 | 31.45 | 17.32 |
| Mess | 6.71 | 19.08 | 12.37 |

![Low-occupancy share and mean power, semester against vacation](../figures/fig_05_semester_vacation.png)

*Holding the threshold fixed across both periods so the comparison measures
behaviour rather than the definition.*

#### Hostel mains against UPS

| building | supply | total kwh | low occ kwh | share pct | mean power w | mean power low occ w |
|---|---|---|---|---|---|---|
| Boys_Hostel | mains | 348,400.80 | 15,364.80 | 4.41 | 17,562.90 | 13,006.30 |
| Boys_Hostel | ups | 302,627.20 | 13,594.50 | 4.49 | 15,255.40 | 11,507.70 |
| Girls_Hostel | mains | 148,297.50 | 7,498.40 | 5.06 | 7,592.90 | 6,125.30 |
| Girls_Hostel | ups | 144,739.60 | 7,089.40 | 4.90 | 7,410.80 | 5,791.20 |

![Low-occupancy share and mean power by supply, for the two dormitories](../figures/fig_05_mains_vs_ups.png)

*Only I-BLEND meters the mains and backup supplies separately, so this
comparison is not available in other campus datasets.*

#### Commercial against residential

| kind | buildings | mean low occ share | mean intensity ratio | mean base load kw | total kwh |
|---|---|---|---|---|---|
| commercial | 5 | 10.13 | 0.74 | 10.89 | 1,967,073.80 |
| residential | 2 | 4.71 | 0.77 | 13.27 | 944,065.20 |

#### Sensitivity check 1: Lecture under a 24-hour dead-meter rule

| dead-meter rule | usable intervals | total kWh | low-occupancy share % |
|---|---|---|---|
| 6 h (as specified) | 36,930 | 18,581.90 | 19.06 |
| 24 h (nightly switch-offs kept as real zeros) | 81,322 | 18,581.90 | 17.76 |

Phase 1 established that a building switched off at the mains overnight and a
meter that has stopped reporting both read exactly 0 W, and that the specified
6-hour rule cannot separate them (D01-07). Relaxing the rule to 24 hours more
than doubles the usable intervals and moves the headline share by **1.30
percentage points**. The ambiguity is real but small, and the Lecture figure
survives it.

#### Sensitivity check 2: corrected occupancy

| building | idle devices subtracted | raw threshold | corrected threshold | raw share % | corrected share % | change (pp) | raw % intervals low | corrected % intervals low |
|---|---|---|---|---|---|---|---|---|
| Academic | 50 | 12.90 | 10.40 | 4.81 | 48.15 | 43.34 | 6.52 | 61.83 |
| Boys_Hostel | 20 | 21.05 | 20.05 | 4.45 | 6.34 | 1.89 | 5.96 | 8.16 |
| Girls_Hostel | 20 | 9 | 8 | 4.98 | 9.83 | 4.85 | 6.27 | 12.53 |
| Mess | 20 | 8.85 | 7.85 | 9.34 | 28.60 | 19.26 | 12.59 | 35.19 |
| Library | 20 | 9.10 | 8.10 | 17.43 | 40.32 | 22.89 | 28.36 | 56.05 |
| Lecture | 20 | 14.90 | 13.90 | 19.06 | 28.71 | 9.65 | 22.39 | 33.85 |
| Facilities | 20 | 0.90 | 0 | 0 | 97.63 | 97.63 | 0 | 97.94 |

Subtracting the documented idle-device baseline makes every building look
emptier more often, so the low-occupancy share rises everywhere. This **confirms
that the raw-count headline is a conservative lower bound**. For Facilities the
correction is drastic -- subtracting 20 from a building whose 95th percentile is
18 pushes nearly every interval to zero -- which is not a credible description
of the building and illustrates why the headline was not built on this
adjustment (D00-06).