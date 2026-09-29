
**The single most important finding in exploration: occupancy never reaches zero.**
The minimum count in every one of the seven buildings is **1**, not 0. This is the
WiFi over-counting the dataset authors warn about -- idle phones and laptops stay
associated with an access point long after their owner has left. The consequence is
structural, not cosmetic: *the main research question cannot be phrased as "energy
used while the building is empty", because no such reading exists in this dataset.*

It must instead be "energy used while occupancy is **low**", against a threshold we
state openly. We use a threshold relative to each building's own scale:
**low occupancy = occupancy at or below 5% of that building's
95th-percentile occupancy.** An absolute cut-off would be
meaningless across buildings whose normal populations differ by a factor of twenty.

Two buildings do not fit the standard recipe, and both are reported rather than
quietly dropped:

- **Facilities (SRB)** is small: its occupancy runs 1 to
  47 with a 95th percentile of 18, so the
  threshold works out to **0.90** -- below its own
  minimum observed count of 1. **No reading qualifies**
  (0.00% of rows). We keep the identical
  rule for every building rather than bending the definition for one, report this
  cell honestly as "no qualifying intervals", and read Facilities off the
  threshold-sensitivity curve in Phase 5 instead.
- **Lecture (LCB)** has 60.4% of its
  readings under the threshold, and its meter reads exactly 0 W for
  81.7% of the record. Its waste figure is therefore computed only
  over the periods when the meter was demonstrably alive, with the coverage
  reported alongside.

Reassuringly, **every occupancy timestamp sits exactly on a 10-minute boundary**,
so energy and occupancy line up without any fuzzy time matching.
