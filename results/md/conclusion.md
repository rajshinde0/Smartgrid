#### What we set out to do

We asked three questions of the I-BLEND campus dataset: how much energy is used
while buildings are nearly empty, how well occupancy and time predict power, and
whether an occupancy-aware anomaly detector beats a time-only one.

#### What we found

**1. Nearly-empty buildings still draw most of their average power.** Between
62% and 85% of it, depending on the building. In every one of the seven, the
base load -- the part drawn whether or not anyone is present -- is the larger
share of consumption. Applying the published literature's own clock-based
definition to our data reproduces its headline figure to within a percentage
point, which is strong evidence the measurement is sound.

**2. Occupancy is a weak predictor of power.** It explains between 8% and 44% of
the variation, and adds only +0.107 to validation R-squared over a time-only
model. This arrived independently from three different directions -- correlation
analysis, regression, and the flat daily profiles PCA produced -- and it agrees
with the published LBNL result.

**3. An occupancy-aware detector is better, but only just.** All five fair
comparisons favour it, by one to three percentage points each, with the largest
gains on exactly the anomaly type where occupancy ought to help. A detector
cannot exploit information that is not there, and finding (2) explains finding
(3).

**4. Two things we did not go looking for.** Campus consumption grew 32-48% in
four years. And the most extreme "anomalies" in the real data turned out to be a
single recurring schedule change being re-reported every morning -- a reminder
that a detector on a fixed historical baseline decays.

#### What it means

The practical implication is not "install occupancy sensing". Occupancy data
turned out to add little that the clock does not already provide on this campus.
The implication is that **the fixed part of these buildings' load is where the
opportunity is**. A building that draws 74% of its average power with nobody in
it is not failing to respond to occupancy -- it is running equipment on a
schedule that ignores occupancy entirely, and that is a controls and
commissioning problem rather than a sensing problem.

The Library is the proof that it need not be so: it drops 65% at weekends and
runs at 62% when nearly empty, the best on campus. Whatever the Library does,
the others could do.

#### Future scope

1. **Add weather data.** The single highest-value addition. It would separate
   cooling load from occupancy-driven load and turn "some of this is air
   conditioning an empty building" from a caveat into a number.
2. **Sub-metering.** One meter per building can say *how much* is wasted but never
   *what* is wasting it. Circuit-level metering would make the findings
   actionable.
3. **Rolling re-baselining.** Section 9 shows a fixed historical model decaying
   into constant false alarms. A model refitted on a trailing window would adapt
   to schedule changes instead of re-reporting them.
4. **Occupancy calibration.** A short manual count against the WiFi signal would
   replace the paper's approximate 20-device offset with a measured one, and turn
   our conservative lower bound into a point estimate.
5. **Cost and carbon.** Every kWh in this report could be priced and given an
   emissions factor, which is what turns an analysis into a business case.
6. **The methods we deliberately left out.** Gradient boosting, deep sequence
   models, real-time streaming and a fault-diagnosis layer were all out of scope
   here. None of them would change the headline finding, which is an accounting
   result rather than a modelling one -- but they would matter for a deployed
   system.