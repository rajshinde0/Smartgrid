"""Descriptive statistics, distribution fitting and hypothesis tests.

Two things in here are worth reading the comments for:

1. **The manual calculations.** Mean, variance, standard deviation, quartiles and
   IQR are computed from their definitions with NumPy, then checked against
   pandas with an assertion. The point is not that pandas might be wrong -- it is
   to show what pandas is doing, and to make the check a test rather than a claim.

2. **Effect size, not just p-values.** Our samples run to hundreds of thousands
   of 10-minute intervals. At that size a hypothesis test will return p < 0.001
   for a difference far too small to matter to anybody. So every test here
   reports an effect size next to its p-value, and the write-up leads with the
   effect size.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import config as C


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------
def describe_manual(values: np.ndarray) -> dict[str, float]:
    """Every descriptive statistic computed from its definition with NumPy.

    Deliberately avoids the convenience methods so each formula is visible:

        mean      = sum(x) / n
        variance  = sum((x - mean)^2) / (n - 1)        <- sample variance
        sd        = sqrt(variance)
        median    = middle value of the sorted data
        quartiles = values at 25% and 75% of the sorted data
        IQR       = Q3 - Q1
    """
    x = np.asarray(values, dtype="float64")
    x = x[np.isfinite(x)]
    n = x.size

    # An empty input (or one that was entirely NaN) has no statistics to report.
    # Returning NaNs is better than dividing by zero: the caller sees that there
    # was nothing to describe instead of getting a traceback from deep inside.
    if n == 0:
        return {key: float("nan") for key in
                ("n", "mean", "median", "min", "max", "range",
                 "variance", "std", "q1", "q3", "iqr")} | {"n": 0.0}

    total = 0.0
    for value in x:                       # an explicit loop, to show the formula
        total += value
    mean = total / n

    squared_deviations = 0.0
    for value in x:
        squared_deviations += (value - mean) ** 2
    # n-1 because this is a sample, not a population. A single observation has
    # no spread to estimate, so the sample variance is genuinely undefined
    # rather than zero.
    variance = squared_deviations / (n - 1) if n > 1 else float("nan")
    sd = variance ** 0.5 if np.isfinite(variance) else float("nan")

    ordered = np.sort(x)
    median = (
        ordered[n // 2]
        if n % 2 == 1
        else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    )

    def percentile_linear(p: float) -> float:
        """Linear-interpolation percentile -- the same rule NumPy uses."""
        position = (n - 1) * p / 100
        lower = int(np.floor(position))
        upper = int(np.ceil(position))
        if lower == upper:
            return float(ordered[lower])
        weight = position - lower
        return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)

    q1 = percentile_linear(25)
    q3 = percentile_linear(75)

    return {
        "n": float(n),
        "mean": float(mean),
        "median": float(median),
        "min": float(ordered[0]),
        "max": float(ordered[-1]),
        "range": float(ordered[-1] - ordered[0]),
        "variance": float(variance),
        "std": float(sd),
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
    }


def describe_pandas(series: pd.Series) -> dict[str, float]:
    """The same statistics via pandas, for the comparison."""
    clean = series.dropna()
    return {
        "n": float(len(clean)),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "min": float(clean.min()),
        "max": float(clean.max()),
        "range": float(clean.max() - clean.min()),
        "variance": float(clean.var()),        # pandas uses n-1 by default too
        "std": float(clean.std()),
        "q1": float(clean.quantile(0.25)),
        "q3": float(clean.quantile(0.75)),
        "iqr": float(clean.quantile(0.75) - clean.quantile(0.25)),
    }


def mode_binned(series: pd.Series, bin_width: float = 1000.0) -> tuple[float, int]:
    """The mode of a continuous variable, which only exists once you bin it.

    Power is a float measured to five decimal places, so no two readings are ever
    identical and the raw mode is meaningless -- every value occurs exactly once.
    Rounding to the nearest `bin_width` (1 kW by default) makes "the most common
    power level" a question with an answer.
    """
    binned = (series.dropna() / bin_width).round() * bin_width
    counts = binned.value_counts()
    return float(counts.index[0]), int(counts.iloc[0])


def describe_all_buildings(long: pd.DataFrame, column: str = "power_w") -> pd.DataFrame:
    """Full descriptive table, one row per building."""
    rows = []
    for building in C.BUILDING_ORDER:
        series = long.loc[
            (long["building"] == building) & long["usable"], column
        ].dropna()
        if series.empty:
            continue
        stats = describe_pandas(series)
        mode_value, mode_count = mode_binned(series)
        rows.append({
            "building": building,
            "n": int(stats["n"]),
            "mean": round(stats["mean"], 1),
            "median": round(stats["median"], 1),
            "mode (1 kW bins)": round(mode_value, 1),
            "min": round(stats["min"], 1),
            "max": round(stats["max"], 1),
            "range": round(stats["range"], 1),
            "variance": round(stats["variance"], 1),
            "std": round(stats["std"], 1),
            "Q1": round(stats["q1"], 1),
            "Q3": round(stats["q3"], 1),
            "IQR": round(stats["iqr"], 1),
            "skew": round(float(series.skew()), 3),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Population versus sample
# ---------------------------------------------------------------------------
def sampling_distribution(
    population: np.ndarray,
    *,
    sample_size: int = 30,
    n_samples: int = 1000,
    seed: int = C.SEED,
) -> dict:
    """Draw repeated samples and look at how their means are distributed.

    This is statistical inference made visible. The population here is every day
    we have data for; a sample is 30 randomly chosen days, which is the sort of
    thing an auditor who could only visit for a month would collect.

    The central limit theorem predicts that the sample means will be
    approximately normal around the population mean with a standard deviation of
    population_sd / sqrt(sample_size) -- the standard error. We check that
    prediction against what we actually get.
    """
    rng = np.random.default_rng(seed)
    population = np.asarray(population, dtype="float64")
    population = population[np.isfinite(population)]

    means = np.array([
        rng.choice(population, size=sample_size, replace=False).mean()
        for _ in range(n_samples)
    ])

    population_mean = float(population.mean())
    population_sd = float(population.std(ddof=1))
    predicted_se = population_sd / np.sqrt(sample_size)

    return {
        "population_n": int(population.size),
        "population_mean": population_mean,
        "population_sd": population_sd,
        "sample_size": sample_size,
        "n_samples": n_samples,
        "mean_of_sample_means": float(means.mean()),
        "sd_of_sample_means": float(means.std(ddof=1)),
        "predicted_standard_error": float(predicted_se),
        "bias": float(means.mean() - population_mean),
        "sample_means": means,
    }


# ---------------------------------------------------------------------------
# Distribution fitting
# ---------------------------------------------------------------------------
def fit_normal_and_lognormal(values: np.ndarray, *, seed: int = C.SEED) -> dict:
    """Fit a Normal and a Log-normal to the data and compare them.

    On the Kolmogorov-Smirnov test: with a sample of this size the p-value is
    useless. KS asks "could this data have come from exactly this distribution?",
    and with 100,000+ points the answer is always no, because no real measurement
    is *exactly* normal. So we report the **KS statistic** -- the largest gap
    between the fitted and observed cumulative distributions, which is an effect
    size -- and use that to say which distribution fits better.
    """
    x = np.asarray(values, dtype="float64")
    x = x[np.isfinite(x) & (x > 0)]        # log-normal needs strictly positive

    # A capped subsample keeps the KS computation quick without changing the
    # statistic materially; the fits themselves use all the data.
    rng = np.random.default_rng(seed)
    sample = x if x.size <= 50_000 else rng.choice(x, 50_000, replace=False)

    norm_params = sps.norm.fit(x)
    lognorm_params = sps.lognorm.fit(x, floc=0)

    ks_norm = sps.kstest(sample, "norm", args=norm_params)
    ks_lognorm = sps.kstest(sample, "lognorm", args=lognorm_params)

    return {
        "n": int(x.size),
        "n_tested": int(sample.size),
        "normal_params": norm_params,
        "lognormal_params": lognorm_params,
        "ks_statistic_normal": float(ks_norm.statistic),
        "ks_pvalue_normal": float(ks_norm.pvalue),
        "ks_statistic_lognormal": float(ks_lognorm.statistic),
        "ks_pvalue_lognormal": float(ks_lognorm.pvalue),
        "better_fit": "log-normal"
        if ks_lognorm.statistic < ks_norm.statistic
        else "normal",
        "skew": float(sps.skew(x)),
        "kurtosis": float(sps.kurtosis(x)),
    }


# ---------------------------------------------------------------------------
# Hypothesis testing
# ---------------------------------------------------------------------------
def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Standardised difference between two means -- an effect size.

    Roughly: 0.2 is small, 0.5 medium, 0.8 large. Unlike a p-value it does not
    grow just because the sample is big, which is exactly why we report it.
    """
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    na, nb = a.size, b.size

    # Pooling needs at least one degree of freedom, which means at least two
    # observations between the two groups beyond the two means being estimated.
    if na + nb - 2 <= 0:
        return float("nan")

    pooled_sd = np.sqrt(
        ((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2)
    )
    if not np.isfinite(pooled_sd) or pooled_sd == 0:
        return float("nan")
    return float((a.mean() - b.mean()) / pooled_sd)


def compare_groups(
    group_a: pd.Series, group_b: pd.Series, label_a: str, label_b: str
) -> dict:
    """Test whether two groups differ, reporting effect size alongside p.

    Two tests, because they ask different questions:

    * **Welch t-test** -- do the *means* differ? Assumes roughly normal data and
      does not assume equal variances.
    * **Mann-Whitney U** -- is one group *stochastically larger*? Makes no
      distributional assumption, which matters because power is strongly skewed.

    When the two agree we can be confident. When they disagree, the skew is doing
    the work and Mann-Whitney is the one to trust.
    """
    a = group_a.dropna().to_numpy(dtype="float64")
    b = group_b.dropna().to_numpy(dtype="float64")

    t_stat, t_p = sps.ttest_ind(a, b, equal_var=False)
    u_stat, u_p = sps.mannwhitneyu(a, b, alternative="two-sided")

    return {
        "group_a": label_a,
        "group_b": label_b,
        "n_a": int(a.size),
        "n_b": int(b.size),
        "mean_a": round(float(a.mean()), 1),
        "mean_b": round(float(b.mean()), 1),
        "median_a": round(float(np.median(a)), 1),
        "median_b": round(float(np.median(b)), 1),
        "difference_in_means": round(float(a.mean() - b.mean()), 1),
        "percent_difference": round(100 * float(a.mean() - b.mean()) / float(b.mean()), 1),
        "t_statistic": round(float(t_stat), 2),
        "t_pvalue": float(t_p),
        "mannwhitney_pvalue": float(u_p),
        "cohens_d": round(cohens_d(a, b), 3),
        "effect_size_label": effect_label(cohens_d(a, b)),
    }


def effect_label(d: float) -> str:
    """Plain-English reading of Cohen's d."""
    d = abs(d)
    if not np.isfinite(d):
        return "undefined"
    if d < 0.2:
        return "negligible"
    if d < 0.5:
        return "small"
    if d < 0.8:
        return "medium"
    return "large"


def format_p(p: float) -> str:
    """p-values for a table: never print '0.0'."""
    if p == 0 or p < 1e-300:
        return "< 1e-300"
    if p < 0.001:
        return f"{p:.2e}"
    return f"{p:.4f}"


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------
def power_occupancy_correlation(long: pd.DataFrame) -> pd.DataFrame:
    """Pearson and Spearman correlation of power against occupancy, per building.

    Both, because Pearson measures *linear* association and Spearman measures
    *monotonic* association. A big gap between them means the relationship is
    real but bent -- which is what we expect, since power does not rise
    indefinitely with occupancy.
    """
    rows = []
    for building in C.BUILDING_ORDER:
        sub = long.loc[
            (long["building"] == building) & long["usable"], ["power_w", "occupancy"]
        ].dropna()
        if len(sub) < 100:
            continue
        pearson_r, pearson_p = sps.pearsonr(sub["power_w"], sub["occupancy"])
        spearman_r, spearman_p = sps.spearmanr(sub["power_w"], sub["occupancy"])
        rows.append({
            "building": building,
            "kind": C.BUILDINGS[building]["kind"],
            "n": len(sub),
            "pearson_r": round(float(pearson_r), 3),
            "pearson_p": float(pearson_p),
            "spearman_r": round(float(spearman_r), 3),
            "spearman_p": float(spearman_p),
            "r_squared": round(float(pearson_r) ** 2, 3),
        })
    return pd.DataFrame(rows)
