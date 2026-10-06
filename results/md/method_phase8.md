Phase 8 closes the project's largest limitation.

**The data.** I-BLEND ships a weather file, but it covers March-June 2018 and
has no overlap with the analysis window. Outdoor conditions therefore come from
**METAR** -- the routine report every airport issues -- for Delhi Indira Gandhi
International (ICAO `VIDP`), archived free by Iowa State University. It covers
2014-02-15 to 2017-11-03 at roughly 30-minute resolution, already in
Asia/Kolkata, and reaches **96.13%** of the analysis intervals. It is resampled
onto the 10-minute grid by time interpolation, filling only short gaps under the
same whole-run rule used for power.

**The honest caveat.** VIDP is about **25 km** from the campus. Airport weather
is not campus weather. This replaces an *unmeasured* confound with a *measured
proxy* -- better, not perfect, and every number below carries that.

**Cooling degree hours.** Building power does not track raw temperature so much
as `max(0, T - T_base)`: below the base a building needs no cooling, above it
load rises roughly linearly. `T_base` is **fitted per building** by scanning
16-30 °C and keeping the value that explains most variation, rather than being
assigned a textbook setpoint.

**A physics check before any result.** Mean power is tabulated against
temperature band per building. Cooled buildings must rise with heat and a
building that is mostly switched off must not. Nothing downstream would have
been reported had that failed.

**The 2x2.** Four models are fitted on **identical rows** -- the 94% with a
temperature -- so no comparison is confounded by a different sample: B (time), C
(time + occupancy), E (time + weather), F (both). `C - B` is what occupancy is
worth with weather unknown; `F - E` is what it is worth once weather is known.
The published B and C are untouched; these are re-fits for comparison only.

**The decomposition.** Within low-occupancy intervals, `power = intercept +
slope x CDH + hour-of-day effects`. Hour of day **must** be controlled for:
nearly half of all low-occupancy intervals fall between midnight and 6 a.m.,
when the building is both empty and cool, and without hour dummies the fit
confuses "cooler at night" with "needs less cooling" -- R-squared roughly
trebles once it is included. Buildings whose fitted slope comes out negative are
reported as **not identifiable**, with the reason, rather than given a
nonsensical negative cooling share.

**Notebook:** `notebooks/08_weather.ipynb`.