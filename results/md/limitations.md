#### 1. Occupancy is a device count, not a count of people

This is the deepest limitation in the project and it shapes every result. The
occupancy signal counts devices associated with a building's WiFi access points.
A phone left charging in an empty room is counted; a visitor with no device is
not. The dataset authors estimate the over-count at roughly 20 devices per
building and about 50 in the Academic building.

The concrete consequence is that **the minimum occupancy in every building is 1,
never 0**, so this project cannot measure "energy used while empty" and instead
measures "energy used at low occupancy" against a stated relative threshold.
Section 6.6's corrected-occupancy check shows that subtracting the documented
baseline raises the low-occupancy share in every building, which means **our
headline figures are a conservative lower bound** rather than an overstatement.

#### 2. No weather data covering the analysis period

I-BLEND *does* ship a weather record -- `IIITD_and_airport_data.csv`, with
temperature and humidity measured both at IIIT-Delhi and at Delhi airport. It is
unusable here for one decisive reason: **it covers 1 March to 29 June 2018, and
our analysis window is February 2014 to November 2017.** The overlap is exactly
**zero rows**. It was published to quantify how well a campus sensor agrees with
the airport station, not as a weather history for the energy record.

So the limitation stands, but in a sharper form than "there is no weather data".
In Delhi this matters more than it would almost anywhere else, because the long
summer vacation coincides with the hottest months. Phase 2 found that Facilities
uses **17% more** power during vacation than during term, and the Academic
building slightly more, which is almost certainly air conditioning rather than
people.

So some of what we call low-occupancy consumption is **cooling an empty
building**. That is still waste, but a different kind with a different remedy --
setback temperatures rather than switching off lights -- and we cannot separate
the two. Weather for 2014-2017 would have to come from an external source such
as a Delhi airport METAR archive; it remains the single most valuable addition
this project could receive.

#### 3. The injected anomalies are synthetic

Every anomaly used to score the detectors in section 9 was **created by us** and
injected into a copy of the test data with a recorded seed, because no real
fault on this campus was ever labelled. They are a measuring instrument for
comparing two detectors, and **no injected event corresponds to anything that
happened at IIIT-Delhi**.

This means the detector comparison is only as realistic as our idea of what
waste looks like. We modelled it as a sustained +15-30% lift during
low-occupancy periods; if real waste on this campus takes a different shape, the
ranking could differ. The real-data findings are reported separately and
described only as patterns worth inspecting.

#### 4. Very uneven data coverage

Usable coverage ranges from **18.9%** to **90.5%**. The Lecture building is the
extreme case: its meter is flagged off for **25,488 hours**, leaving only 18.9%
of its intervals usable, so every Lecture figure rests on a much smaller sample
than the others. The Boys hostel, Girls hostel and Library each lose several
consecutive months to meter outages. This is a smaller sample, not a biased
measurement -- but conclusions about those buildings are correspondingly less
certain.

#### 5. A dead meter and a building switched off look identical

Both read exactly 0 W, and no rule based on the power value alone can tell them
apart. The Lecture building's zero runs form two clear populations -- nightly
stretches around 13 hours and outages lasting up to 46 days -- and the specified
6-hour rule catches both. Section 6.6's 24-hour sensitivity check shows this is
worth about 1.3 percentage points on the Lecture figure. Real: small, and
quantified rather than hidden.

#### 6. The semester calendar is now official, but it is a daily flag

Semester and vacation come from the **official IIIT-Delhi calendar published
with I-BLEND**, one CSV per year covering 2013-2017. This is ground truth rather
than an estimate, and it also supplies an `is_working_day` flag that knows about
public holidays.

Two caveats remain. First, it is a **daily** label: a day is high- or
low-activity as a whole, so a detector cannot use it to distinguish 9 a.m. from
9 p.m. on the same day -- that job falls to the hour features. Second, the
official `L` (low activity) label bundles vacations, weekends and public
holidays together, so "vacation" in this report means "low-activity day" rather
than "inside a vacation window"; the two are not identical.

*A correction worth recording:* an earlier version of this project approximated
the calendar, having searched the project GitHub site -- which hosts only the
website assets and the reading scripts -- and wrongly concluded no calendar
existed. It is published on figshare alongside the data. The approximation
agreed with the real calendar on only about two-thirds of days. Everything in
this report now uses the published calendar (decision D01-03).

#### 7. The base load is partly an extrapolation

Model A estimates base load as the power a fitted line predicts at zero
occupancy. For buildings whose occupancy never approaches zero -- the two
dormitories especially -- that point lies far outside the observed data, and the
estimate departs from the directly measured night-time median by up to **50%**.
Section 6.6 reports both, ranks buildings on the *measured* quantity, and flags
where the modelled one should not be trusted.

#### 8. The models are baselines, not forecasts, and they age

Models B and C deliberately exclude lag features, which costs a great deal of
accuracy (validation R-squared would rise from about 0.29 to over 0.9 with a
one-hour lag). That is the price of a baseline that can detect sustained waste
rather than absorbing it. Separately, campus consumption grew 32-48% across the
record, and the power-occupancy correlation itself weakened over time in the
Academic building (r fell from 0.71 to 0.45). A model of this campus **needs
periodic refitting**; section 9 shows what happens when it does not get it -- a
schedule change in August 2017 is re-reported as an anomaly every morning for
months.

#### 9. Seven buildings, one campus, one climate

Every finding here describes **these seven buildings in these years**.
Generalising to other campuses would require assuming Delhi's climate, this
institution's routine and this building stock are representative, and we do not
assume that. Where published figures from other campuses are quoted, they are
offered as context, not as validation.

#### 10. No sub-metering

Each building has one meter (two for the dormitories). We can say a building
draws 20 kW at 3 a.m.; we cannot say how much of that is lighting, air
conditioning, servers or lifts. That is exactly the information an energy
manager would need to act on these findings, and it is the natural next step.