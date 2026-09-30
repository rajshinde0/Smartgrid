Exploration produced four findings that shaped everything after it.

1. **The working period is set by occupancy, not energy.** Energy covers
   Aug 2013 – Dec 2017,
   occupancy only Feb 2014 – Nov 2017.
   The project analyses the overlap.

2. **"Empty" is not measurable in this dataset.** Minimum occupancy is 1 in all
   seven buildings (section 4.7). The main question had to be re-specified around a
   relative low-occupancy threshold, with a sensitivity curve to show how much the
   answer depends on where that threshold is put.

3. **Negative `power_factor` is a sign convention, not corrupt data.** It affects
   0.01%–67.55% of readings depending on the meter. The decisive
   evidence is that the range is exactly −0.999 to +1.000 *while `power` itself is
   never negative*: if current were genuinely flowing backwards, power would be
   negative too. Treating these as invalid would have deleted more than half of the
   Library record. We keep the magnitude and retain the sign as a separate flag.

4. **Coverage is much worse than row counts suggest.** Row coverage ranges from
   71.5% to
   99.5%, and the worst meters lose
   whole months at a time -- the largest single gap is
   5,311 hours
   (221 days). The Lecture meter
   additionally reads exactly 0 W for 81.7% of its record, which is a
   dead meter rather than an idle building.