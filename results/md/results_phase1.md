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