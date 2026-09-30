**The definition.** I-BLEND occupancy never reads zero -- the minimum in every
building is 1, because WiFi counts idle devices -- so "energy used while empty"
is not a quantity this dataset can report. The question is asked about *low*
occupancy instead:

> **low occupancy = occupancy at or below 5% of that
> building's own 95th-percentile occupancy.**

The threshold is relative to each building's own scale because an absolute count
is not comparable between a 600-person dormitory and a 47-person facilities
block. Thresholds are reported per building.

**What counts as energy.** Only *usable* intervals: meter alive, reading present,
occupancy known. Numerator and denominator use the same set, so the share is a
true proportion of measured consumption rather than an artefact of missing data;
coverage is reported beside every figure.

**Two measures, because they answer different questions.** The *low-occupancy
energy share* depends partly on how often a building happens to be nearly empty,
which is a fact about the campus timetable. The *intensity ratio* -- mean power
when nearly empty divided by mean power overall -- isolates the building's own
behaviour, and is the number to quote.

**Sensitivity.** Because 5% is a judgement, the whole calculation is repeated for
every threshold from 0% to 20% of p95 and published as a curve.

**Comparison with the literature.** The published figures use a *clock-based*
rule, not a measured occupancy signal, so we compute their definition on our data
(outside 08:00-18:00 on weekdays) as well as our own, and compare like with like.

**Two sensitivity checks owed from earlier phases** are settled here: the Lecture
building recomputed under a 24-hour dead-meter rule (D01-07), and a
corrected-occupancy run subtracting the documented idle-device baseline (D00-06).

**Notebook:** `notebooks/05_waste.ipynb`.