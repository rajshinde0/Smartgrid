
Phase 2 describes the data before any model is fitted.

**Attribute classification.** Every column is classified as nominal, ordinal,
binary (symmetric or **asymmetric**), discrete numeric or continuous numeric.
The asymmetric binary attributes -- `meter_off`, `is_missing`,
`was_interpolated`, `outlier_iqr`, `outlier_zscore` -- are the ones where only
the "True" state carries information; treating them as ordinary binary attributes
would overstate how similar two records are.

**Descriptive statistics.** Mean, median, mode, range, variance, standard
deviation, quartiles and IQR for every building. The mode of a continuous
variable only exists once it is binned, so power is rounded to the nearest
kilowatt first. Every statistic is then **recomputed by hand from its definition
with NumPy** -- explicit loops for the mean and the sum of squared deviations, a
sort for the median and quartiles -- and asserted equal to the pandas result.

**Population versus sample.** Treating every day of the Academic building's
record as the population, 1,000 random samples of 30 days are drawn and the
distribution of their means compared against the population mean and against the
standard error the central limit theorem predicts.

**Distribution fitting.** A Normal and a Log-normal are fitted with `scipy`,
compared by histogram overlay, Q-Q plot and Kolmogorov-Smirnov test. With
176,726 readings the KS p-value is uninformative -- it rejects any
distribution -- so the comparison is made on the **KS statistic**, which is an
effect size.

**Hypothesis tests.** Semester versus vacation and weekday versus weekend, for
every building, with both a Welch t-test (means, assumes approximate normality)
and a Mann-Whitney U test (stochastic dominance, assumes nothing). **Cohen's d is
reported beside every p-value**, because at these sample sizes significance is
guaranteed and only effect size is informative.

**Notebook:** `notebooks/02_stats_eda.ipynb`.
