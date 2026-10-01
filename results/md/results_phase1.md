**Seven clean tables, and a very uneven amount of usable data.**

After cleaning, merging with occupancy and flagging dead meters, the proportion
of 10-minute intervals that are actually usable -- meter alive, reading present,
occupancy known -- varies from **18.9%** to **90.5%**:

| building | rows | usable rows | pct usable | pct power missing | pct occupancy missing | hours meter off | total kwh |
|---|---|---|---|---|---|---|---|
| Academic | 195,406 | 176,756 | 90.46 | 1.96 | 8.04 | 10.50 | 849,728.20 |
| Boys_Hostel | 195,407 | 120,114 | 61.47 | 30.65 | 7.96 | 0 | 656,715.30 |
| Girls_Hostel | 195,406 | 117,292 | 60.02 | 32.39 | 8.05 | 0 | 293,330.80 |
| Mess | 195,405 | 157,376 | 80.54 | 11.18 | 8.69 | 0 | 617,014.90 |
| Library | 195,406 | 118,742 | 60.77 | 30.41 | 11.46 | 0 | 201,095.10 |
| Lecture | 195,397 | 36,854 | 18.86 | 80.24 | 22.46 | 25,501 | 18,583.30 |
| Facilities | 174,600 | 149,637 | 85.70 | 4.66 | 9.71 | 0 | 281,884.90 |

Three observations matter for everything that follows.

1. **Lecture is only 18.9% usable.** Its meter is flagged off
   for **25,501 hours** -- about
   2.9 years of the 3.7-year window. Its
   results rest on a far smaller sample than any other building, and every table
   it appears in says so.
2. **The Boys hostel, Girls hostel and Library sit near 60%** because of
   multi-month meter outages visible in section 4.9. That is a smaller sample,
   not a worse measurement.
3. **Academic is the most complete** at 90.5%, which is why
   it is used as the worked example throughout the notebooks.

**The pipeline was independently cross-checked.** Our per-building mean power,
computed from the individual meter files through chunked ingestion, was compared
against `all_buildings_power.csv`, which holds every meter side by side. All
seven agree to within **0.122%** (largest disagreement), which rules out a whole
class of silent error in timestamp handling, unit conversion and chunk
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

**The semester flag comes from the official IIIT-Delhi calendar** published with
I-BLEND on figshare -- one CSV per year, 2013-2017, marking each day as working
or not and as high- or low-activity. Cross-checking it against the data confirms
it behaves as it should: dormitory median occupancy on low-activity days is
**42%** of the high-activity median for the Boys hostel and **53%** for the
Girls hostel, while the Academic building falls much less -- exactly what you
would expect when staff keep working through the breaks.

An earlier version of this analysis approximated the calendar, having looked for
it on the project GitHub site rather than on figshare. That approximation agreed
with the published calendar on only **68.5%** of days, chiefly because the
official definition of low activity includes every weekend and public holiday.
The approximation survives in the code as a fallback for anyone who cannot
download the calendar files.

![Median occupancy by month, with the approximated vacation months shaded](../figures/fig_01_semester_validation.png)

*The dip is centred on June and July exactly where the approximation puts it,
and it is much deeper in the two dormitories than in the Academic building.*

**Dead-meter detection.**

![Lecture building in a partly-dead month, with flagged meter-off periods shaded](../figures/fig_01_dead_meter_lecture.png)

*Everything shaded is excluded from the energy accounting rather than counted as
zero consumption.*

**A limitation of this rule, stated openly.** In the month shown the meter
alternates between about 4 kW by day and exactly zero every night -- which looks
less like a broken meter than like a building switched off at the mains. Both
report exactly 0 W, and no rule based on the power value alone can separate
them. Checking the length of every zero run shows two distinct populations:

![How long the Lecture building's zero-power stretches last](../figures/fig_01_zero_run_lengths_lecture.png)

*Two populations: many short runs near half a day (the nightly switch-off, 34.5%
of all zero hours) and a few very long runs that account for 65.5% of them.*

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

*The flagged points are mostly ordinary working-day peaks. An automatic 'remove
outliers' step would have deleted every busy afternoon -- which is why this
project flags instead of deletes.*

**Transformation and scaling.**

![Academic power before and after a log transform](../figures/fig_01_log_transform_power.png)

*The log transform cuts skew from 1.16 to 0.02, but the distribution stays
bimodal -- a night cluster and a day cluster -- because that is a real physical
feature, not a distortion.*

![The same power data: original, Min-Max scaled, and standardised](../figures/fig_01_scaling_comparison.png)

*Scaling moves and stretches an axis; it does not change the shape of the
distribution. What changes is which features dominate a distance or a regression
coefficient.*