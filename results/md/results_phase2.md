#### Descriptive statistics

| building | n | mean | median | mode (1 kW bins) | min | max | range | variance | std | Q1 | Q3 | IQR | skew |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Academic | 176,807 | 28,844.90 | 23,982.20 | 22,000 | 0 | 87,120.60 | 87,120.60 | 201,275,150.90 | 14,187.10 | 19,227.70 | 34,390.30 | 15,162.60 | 1.16 |
| Boys_Hostel | 120,915 | 32,804.70 | 30,797.90 | 24,000 | 7,043.30 | 87,537.40 | 80,494.10 | 154,018,094.10 | 12,410.40 | 23,401.10 | 39,920.10 | 16,519 | 0.80 |
| Girls_Hostel | 117,508 | 15,001.10 | 14,846 | 15,000 | 4,551 | 30,282.90 | 25,731.90 | 18,673,817.60 | 4,321.30 | 11,869.50 | 17,755.90 | 5,886.40 | 0.28 |
| Mess | 157,526 | 23,523.30 | 22,101 | 18,000 | 233.40 | 133,731.30 | 133,497.80 | 77,655,372.80 | 8,812.20 | 16,869.80 | 28,874 | 12,004.10 | 0.80 |
| Library | 118,872 | 10,162.40 | 7,690 | 5,000 | 768.30 | 46,145.80 | 45,377.50 | 50,332,418.20 | 7,094.50 | 4,999.50 | 13,659 | 8,659.50 | 1.23 |
| Lecture | 36,978 | 3,016.20 | 3,899.50 | 4,000 | 0 | 26,491 | 26,491 | 3,317,062.90 | 1,821.30 | 1,487.10 | 4,313.50 | 2,826.30 | 1.69 |
| Facilities | 149,883 | 11,306.30 | 10,801.30 | 9,000 | 547.20 | 138,916.10 | 138,368.90 | 23,479,779.10 | 4,845.60 | 8,803.80 | 13,118.50 | 4,314.70 | 10.58 |

The mean exceeds the median in every building, so every distribution is
right-skewed. The Boys hostel has the highest average power (32.8 kW), above the
Academic building, because it is occupied around the clock. Facilities is the
extreme case with a skew of 10.6 -- its maximum is more than ten times its
median, pointing to a large intermittent load.

#### Manual calculation checked against pandas

Every statistic above was recomputed from its definition with NumPy and asserted
equal to the pandas result. The largest relative difference across all eleven
statistics was 6.8e-15 -- floating-point noise. The check runs as an assertion,
so the notebook fails if they ever diverge.

#### Population versus sample

![Means of 1,000 random 30-day samples against the true population mean](../figures/fig_02_sampling_distribution.png)

*The sample means form the bell shape the central limit theorem predicts,
centred on the population mean; the observed standard error (36 kWh) matches the
predicted one (37 kWh).*

65.2% of 30-day samples land within 5% of the true mean -- **but only because
the days are drawn at random across the whole year**. An audit that happened to
run in June would measure the air-conditioning season instead. This is why the
project uses the full 3.7-year record rather than a sample.

#### What distribution does power follow?

| distribution | KS statistic (lower is better) | KS p-value |
|---|---|---|
| Normal | 0.17 | < 1e-300 |
| Log-normal | 0.08 | 1.21e-296 |

The log-normal fits better on the KS statistic, as expected for a strictly
positive right-skewed quantity. But the Q-Q plots show **neither is a good
fit**: the Academic building's power is genuinely bimodal -- a night cluster and
a day cluster -- and no unimodal distribution can describe two clusters.

![Fitted distributions and Q-Q plots for Academic building power](../figures/fig_02_distribution_fit.png)

*Both candidate distributions bend away from the line at the extremes; the data
is bimodal, which is a physical feature rather than a distortion.*

This shapes Phase 4: because power is not normally distributed, MAE is reported
alongside RMSE, since RMSE is dominated by the tail.

#### Hypothesis tests

**Semester versus vacation:**

| building | n semester | n vacation | mean semester (W) | mean vacation (W) | difference in means | percent difference | cohens d | effect size label | t-test p | Mann-Whitney p |
|---|---|---|---|---|---|---|---|---|---|---|
| Academic | 76,540 | 100,267 | 32,845.30 | 25,791.10 | 7,054.20 | 27.40 | 0.51 | medium | < 1e-300 | < 1e-300 |
| Boys_Hostel | 56,225 | 64,690 | 37,596.30 | 28,640.10 | 8,956.20 | 31.30 | 0.77 | medium | < 1e-300 | < 1e-300 |
| Girls_Hostel | 57,592 | 59,916 | 16,082.40 | 13,961.80 | 2,120.60 | 15.20 | 0.51 | medium | < 1e-300 | < 1e-300 |
| Mess | 73,885 | 83,641 | 25,268.50 | 21,981.60 | 3,286.90 | 15 | 0.38 | small | < 1e-300 | < 1e-300 |
| Library | 55,967 | 62,905 | 12,437 | 8,138.60 | 4,298.40 | 52.80 | 0.64 | medium | < 1e-300 | < 1e-300 |
| Lecture | 22,308 | 14,670 | 3,768.60 | 1,872.10 | 1,896.50 | 101.30 | 1.21 | large | < 1e-300 | < 1e-300 |
| Facilities | 64,891 | 84,992 | 11,089.60 | 11,471.70 | -382.10 | -3.30 | -0.08 | negligible | 2.20e-53 | 1.88e-85 |

**Weekday versus weekend:**

| building | mean weekday (W) | mean weekend (W) | difference in means | percent difference | cohens d | effect size label | t-test p | Mann-Whitney p |
|---|---|---|---|---|---|---|---|---|
| Academic | 31,625.20 | 21,792.30 | 9,832.80 | 45.10 | 0.73 | medium | < 1e-300 | < 1e-300 |
| Boys_Hostel | 33,463.10 | 31,120.50 | 2,342.60 | 7.50 | 0.19 | negligible | 3.43e-214 | 3.26e-144 |
| Girls_Hostel | 15,240.30 | 14,388.50 | 851.80 | 5.90 | 0.20 | negligible | 2.98e-219 | 1.26e-184 |
| Mess | 24,258.90 | 21,669.30 | 2,589.60 | 12 | 0.30 | small | < 1e-300 | < 1e-300 |
| Library | 11,408.70 | 6,934.60 | 4,474.20 | 64.50 | 0.66 | medium | < 1e-300 | < 1e-300 |
| Lecture | 3,144 | 2,267.70 | 876.30 | 38.60 | 0.49 | small | 6.04e-124 | < 1e-300 |
| Facilities | 11,588.50 | 10,589.50 | 999 | 9.40 | 0.21 | small | 9.31e-219 | < 1e-300 |

Every p-value here is small enough to print in scientific notation, so on a
naive "p < 0.05" reading every difference is significant and the p-values tell
us nothing beyond the fact that we have a lot of data. The **Cohen's d** column
carries the finding, and it is **not uniform across the campus**.

*Semester versus vacation* splits the buildings in two. The **Lecture** (d =
1.21) show large effects -- buildings whose purpose empties out when term ends.
But the **Facilities** (d = -0.08) barely move, and no buildings actually
consumes **more** power during vacation, because the Indian summer vacation
coincides with Delhi's hottest months: cooling load rises exactly as occupation
falls. That is the no-weather-data limitation made visible.

*Weekday versus weekend* splits them the other way. The **Academic** (d = 0.73)
and **Library** (d = 0.66) fall substantially at weekends, while both hostels
are essentially flat (d = 0.19 and 0.20) -- which is correct, because people
live there on Saturdays too.

The contrast is what matters for Phase 5. Buildings *can* respond strongly to
whether people are present -- the Library drops 64% at weekends, so it is
clearly possible. Buildings that do not respond are therefore making a choice,
not obeying a physical necessity.

#### The chart set

![Share of total measured campus energy by building](../figures/fig_02_pie_energy_share.png)

*Shares reflect *measured* energy, and the buildings have very different amounts
of usable data (Lecture only 19%), so this shows what was recorded rather than
what the campus consumed.*

![Average daily energy use by building](../figures/fig_02_bar_daily_energy.png)

*The fair comparison, independent of how many days each meter recorded. The Boys
hostel is the largest daily consumer at 742 kWh/day.*

![Distribution of 10-minute power readings by building](../figures/fig_02_box_power_by_building.png)

*The hostels have narrow boxes -- steady load from continuous occupation.
Academic and Library have tall boxes: they swing between a quiet night baseline
and a busy day.*

![Power distribution in each building](../figures/fig_02_hist_power_all_buildings.png)

*Academic and Library are visibly bimodal (a night hump and a day hump); the
hostels are closer to one broad peak because they never really switch off.*

![Mean power by hour of day, one line per building](../figures/fig_02_hourly_profile_all.png)

*The most important chart in this phase: the commercial buildings fall at night
but do not fall to zero -- the Academic building still draws around 20 kW at 3
a.m. That gap is what Phase 5 quantifies.*

![Power against occupancy, one panel per building](../figures/fig_02_scatter_power_occupancy.png)

*Every cloud slopes upward, and every cloud has a floor well above zero on the
left: even at minimum occupancy the building draws a substantial load.*

#### Power-occupancy correlation

| building | kind | n | pearson r | pearson p | spearman r | spearman p | r squared |
|---|---|---|---|---|---|---|---|
| Academic | commercial | 176,807 | 0.67 | < 1e-300 | 0.65 | < 1e-300 | 0.45 |
| Boys_Hostel | residential | 120,915 | 0.65 | < 1e-300 | 0.66 | < 1e-300 | 0.42 |
| Girls_Hostel | residential | 117,508 | 0.45 | < 1e-300 | 0.43 | < 1e-300 | 0.20 |
| Mess | commercial | 157,526 | 0.41 | < 1e-300 | 0.45 | < 1e-300 | 0.17 |
| Library | commercial | 118,872 | 0.50 | < 1e-300 | 0.61 | < 1e-300 | 0.25 |
| Lecture | commercial | 36,978 | 0.31 | < 1e-300 | 0.36 | < 1e-300 | 0.10 |
| Facilities | commercial | 149,883 | 0.27 | < 1e-300 | 0.37 | < 1e-300 | 0.07 |

Occupancy and power are correlated in every building but never strongly. The
best case is **Academic at r = 0.67**, meaning occupancy explains about 44% of
the variation in its power; the weakest is **Facilities at r = 0.27** (8%). So
**most of what determines a building's power draw is not how many people are in
it** -- a result in its own right, and the quantitative form of the base-load
floor visible in the scatter plots.

Spearman exceeds Pearson for the Library (0.61 against 0.50), indicating a real
but *bent* relationship: power rises with occupancy and then flattens.

![Correlation between numeric features, Academic building](../figures/fig_02_correlation_heatmap.png)

*The strongest predictor of power is power one hour ago (r about 0.95) --
buildings are inertial. Occupancy sits well behind the lag features, which is
why Phase 4's interpretable models use calendar and occupancy features rather
than lags.*

![Mean power by day of week, and semester against vacation](../figures/fig_02_weekday_semester_patterns.png)

*The weekend drop is a few percent, not a collapse. In several buildings
vacation power is as high as or higher than semester power, because Delhi's
summer vacation coincides with the hottest months and the cooling runs
regardless.*