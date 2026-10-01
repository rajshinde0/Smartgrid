Phase 4 builds a baseline of *expected* consumption, not a forecast.

**Models.** **A** is `power = a + b x occupancy`, fitted unscaled so its two
coefficients keep physical units -- `a` watts with nobody present, `b` extra
watts per occupant. **B** uses calendar features only (hour, weekday, month,
weekend flag, semester flag). **C** adds occupancy to B. **D** is a random
forest on C's features, capped at depth 12.

**No lag features.** Power one hour ago correlates with current power at about r
= 0.95, and including it lifts validation R-squared from 0.55 to 0.83. It is
excluded anyway, because a model that knows what the building was drawing an
hour ago has already absorbed any waste into its expectation: if the lights have
been on since 2 a.m. it confidently predicts they will still be on at 3 a.m. and
reports nothing wrong. The notebook demonstrates this rather than asserting it.

**Encoding.** `hour` and `month` are cyclic categories -- hour 23 is adjacent to
hour 0 -- so they are one-hot encoded with `drop="first"` rather than treated as
numbers. The `StandardScaler` sits **inside the scikit-learn `Pipeline`**, so it
is fitted on the training fold only; scaling before splitting would leak the
test set's mean and spread into training.

**Splitting.** Chronological 70 / 15 / 15 via `train_test_split(shuffle=False)`.
Shuffling a time series would fit the model on Thursday to predict Wednesday.
Cross-validation uses `TimeSeriesSplit` with 5 folds, which always trains on a
prefix and validates on the block immediately after.

**Concept drift, and how it is handled.** Mean power rose 32-48% across the
record (section 6.5), so the test split -- the last 15%, which is 2017 -- is the
highest-consuming period and a model fitted on 2014-2016 systematically
under-predicts it. Test metrics are reported **both** uncorrected and after a
**validation-calibrated offset**: the mean error measured on the validation
split, which lies entirely before the test split in time. That is what a
deployed system could legitimately do and involves no test data. Model
*selection* is done on validation.

**Feature selection.** A correlation filter and `SelectKBest` with
`f_regression` are reported for transparency but not used to prune: with a few
dozen encoded columns and 123,729 training rows there is no overfitting pressure
to relieve, and dropping hour dummies would cost interpretability for no gain.

**Notebook:** `notebooks/04_regression.ipynb`.