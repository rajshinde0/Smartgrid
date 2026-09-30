Phase 3 stops treating the data as one long time series and treats it as a
collection of days.

**Building the matrix.** Because Phase 1 placed every building on a complete,
gap-free 10-minute grid, 144 consecutive values are always exactly one calendar
day. The series is trimmed to whole days and then a single NumPy `reshape` turns
it into a (days x 144) matrix -- no pivot and no loop. Days containing any gap,
or any interval flagged `meter_off`, are excluded: 1,302 of 1,356 days survive
for the Academic building.

**Reducing to hourly.** Each row is reshaped from 144 into (24, 6) and averaged
along the last axis -- a vectorized operation. The same calculation written as
three nested Python loops gives identical numbers (largest difference 0.0e+00)
and is 69x slower, which is the practical argument for vectorisation throughout
the project.

**Standardisation.** Each hour column is centred and scaled to unit variance.
Without it PCA would mostly describe the midday hours, because they vary most in
absolute terms; with it, the components describe the *shape* of a day rather
than its size.

**PCA by hand.** The covariance matrix of the standardised data is formed
explicitly, its eigenvalues and eigenvectors taken with `np.linalg.eig`, sorted
by eigenvalue and used to project the data. `sklearn.decomposition.PCA` is then
run on the same matrix and the two asserted equal. Eigenvector signs are aligned
before comparison, because an eigenvector multiplied by -1 is still a valid
eigenvector and two correct implementations can legitimately disagree on sign.

**Clustering.** k-means with k = 4 on the first three component scores, seed
42. Clusters are named from measurable properties of their average
profile -- overall level, the size of the night-to-day rise, and the hour of the
peak -- rather than by eye, so the names are reproducible.

**Relation to prior work.** Day-profile clustering on this campus has already
been published (Rashid & Singh, 2018). This phase is supporting analysis, not
part of the novelty claim.

**Notebook:** `notebooks/03_pca.ipynb`.