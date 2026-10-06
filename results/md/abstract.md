Buildings consume electricity when nobody is using them, but measuring how much
requires fine-grained energy data and some knowledge of whether anyone was
there. The public **I-BLEND** dataset has both: 1-minute electrical readings
from nine meters across seven IIIT-Delhi buildings, paired with 10-minute counts
of WiFi-associated devices. This project presents **the first occupancy-aware
energy-waste and anomaly analysis of I-BLEND**, covering all 7 buildings over
the 3.7 years where both signals overlap (February 2014 to November 2017). The
methods are standard; the contribution is the application.

Because WiFi occupancy **never reads zero** -- the minimum in every building is
1, since idle devices stay connected -- "empty" is not a state this dataset can
report. We therefore define low occupancy relative to each building's own scale,
at or below 5% of its 95th-percentile occupancy, and publish a sensitivity curve
across every threshold from 0% to 20%.

**The headline finding is that when these buildings are at their emptiest they
still draw between 62% and 85% of their average power.** Low-occupancy
consumption accounts for 4.4% to 19.1% of measured energy depending on the
building, and in every building the base load -- the power drawn whether or not
anyone is present -- is the larger share of mean consumption. As an external
check, applying the clock-based definition of Masoso & Grobler (2010) to this
data reproduces their published 56% to within a percentage point (55.2% for the
Academic building, 55.0% for the Library).

Two further results emerged. Occupancy is a **weak predictor**: it raises
validation R-squared by only +0.106 on average over a time-only model, and
explains between 8% and 44% of the variation in power. And a controlled
experiment on synthetic anomalies shows an occupancy-aware detector is
**consistently but only marginally** better than a time-only one --
matched-budget F1 0.287 against 0.289, average precision 0.415 against 0.430 --
with the gains concentrated, as theory predicts, on sustained waste rather than
on spikes.

Separately, campus consumption **grew 32% to 48% between 2014 and 2017**, which
required explicit handling of concept drift and which reappears in the anomaly
results as a recurring false alarm.

Because the weather record shipped with I-BLEND covers March-June 2018 and does
not overlap the analysis window, outdoor temperature was taken from Delhi
airport METAR, which does. That settles what the low-occupancy consumption
actually is: cooling accounts for only **1.1%-9.0%** of it where the split is
identifiable, because the empty hours are also the cool hours, so the waste is
overwhelmingly a controls and scheduling problem rather than an air-conditioning
artefact. The same data shows roughly a quarter of occupancy's apparent
predictive value (+0.107 validation R-squared falling to +0.078) was seasonality
in disguise. The airport lies 25 km from campus, so this is a measured proxy
rather than campus weather.