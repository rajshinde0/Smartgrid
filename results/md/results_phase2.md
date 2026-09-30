#### Descriptive statistics

| building | n | mean | median | mode (1 kW bins) | min | max | range | variance | std | Q1 | Q3 | IQR | skew |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Academic | 176,730 | 28,843.90 | 23,980 | 22,000 | 0 | 87,120.60 | 87,120.60 | 201,289,521 | 14,187.70 | 19,226.70 | 34,389.50 | 15,162.80 | 1.16 |
| Boys_Hostel | 119,024 | 32,818.30 | 30,793.40 | 24,000 | 7,043.30 | 87,537.40 | 80,494.10 | 155,657,815.10 | 12,476.30 | 23,327.70 | 39,994.40 | 16,666.70 | 0.80 |
| Girls_Hostel | 117,186 | 15,003.70 | 14,849.10 | 15,000 | 4,551 | 30,282.90 | 25,731.90 | 18,659,460.70 | 4,319.70 | 11,874.90 | 17,758.70 | 5,883.80 | 0.28 |
| Mess | 157,266 | 23,523 | 22,100.10 | 18,000 | 233.40 | 133,731.30 | 133,497.80 | 77,680,420.70 | 8,813.60 | 16,869.20 | 28,874.60 | 12,005.40 | 0.80 |
| Library | 118,720 | 10,161.40 | 7,688.90 | 5,000 | 768.30 | 46,145.80 | 45,377.50 | 50,335,404.50 | 7,094.70 | 4,999.80 | 13,654 | 8,654.20 | 1.23 |
| Lecture | 36,930 | 3,019 | 3,902 | 4,000 | 0 | 26,491 | 26,491 | 3,312,273.10 | 1,820 | 1,490.10 | 4,313.70 | 2,823.60 | 1.69 |
| Facilities | 149,353 | 11,299.70 | 10,791.80 | 9,000 | 547.20 | 138,916.10 | 138,368.90 | 23,527,220 | 4,850.50 | 8,797.20 | 13,110.60 | 4,313.30 | 10.59 |

The mean exceeds the median in every building, so every distribution is
right-skewed. The Boys hostel has the highest average power (32.8 kW), above the
Academic building, because it is occupied around the clock. Facilities is the
extreme case with a skew of 10.6 -- its maximum is more than ten times its
median, pointing to a large intermittent load.

#### Manual calculation checked against pandas

Every statistic above was recomputed from its definition with NumPy and asserted
equal to the pandas result. The largest relative difference across all eleven
statistics was 4.5e-15 -- floating-point noise. The check runs as an assertion,
so the notebook fails if they ever diverge.

#### Population versus sample

![Means of 1,000 random 30-day samples against the true population mean](../figures/fig_02_sampling_distribution.png)

*The sample means form the bell shape the central limit theorem predicts,
centred on the population mean; the observed standard error (36 kWh) matches the
predicted one (37 kWh).*

65.0% of 30-day samples land within 5% of the true mean -- **but only because
the days are drawn at random across the whole year**. An audit that happened to
run in June would measure the air-conditioning season instead. This is why the
project uses the full 3.7-year record rather than a sample.

#### What distribution does power follow?

| distribution | KS statistic (lower is better) | KS p-value |
|---|---|---|
| Normal | 0.17 | < 1e-300 |
| Log-normal | 0.08 | 1.03e-300 |

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
| Academic | 76,494 | 100,236 | 32,843.90 | 25,791.30 | 7,052.50 | 27.30 | 0.51 | medium | < 1e-300 | < 1e-300 |
| Boys_Hostel | 56,112 | 62,912 | 37,595.50 | 28,557.50 | 9,038.10 | 31.60 | 0.78 | medium | < 1e-300 | < 1e-300 |
| Girls_Hostel | 57,428 | 59,758 | 16,084.90 | 13,964.60 | 2,120.30 | 15.20 | 0.51 | medium | < 1e-300 | < 1e-300 |
| Mess | 73,770 | 83,496 | 25,268.40 | 21,980.90 | 3,287.50 | 15 | 0.38 | small | < 1e-300 | < 1e-300 |
| Library | 55,934 | 62,786 | 12,435.70 | 8,135.20 | 4,300.50 | 52.90 | 0.64 | medium | < 1e-300 | < 1e-300 |
| Lecture | 22,272 | 14,658 | 3,772.90 | 1,873.50 | 1,899.30 | 101.40 | 1.21 | large | < 1e-300 | < 1e-300 |
| Facilities | 64,564 | 84,789 | 11,076 | 11,470.10 | -394.10 | -3.40 | -0.08 | negligible | 2.21e-56 | 5.68e-91 |

**Weekday versus weekend:**

| building | mean weekday (W) | mean weekend (W) | difference in means | percent difference | cohens d | effect size label | t-test p | Mann-Whitney p |
|---|---|---|---|---|---|---|---|---|
| Academic | 31,624.20 | 21,791.20 | 9,833 | 45.10 | 0.73 | medium | < 1e-300 | < 1e-300 |
| Boys_Hostel | 33,475 | 31,136.80 | 2,338.30 | 7.50 | 0.19 | negligible | 1.03e-207 | 3.77e-139 |
| Girls_Hostel | 15,243.20 | 14,390.20 | 853 | 5.90 | 0.20 | negligible | 1.97e-219 | 1.65e-184 |
| Mess | 24,259.30 | 21,668 | 2,591.20 | 12 | 0.30 | small | < 1e-300 | < 1e-300 |
| Library | 11,408 | 6,934.90 | 4,473.10 | 64.50 | 0.66 | medium | < 1e-300 | < 1e-300 |
| Lecture | 3,146.50 | 2,271.60 | 874.90 | 38.50 | 0.49 | small | 2.70e-123 | < 1e-300 |
| Facilities | 11,581.70 | 10,582.70 | 999 | 9.40 | 0.21 | small | 3.48e-217 | < 1e-300 |

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
hostel is the largest daily consumer at 731 kWh/day.*

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
| Academic | commercial | 176,730 | 0.67 | < 1e-300 | 0.65 | < 1e-300 | 0.45 |
| Boys_Hostel | residential | 119,024 | 0.65 | < 1e-300 | 0.66 | < 1e-300 | 0.42 |
| Girls_Hostel | residential | 117,186 | 0.45 | < 1e-300 | 0.43 | < 1e-300 | 0.20 |
| Mess | commercial | 157,266 | 0.41 | < 1e-300 | 0.45 | < 1e-300 | 0.17 |
| Library | commercial | 118,720 | 0.50 | < 1e-300 | 0.61 | < 1e-300 | 0.25 |
| Lecture | commercial | 36,930 | 0.31 | < 1e-300 | 0.36 | < 1e-300 | 0.10 |
| Facilities | commercial | 149,353 | 0.27 | < 1e-300 | 0.37 | < 1e-300 | 0.07 |

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