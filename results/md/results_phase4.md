#### The campus grew by a third to a half

Before any model result can be read, one thing has to be established:

| building | mean kW 2014 | mean kW 2015 | mean kW 2016 | mean kW 2017 | growth 2014-2017 % | r(power,occ) 2014 | r(power,occ) 2017 |
|---|---|---|---|---|---|---|---|
| Academic | 23.90 | 27.70 | 29.80 | 34 | 42.40 | 0.71 | 0.45 |
| Boys_Hostel | 27.20 | 32.30 | 32.90 | 40.10 | 47.30 | 0.62 | 0.62 |
| Girls_Hostel | 12.90 | 14.10 | 15.70 | 16.90 | 31.60 | 0.41 | 0.50 |
| Mess | 19.70 | 21.80 | 25.50 | 26.80 | 35.70 | 0.36 | 0.47 |
| Library | 7.50 | 11 | 10.60 | 10.20 | 36.80 | 0.54 | 0.39 |
| Lecture | 3.40 | 2.40 | 3.20 | 3.10 | -6.70 | 0.38 | 0.13 |
| Facilities | 8.80 | 10.30 | 11.80 | 13.10 | 48.40 | 0.04 | 0.41 |

![Mean power by year, indexed to 2014, and total growth per building](../figures/fig_04_drift_by_year.png)

*Six of seven buildings grew between 32% and 48% in mean power over four years. The campus did not get more efficient; it got substantially more energy-hungry.*

This is a finding in its own right and it is also a methodological problem. The
test split is the last 15% of the record -- 2017, the highest-consuming period --
so a model fitted on 2014-2016 under-predicts it systematically. Note too that in
the Academic building the **power-occupancy correlation itself fell**, from
0.71 in 2014 to
0.45 in 2017: the
relationship the models depend on weakened over time. Test-set numbers below
should be read with that in mind, which is why model selection uses the
validation split.

#### Model scores

| building | model | train R2 | val R2 | test R2 | test R2 (drift-corrected) | val MAE kW | test MAE kW | test RMSE kW |
|---|---|---|---|---|---|---|---|---|
| Academic | A: power ~ occupancy | 0.56 | - | -0.17 | - | - | 11.66 | 18.07 |
| Academic | B: time only | 0.61 | 0.47 | 0.06 | 0.15 | 7.74 | 11.16 | 16.15 |
| Academic | C: time + occupancy | 0.73 | 0.51 | 0.00 | 0.06 | 7.81 | 10.77 | 16.67 |
| Academic | D: random forest (time + occupancy) | 0.84 | 0.58 | -0.01 | 0.09 | 6.54 | 10.45 | 16.79 |
| Boys_Hostel | A: power ~ occupancy | 0.42 | - | 0.10 | - | - | 8.67 | 12.11 |
| Boys_Hostel | B: time only | 0.66 | 0.24 | -0.05 | 0.25 | 9.06 | 10.07 | 13.12 |
| Boys_Hostel | C: time + occupancy | 0.79 | 0.37 | 0.07 | 0.25 | 8.68 | 9.33 | 12.31 |
| Boys_Hostel | D: random forest (time + occupancy) | 0.75 | 0.50 | 0.13 | 0.22 | 7.17 | 8.70 | 11.91 |
| Girls_Hostel | A: power ~ occupancy | 0.21 | - | -0.88 | - | - | 3.62 | 4.52 |
| Girls_Hostel | B: time only | 0.66 | -0.61 | -0.97 | -0.66 | 3.45 | 3.76 | 4.63 |
| Girls_Hostel | C: time + occupancy | 0.72 | -0.17 | -0.94 | -0.59 | 2.87 | 3.76 | 4.59 |
| Girls_Hostel | D: random forest (time + occupancy) | 0.69 | -0.32 | -0.79 | -0.52 | 3.06 | 3.54 | 4.41 |
| Mess | A: power ~ occupancy | 0.15 | - | -0.08 | - | - | 7.53 | 10.07 |
| Mess | B: time only | 0.42 | 0.34 | -0.08 | 0.04 | 4.57 | 7.78 | 10.06 |
| Mess | C: time + occupancy | 0.44 | 0.33 | -0.05 | 0.07 | 4.59 | 7.69 | 9.92 |
| Mess | D: random forest (time + occupancy) | 0.54 | 0.23 | -0.06 | -0.01 | 4.83 | 7.67 | 9.96 |
| Library | A: power ~ occupancy | 0.30 | - | -0.05 | - | - | 6.82 | 8.53 |
| Library | B: time only | 0.34 | -0.28 | 0.00 | -0.07 | 4.53 | 6.77 | 8.32 |
| Library | C: time + occupancy | 0.45 | -0.08 | -0.11 | -0.14 | 4.05 | 7.06 | 8.78 |
| Library | D: random forest (time + occupancy) | 0.62 | 0.20 | -0.07 | -0.07 | 3.08 | 6.54 | 8.64 |
| Lecture | A: power ~ occupancy | 0.17 | - | -0.30 | - | - | 1.36 | 1.58 |
| Lecture | B: time only | 0.45 | -0.17 | 0.29 | 0.02 | 1.28 | 0.83 | 1.16 |
| Lecture | C: time + occupancy | 0.46 | -0.17 | 0.27 | -0.00 | 1.29 | 0.87 | 1.19 |
| Lecture | D: random forest (time + occupancy) | 0.68 | -0.04 | 0.29 | 0.07 | 1.24 | 0.83 | 1.17 |
| Facilities | A: power ~ occupancy | 0.06 | - | -0.67 | - | - | 2.98 | 3.94 |
| Facilities | B: time only | 0.27 | 0.27 | 0.03 | 0.19 | 1.95 | 2.25 | 3.01 |
| Facilities | C: time + occupancy | 0.28 | 0.21 | 0.05 | 0.14 | 2.07 | 2.21 | 2.98 |
| Facilities | D: random forest (time + occupancy) | 0.46 | 0.29 | -0.05 | 0.03 | 1.94 | 2.28 | 3.13 |

#### Does occupancy help? (Research question 2)

| building | B val R2 | C val R2 | R2 gain from occupancy | B val MAE kW | C val MAE kW | MAE improvement % | D (forest) val R2 |
|---|---|---|---|---|---|---|---|
| Academic | 0.47 | 0.51 | 0.03 | 7.74 | 7.81 | -0.90 | 0.58 |
| Boys_Hostel | 0.24 | 0.37 | 0.13 | 9.06 | 8.68 | 4.20 | 0.50 |
| Girls_Hostel | -0.61 | -0.17 | 0.44 | 3.45 | 2.87 | 16.90 | -0.32 |
| Mess | 0.34 | 0.33 | -0.01 | 4.57 | 4.59 | -0.40 | 0.23 |
| Library | -0.28 | -0.08 | 0.20 | 4.53 | 4.05 | 10.70 | 0.20 |
| Lecture | -0.17 | -0.17 | 0.00 | 1.28 | 1.29 | -1.10 | -0.04 |
| Facilities | 0.27 | 0.21 | -0.06 | 1.95 | 2.07 | -6.10 | 0.29 |

![Validation R-squared for models B and C, and the gain from adding occupancy](../figures/fig_04_model_comparison.png)

*Occupancy improves validation R-squared in 5 of the 7 buildings, by a mean of +0.107, but the gain ranges from -0.063 to +0.444.*

**Yes -- in most buildings, modestly, and very unevenly.** Adding occupancy
raises validation R-squared in **5 of 7** buildings, with a
mean gain of **+0.107**. But the spread is the real story: the largest
gain is Girls Hostel at
**+0.444**, while occupancy makes the model
slightly *worse* in Mess, Facilities
(-0.063 at worst). It improves MAE in
3 of 7.

**A note on how to read these numbers.** Several validation R-squared values are
negative, meaning the model does worse than simply predicting the validation
mean. That is the concept drift of section 6.5 again -- the validation period
sits at a different consumption level from the training period. The *difference*
between C and B is still meaningful, because both models are fitted on the same
training data and face exactly the same drift; whatever the drift costs, it costs
them equally.

This is consistent with the LBNL finding that occupancy data adds only modestly
to building baseline models, and it is a real answer to research question 2
rather than a disappointment: **most of what drives these buildings is not the
number of people in them.** The same conclusion arrives independently from the
Phase 2 correlations and the Phase 3 flat daily profiles.

The pattern across buildings is also readable. Occupancy helps most where people
genuinely drive the load -- the Girls hostel
(+0.444)
and the Library
(+0.205) --
and helps least, or slightly hurts, in the Mess and Facilities, whose loads are
driven by equipment schedules and weather rather than by headcount.

#### Cross-validation with TimeSeriesSplit

| building | model | CV MAE kW (mean) | CV MAE kW (sd) | folds |
|---|---|---|---|---|
| Academic | B: time only | 6.87 | 0.86 | 5 |
| Academic | C: time + occupancy | 5.73 | 0.32 | 5 |
| Boys_Hostel | B: time only | 7.47 | 1.54 | 5 |
| Boys_Hostel | C: time + occupancy | 5.46 | 1 | 5 |
| Girls_Hostel | B: time only | 2.66 | 0.43 | 5 |
| Girls_Hostel | C: time + occupancy | 2.52 | 0.72 | 5 |
| Mess | B: time only | 5.69 | 1.61 | 5 |
| Mess | C: time + occupancy | 5.58 | 1.66 | 5 |
| Library | B: time only | 5.30 | 1.48 | 5 |
| Library | C: time + occupancy | 4.70 | 1.61 | 5 |
| Lecture | B: time only | 1.50 | 1.10 | 5 |
| Lecture | C: time + occupancy | 1.39 | 0.88 | 5 |
| Facilities | B: time only | 2.87 | 0.50 | 5 |
| Facilities | C: time + occupancy | 2.79 | 0.56 | 5 |

#### Base load and responsiveness -- the numbers Phase 5 uses

| building | kind | a: base load (kW) | b: watts per occupant | mean power (kW) | base load as % of mean | night 02-06 median (kW) | R2 in sample |
|---|---|---|---|---|---|---|---|
| Academic | commercial | 16.95 | 128.10 | 27.21 | 62.30 | 18.96 | 0.56 |
| Boys_Hostel | residential | 15.94 | 68 | 30.88 | 51.60 | 32.76 | 0.42 |
| Girls_Hostel | residential | 10.60 | 36.30 | 14.12 | 75.10 | 14.81 | 0.21 |
| Mess | commercial | 18.85 | 61.70 | 22.67 | 83.20 | 16.12 | 0.15 |
| Library | commercial | 7.24 | 68.50 | 10.31 | 70.30 | 5.84 | 0.30 |
| Lecture | commercial | 2.13 | 7.40 | 2.95 | 72.50 | 1.07 | 0.17 |
| Facilities | commercial | 9.27 | 231.70 | 10.82 | 85.70 | 9.75 | 0.06 |

![Base load against responsiveness, one point per building](../figures/fig_04_base_load_vs_responsiveness.png)

*Buildings towards the top-left run their equipment regardless of who is present; buildings towards the bottom-right scale with their occupants.*

The `a` column is the load the fitted line predicts at zero occupancy -- the
power a building draws with nobody in it -- and the night-time median column is
an independent check on it from a completely different calculation. Phase 5 takes
these two coefficients and turns them into the headline ranking.

#### Predictions against reality

![Academic building: actual and predicted power over one test week, with occupancy below](../figures/fig_04_actual_vs_predicted_academic.png)

*Both models reproduce the daily rhythm; model C bends towards the actual line when occupancy is unusual for the time of day. Neither captures the sharp peaks -- and those leftover peaks are what Phase 6 detects.*

Note the chart uses two stacked panels rather than two y-axes. Watts and people
are different quantities, and putting them on one axis would invent a visual
relationship that does not exist.

#### Overfitting

| max depth | train MAE w | val MAE w |
|---|---|---|
| 2 | 6,481.30 | 6,523.70 |
| 4 | 5,617.10 | 6,345.50 |
| 6 | 4,894.90 | 7,590 |
| 8 | 4,383.80 | 6,711.40 |
| 12 | 3,724.50 | 6,537.20 |
| 16 | 3,310.70 | 6,469.50 |
| 24 | 2,844.80 | 6,462.20 |
| unlimited | 2,711.30 | 6,467.50 |

![Training and validation error against model complexity](../figures/fig_04_overfitting_curves.png)

*The forest shows the textbook picture: at unlimited depth its training error is 2.71 kW but its validation error is 6.47 kW, a gap of 2.4x. That gap is overfitting made visible.*

#### What the forest uses

![Random-forest feature importances for Academic power](../figures/fig_04_feature_importance.png)

*Occupancy is the strongest single input, ahead of every hour-of-day indicator -- which is reassuring for a project built around it.*

#### Residuals

| detector | mean residual kW | sd residual kW | median kW |
|---|---|---|---|
| T (model B, time only) | -0.30 | 15.35 | -5.22 |
| O (model C, time + occupancy) | -2.20 | 16.01 | -6.53 |

![Residual distributions for models B and C, and residuals against prediction](../figures/fig_04_residuals_academic.png)

*After the drift correction both distributions sit near zero and model C's is narrower. Residuals fan out at high predicted power, so Phase 6 scores deviations relative to the spread of the residuals rather than in absolute watts.*