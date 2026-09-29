
### How many shapes does a day have?

| component | variance explained % | cumulative % |
|---|---|---|
| PC1 | 55 | 55 |
| PC2 | 21 | 75.90 |
| PC3 | 10.90 | 86.90 |
| PC4 | 4.30 | 91.20 |
| PC5 | 3 | 94.10 |
| PC6 | 1.30 | 95.40 |

The first component alone accounts for **55.0%** of the variation
between days, and the first three for **86.9%**. An
Academic-building day is therefore well described by three numbers instead of 24.

![Scree plot for Academic building daily load profiles](../figures/fig_03_scree_academic.png)

*PC1 explains 55.0% and the first three together 86.9% -- a real reduction in dimensionality, not a cosmetic one.*

### What the components mean

![The three main shapes of a day, Academic building](../figures/fig_03_components_academic.png)

*PC1 has weights all of one sign -- it is the overall level of the day. PC2 changes sign across the clock -- it contrasts daytime against night. PC3 shifts the timing of the peak.*

**PC1 is 'how much'** -- its weights all share a sign, so a day scoring high is
above average at every hour. **PC2 is 'day versus night'** -- its weights change
sign, contrasting working hours with the night, so a high score means a peaky
day. **PC3 is the timing of the peak.** This is the usual pattern in building
energy data, which is itself a check that the matrix and the arithmetic are
behaving.

### Do days separate by calendar without being told the calendar?

![Days in PC1-PC2 space, coloured by weekend and by vacation](../figures/fig_03_pc_scatter_academic.png)

*Weekends separate clearly along PC2 -- flatter days with less contrast between working hours and night. PCA was never given the day of the week.*

![The same days in three dimensions](../figures/fig_03_pc3d_academic.png)

*Adding PC3 brings the displayed variance to 87%.*

Yes -- and the two calendar facts separate along *different* components. Weekends
sit lower on **PC2**: nobody arrives in the morning, so the daytime rise never
happens and the day is flat. Semester and vacation separate along **PC1**
instead, and less cleanly, because vacation days are not uniformly quieter --
some are among the highest-consuming days in the record, which is the summer
cooling load again.

### Day types

| cluster | name | days | mean power (kW) | night floor (kW) | midday (kW) | % weekend | % vacation |
|---|---|---|---|---|---|---|---|
| 0 | high load, daytime peak | 450 | 35.40 | 22.10 | 54.10 | 4.40 | 36.70 |
| 1 | lowest load, flat all day | 284 | 18.10 | 17.30 | 19.90 | 63.40 | 19 |
| 2 | highest load, morning peak | 80 | 41.20 | 36.20 | 59 | 7.50 | 18.80 |
| 3 | low load, morning peak | 488 | 26.10 | 20.10 | 35.50 | 33.40 | 22.10 |

![k-means day types: average profile of each cluster, and the clusters in component space](../figures/fig_03_day_types_academic.png)

*The clusters correspond to recognisable kinds of day rather than arbitrary groupings -- their weekend and vacation shares differ sharply even though k-means never saw the calendar.*

### Which days are unusual?

![Reconstruction error per day, and the most and least typical days](../figures/fig_03_reconstruction_error_academic.png)

*A day the three main components cannot reproduce is an unusual day. This whole-day score cross-checks the interval-level detector built in Phase 6.*

### The same analysis on a dormitory

![Boys Hostel: scree plot, component shapes and days in component space](../figures/fig_03_pca_boys_hostel.png)

*The first three components explain 93.0% here, and the component shapes differ from the Academic building's -- the structure is a property of each building, not a universal.*

### Every building's daily shape, side by side

![The shape of an average day, each building scaled to its own mean](../figures/fig_03_day_shapes_all_buildings.png)

*Scaling out size leaves only shape. Academic and Library rise in the morning; the hostels do the opposite, lowest at midday and highest in the evening; the Mess shows meal-time peaks; Facilities is nearly a flat line.*

Buildings needing fewer than 30 complete days are absent, and their absence is a
result rather than an omission: drawing an average daily shape requires days that
run midnight to midnight with a live meter throughout.

| building | complete days available |
|---|---|
| Academic | 1,302 |
| Facilities | 1,119 |
| Mess | 1,105 |
| Library | 915 |
| Boys_Hostel | 828 |
| Girls_Hostel | 808 |
| Lecture | 1 |

**The Facilities line is the most important thing in this chart.** A building
whose daily profile is flat is consuming almost independently of the time of day
-- and therefore almost independently of whether anyone is inside. That is the
Phase 5 result appearing in advance, in a completely different kind of analysis.
