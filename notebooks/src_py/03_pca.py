"""Phase 3 -- PCA on daily load profiles. Percent-format source."""

# %% [markdown]
# # SMARTGRID-X -- Phase 3: Principal component analysis of daily load profiles
#
# **What this notebook does.** So far we have treated the data as one long time
# series. Here we treat it as a **collection of days**: each day becomes a row of
# 144 numbers, one per 10-minute block. PCA then asks a simple question --
#
# > out of all the different-looking days, how many basic *shapes* do you really
# > need to reproduce most of them?
#
# **Why it is worth doing.** If two or three shapes account for most days, then
# a building's behaviour is much simpler than 144 numbers a day suggests, and
# days that do *not* fit those shapes are unusual and worth looking at.
#
# **An honesty note on novelty.** Clustering daily load profiles on this campus
# has already been published (Rashid & Singh, *Monitor*, 2018). This phase is
# **supporting analysis, not a novelty claim**. It is here because it describes
# the data usefully and because it feeds a whole-day anomaly score that
# cross-checks Phase 6.
#
# Everything is done in NumPy rather than pandas, because reshaping, slicing a
# block out of a matrix, and averaging groups of columns without a loop are array
# operations -- doing them in pandas would hide the mechanics.

# %%
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers the 3d projection)
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from IPython.display import display

from src import config as C
from src import build, pca as P, report, viz

viz.setup_style()
C.ensure_dirs()
pd.set_option("display.width", 200)
np.random.seed(C.SEED)

TARGET = "Academic"
academic, _ = build.build_building(TARGET, verbose=False)
print(f"{TARGET}: {len(academic):,} ten-minute intervals")

# %% [markdown]
# ## Step 1: from a time series to a matrix of days
#
# Phase 1 put every building on a **complete, gap-free 10-minute grid**. That is
# what makes this step a single `reshape` rather than a complicated pivot: 144
# consecutive values genuinely are one calendar day, every time.
#
# We trim to whole days first (start at the first midnight, end at the last
# 23:50), then reshape the flat array of `n` values into `(n / 144, 144)`.

# %%
matrix, dates, complete = P.day_matrix(academic, "power_w")

print(f"flat series          : {len(academic):,} values")
print(f"reshaped to          : {matrix.shape[0]:,} days x {matrix.shape[1]} blocks")
print(f"days with no gaps and a live meter: {complete.sum():,} "
      f"({100 * complete.mean():.1f}%)")
print(f"date range           : {dates[0]:%Y-%m-%d} to {dates[-1]:%Y-%m-%d}")
print(f"\ndtype {matrix.dtype}, {matrix.nbytes / 1024:.0f} KB, "
      f"{matrix.ndim} dimensions")

# %% [markdown]
# ### Indexing, slicing and matrix subsetting
#
# A 2-D NumPy array is indexed `array[rows, columns]`, and both parts can be
# slices. For our matrix that has a direct physical meaning: **rows are days,
# columns are times of day**, so a slice of both selects a block of the calendar
# crossed with a block of the clock.

# %%
# A single element: one day, one 10-minute block.
print(f"matrix[0, 0]      one value  -> {matrix[0, 0]:,.0f} W "
      f"({dates[0]:%Y-%m-%d} at 00:00)")

# A whole row: one complete day.
print(f"matrix[10]        one day    -> shape {matrix[10].shape}")

# A whole column: the same time of day, across every day. We use nanmean here,
# because the full matrix still contains the incomplete days -- a plain mean()
# would return nan, which is a useful reminder that the gaps are still present
# and have to be excluded deliberately rather than by accident.
print(f"matrix[:, 72]     12:00 on every day -> shape {matrix[:, 72].shape}, "
      f"mean {np.nanmean(matrix[:, 72]):,.0f} W "
      f"(plain mean() would give {matrix[:, 72].mean():.0f} -- the gaps are real)")

# A block: the first 7 days, working hours only (09:00 to 17:59 is blocks 54-107).
week_working = matrix[0:7, 54:108]
print(f"matrix[0:7, 54:108]  first week, working hours -> shape "
      f"{week_working.shape}, mean {np.nanmean(week_working):,.0f} W")

# Boolean indexing: every complete day.
clean = matrix[complete]
print(f"matrix[complete]  usable days -> shape {clean.shape}")

# Compare two blocks of the clock on the same days.
night = matrix[complete][:, 0:36]      # 00:00-05:59
midday = matrix[complete][:, 60:84]    # 10:00-13:59
print(f"\nmean night power  (00:00-06:00): {np.nanmean(night):,.0f} W")
print(f"mean midday power (10:00-14:00): {np.nanmean(midday):,.0f} W")
print(f"the night floor is {100 * np.nanmean(night) / np.nanmean(midday):.0f}% "
      f"of the midday level")

# %% [markdown]
# **Takeaway.** That last number is the Phase 5 question in one line: with the
# building essentially empty, it still draws roughly **half** of its midday
# power.

# %% [markdown]
# ## Step 2: vectorized operations, and why they matter
#
# 144 columns is more resolution than the component shapes need, so we average
# each group of 6 blocks into one hour, giving a 24-column matrix.
#
# There are two ways to do it. The **vectorized** way reshapes each row from 144
# into (24, 6) and averages along the last axis -- one operation, no Python-level
# iteration. The **loop** way does the same arithmetic with three nested `for`
# loops. They produce identical numbers; we time both to show what vectorisation
# actually buys.

# %%
X = matrix[complete]

start = time.perf_counter()
hourly_vec = P.to_hourly_vectorized(X)
time_vec = time.perf_counter() - start

start = time.perf_counter()
hourly_loop = P.to_hourly_loop(X)
time_loop = time.perf_counter() - start

print(f"vectorized : {time_vec * 1000:9.2f} ms")
print(f"Python loop: {time_loop * 1000:9.2f} ms")
print(f"speed-up   : {time_loop / time_vec:9.0f}x")
print(f"\nidentical results: {np.allclose(hourly_vec, hourly_loop)}")
print(f"largest difference: {np.abs(hourly_vec - hourly_loop).max():.2e}")

assert np.allclose(hourly_vec, hourly_loop)

# %% [markdown]
# **Takeaway.** Same arithmetic, same answer, orders of magnitude apart in time.
# The loop runs the arithmetic in Python; the vectorized version hands the whole
# operation to compiled code that works on the array at once. On this small
# matrix it does not matter, but it is the reason the whole project is feasible:
# if every operation in Phase 1 had been written as a Python loop over 2.3 million
# rows, the pipeline would take hours instead of seconds.

# %% [markdown]
# ## Step 3: standardising before PCA
#
# PCA is defined in terms of variance, so it will pay most attention to whatever
# varies most. Every column here is in watts, so units are not the problem -- but
# the midday columns still swing far more than the 4 a.m. columns, and without
# scaling PCA would essentially just describe the middle of the day.
#
# Standardising each column (subtract its mean, divide by its standard deviation)
# puts every hour on an equal footing, so the components describe the *shape* of
# a day rather than its overall size.

# %%
scaled, col_means, col_sds = P.standardize(hourly_vec)
print(f"standardised matrix: {scaled.shape}")
print(f"column means after scaling (should be ~0): {np.abs(scaled.mean(axis=0)).max():.2e}")
print(f"column SDs after scaling  (should be ~1): "
      f"{np.abs(scaled.std(axis=0, ddof=1) - 1).max():.2e}")

profile = pd.DataFrame({
    "hour": range(24),
    "mean power (W)": col_means.round(0),
    "std dev (W)": col_sds.round(0),
})
display(profile.T)

# %% [markdown]
# ## Step 4: PCA by hand, then checked against scikit-learn
#
# We compute PCA from its definition:
#
# 1. the **covariance matrix** of the standardised data
# 2. its **eigenvalues and eigenvectors** with `np.linalg.eig`
# 3. sort by eigenvalue, largest first -- that ordering *is* the ranking of
#    components by variance explained
# 4. **project** the data onto the eigenvectors to get the scores
#
# Then we run `sklearn.decomposition.PCA` on the same matrix and assert the two
# agree. One subtlety: an eigenvector multiplied by -1 is still an eigenvector of
# the same eigenvalue, so "the" first component is only defined up to sign. Two
# correct implementations can disagree about it, so signs are aligned before
# comparing -- that is part of a fair comparison, not a fudge.

# %%
hand = P.pca_by_hand(scaled)
print(f"covariance matrix: {hand['covariance'].shape}")
print(f"eigenvalues (first 6): {np.round(hand['eigenvalues'][:6], 4)}")

sk = PCA()
sk_scores = sk.fit_transform(scaled)

check = pd.DataFrame({
    "component": [f"PC{i + 1}" for i in range(6)],
    "by hand -- variance explained": hand["explained_variance_ratio"][:6].round(5),
    "sklearn -- variance explained": sk.explained_variance_ratio_[:6].round(5),
})
check["difference"] = (
    check["by hand -- variance explained"] - check["sklearn -- variance explained"]
)
display(check)

aligned = P.align_signs(hand["eigenvectors"], sk.components_.T)
assert np.allclose(hand["explained_variance_ratio"], sk.explained_variance_ratio_)
assert np.allclose(aligned[:, :5], sk.components_.T[:, :5], atol=1e-8)
print("\nHand-computed PCA matches scikit-learn exactly "
      "(eigenvalues and, after sign alignment, eigenvectors).")

# %% [markdown]
# ## Step 5: the scree plot -- how many components do we need?

# %%
n_show = 12
ratio = hand["explained_variance_ratio"][:n_show]
cumulative = hand["cumulative_variance"][:n_show]

fig, ax = plt.subplots(figsize=(10, 4.2))
bars = ax.bar(range(1, n_show + 1), 100 * ratio, color=viz.CATEGORICAL[0],
              label="variance explained by this component")
ax.set_xlabel("Principal component")
ax.set_ylabel("% of variance explained")
ax.set_xticks(range(1, n_show + 1))
ax.set_title(f"Scree plot -- {TARGET} building daily load profiles")

for i, (bar, value) in enumerate(zip(bars[:4], ratio[:4])):
    ax.annotate(f"{100 * value:.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, 100 * value),
                xytext=(0, 4), textcoords="offset points", ha="center",
                fontsize=9, color=viz.INK_SECONDARY)

ax.annotate(
    f"first 3 components together explain {100 * cumulative[2]:.1f}%",
    xy=(4.2, 100 * ratio[0] * 0.75), fontsize=9, color=viz.INK_SECONDARY,
)
ax.legend(loc="upper right")
viz.save_fig(fig, f"fig_03_scree_{TARGET.lower()}")

scree_table = pd.DataFrame({
    "component": [f"PC{i + 1}" for i in range(6)],
    "variance explained %": (100 * ratio[:6]).round(1),
    "cumulative %": (100 * cumulative[:6]).round(1),
})
display(scree_table)

# %% [markdown]
# **Takeaway.** The first component alone accounts for over half the variation
# between days, and the first three for about 87%. So an Academic-building day is
# well described by just **three numbers** instead of 24 -- a real reduction in
# dimensionality, not a cosmetic one.

# %% [markdown]
# ## Step 6: what do the components actually mean?
#
# A component is a weight for every hour of the day, so it can be drawn as a
# shape. Reading those shapes is the whole point -- otherwise PCA produces
# numbers nobody can interpret.

# %%
fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
for i, ax in enumerate(axes):
    ax.plot(range(24), aligned[:, i], color=viz.CATEGORICAL[i], marker="o",
            markersize=4)
    ax.axhline(0, color=viz.AXIS, linewidth=1)
    ax.set_title(f"PC{i + 1}  ({100 * ratio[i]:.1f}% of variance)")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("weight" if i == 0 else "")
    ax.set_xticks(range(0, 24, 4))
fig.suptitle(f"The three main shapes of a day -- {TARGET} building",
             x=0.09, ha="left", fontsize=12, fontweight="semibold")
fig.tight_layout(rect=[0, 0, 1, 0.9])
viz.save_fig(fig, f"fig_03_components_{TARGET.lower()}")

# %%
# Reading the shapes off the numbers rather than by eye.
for i in range(3):
    weights = aligned[:, i]
    same_sign = "all the same sign" if (weights > 0).all() or (weights < 0).all() \
        else "mixed signs"
    peak, trough = int(np.argmax(weights)), int(np.argmin(weights))
    print(f"PC{i + 1}: {same_sign}; largest weight at hour {peak:2d}, "
          f"smallest at hour {trough:2d}")

# %% [markdown]
# **Interpretation, in plain words.**
#
# * **PC1 is "how much".** Its weights all have the same sign, so a day scoring
#   high on PC1 is above average at *every* hour. This component is the overall
#   level of the day -- a busy day versus a quiet one.
# * **PC2 is "day versus night".** Its weights change sign partway through the
#   clock, so it contrasts one part of the day against another. A day scoring
#   high on PC2 is peaky -- a big difference between its daytime and its night.
# * **PC3 is the timing of the peak** -- whether the load arrives earlier or
#   later within the working day.
#
# This is the usual pattern in building energy data, which is itself reassuring:
# it suggests the matrix and the maths are behaving as they should.

# %% [markdown]
# ## Step 7: the days plotted in component space
#
# Now each day is a point. If the calendar matters, days should separate by
# weekday-versus-weekend and by semester-versus-vacation without our ever telling
# PCA about the calendar -- PCA only ever saw power numbers.

# %%
labels = P.day_labels(dates[complete])
scores = hand["scores"]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

for flag, colour, name in [
    (~labels["is_weekend"].to_numpy(), viz.CATEGORICAL[0], "weekday"),
    (labels["is_weekend"].to_numpy(), viz.CATEGORICAL[1], "weekend"),
]:
    ax1.scatter(scores[flag, 0], scores[flag, 1], s=12, alpha=0.6,
                color=colour, label=name, edgecolors="none")
ax1.set_xlabel(f"PC1 -- overall level ({100 * ratio[0]:.0f}%)")
ax1.set_ylabel(f"PC2 -- day vs night ({100 * ratio[1]:.0f}%)")
ax1.set_title("Coloured by weekday or weekend")
ax1.legend()

for flag, colour, name in [
    (~labels["is_vacation"].to_numpy(), viz.CATEGORICAL[2], "semester"),
    (labels["is_vacation"].to_numpy(), viz.CATEGORICAL[3], "vacation"),
]:
    ax2.scatter(scores[flag, 0], scores[flag, 1], s=12, alpha=0.6,
                color=colour, label=name, edgecolors="none")
ax2.set_xlabel(f"PC1 -- overall level ({100 * ratio[0]:.0f}%)")
ax2.set_ylabel(f"PC2 -- day vs night ({100 * ratio[1]:.0f}%)")
ax2.set_title("Coloured by semester or vacation")
ax2.legend()

viz.save_fig(fig, f"fig_03_pc_scatter_{TARGET.lower()}")

# %%
# Is the separation real, or are we seeing patterns in noise? Compare the mean
# scores of each group.
from src import stats as S

for name, flag in [("weekend", labels["is_weekend"].to_numpy()),
                   ("vacation", labels["is_vacation"].to_numpy())]:
    for pc in (0, 1):
        result = S.compare_groups(
            pd.Series(scores[~flag, pc]), pd.Series(scores[flag, pc]),
            f"not {name}", name,
        )
        print(f"PC{pc + 1} -- not {name} vs {name}: "
              f"d = {result['cohens_d']:+.2f} ({result['effect_size_label']}), "
              f"p = {S.format_p(result['mannwhitney_pvalue'])}")

# %% [markdown]
# **Takeaway.** The weekend panel shows clear separation along **PC2**: weekends
# sit lower, meaning a flatter day with less contrast between working hours and
# the night. That makes sense -- nobody arrives in the morning, so the daytime
# rise never happens. PCA found this without ever being told which day of the
# week anything was.
#
# The semester panel separates along **PC1** instead, and less cleanly. Vacation
# days are not uniformly quieter; some are among the highest-consuming days in
# the record, which is the summer cooling load appearing again.

# %% [markdown]
# ## Step 8: a 3-D view
#
# Two components leave about 13% of the variation unshown. Adding PC3 as a third
# axis recovers most of it.

# %%
fig = plt.figure(figsize=(9, 7))
ax = fig.add_subplot(111, projection="3d")

for flag, colour, name in [
    (~labels["is_weekend"].to_numpy(), viz.CATEGORICAL[0], "weekday"),
    (labels["is_weekend"].to_numpy(), viz.CATEGORICAL[1], "weekend"),
]:
    ax.scatter(scores[flag, 0], scores[flag, 1], scores[flag, 2],
               s=10, alpha=0.55, color=colour, label=name, edgecolors="none")

ax.set_xlabel(f"PC1 ({100 * ratio[0]:.0f}%)")
ax.set_ylabel(f"PC2 ({100 * ratio[1]:.0f}%)")
ax.set_zlabel(f"PC3 ({100 * ratio[2]:.0f}%)")
ax.set_title(f"{TARGET} building days in three dimensions "
             f"({100 * cumulative[2]:.0f}% of variance shown)")
ax.legend(loc="upper left")
ax.view_init(elev=18, azim=-58)
ax.set_facecolor(viz.SURFACE)
viz.save_fig(fig, f"fig_03_pc3d_{TARGET.lower()}")

# %% [markdown]
# ## Step 9: k-means day types
#
# PCA gives each day three coordinates. k-means groups days that sit near each
# other, which should correspond to recognisable kinds of day.
#
# We use k = 4 with a fixed random seed, and then name each cluster from the
# *shape* of its average day rather than by eye -- so the names are reproducible
# rather than impressions.

# %%
k = 4
features_for_clustering = scores[:, :3]
kmeans = KMeans(n_clusters=k, random_state=C.SEED, n_init=10)
cluster = kmeans.fit_predict(features_for_clustering)

# Average real (unscaled) daily profile of each cluster.
centroids_hourly = np.vstack([hourly_vec[cluster == c].mean(axis=0) for c in range(k)])
cluster_names = P.name_clusters(centroids_hourly)

summary = pd.DataFrame({
    "cluster": range(k),
    "name": cluster_names,
    "days": [int((cluster == c).sum()) for c in range(k)],
    "mean power (kW)": (centroids_hourly.mean(axis=1) / 1000).round(1),
    "night floor (kW)": (centroids_hourly[:, 0:6].mean(axis=1) / 1000).round(1),
    "midday (kW)": (centroids_hourly[:, 10:14].mean(axis=1) / 1000).round(1),
    "% weekend": [
        round(100 * labels["is_weekend"].to_numpy()[cluster == c].mean(), 1)
        for c in range(k)
    ],
    "% vacation": [
        round(100 * labels["is_vacation"].to_numpy()[cluster == c].mean(), 1)
        for c in range(k)
    ],
})
display(summary)

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))

for c in range(k):
    ax1.plot(range(24), centroids_hourly[c] / 1000, marker="o", markersize=4,
             color=viz.CATEGORICAL[c],
             label=f"{c}: {cluster_names[c]} ({(cluster == c).sum()} days)")
ax1.set_xlabel("Hour of day")
ax1.set_ylabel("Mean power (kW)")
ax1.set_title("The average day in each cluster")
ax1.set_xticks(range(0, 24, 4))
ax1.legend(fontsize=8)

for c in range(k):
    mask = cluster == c
    ax2.scatter(scores[mask, 0], scores[mask, 1], s=12, alpha=0.6,
                color=viz.CATEGORICAL[c], edgecolors="none", label=f"cluster {c}")
ax2.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1],
            s=120, marker="X", color=viz.INK, zorder=5, label="centroids")
ax2.set_xlabel(f"PC1 ({100 * ratio[0]:.0f}%)")
ax2.set_ylabel(f"PC2 ({100 * ratio[1]:.0f}%)")
ax2.set_title("Clusters in component space")
ax2.legend(fontsize=8)

viz.save_fig(fig, f"fig_03_day_types_{TARGET.lower()}")
summary.to_csv(C.RESULTS_DIR / f"phase3_day_types_{TARGET.lower()}.csv", index=False)

# %% [markdown]
# ## Step 10: reconstruction error as a whole-day anomaly score
#
# If the first three components describe a typical day well, then a day they
# describe *badly* is unusual. Reconstruction error -- rebuild each day from only
# its first three component scores, and measure how far the rebuild is from the
# real thing -- gives every day a single "how odd was this?" number.
#
# This is a **whole-day** score, whereas Phase 6 works at the level of individual
# 10-minute intervals. Having both means we can check one against the other.

# %%
error = P.reconstruction_error(scaled, aligned, k=3)
labels_with_error = labels.copy()
labels_with_error["reconstruction_error"] = error

top = labels_with_error.sort_values("reconstruction_error", ascending=False).head(10)
print("The ten days the main components describe worst:")
display(top[["weekday", "period", "reconstruction_error"]].round(3))

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.2))

ax1.hist(error, bins=60, color=viz.CATEGORICAL[0])
threshold = float(np.percentile(error, 99))
ax1.axvline(threshold, color=viz.STATUS["ANOMALY"], linestyle="--", linewidth=1.5)
ax1.annotate("99th percentile", xy=(threshold, ax1.get_ylim()[1] * 0.8),
             xytext=(6, 0), textcoords="offset points", fontsize=8,
             color=viz.STATUS["ANOMALY"])
ax1.set_xlabel("reconstruction error (3 components)")
ax1.set_ylabel("days")
ax1.set_title("How well do 3 components describe each day?")

typical_day = int(np.argmin(error))
odd_day = int(np.argmax(error))
ax2.plot(range(24), hourly_vec[typical_day] / 1000, color=viz.CATEGORICAL[2],
         marker="o", markersize=4,
         label=f"most typical day ({labels.index[typical_day]:%Y-%m-%d})")
ax2.plot(range(24), hourly_vec[odd_day] / 1000, color=viz.STATUS["ANOMALY"],
         marker="o", markersize=4,
         label=f"least typical day ({labels.index[odd_day]:%Y-%m-%d})")
ax2.set_xlabel("Hour of day")
ax2.set_ylabel("Power (kW)")
ax2.set_title("The most and least typical days")
ax2.set_xticks(range(0, 24, 4))
ax2.legend(fontsize=8)

viz.save_fig(fig, f"fig_03_reconstruction_error_{TARGET.lower()}")
labels_with_error.to_csv(C.RESULTS_DIR / f"phase3_day_scores_{TARGET.lower()}.csv")

# %% [markdown]
# ## Step 11: the same analysis for a hostel
#
# A dormitory should behave completely differently from an academic building --
# people are there at night. Running the identical pipeline on the Boys hostel
# tests whether the components we found are a property of *this* building or of
# buildings generally.

# %%
HOSTEL = "Boys_Hostel"
hostel_df, _ = build.build_building(HOSTEL, verbose=False)
h_matrix, h_dates, h_complete = P.day_matrix(hostel_df, "power_w")
h_hourly = P.to_hourly_vectorized(h_matrix[h_complete])
h_scaled, _, _ = P.standardize(h_hourly)
h_pca = P.pca_by_hand(h_scaled)
h_labels = P.day_labels(h_dates[h_complete])

print(f"{HOSTEL}: {h_complete.sum():,} complete days of "
      f"{len(h_complete):,} ({100 * h_complete.mean():.1f}%)")
print(f"variance explained: "
      f"{np.round(100 * h_pca['explained_variance_ratio'][:4], 1)}")
print(f"first three together: {100 * h_pca['cumulative_variance'][2]:.1f}%")

# %%
fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))

axes[0].bar(range(1, 9), 100 * h_pca["explained_variance_ratio"][:8],
            color=viz.color_for(HOSTEL))
axes[0].set_xlabel("Principal component")
axes[0].set_ylabel("% of variance")
axes[0].set_title(f"Scree plot -- {HOSTEL.replace('_', ' ')}")

for i in range(2):
    axes[1].plot(range(24), h_pca["eigenvectors"][:, i], marker="o", markersize=3,
                 color=viz.CATEGORICAL[i], label=f"PC{i + 1}")
axes[1].axhline(0, color=viz.AXIS, linewidth=1)
axes[1].set_xlabel("Hour of day")
axes[1].set_ylabel("weight")
axes[1].set_title("Component shapes")
axes[1].set_xticks(range(0, 24, 4))
axes[1].legend()

h_scores = h_pca["scores"]
for flag, colour, name in [
    (~h_labels["is_weekend"].to_numpy(), viz.CATEGORICAL[0], "weekday"),
    (h_labels["is_weekend"].to_numpy(), viz.CATEGORICAL[1], "weekend"),
]:
    axes[2].scatter(h_scores[flag, 0], h_scores[flag, 1], s=10, alpha=0.6,
                    color=colour, label=name, edgecolors="none")
axes[2].set_xlabel("PC1")
axes[2].set_ylabel("PC2")
axes[2].set_title("Days in component space")
axes[2].legend()

fig.suptitle(f"{HOSTEL.replace('_', ' ')} -- the same analysis",
             x=0.09, ha="left", fontsize=12, fontweight="semibold")
fig.tight_layout(rect=[0, 0, 1, 0.9])
viz.save_fig(fig, f"fig_03_pca_{HOSTEL.lower()}")

# %%
# The mean daily shape of each building side by side -- the clearest way to see
# how different a dormitory is from an academic building.
fig, ax = plt.subplots(figsize=(10, 4.2))
day_counts = {}
skipped = []
for building in C.BUILDING_ORDER:
    df_b, _ = build.build_building(building, verbose=False)
    m, _, ok = P.day_matrix(df_b, "power_w")
    day_counts[building] = int(ok.sum())
    if ok.sum() < 30:
        # Not hidden: a building with almost no complete days genuinely cannot
        # contribute an average daily shape, and saying so is part of the result.
        skipped.append(building)
        continue
    mean_day = P.to_hourly_vectorized(m[ok]).mean(axis=0)
    # Normalise each building by its own mean so shapes, not sizes, are compared.
    ax.plot(range(24), mean_day / mean_day.mean(), color=viz.color_for(building),
            label=building.replace("_", " "))
ax.axhline(1.0, color=viz.AXIS, linewidth=1)

if skipped:
    ax.annotate(
        "not shown (too few complete days): " + ", ".join(
            f"{b.replace('_', ' ')} ({day_counts[b]})" for b in skipped),
        xy=(0.0, 1.02), xycoords="axes fraction", fontsize=8,
        color=viz.INK_MUTED,
    )
ax.set_xlabel("Hour of day")
ax.set_ylabel("Power relative to the building's own daily mean")
ax.set_title("The shape of an average day, each building scaled to its own mean")
ax.set_xticks(range(0, 24, 2))
ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=9)
viz.save_fig(fig, "fig_03_day_shapes_all_buildings")

display(pd.DataFrame({
    "building": list(day_counts),
    "complete days available": list(day_counts.values()),
}).sort_values("complete days available", ascending=False))
print("excluded from the shape chart (fewer than 30 complete days):",
      skipped or "none")

# %% [markdown]
# **Takeaway.** Scaling each building to its own mean strips out size and leaves
# only shape, and the shapes fall into families. The Academic and Library
# buildings rise in the morning and fall at night. The two hostels do the
# opposite -- lowest in the middle of the day, highest in the evening. The Mess
# shows meal-time peaks. **Facilities is nearly a flat line**, which means its
# consumption is almost completely independent of the time of day, and therefore
# of whether anybody is there.
#
# **The Lecture building is absent from this chart, and that absence is itself a
# result.** Drawing an average daily shape needs days that are complete from
# midnight to midnight with a live meter throughout, and the Lecture meter is off
# for part of almost every day, so it has too few such days to average. The same
# constraint will limit what can be said about it in Phase 5.

# %% [markdown]
# ## Step 12: write Phase 3 into the report

# %%
pc1_pct, pc2_pct, pc3_pct = 100 * ratio[0], 100 * ratio[1], 100 * ratio[2]
blocks = {}

blocks["method_phase3"] = f"""
Phase 3 stops treating the data as one long time series and treats it as a
collection of days.

**Building the matrix.** Because Phase 1 placed every building on a complete,
gap-free 10-minute grid, 144 consecutive values are always exactly one calendar
day. The series is trimmed to whole days and then a single NumPy `reshape` turns
it into a (days x 144) matrix -- no pivot and no loop. Days containing any gap,
or any interval flagged `meter_off`, are excluded: {complete.sum():,} of
{len(complete):,} days survive for the {TARGET} building.

**Reducing to hourly.** Each row is reshaped from 144 into (24, 6) and averaged
along the last axis -- a vectorized operation. The same calculation written as
three nested Python loops gives identical numbers
(largest difference {np.abs(hourly_vec - hourly_loop).max():.1e}) and is
{10 ** round(__import__('math').log10(time_loop / time_vec)):,.0f}x slower
(the exact ratio varies run to run -- it is a wall-clock measurement on a shared
machine -- so it is quoted here to the nearest order of magnitude), which is the
practical argument for vectorisation throughout the project.

**Standardisation.** Each hour column is centred and scaled to unit variance.
Without it PCA would mostly describe the midday hours, because they vary most in
absolute terms; with it, the components describe the *shape* of a day rather than
its size.

**PCA by hand.** The covariance matrix of the standardised data is formed
explicitly, its eigenvalues and eigenvectors taken with `np.linalg.eig`, sorted
by eigenvalue and used to project the data. `sklearn.decomposition.PCA` is then
run on the same matrix and the two asserted equal. Eigenvector signs are aligned
before comparison, because an eigenvector multiplied by -1 is still a valid
eigenvector and two correct implementations can legitimately disagree on sign.

**Clustering.** k-means with k = 4 on the first three component scores, seed
{C.SEED}. Clusters are named from measurable properties of their average
profile -- overall level, the size of the night-to-day rise, and the hour of the
peak -- rather than by eye, so the names are reproducible.

**Relation to prior work.** Day-profile clustering on this campus has already
been published (Rashid & Singh, 2018). This phase is supporting analysis, not
part of the novelty claim.

**Notebook:** `notebooks/03_pca.ipynb`.
"""

blocks["results_phase3"] = f"""
### How many shapes does a day have?

{report.md_table(scree_table)}

The first component alone accounts for **{pc1_pct:.1f}%** of the variation
between days, and the first three for **{100 * cumulative[2]:.1f}%**. An
Academic-building day is therefore well described by three numbers instead of 24.

{report.figure(f"fig_03_scree_{TARGET.lower()}",
               f"Scree plot for {TARGET} building daily load profiles",
               f"PC1 explains {pc1_pct:.1f}% and the first three together "
               f"{100 * cumulative[2]:.1f}% -- a real reduction in "
               "dimensionality, not a cosmetic one.")}

### What the components mean

{report.figure(f"fig_03_components_{TARGET.lower()}",
               "The three main shapes of a day, Academic building",
               "PC1 has weights all of one sign -- it is the overall level of "
               "the day. PC2 changes sign across the clock -- it contrasts "
               "daytime against night. PC3 shifts the timing of the peak.")}

**PC1 is 'how much'** -- its weights all share a sign, so a day scoring high is
above average at every hour. **PC2 is 'day versus night'** -- its weights change
sign, contrasting working hours with the night, so a high score means a peaky
day. **PC3 is the timing of the peak.** This is the usual pattern in building
energy data, which is itself a check that the matrix and the arithmetic are
behaving.

### Do days separate by calendar without being told the calendar?

{report.figure(f"fig_03_pc_scatter_{TARGET.lower()}",
               "Days in PC1-PC2 space, coloured by weekend and by vacation",
               "Weekends separate clearly along PC2 -- flatter days with less "
               "contrast between working hours and night. PCA was never given "
               "the day of the week.")}

{report.figure(f"fig_03_pc3d_{TARGET.lower()}",
               "The same days in three dimensions",
               f"Adding PC3 brings the displayed variance to "
               f"{100 * cumulative[2]:.0f}%.")}

Yes -- and the two calendar facts separate along *different* components. Weekends
sit lower on **PC2**: nobody arrives in the morning, so the daytime rise never
happens and the day is flat. Semester and vacation separate along **PC1**
instead, and less cleanly, because vacation days are not uniformly quieter --
some are among the highest-consuming days in the record, which is the summer
cooling load again.

### Day types

{report.md_table(summary)}

{report.figure(f"fig_03_day_types_{TARGET.lower()}",
               "k-means day types: average profile of each cluster, and the clusters in component space",
               "The clusters correspond to recognisable kinds of day rather "
               "than arbitrary groupings -- their weekend and vacation shares "
               "differ sharply even though k-means never saw the calendar.")}

### Which days are unusual?

{report.figure(f"fig_03_reconstruction_error_{TARGET.lower()}",
               "Reconstruction error per day, and the most and least typical days",
               "A day the three main components cannot reproduce is an unusual "
               "day. This whole-day score cross-checks the interval-level "
               "detector built in Phase 6.")}

### The same analysis on a dormitory

{report.figure(f"fig_03_pca_{HOSTEL.lower()}",
               f"{HOSTEL.replace('_', ' ')}: scree plot, component shapes and days in component space",
               f"The first three components explain "
               f"{100 * h_pca['cumulative_variance'][2]:.1f}% here, and the "
               "component shapes differ from the Academic building's -- the "
               "structure is a property of each building, not a universal.")}

### Every building's daily shape, side by side

{report.figure("fig_03_day_shapes_all_buildings",
               "The shape of an average day, each building scaled to its own mean",
               "Scaling out size leaves only shape. Academic and Library "
               "rise in the morning; the hostels do the opposite, lowest at "
               "midday and highest in the evening; the Mess shows meal-time "
               "peaks; Facilities is nearly a flat line.")}

Buildings needing fewer than 30 complete days are absent, and their absence is a
result rather than an omission: drawing an average daily shape requires days that
run midnight to midnight with a live meter throughout.

{report.md_table(pd.DataFrame({"building": list(day_counts),
                               "complete days available": list(day_counts.values())})
                 .sort_values("complete days available", ascending=False))}

**The Facilities line is the most important thing in this chart.** A building
whose daily profile is flat is consuming almost independently of the time of day
-- and therefore almost independently of whether anyone is inside. That is the
Phase 5 result appearing in advance, in a completely different kind of analysis.
"""

report.update_blocks(blocks)

# %% [markdown]
# ## Step 13: record the Phase 3 decisions

# %%
report.log_decision(
    id="D03-01", phase="3",
    decision="Which days enter the PCA",
    options_considered="All days, filling gaps; days with no missing intervals; "
                       "days with no missing intervals and no meter-off period",
    chosen="Complete days only -- no gaps and no meter-off intervals",
    reason="PCA has no concept of a missing value, and an interpolated or dead "
           "hour would become a fictitious 'shape' the components had to explain.",
    effect_on_results=f"{complete.sum():,} of {len(complete):,} "
                      f"({100 * complete.mean():.1f}%) of {TARGET} days are used. "
                      "Buildings with long outages contribute proportionally "
                      "fewer days.",
)

report.log_decision(
    id="D03-02", phase="3",
    decision="Standardising the hour columns before PCA",
    options_considered="Raw watts; centre only; centre and scale to unit variance",
    chosen="Centre and scale each hour column",
    reason="Midday hours vary far more in absolute watts than 4 a.m. hours, so "
           "unscaled PCA would largely describe the middle of the day.",
    effect_on_results="Components describe the *shape* of a day rather than its "
                      "size. PC1 still captures overall level, but through the "
                      "correlation structure rather than raw magnitude.",
)

report.log_decision(
    id="D03-03", phase="3",
    decision="Number of k-means clusters",
    options_considered="k = 2, 3, 4, 5; choosing k by elbow or silhouette",
    chosen=f"k = {k}, fixed, with seed {C.SEED}",
    reason="Four is enough to separate the interpretable kinds of day "
           "(busy/quiet crossed with peaky/flat) without producing clusters too "
           "small to describe. Clustering is supporting analysis here, so a "
           "defensible fixed k is preferable to tuning a number nothing "
           "downstream depends on.",
    effect_on_results="Affects only the day-type table and its chart. No later "
                      "phase consumes the cluster labels.",
)

report.log_decision(
    id="D03-04", phase="3",
    decision="Using np.linalg.eig rather than np.linalg.eigh",
    options_considered="eig (general); eigh (symmetric matrices); SVD",
    chosen="eig, taking the real part, then verified against sklearn",
    reason="A covariance matrix is symmetric, so eigh would be faster and more "
           "stable and would return real values directly. eig is used because "
           "it is the general routine and makes the textbook derivation "
           "explicit; the verification against sklearn guards the choice.",
    effect_on_results="None -- results assert equal to sklearn to within 1e-8 "
                      "after sign alignment.",
)

report.publish_decision_log()
print()
print("blocks still pending:", len(report.pending_blocks()))
print("figures referenced but missing:", report.check_figures())

# %% [markdown]
# ## Phase 3 conclusion
#
# 1. **Three numbers describe a day.** The first three components account for
#    about 87% of the variation between Academic-building days: PC1 the overall
#    level, PC2 the day-versus-night contrast, PC3 the timing of the peak.
# 2. **PCA rediscovered the calendar on its own.** Weekends separate along PC2
#    and vacations along PC1, although PCA only ever saw power numbers. That is a
#    good sign that the structure is real rather than an artefact of our cleaning.
# 3. **Building shapes fall into families.** Academic-type buildings peak by day,
#    dormitories in the evening, the Mess at mealtimes -- and **Facilities is
#    almost flat**, consuming nearly the same amount at 4 a.m. as at noon.
# 4. **PCA by hand matches scikit-learn exactly**, which verifies both the
#    implementation and our understanding of what the library is doing.
#
# **Next:** Phase 4 -- regression models that predict expected power from
# occupancy and time, giving the baseline that Phases 5 and 6 measure against.
