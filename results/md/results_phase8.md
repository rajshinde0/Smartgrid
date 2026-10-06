#### The weather data behaves like weather

| building | 0-15C | 15-20C | 20-25C | 25-30C | 30-35C | 35-40C | 40-50C | hot vs mild % | r(power, temp) |
|---|---|---|---|---|---|---|---|---|---|
| Academic | 19.90 | 22.70 | 24.30 | 27.30 | 34.10 | 38.70 | 41.80 | 51.40 | 0.42 |
| Boys_Hostel | 27.90 | 28.10 | 31.20 | 35.80 | 35.80 | 31.30 | 26.10 | 12 | 0.14 |
| Girls_Hostel | 12.60 | 13 | 13.90 | 16 | 16.40 | 15.10 | 13.40 | 16.20 | 0.23 |
| Mess | 18.70 | 20.50 | 21 | 23.10 | 27.40 | 28.70 | 27.20 | 33.10 | 0.37 |
| Library | 9.90 | 9.80 | 8.80 | 8.90 | 11 | 12.40 | 13.20 | 25.30 | 0.12 |
| Lecture | 4.10 | 3.50 | 3.40 | 3.10 | 3.10 | 2.80 | 2.10 | -12.40 | -0.18 |
| Facilities | 8.50 | 8.10 | 8.90 | 11 | 13.20 | 15 | 17.20 | 61.90 | 0.48 |

![Mean power against outdoor temperature, and the cost of hotter weather](../figures/fig_08_temperature_response.png)

*Facilities climbs +62% from mild to hot weather while Lecture falls -12% -- a
cooled building and a switched-off one behaving exactly as they should.*

The check passes convincingly. **Facilities (+62%)** and Academic climb steeply
with temperature; **Lecture (-12%)** does the opposite, which is the negative
control working -- a building that is mostly switched off cannot respond to
heat. The hostels rise then fall above 35 °C, which is also right: their hottest
hours fall in the vacation, when the students have gone home.

#### Was occupancy's contribution partly summer heat?

| building | B (time) | C (+occ) | E (+weather) | F (+both) | occupancy alone (C-B) | occupancy given weather (F-E) | weather alone (E-B) |
|---|---|---|---|---|---|---|---|
| Academic | 0.50 | 0.51 | 0.51 | 0.47 | 0.01 | -0.04 | 0.01 |
| Boys_Hostel | 0.23 | 0.42 | 0.28 | 0.46 | 0.19 | 0.18 | 0.05 |
| Girls_Hostel | -0.62 | -0.22 | -0.52 | -0.14 | 0.41 | 0.37 | 0.11 |
| Mess | 0.32 | 0.33 | 0.37 | 0.38 | 0.01 | 0.00 | 0.05 |
| Library | -0.27 | -0.06 | -0.17 | -0.03 | 0.20 | 0.14 | 0.09 |
| Lecture | -0.20 | -0.20 | -0.20 | -0.20 | 0.01 | 0.01 | 0.00 |
| Facilities | 0.28 | 0.22 | 0.46 | 0.34 | -0.07 | -0.12 | 0.18 |

![What occupancy is worth before and after accounting for weather](../figures/fig_08_occupancy_vs_weather.png)

*Occupancy's mean contribution falls from +0.107 to +0.078 in validation
R-squared once temperature is known.*

**Yes -- about a quarter of it.** Occupancy and temperature are both seasonal,
and the campus empties in exactly the months Delhi is hottest. Fitted on
identical rows, occupancy is worth **+0.107** in validation R-squared when the
weather is unknown and only **+0.078** once it is known -- a **27% shrinkage**.
Weather alone is worth **+0.070**, comparable to occupancy.

The per-building pattern splits the campus cleanly. The two dormitories and the
Library stay genuinely occupancy-driven even with weather known. **Facilities is
the opposite**: occupancy is worth **-0.118** there once temperature is known,
while weather alone is worth **+0.175**. That resolves something Phase 4 could
only note -- Facilities was the building where adding occupancy made the model
*worse*, and the reason is that it is a weather-driven building where occupancy
was standing in for a season it only partly tracks.

#### How much of the waste is cooling?

| building | n | base c | r2 | mean power kw | schedule kw | weather kw | weather share pct |
|---|---|---|---|---|---|---|---|
| Academic | 11,191 | 27 | 0.19 | 21.37 | 20.52 | 0.85 | 4 |
| Boys_Hostel | 7,015 | 16 | 0.28 | 24.52 | 22.30 | 2.21 | 9 |
| Girls_Hostel | 7,250 | 30 | 0.21 | 11.92 | 11.79 | 0.13 | 1.10 |
| Mess | 19,227 | 30 | 0.22 | 17.51 | 17.29 | 0.22 | 1.30 |

![What nearly-empty buildings are actually drawing power for](../figures/fig_08_waste_decomposition.png)

*Cooling accounts for 1.1%-9.0% of low-occupancy consumption where it can be
measured. The rest is drawn regardless of the weather.*

**The limitation turns out to have been mild, and that strengthens the main
finding.** Where the split can be measured, cooling accounts for between **1.1%
and 9.0%** of low-occupancy consumption, a mean of about **4%**. The other
91-99% is drawn regardless of the weather.

The reason is almost obvious once stated: **the empty hours are the cool
hours.** Nearly half of all low-occupancy intervals fall between midnight and 6
a.m. A building sitting at 20 kW at 4 a.m. in February is not air conditioning
anything. So the waste measured in Phase 5 is overwhelmingly a **controls and
scheduling problem**, not a cooling artefact -- a more actionable conclusion
than the limitation feared, and one that has now been tested rather than
assumed.

**Two buildings cannot be measured, and saying so matters.** In Library,
Lecture, Facilities the low-occupancy intervals are themselves seasonal: both
are closed during the hot vacation months, so within that sample high
temperature coincides with a shut building and the fitted slope comes out
negative. That is a confound between season and usage, not a cooling response,
and a negative "cooling share" would be nonsense. They are reported as not
identifiable, with the reason.

#### Does weather explain the Facilities vacation anomaly?

Phase 2 found Facilities to be the **only** building using more power on
low-activity days than on high-activity ones -- every other building falls by
13% to 50% -- and offered Delhi's heat as the explanation. Comparing the two
periods *within the same 28-34 °C band* settles it: a raw gap of +3.0% on this
sample becomes **-4.9%** once temperature is held constant, so holding the
weather fixed does not merely remove the gap, it reverses it. The building does
not draw more because the campus is empty; it draws more because the days when
the campus is quiet are the days when Delhi is hottest, and Facilities is the
most weather-sensitive building on site.

#### Does weather help an anomaly detector?

| detector | roc auc | average precision |
|---|---|---|
| OW (time+occ+weather) | 0.70 | 0.43 |
| T (time) | 0.67 | 0.41 |
| W (time+weather) | 0.67 | 0.42 |

Scored on the same synthetic anomalies as Phase 6, with the same seed and the
same one-sided rule. This addresses the caveat Phase 6 had to leave standing --
that its real-data findings could not be told apart from hot days.