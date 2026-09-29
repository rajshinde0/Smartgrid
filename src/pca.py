"""Daily load profiles as a matrix, and principal component analysis of them.

The idea is to stop treating the data as one long time series and start treating
it as a **collection of days**. Each day becomes a row of 144 numbers (one per
10-minute block), so a year is a 365 x 144 matrix. PCA then asks: what are the
few basic shapes that, combined, reproduce most of those days?

Everything here is NumPy rather than pandas, because the operations -- reshaping,
slicing a block out of a matrix, averaging groups of columns without a loop --
are array operations, and doing them in pandas would hide what is going on.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

BLOCKS_PER_DAY = 144        # 24 hours at 10-minute resolution
BLOCKS_PER_HOUR = 6


def day_matrix(
    df: pd.DataFrame,
    value_col: str = "power_w",
    *,
    require_usable: bool = True,
) -> tuple[np.ndarray, pd.DatetimeIndex, np.ndarray]:
    """Turn a 10-minute series into a (days x 144) matrix by reshaping.

    This works only because Phase 1 put every building on a complete, gap-free
    10-minute grid: 144 consecutive values really are one calendar day. We trim
    to whole days first (start at the first midnight, end at the last 23:50) and
    then a single `reshape` does the rest -- no loop, no pivot.

    Returns the matrix, the dates of its rows, and a boolean mask saying which
    rows are complete enough to analyse.
    """
    series = df[value_col]

    # Trim to whole days.
    starts = np.flatnonzero((df.index.hour == 0) & (df.index.minute == 0))
    ends = np.flatnonzero((df.index.hour == 23) & (df.index.minute == 50))
    if len(starts) == 0 or len(ends) == 0:
        raise ValueError("series does not contain a whole day")
    first, last = int(starts[0]), int(ends[-1])

    values = series.to_numpy(dtype="float64")[first : last + 1]
    n_days = values.size // BLOCKS_PER_DAY
    values = values[: n_days * BLOCKS_PER_DAY]

    # The reshape: one row per day, one column per 10-minute block.
    matrix = values.reshape(n_days, BLOCKS_PER_DAY)

    dates = pd.DatetimeIndex(
        df.index[first : first + n_days * BLOCKS_PER_DAY : BLOCKS_PER_DAY]
    ).normalize()

    complete = ~np.isnan(matrix).any(axis=1)
    if require_usable and "meter_off" in df.columns:
        off = (
            df["meter_off"].to_numpy(dtype=bool)[first : last + 1][
                : n_days * BLOCKS_PER_DAY
            ].reshape(n_days, BLOCKS_PER_DAY)
        )
        complete &= ~off.any(axis=1)

    return matrix, dates, complete


def to_hourly_vectorized(matrix: np.ndarray) -> np.ndarray:
    """Collapse 144 ten-minute columns to 24 hourly columns, without a loop.

    Reshape each row from 144 into (24, 6) -- 24 hours of 6 blocks each -- and
    average along the last axis. One operation, no Python-level iteration.
    """
    n_days = matrix.shape[0]
    return matrix.reshape(n_days, 24, BLOCKS_PER_HOUR).mean(axis=2)


def to_hourly_loop(matrix: np.ndarray) -> np.ndarray:
    """The same result with explicit Python loops, purely for the timing comparison."""
    n_days = matrix.shape[0]
    out = np.empty((n_days, 24))
    for row in range(n_days):
        for hour in range(24):
            total = 0.0
            for block in range(BLOCKS_PER_HOUR):
                total += matrix[row, hour * BLOCKS_PER_HOUR + block]
            out[row, hour] = total / BLOCKS_PER_HOUR
    return out


def standardize(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Centre and scale each column. Returns the scaled matrix, means and SDs.

    PCA is defined in terms of variance, so a column measured in larger numbers
    would dominate purely because of its units. Here every column is watts, but
    the midday columns still vary far more than the 4 a.m. columns, and without
    scaling PCA would mostly describe the midday hours.
    """
    means = matrix.mean(axis=0)
    sds = matrix.std(axis=0, ddof=1)
    sds = np.where(sds == 0, 1.0, sds)     # a constant column cannot be scaled
    return (matrix - means) / sds, means, sds


def pca_by_hand(scaled: np.ndarray) -> dict:
    """PCA computed from its definition: covariance matrix, then eigenvectors.

    The steps are exactly the textbook ones:

      1. covariance matrix of the standardised data (which is the correlation
         matrix of the original data)
      2. its eigenvalues and eigenvectors
      3. sort by eigenvalue, largest first -- that ordering *is* the ranking of
         components by how much variance they explain
      4. project the data onto the eigenvectors to get the scores

    We use `np.linalg.eig` because that is the general routine. For a symmetric
    matrix like a covariance matrix, `np.linalg.eigh` is both faster and more
    numerically stable, and it returns real values directly -- `eig` can return
    a tiny imaginary part from rounding, which is why the real part is taken
    below.
    """
    n = scaled.shape[0]
    covariance = (scaled.T @ scaled) / (n - 1)

    eigenvalues, eigenvectors = np.linalg.eig(covariance)
    eigenvalues = np.real(eigenvalues)
    eigenvectors = np.real(eigenvectors)

    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    scores = scaled @ eigenvectors

    return {
        "covariance": covariance,
        "eigenvalues": eigenvalues,
        "eigenvectors": eigenvectors,       # columns are the components
        "scores": scores,
        "explained_variance_ratio": eigenvalues / eigenvalues.sum(),
        "cumulative_variance": np.cumsum(eigenvalues) / eigenvalues.sum(),
    }


def align_signs(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Flip the columns of `a` so its component signs match `b`.

    An eigenvector multiplied by -1 is still an eigenvector of the same
    eigenvalue, so "the" first component is only defined up to sign. Two correct
    implementations can disagree on it. Aligning signs before comparing is
    therefore part of a fair comparison, not a fudge.
    """
    out = a.copy()
    for j in range(min(a.shape[1], b.shape[1])):
        if np.dot(a[:, j], b[:, j]) < 0:
            out[:, j] *= -1
    return out


def day_labels(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Calendar context for each day in the matrix, for colouring the plots."""
    from . import features

    vacation = features.is_vacation(dates)
    return pd.DataFrame(
        {
            "date": dates,
            "weekday": dates.day_name(),
            "day_of_week": dates.dayofweek,
            "is_weekend": dates.dayofweek >= 5,
            "month": dates.month,
            "year": dates.year,
            "is_vacation": vacation,
            "period": np.where(vacation, "vacation", "semester"),
        }
    ).set_index("date")


def name_clusters(centroids_hourly: np.ndarray) -> list[str]:
    """Give each k-means cluster a plain-English name from its average shape.

    Named from three readable properties of the centroid: its overall level
    relative to the other clusters, how much it rises from night to day, and
    when its peak falls.
    """
    names = []
    levels = centroids_hourly.mean(axis=1)
    rank = np.argsort(np.argsort(levels))        # 0 = lowest overall level

    for i, profile in enumerate(centroids_hourly):
        night = profile[0:6].mean()              # 00:00-05:59
        day = profile[9:18].mean()               # 09:00-17:59
        swing = (day - night) / night if night > 0 else np.inf
        peak_hour = int(np.argmax(profile))

        if swing < 0.15:
            shape = "flat all day"
        elif peak_hour < 12:
            shape = "morning peak"
        elif peak_hour >= 18:
            shape = "evening peak"
        else:
            shape = "daytime peak"

        level = ["lowest", "low", "high", "highest"][
            min(rank[i], 3) if len(centroids_hourly) > 3 else min(rank[i], 1) * 3
        ]
        names.append(f"{level} load, {shape}")
    return names


def reconstruction_error(scaled: np.ndarray, eigenvectors: np.ndarray, k: int) -> np.ndarray:
    """How badly each day is described by only the first k components.

    A day that the main components cannot reproduce is an unusual day. This is a
    whole-day anomaly score, and it is a useful cross-check on the interval-level
    detector built in Phase 6.
    """
    components = eigenvectors[:, :k]
    reconstructed = (scaled @ components) @ components.T
    return np.sqrt(((scaled - reconstructed) ** 2).mean(axis=1))
