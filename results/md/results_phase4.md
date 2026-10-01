#### The campus grew by a third to a half

Before any model result can be read, one thing has to be established:

| building | mean kW 2014 | mean kW 2015 | mean kW 2016 | mean kW 2017 | growth 2014-2017 % | r(power,occ) 2014 | r(power,occ) 2017 |
|---|---|---|---|---|---|---|---|
| Academic | 23.90 | 27.70 | 29.80 | 34 | 42.40 | 0.71 | 0.45 |
| Boys_Hostel | 27.20 | 32.30 | 32.90 | 39.80 | 46.20 | 0.61 | 0.62 |
| Girls_Hostel | 12.90 | 14.10 | 15.70 | 16.90 | 31.60 | 0.41 | 0.50 |
| Mess | 19.70 | 21.80 | 25.50 | 26.80 | 35.70 | 0.36 | 0.47 |
| Library | 7.50 | 11 | 10.60 | 10.20 | 36.80 | 0.54 | 0.39 |
| Lecture | 3.40 | 2.40 | 3.20 | 3.20 | -6.60 | 0.38 | 0.13 |
| Facilities | 8.80 | 10.30 | 11.80 | 13.10 | 48.40 | 0.04 | 0.40 |

![Mean power by year, indexed to 2014, and total growth per building](../figures/fig_04_drift_by_year.png)

*Six of seven buildings grew between 32% and 48% in mean power over four years.
The campus did not get more efficient; it got substantially more energy-hungry.*

This is a finding in its own right and it is also a methodological problem. The
test split is the last 15% of the record -- 2017, the highest-consuming period
-- so a model fitted on 2014-2016 under-predicts it systematically. Note too
that in the Academic building the **power-occupancy correlation itself fell**,
from 0.71 in 2014 to 0.45 in 2017: the relationship the models depend on
weakened over time. Test-set numbers below should be read with that in mind,
which is why model selection uses the validation split.

#### Model scores

| building | model | train R2 | val R2 | test R2 | test R2 (drift-corrected) | val MAE kW | test MAE kW | test RMSE kW |
|---|---|---|---|---|---|---|---|---|
| Academic | A: power ~ occupancy | 0.56 | - | -0.17 | - | - | 11.66 | 18.06 |
| Academic | B: time only | 0.62 | 0.51 | 0.09 | 0.17 | 7.57 | 11.18 | 15.94 |
| Academic | C: time + occupancy | 0.73 | 0.52 | 0.01 | 0.07 | 7.71 | 10.73 | 16.59 |
| Academic | D: random forest (time + occupancy) | 0.84 | 0.59 | 0.01 | 0.11 | 6.53 | 10.36 | 16.60 |
| Boys_Hostel | A: power ~ occupancy | 0.41 | - | 0.11 | - | - | 8.59 | 12.04 |
| Boys_Hostel | B: time only | 0.68 | 0.23 | 0.01 | 0.29 | 9.13 | 9.69 | 12.70 |
| Boys_Hostel | C: time + occupancy | 0.78 | 0.42 | 0.08 | 0.27 | 8.26 | 9.36 | 12.25 |
| Boys_Hostel | D: random forest (time + occupancy) | 0.74 | 0.59 | 0.16 | 0.22 | 6.52 | 8.56 | 11.66 |
| Girls_Hostel | A: power ~ occupancy | 0.21 | - | -0.88 | - | - | 3.61 | 4.52 |
| Girls_Hostel | B: time only | 0.69 | -0.63 | -0.84 | -0.65 | 3.47 | 3.62 | 4.47 |
| Girls_Hostel | C: time + occupancy | 0.73 | -0.23 | -0.86 | -0.57 | 2.96 | 3.68 | 4.50 |
| Girls_Hostel | D: random forest (time + occupancy) | 0.69 | -0.42 | -0.71 | -0.50 | 3.20 | 3.46 | 4.31 |
| Mess | A: power ~ occupancy | 0.15 | - | -0.08 | - | - | 7.53 | 10.07 |
| Mess | B: time only | 0.43 | 0.32 | -0.04 | 0.06 | 4.65 | 7.65 | 9.89 |
| Mess | C: time + occupancy | 0.44 | 0.33 | -0.03 | 0.07 | 4.61 | 7.61 | 9.83 |
| Mess | D: random forest (time + occupancy) | 0.54 | 0.22 | -0.05 | 0 | 4.86 | 7.64 | 9.92 |
| Library | A: power ~ occupancy | 0.30 | - | -0.05 | - | - | 6.82 | 8.53 |
| Library | B: time only | 0.36 | -0.26 | 0.04 | -0.03 | 4.49 | 6.73 | 8.17 |
| Library | C: time + occupancy | 0.46 | -0.06 | -0.09 | -0.12 | 4.02 | 7.03 | 8.72 |
| Library | D: random forest (time + occupancy) | 0.62 | 0.16 | -0.08 | -0.08 | 3.11 | 6.60 | 8.67 |
| Lecture | A: power ~ occupancy | 0.17 | - | -0.32 | - | - | 1.35 | 1.57 |
| Lecture | B: time only | 0.48 | -0.20 | 0.23 | -0.13 | 1.26 | 0.83 | 1.20 |
| Lecture | C: time + occupancy | 0.49 | -0.19 | 0.22 | -0.13 | 1.27 | 0.86 | 1.21 |
| Lecture | D: random forest (time + occupancy) | 0.70 | -0.05 | 0.22 | -0.06 | 1.23 | 0.82 | 1.21 |
| Facilities | A: power ~ occupancy | 0.06 | - | -0.67 | - | - | 2.97 | 3.94 |
| Facilities | B: time only | 0.27 | 0.30 | 0.03 | 0.20 | 1.92 | 2.24 | 3 |
| Facilities | C: time + occupancy | 0.28 | 0.24 | 0.04 | 0.16 | 2.03 | 2.21 | 2.99 |
| Facilities | D: random forest (time + occupancy) | 0.44 | 0.33 | -0.07 | 0.04 | 1.87 | 2.32 | 3.16 |

#### Does occupancy help? (Research question 2)

| building | B val R2 | C val R2 | R2 gain from occupancy | B val MAE kW | C val MAE kW | MAE improvement % | D (forest) val R2 |
|---|---|---|---|---|---|---|---|
| Academic | 0.51 | 0.52 | 0.01 | 7.57 | 7.71 | -1.90 | 0.59 |
| Boys_Hostel | 0.23 | 0.42 | 0.19 | 9.13 | 8.26 | 9.50 | 0.59 |
| Girls_Hostel | -0.63 | -0.23 | 0.40 | 3.47 | 2.96 | 14.50 | -0.42 |
| Mess | 0.32 | 0.33 | 0.01 | 4.65 | 4.61 | 0.90 | 0.22 |
| Library | -0.26 | -0.06 | 0.20 | 4.49 | 4.02 | 10.50 | 0.16 |
| Lecture | -0.20 | -0.19 | 0.01 | 1.26 | 1.27 | -0.70 | -0.05 |
| Facilities | 0.30 | 0.24 | -0.06 | 1.92 | 2.03 | -5.80 | 0.33 |

![Validation R-squared for models B and C, and the gain from adding occupancy](../figures/fig_04_model_comparison.png)

*Occupancy improves validation R-squared in 6 of the 7 buildings, by a mean of
+0.106, but the gain ranges from -0.062 to +0.395.*

**Yes -- in most buildings, modestly, and very unevenly.** Adding occupancy
raises validation R-squared in **6 of 7** buildings, with a mean gain of
**+0.106**. But the spread is the real story: the largest gain is Girls Hostel
at **+0.395**, while occupancy makes the model slightly *worse* in Facilities
(-0.062 at worst). It improves MAE in 4 of 7.

**A note on how to read these numbers.** Several validation R-squared values are
negative, meaning the model does worse than simply predicting the validation
mean. That is the concept drift of section 6.5 again -- the validation period
sits at a different consumption level from the training period. The *difference*
between C and B is still meaningful, because both models are fitted on the same
training data and face exactly the same drift; whatever the drift costs, it
costs them equally.

This is consistent with the LBNL finding that occupancy data adds only modestly
to building baseline models, and it is a real answer to research question 2
rather than a disappointment: **most of what drives these buildings is not the
number of people in them.** The same conclusion arrives independently from the
Phase 2 correlations and the Phase 3 flat daily profiles.

The pattern across buildings is also readable. Occupancy helps most where people
genuinely drive the load -- the Girls hostel (+0.395) and the Library (+0.198)
-- and helps least, or slightly hurts, in the Mess and Facilities, whose loads
are driven by equipment schedules and weather rather than by headcount.

#### Cross-validation with TimeSeriesSplit

| building | model | CV MAE kW (mean) | CV MAE kW (sd) | folds |
|---|---|---|---|---|
| Academic | B: time only | 6.82 | 0.85 | 5 |
| Academic | C: time + occupancy | 5.77 | 0.35 | 5 |
| Boys_Hostel | B: time only | 7.16 | 1.80 | 5 |
| Boys_Hostel | C: time + occupancy | 5.03 | 0.26 | 5 |
| Girls_Hostel | B: time only | 2.45 | 0.45 | 5 |
| Girls_Hostel | C: time + occupancy | 2.48 | 0.66 | 5 |
| Mess | B: time only | 5.65 | 1.61 | 5 |
| Mess | C: time + occupancy | 5.58 | 1.66 | 5 |
| Library | B: time only | 5.12 | 1.27 | 5 |
| Library | C: time + occupancy | 4.55 | 1.45 | 5 |
| Lecture | B: time only | 1.46 | 1.05 | 5 |
| Lecture | C: time + occupancy | 1.37 | 0.87 | 5 |
| Facilities | B: time only | 2.88 | 0.58 | 5 |
| Facilities | C: time + occupancy | 2.80 | 0.64 | 5 |

#### Base load and responsiveness -- the numbers Phase 5 uses

| building | kind | a: base load (kW) | b: watts per occupant | mean power (kW) | base load as % of mean | night 02-06 median (kW) | R2 in sample |
|---|---|---|---|---|---|---|---|
| Academic | commercial | 16.95 | 128.10 | 27.21 | 62.30 | 18.96 | 0.56 |
| Boys_Hostel | residential | 16.32 | 66.60 | 30.87 | 52.90 | 32.67 | 0.41 |
| Girls_Hostel | residential | 10.60 | 36.30 | 14.12 | 75.10 | 14.82 | 0.21 |
| Mess | commercial | 18.85 | 61.70 | 22.67 | 83.20 | 16.12 | 0.15 |
| Library | commercial | 7.24 | 68.50 | 10.31 | 70.30 | 5.84 | 0.30 |
| Lecture | commercial | 2.14 | 7.30 | 2.95 | 72.50 | 1.07 | 0.17 |
| Facilities | commercial | 9.27 | 232 | 10.82 | 85.60 | 9.75 | 0.06 |

![Base load against responsiveness, one point per building](../figures/fig_04_base_load_vs_responsiveness.png)

*Buildings towards the top-left run their equipment regardless of who is
present; buildings towards the bottom-right scale with their occupants.*

The `a` column is the load the fitted line predicts at zero occupancy -- the
power a building draws with nobody in it -- and the night-time median column is
an independent check on it from a completely different calculation. Phase 5
takes these two coefficients and turns them into the headline ranking.

#### Predictions against reality

![Academic building: actual and predicted power over one test week, with occupancy below](../figures/fig_04_actual_vs_predicted_academic.png)

*Both models reproduce the daily rhythm; model C bends towards the actual line
when occupancy is unusual for the time of day. Neither captures the sharp peaks
-- and those leftover peaks are what Phase 6 detects.*

Note the chart uses two stacked panels rather than two y-axes. Watts and people
are different quantities, and putting them on one axis would invent a visual
relationship that does not exist.

#### Overfitting

| max depth | train MAE w | val MAE w |
|---|---|---|
| 2 | 6,481.20 | 6,519.60 |
| 4 | 5,642.90 | 6,243.50 |
| 6 | 4,935 | 7,190.10 |
| 8 | 4,416.70 | 6,694.40 |
| 12 | 3,746.40 | 6,533.90 |
| 16 | 3,322.20 | 6,408.10 |
| 24 | 2,838.10 | 6,406 |
| unlimited | 2,688.30 | 6,423.90 |

![Training and validation error against model complexity](../figures/fig_04_overfitting_curves.png)

*The forest shows the textbook picture: at unlimited depth its training error is
2.69 kW but its validation error is 6.42 kW, a gap of 2.4x. That gap is
overfitting made visible.*

#### What the forest uses

![Random-forest feature importances for Academic power](../figures/fig_04_feature_importance.png)

*Occupancy is the strongest single input, ahead of every hour-of-day indicator
-- which is reassuring for a project built around it.*

#### Residuals

| detector | mean residual kW | sd residual kW | median kW |
|---|---|---|---|
| T (model B, time only) | -0.21 | 15.18 | -4.68 |
| O (model C, time + occupancy) | -2.10 | 15.93 | -6.36 |

![Residual distributions for models B and C, and residuals against prediction](../figures/fig_04_residuals_academic.png)

*After the drift correction both distributions sit near zero and model C's is
narrower. Residuals fan out at high predicted power, so Phase 6 scores
deviations relative to the spread of the residuals rather than in absolute
watts.*