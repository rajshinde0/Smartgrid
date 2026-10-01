#### Descriptive statistics

| building | n | mean | median | mode (1 kW bins) | min | max | range | variance | std | Q1 | Q3 | IQR | skew |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Academic | 176,756 | 28,844.10 | 23,980.20 | 22,000 | 0 | 87,120.60 | 87,120.60 | 201,282,884.10 | 14,187.40 | 19,227.50 | 34,389.70 | 15,162.20 | 1.16 |
| Boys_Hostel | 120,114 | 32,804.60 | 30,780.20 | 24,000 | 7,043.30 | 87,537.40 | 80,494.10 | 154,674,314 | 12,436.80 | 23,372.50 | 39,942.70 | 16,570.10 | 0.80 |
| Girls_Hostel | 117,292 | 15,005.20 | 14,850.40 | 15,000 | 4,551 | 30,282.90 | 25,731.90 | 18,664,853.30 | 4,320.30 | 11,876.50 | 17,758.70 | 5,882.20 | 0.28 |
| Mess | 157,376 | 23,523.90 | 22,101.60 | 18,000 | 233.40 | 133,731.30 | 133,497.80 | 77,672,114.80 | 8,813.20 | 16,869.90 | 28,874.70 | 12,004.80 | 0.80 |
| Library | 118,742 | 10,161.30 | 7,688.70 | 5,000 | 768.30 | 46,145.80 | 45,377.50 | 50,340,732 | 7,095.10 | 4,999.40 | 13,654.10 | 8,654.60 | 1.23 |
| Lecture | 36,854 | 3,025.50 | 3,908.40 | 4,000 | 0 | 26,491 | 26,491 | 3,299,591.60 | 1,816.50 | 1,495.10 | 4,313.90 | 2,818.80 | 1.70 |
| Facilities | 149,637 | 11,302.70 | 10,796.20 | 9,000 | 547.20 | 138,916.10 | 138,368.90 | 23,497,981.10 | 4,847.50 | 8,800.90 | 13,114.20 | 4,313.30 | 10.59 |

The mean exceeds the median in every building, so every distribution is
right-skewed. The Boys hostel has the highest average power (32.8 kW), above the
Academic building, because it is occupied around the clock. Facilities is the
extreme case with a skew of 10.6 -- its maximum is more than ten times its
median, pointing to a large intermittent load.

#### Manual calculation checked against pandas

Every statistic above was recomputed from its definition with NumPy and asserted
equal to the pandas result. The largest relative difference across all eleven
statistics was 4.0e-15 -- floating-point noise. The check runs as an assertion,
so the notebook fails if they ever diverge.

#### Population versus sample

![Means of 1,000 random 30-day samples against the true population mean](../figures/fig_02_sampling_distribution.png)

*The sample means form the bell shape the central limit theorem predicts,
centred on the population mean; the observed standard error (36 kWh) matches the
predicted one (37 kWh).*

64.9% of 30-day samples land within 5% of the true mean -- **but only because
the days are drawn at random across the whole year**. An audit that happened to
run in June would measure the air-conditioning season instead. This is why the
project uses the full 3.7-year record rather than a sample.

#### What distribution does power follow?

| distribution | KS statistic (lower is better) | KS p-value |
|---|---|---|
| Normal | 0.17 | < 1e-300 |
| Log-normal | 0.08 | < 1e-300 |

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
| Academic | 76,510 | 100,246 | 32,844.10 | 25,791.20 | 7,052.90 | 27.30 | 0.51 | medium | < 1e-300 | < 1e-300 |
| Boys_Hostel | 56,168 | 63,946 | 37,595 | 28,596.90 | 8,998.10 | 31.50 | 0.78 | medium | < 1e-300 | < 1e-300 |
| Girls_Hostel | 57,493 | 59,799 | 16,085.90 | 13,966.10 | 2,119.80 | 15.20 | 0.51 | medium | < 1e-300 | < 1e-300 |
| Mess | 73,828 | 83,548 | 25,268.20 | 21,982.50 | 3,285.70 | 14.90 | 0.38 | small | < 1e-300 | < 1e-300 |
| Library | 55,939 | 62,803 | 12,435.70 | 8,135.50 | 4,300.20 | 52.90 | 0.64 | medium | < 1e-300 | < 1e-300 |
| Lecture | 22,226 | 14,628 | 3,781 | 1,877.50 | 1,903.50 | 101.40 | 1.22 | large | < 1e-300 | < 1e-300 |
| Facilities | 64,745 | 84,892 | 11,081.70 | 11,471.30 | -389.60 | -3.40 | -0.08 | negligible | 2.62e-55 | 9.39e-89 |

**Weekday versus weekend:**

| building | mean weekday (W) | mean weekend (W) | difference in means | percent difference | cohens d | effect size label | t-test p | Mann-Whitney p |
|---|---|---|---|---|---|---|---|---|
| Academic | 31,624.60 | 21,790.90 | 9,833.70 | 45.10 | 0.73 | medium | < 1e-300 | < 1e-300 |
| Boys_Hostel | 33,463.60 | 31,118.10 | 2,345.50 | 7.50 | 0.19 | negligible | 2.55e-212 | 5.08e-143 |
| Girls_Hostel | 15,244.20 | 14,392.60 | 851.70 | 5.90 | 0.20 | negligible | 8.35e-219 | 2.79e-184 |
| Mess | 24,260 | 21,668.80 | 2,591.10 | 12 | 0.30 | small | < 1e-300 | < 1e-300 |
| Library | 11,408.20 | 6,934.10 | 4,474.10 | 64.50 | 0.66 | medium | < 1e-300 | < 1e-300 |
| Lecture | 3,154.50 | 2,271 | 883.50 | 38.90 | 0.49 | small | 1.08e-125 | < 1e-300 |
| Facilities | 11,584.40 | 10,586.90 | 997.50 | 9.40 | 0.21 | small | 2.23e-217 | < 1e-300 |

Every p-value here is small enough to print in scientific notation, so on a
naive "p < 0.05" reading every difference is significant and the p-values tell
us nothing beyond the fact that we have a lot of data. The **Cohen's d** column
carries the finding, and it is **not uniform across the campus**.

*Semester versus vacation* splits the buildings in two. The **Lecture** (d =
1.22) show large effects -- buildings whose purpose empties out when term ends.
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
hostel is the largest daily consumer at 738 kWh/day.*

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
| Academic | commercial | 176,756 | 0.67 | < 1e-300 | 0.65 | < 1e-300 | 0.45 |
| Boys_Hostel | residential | 120,114 | 0.65 | < 1e-300 | 0.66 | < 1e-300 | 0.42 |
| Girls_Hostel | residential | 117,292 | 0.45 | < 1e-300 | 0.43 | < 1e-300 | 0.20 |
| Mess | commercial | 157,376 | 0.41 | < 1e-300 | 0.45 | < 1e-300 | 0.17 |
| Library | commercial | 118,742 | 0.50 | < 1e-300 | 0.61 | < 1e-300 | 0.25 |
| Lecture | commercial | 36,854 | 0.31 | < 1e-300 | 0.36 | < 1e-300 | 0.10 |
| Facilities | commercial | 149,637 | 0.27 | < 1e-300 | 0.37 | < 1e-300 | 0.07 |

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