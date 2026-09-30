Phase 1 turns the raw CSVs into one clean, merged, 10-minute table per building.

**Invalid values.** Three rules are applied while reading, and every fix is
counted: `power` outside 0 to 200 kW becomes `NaN`; `voltage` outside 180-270 V
becomes `NaN`; `power_factor` keeps its magnitude with the sign retained as a
separate flag (decision D00-02).

**Dead meters.** Power exactly 0 for more than 6 continuous hours is flagged
`meter_off`. The test uses the *maximum* power within each 10-minute block, so a
block counts as zero only if all ten of its 1-minute readings were zero; blocks
with no readings break a run rather than extending it.

**Outliers are flagged, never deleted.** Both IQR (Tukey fences at 1.5x) and
Z-score (|z| > 3) are computed on live readings only and stored as columns.
Deleting them would remove exactly the abnormal events Phase 6 is built to
detect.

**Resampling.** 1-minute readings are averaged into 10min blocks to match the
native resolution of the occupancy data. Because a block can straddle a chunk
boundary, each chunk contributes per-block *sums and counts* which are added
across chunks before the mean is formed -- exactly equal to a single-pass mean.
Blocks are then placed on a complete time grid, so missing intervals are
explicit rather than absent.

**Merging.** Energy is joined to occupancy on the timestamp with an inner join.
Every occupancy timestamp already falls exactly on a 10-minute boundary, so no
tolerance matching is needed. For the two dormitories, mains and UPS are kept as
separate columns and also summed; the sum is `NaN` if either meter is missing.

**Gap filling.** Gaps of at most 30 minutes (3 blocks) are filled by time
interpolation and marked `was_interpolated`. Longer gaps are left missing.

**Features.** `hour`, `minute_of_day`, `month`, `year`, `weekday` (an *ordered*
categorical so Monday sorts before Tuesday), `is_weekend`, `is_semester` /
`is_vacation`, power lagged 1 hour and 1 day, 24-hour rolling mean and standard
deviation (computed with `closed="left"` so the current block is excluded and no
future information leaks), and `kwh = watts / 1000 x 10/60`.

**Semester flag.** Taken from the **official IIIT-Delhi calendar published with
I-BLEND** (one CSV per year, 2013-2017, in the same figshare collection as the
data), which marks each day as a working day or not and as high- or
low-activity. This replaced an approximation used in an earlier version of the
project, which agreed with the published calendar on only about two-thirds of
days (decision D01-03). It also supplies an `is_working_day` model feature that
knows about public holidays, which a weekend flag cannot see.

**Notebook:** `notebooks/01_data_prep.ipynb`.