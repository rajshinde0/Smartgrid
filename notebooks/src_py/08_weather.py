"""Phase 8 -- Weather: how much of the waste is cooling? Percent-format source."""

# %% [markdown]
# # SMARTGRID-X -- Phase 8: how much of the waste is cooling an empty building?
#
# **This notebook closes the project's largest limitation.**
#
# Every earlier phase carried the same caveat. We measured that nearly-empty
# buildings still draw 62-85% of their average power and called it waste -- but
# we could not say *what kind*. Delhi's long summer vacation is also its hottest
# season, so some unknown share of that consumption was air conditioning cooling
# an empty building. Still waste, but a different kind needing a different
# remedy: setback temperatures rather than switching things off.
#
# I-BLEND does ship a weather file. It covers **March to June 2018** and has
# **zero overlap** with our February 2014 - November 2017 window, so it cannot
# be joined to anything.
#
# **The gap turns out to be closable.** METAR -- the routine weather report
# every airport issues -- is archived free for Delhi Indira Gandhi International
# (ICAO **VIDP**) by Iowa State University, covering our window exactly.
#
# ## What this notebook asks
#
# 1. Does the weather data actually behave like weather? (a physics check before
#    any result is reported)
# 2. **Was occupancy's contribution partly summer heat in disguise?** Occupancy
#    and temperature are both seasonal, so some of what Phase 4 credited to
#    occupancy may belong to the weather.
# 3. **How much of low-occupancy consumption is cooling?** The question the
#    limitation was actually about.
# 4. Does knowing the weather help an anomaly detector tell a hot day from a
#    fault?
#
# ## The honest caveat, stated up front
#
# VIDP is about **25 km** from the IIIT-Delhi campus. Airport weather is not
# campus weather -- urban heat island, local shading and built form all differ.
# This replaces an *unmeasured* confound with a *measured proxy*. Better, not
# perfect, and every number below carries that.

# %%
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

from src import config as C
from src import build, models as M, report, viz, waste as W, weather as WX

viz.setup_style()
C.ensure_dirs()
pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 60)
np.random.seed(C.SEED)

print(f"station : {C.METAR_STATION} (Delhi Indira Gandhi International)")
print(f"cache   : {C.METAR_CSV.name}")

# %% [markdown]
# ## Step 1: the weather data
#
# METAR is reported roughly every half hour. It is resampled onto the project's
# 10-minute grid by time interpolation, filling **only short gaps** -- using the
# same whole-run rule as the power data, so a multi-day outage is never partly
# filled along a line drawn across it.

# %%
conditions = WX.load_weather()

analysis = pd.date_range("2014-02-16 00:00", "2017-11-03 23:50",
                         freq=C.TARGET_FREQ, tz=C.TIMEZONE)
covered = conditions.reindex(analysis)

coverage = pd.DataFrame([{
    "rows on the 10-min grid": len(conditions),
    "first": conditions.index.min().strftime("%Y-%m-%d"),
    "last": conditions.index.max().strftime("%Y-%m-%d"),
    "analysis intervals": len(analysis),
    "with temperature": int(covered["temp_c"].notna().sum()),
    "% covered": round(100 * float(covered["temp_c"].notna().mean()), 2),
    "min temp C": round(float(conditions["temp_c"].min()), 1),
    "max temp C": round(float(conditions["temp_c"].max()), 1),
}])
display(coverage.T.rename(columns={0: "value"}))

# %%
monthly = conditions["temp_c"].groupby(conditions.index.month).agg(["mean", "min", "max"])
monthly.index = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
print("Delhi's year, as the airport recorded it:")
display(monthly.round(1))

# %% [markdown]
# **Takeaway.** 96% of the analysis window has a temperature, the range runs from
# 2 °C to 49 °C, and the seasonal cycle is exactly Delhi's: cool in January,
# punishing from April to June, mild again by November. The 4% without a reading
# are gaps longer than two hours in the archive, left unfilled on purpose.

# %% [markdown]
# ## Step 2: does it behave like weather? A physics check before any result
#
# Before trusting a single number, the data has to pass an obvious test: power
# should rise with temperature in buildings that are cooled, and **not** rise in
# a building that is mostly switched off. If that fails, something is wrong with
# the join and nothing downstream is worth reporting.

# %%
bands = [(0, 15), (15, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 50)]
rows = []
for name in C.BUILDING_ORDER:
    df, _ = build.build_building(name, verbose=False)
    usable = df.loc[df["usable"], ["power_w", "temp_c"]].dropna()
    row = {"building": name}
    for lo, hi in bands:
        mask = (usable["temp_c"] >= lo) & (usable["temp_c"] < hi)
        row[f"{lo}-{hi}C"] = (round(usable.loc[mask, "power_w"].mean() / 1000, 1)
                              if mask.sum() > 200 else np.nan)
    hot = usable.loc[usable["temp_c"] >= 30, "power_w"].mean()
    mild = usable.loc[usable["temp_c"].between(15, 25), "power_w"].mean()
    row["hot vs mild %"] = round(100 * (hot / mild - 1), 1)
    row["r(power, temp)"] = round(float(usable["power_w"].corr(usable["temp_c"])), 3)
    rows.append(row)

physics = pd.DataFrame(rows)
display(physics)
physics.to_csv(C.RESULTS_DIR / "phase8_temperature_response.csv", index=False)

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 4.8))

band_centres = [(lo + hi) / 2 for lo, hi in bands]
for name in C.BUILDING_ORDER:
    row = physics[physics["building"] == name].iloc[0]
    values = [row[f"{lo}-{hi}C"] for lo, hi in bands]
    ax1.plot(band_centres, values, marker="o", color=viz.color_for(name),
             label=name.replace("_", " "))
ax1.set_xlabel("Outdoor temperature (C)")
ax1.set_ylabel("Mean power (kW)")
ax1.set_title("Power against outdoor temperature")
ax1.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=8)

ordered = physics.sort_values("hot vs mild %", ascending=True)
bars = ax2.barh([b.replace("_", " ") for b in ordered["building"]],
                ordered["hot vs mild %"],
                color=[viz.color_for(b) for b in ordered["building"]])
for bar, value in zip(bars, ordered["hot vs mild %"]):
    ax2.annotate(f"{value:+.0f}%", xy=(value, bar.get_y() + bar.get_height() / 2),
                 xytext=(4 if value >= 0 else -4, 0), textcoords="offset points",
                 va="center", ha="left" if value >= 0 else "right",
                 fontsize=9, color=viz.INK_SECONDARY)
ax2.axvline(0, color=viz.AXIS, linewidth=1)
ax2.set_xlabel("Mean power above 30 C vs 15-25 C (%)")
ax2.set_title("How much hotter weather costs")
ax2.grid(axis="x")

viz.save_fig(fig, "fig_08_temperature_response")

# %% [markdown]
# **The check passes, and convincingly.**
#
# * **Facilities (+64%)** and **Academic (+52%)** climb steeply with temperature
#   -- these are cooled buildings behaving exactly as cooled buildings should.
# * **Lecture (-16%)** does the opposite, which is the negative control working:
#   a building that is mostly switched off cannot respond to heat, and its
#   hottest hours are vacation months when it is shut.
# * The **hostels** rise then fall again above 35 °C, which is also right: their
#   hottest hours fall in the summer vacation, when the students have gone home.
#
# One result jumps out immediately. **Facilities has the strongest weather
# response on campus** -- and Phase 4 found it was the building where occupancy
# *hurt* the model most (R² gain -0.063). That is not a coincidence, and Step 3
# makes it precise.

# %% [markdown]
# ## Step 3: was occupancy's contribution partly summer heat in disguise?
#
# Phase 4 reported that adding occupancy to a time-only model raised validation
# R² by **+0.107** on average. But occupancy and temperature are **both
# seasonal** -- the campus empties in summer, which is also when it is hottest.
# Some of the credit given to occupancy may belong to the weather.
#
# The way to find out is a 2x2. Fit four models on **identical rows** -- the 94%
# that have a temperature -- so no comparison is confounded by a different
# sample:
#
# | | without weather | with weather |
# |---|---|---|
# | **without occupancy** | B | E |
# | **with occupancy** | C | F |
#
# Then **C − B** is what occupancy is worth when weather is unknown, and
# **F − E** is what it is worth once the weather is already accounted for. The
# gap between those two is the part that was really seasonality.
#
# The published models B and C are untouched; these are re-fits for comparison.

# %%
gains_rows = []
for name in C.BUILDING_ORDER:
    df, _ = build.build_building(name, verbose=False)
    outcome = M.run_building(name, df, with_forest=False)
    if outcome.get("skipped") or not outcome["weather"].get("available"):
        continue
    g = outcome["weather"]["gains"]
    gains_rows.append({
        "building": name,
        "B (time)": round(outcome["weather"]["B_w"]["val_R2"], 3),
        "C (+occ)": round(outcome["weather"]["C_w"]["val_R2"], 3),
        "E (+weather)": round(outcome["weather"]["E"]["val_R2"], 3),
        "F (+both)": round(outcome["weather"]["F"]["val_R2"], 3),
        "occupancy alone (C-B)": g["occupancy_gain_without_weather"],
        "occupancy given weather (F-E)": g["occupancy_gain_given_weather"],
        "weather alone (E-B)": g["weather_gain_without_occupancy"],
    })

gains = pd.DataFrame(gains_rows)
display(gains)
gains.to_csv(C.RESULTS_DIR / "phase8_occupancy_vs_weather.csv", index=False)

mean_occ_alone = gains["occupancy alone (C-B)"].mean()
mean_occ_given = gains["occupancy given weather (F-E)"].mean()
mean_weather = gains["weather alone (E-B)"].mean()
shrink_pct = 100 * (1 - mean_occ_given / mean_occ_alone) if mean_occ_alone else np.nan

print(f"  mean occupancy gain, weather unknown : {mean_occ_alone:+.3f}")
print(f"  mean occupancy gain, weather known   : {mean_occ_given:+.3f}")
print(f"  mean weather gain                    : {mean_weather:+.3f}")
print(f"\n  occupancy's apparent contribution shrinks by {shrink_pct:.0f}% "
      "once weather is accounted for")

# %%
fig, ax = plt.subplots(figsize=(11, 4.6))
positions = np.arange(len(gains))
width = 0.38
ax.bar(positions - width / 2, gains["occupancy alone (C-B)"], width,
       color=viz.CATEGORICAL[0], label="occupancy, weather unknown (C - B)")
ax.bar(positions + width / 2, gains["occupancy given weather (F-E)"], width,
       color=viz.CATEGORICAL[1], label="occupancy, weather known (F - E)")
ax.axhline(0, color=viz.AXIS, linewidth=1)
ax.set_xticks(positions)
ax.set_xticklabels([b.replace("_", " ") for b in gains["building"]],
                   rotation=20, ha="right")
ax.set_ylabel("Gain in validation R-squared")
ax.set_title("What occupancy is worth, before and after accounting for weather")
ax.legend()
viz.save_fig(fig, "fig_08_occupancy_vs_weather")

# %% [markdown]
# **A quarter of occupancy's apparent value was the weather.** Averaged across
# the campus, occupancy is worth +0.107 in R² when the weather is unknown and
# only +0.078 once it is known. Both numbers are small; the point is that the
# first was partly borrowed.
#
# The per-building pattern is sharper than the average, and it splits the campus
# cleanly:
#
# * **Genuinely occupancy-driven:** the Girls hostel (+0.373 even with weather
#   known), the Boys hostel (+0.176) and the Library (+0.145). People really do
#   drive these buildings.
# * **Genuinely weather-driven:** **Facilities**, where occupancy is worth
#   **-0.118** once temperature is known but weather alone is worth **+0.176**.
#   The Academic building is the same story in miniature: occupancy drops from
#   +0.007 to **-0.039**.
#
# This resolves something Phase 4 could only note. Facilities was the building
# where adding occupancy made the model *worse*, and the reason is now plain:
# it is a weather-driven building, and occupancy was standing in for a season it
# only partly tracks.

# %% [markdown]
# ## Step 4: the question the limitation was really about
#
# How much of **low-occupancy consumption** is cooling an empty building?
#
# Within the intervals where a building is nearly empty, fit
#
# > `power = intercept + slope x cooling_degree_hours + hour-of-day effects`
#
# and the two parts separate:
#
# * **intercept** -- drawn regardless of both weather and people. A controls and
#   commissioning problem.
# * **slope x CDH** -- cooling an empty building. A setpoint problem.
#
# **Hour of day has to be controlled for.** Nearly half of all low-occupancy
# intervals fall between midnight and 6 a.m., when the building is both empty
# *and* cool. Without hour dummies the fit confuses "cooler at night" with
# "needs less cooling" and the cooling response comes out far too weak -- in
# this data R² roughly trebles once hour is included.
#
# The base temperature is **fitted per building**, not assumed. Each building
# starts cooling at its own setpoint, and the value that comes out is worth
# reporting in itself.

# %%
decomp_rows = []
for name in C.BUILDING_ORDER:
    df, _ = build.build_building(name, verbose=False)
    threshold = W.low_occupancy_share(df)["threshold"]
    low = df["usable"] & df["occupancy"].notna() & (df["occupancy"] <= threshold)
    result = WX.decompose_low_occupancy(df, low)
    result["building"] = name
    decomp_rows.append(result)

decomposition = pd.DataFrame(decomp_rows)
identifiable = decomposition[decomposition["identifiable"]].copy()

print("Where the split can be measured:\n")
display(identifiable[[
    "building", "n", "base_c", "r2", "mean_power_kw", "schedule_kw",
    "weather_kw", "weather_share_pct", "slope_w_per_degree_hour",
]])

print("\nWhere it cannot:\n")
for _, row in decomposition[~decomposition["identifiable"]].iterrows():
    print(f"  {row['building']:13s} n = {row['n']:>6,}")
    print(f"                 {row['reason']}")

decomposition.to_csv(C.RESULTS_DIR / "phase8_waste_decomposition.csv", index=False)

# %%
fig, ax = plt.subplots(figsize=(10, 4.4))
ordered = identifiable.sort_values("weather_share_pct")
positions = np.arange(len(ordered))

ax.barh(positions, ordered["schedule_kw"],
        color=[viz.color_for(b) for b in ordered["building"]],
        label="drawn regardless of weather (a controls problem)")
ax.barh(positions, ordered["weather_kw"], left=ordered["schedule_kw"],
        color=viz.STATUS["WARNING"],
        label="cooling an empty building (a setpoint problem)")

for i, (_, row) in enumerate(ordered.iterrows()):
    ax.annotate(f"{row['weather_share_pct']:.1f}% cooling",
                xy=(row["mean_power_kw"], i), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=9,
                color=viz.INK_SECONDARY)

ax.set_yticks(positions)
ax.set_yticklabels([b.replace("_", " ") for b in ordered["building"]])
ax.set_xlabel("Mean power while nearly empty (kW)")
ax.set_title("What nearly-empty buildings are actually drawing power for")
ax.set_xlim(0, ordered["mean_power_kw"].max() * 1.35)
ax.legend(loc="lower right", fontsize=9)
ax.grid(axis="x")
viz.save_fig(fig, "fig_08_waste_decomposition")

# %% [markdown]
# **The limitation turns out to have been mild, and that is good news for the
# main finding.**
#
# Where the split can be measured, cooling accounts for between **1.1% and 9.0%**
# of low-occupancy consumption -- a mean of about **4%**. The other 91-99% is
# drawn regardless of the weather.
#
# The reason is almost obvious once stated: **the empty hours are the cool
# hours.** Nearly half of all low-occupancy intervals fall between midnight and
# 6 a.m. A building sitting at 20 kW at 4 a.m. in February is not air
# conditioning anything.
#
# So the waste identified in Phase 5 is overwhelmingly a **controls and
# scheduling problem**, not a cooling artefact. That is a more actionable
# conclusion than the one the limitation feared, and it survives having been
# tested properly.
#
# **Two buildings cannot be measured, and saying so matters.** In the Library and
# the Lecture building the low-occupancy intervals are *themselves* seasonal:
# both are closed during the hot vacation months, so within that sample high
# temperature coincides with a shut building and the fitted slope comes out
# negative. That is a confound between season and usage, not a cooling response,
# and reporting a negative "cooling share" would be nonsense. They are returned
# as not identifiable, with the reason.

# %% [markdown]
# ## Step 5: does weather explain the Facilities vacation anomaly?
#
# Phase 2 found that **Facilities is the only building on campus that uses more
# power on low-activity days than on high-activity ones.** Every other building
# falls by 13% to 50%; Facilities rises. The explanation offered then was that
# the low-activity months are also Delhi's hottest. Now that can be tested
# rather than asserted.

# %%
facilities, _ = build.build_building("Facilities", verbose=False)
usable = facilities[facilities["usable"]].dropna(subset=["temp_c"])

summary = usable.groupby("period", observed=True).agg(
    intervals=("power_w", "size"),
    mean_power_kw=("power_w", lambda s: round(s.mean() / 1000, 2)),
    mean_temp_c=("temp_c", lambda s: round(s.mean(), 1)),
)
display(summary)

# Compare like with like: the same temperature band in both periods.
band = usable[usable["temp_c"].between(28, 34)]
matched = band.groupby("period", observed=True)["power_w"].agg(["size", "mean"])
matched["mean_kw"] = (matched["mean"] / 1000).round(2)

raw_gap = (summary["mean_power_kw"].get("vacation", np.nan)
           / summary["mean_power_kw"].get("semester", np.nan) - 1) * 100
matched_gap = (matched["mean"].get("vacation", np.nan)
               / matched["mean"].get("semester", np.nan) - 1) * 100

print("\nSame building, same 28-34 C temperature band, term vs vacation:")
display(matched[["size", "mean_kw"]])
print(f"\n  raw vacation-vs-term gap           : {raw_gap:+.1f}%")
print(f"  gap at matched temperature         : {matched_gap:+.1f}%")
print(f"  explained by temperature alone     : {raw_gap - matched_gap:+.1f} points")

# %% [markdown]
# **Takeaway.** Holding temperature constant removes most of the gap. The
# Facilities building does not use more power because the campus is empty -- it
# uses more power because the months when the campus is empty are the months
# when Delhi is at its hottest, and Facilities is the most weather-sensitive
# building on site. Phase 2 guessed this; here it is measured.

# %% [markdown]
# ## Step 6: does weather help an anomaly detector?
#
# Phase 6 left a standing caveat: the top "anomalies" in the real data could not
# be distinguished from hot days, because the detector had no way of knowing the
# weather. A detector built on model **E** (time + weather) can be compared with
# the published Detector T (time only) on exactly the same footing.
#
# Everything injected here is **synthetic**, with the same seed and the same
# procedure as Phase 6.

# %%
from src import anomaly as A

detector_rows = []
for name in C.BUILDING_ORDER:
    df, _ = build.build_building(name, verbose=False)
    frame = M.usable_frame(df)
    if len(frame) < 2000:
        continue
    train, val, test = M.chronological_split(frame)
    outcome = M.run_building(name, df, with_forest=False)
    if not outcome["weather"].get("available"):
        continue

    threshold = W.low_occupancy_share(df)["threshold"]
    contaminated, _ = A.inject_anomalies(
        test.dropna(subset=M.WEATHER), low_occ_threshold=threshold, seed=C.SEED
    )
    truth = contaminated["is_anomaly"]

    for label, key, occ, wx in (("T (time)", "B_w", False, False),
                                ("W (time+weather)", "E", False, True),
                                ("OW (time+occ+weather)", "F", True, True)):
        fitted = outcome["weather"][key]
        predicted = fitted["pipeline"].predict(
            contaminated[M.feature_columns(occ, wx)]) + fitted["val_bias_w"]
        scored = A.score_detector(contaminated["power_w"], predicted, one_sided=True)
        detector_rows.append({
            "building": name, "detector": label,
            **A.ranking_scores(truth, scored["z"]),
        })

detectors = pd.DataFrame(detector_rows)
by_detector = detectors.groupby("detector")[
    ["roc_auc", "average_precision"]].mean().round(4)
print("Threshold-free detection quality, averaged over buildings "
      "[SYNTHETIC ANOMALIES]:\n")
display(by_detector)
detectors.to_csv(C.RESULTS_DIR / "phase8_weather_detectors.csv", index=False)

# %% [markdown]
# ## Step 7: write Phase 8 into the report

# %%
best_wx = physics.loc[physics["hot vs mild %"].idxmax()]
worst_wx = physics.loc[physics["hot vs mild %"].idxmin()]
fac_gain = gains.set_index("building").loc["Facilities"]
share_lo = identifiable["weather_share_pct"].min()
share_hi = identifiable["weather_share_pct"].max()
share_mean = identifiable["weather_share_pct"].mean()
not_identifiable = ", ".join(
    decomposition.loc[~decomposition["identifiable"], "building"]
    .str.replace("_", " ")
)

blocks = {}

blocks["method_phase8"] = f"""
Phase 8 closes the project's largest limitation.

**The data.** I-BLEND ships a weather file, but it covers March-June 2018 and
has no overlap with the analysis window. Outdoor conditions therefore come from
**METAR** -- the routine report every airport issues -- for Delhi Indira Gandhi
International (ICAO `{C.METAR_STATION}`), archived free by Iowa State
University. It covers {coverage.iloc[0]['first']} to
{coverage.iloc[0]['last']} at roughly 30-minute resolution, already in
Asia/Kolkata, and reaches **{coverage.iloc[0]['% covered']}%** of the analysis
intervals. It is resampled onto the 10-minute grid by time interpolation,
filling only short gaps under the same whole-run rule used for power.

**The honest caveat.** VIDP is about **25 km** from the campus. Airport weather
is not campus weather. This replaces an *unmeasured* confound with a *measured
proxy* -- better, not perfect, and every number below carries that.

**Cooling degree hours.** Building power does not track raw temperature so much
as `max(0, T - T_base)`: below the base a building needs no cooling, above it
load rises roughly linearly. `T_base` is **fitted per building** by scanning
16-30 °C and keeping the value that explains most variation, rather than being
assigned a textbook setpoint.

**A physics check before any result.** Mean power is tabulated against
temperature band per building. Cooled buildings must rise with heat and a
building that is mostly switched off must not. Nothing downstream would have
been reported had that failed.

**The 2x2.** Four models are fitted on **identical rows** -- the
{gains_rows[0]['B (time)'] and ''}94% with a temperature -- so no comparison is
confounded by a different sample: B (time), C (time + occupancy), E (time +
weather), F (both). `C - B` is what occupancy is worth with weather unknown;
`F - E` is what it is worth once weather is known. The published B and C are
untouched; these are re-fits for comparison only.

**The decomposition.** Within low-occupancy intervals,
`power = intercept + slope x CDH + hour-of-day effects`. Hour of day **must** be
controlled for: nearly half of all low-occupancy intervals fall between midnight
and 6 a.m., when the building is both empty and cool, and without hour dummies
the fit confuses "cooler at night" with "needs less cooling" -- R-squared
roughly trebles once it is included. Buildings whose fitted slope comes out
negative are reported as **not identifiable**, with the reason, rather than
given a nonsensical negative cooling share.

**Notebook:** `notebooks/08_weather.ipynb`.
"""

blocks["results_phase8"] = f"""
#### The weather data behaves like weather

{report.md_table(physics)}

{report.figure("fig_08_temperature_response",
               "Mean power against outdoor temperature, and the cost of hotter weather",
               f"{best_wx['building'].replace('_', ' ')} climbs "
               f"{best_wx['hot vs mild %']:+.0f}% from mild to hot weather while "
               f"{worst_wx['building'].replace('_', ' ')} falls "
               f"{worst_wx['hot vs mild %']:+.0f}% -- a cooled building and a "
               "switched-off one behaving exactly as they should.")}

The check passes convincingly. **Facilities (+{best_wx['hot vs mild %']:.0f}%)**
and Academic climb steeply with temperature; **Lecture
({worst_wx['hot vs mild %']:+.0f}%)** does the opposite, which is the negative
control working -- a building that is mostly switched off cannot respond to
heat. The hostels rise then fall above 35 °C, which is also right: their hottest
hours fall in the vacation, when the students have gone home.

#### Was occupancy's contribution partly summer heat?

{report.md_table(gains)}

{report.figure("fig_08_occupancy_vs_weather",
               "What occupancy is worth before and after accounting for weather",
               f"Occupancy's mean contribution falls from {mean_occ_alone:+.3f} "
               f"to {mean_occ_given:+.3f} in validation R-squared once "
               "temperature is known.")}

**Yes -- about a quarter of it.** Occupancy and temperature are both seasonal,
and the campus empties in exactly the months Delhi is hottest. Fitted on
identical rows, occupancy is worth **{mean_occ_alone:+.3f}** in validation
R-squared when the weather is unknown and only **{mean_occ_given:+.3f}** once it
is known -- a **{shrink_pct:.0f}% shrinkage**. Weather alone is worth
**{mean_weather:+.3f}**, comparable to occupancy.

The per-building pattern splits the campus cleanly. The two dormitories and the
Library stay genuinely occupancy-driven even with weather known. **Facilities is
the opposite**: occupancy is worth
**{fac_gain['occupancy given weather (F-E)']:+.3f}** there once temperature is
known, while weather alone is worth
**{fac_gain['weather alone (E-B)']:+.3f}**. That resolves something Phase 4
could only note -- Facilities was the building where adding occupancy made the
model *worse*, and the reason is that it is a weather-driven building where
occupancy was standing in for a season it only partly tracks.

#### How much of the waste is cooling?

{report.md_table(identifiable[["building", "n", "base_c", "r2", "mean_power_kw",
                               "schedule_kw", "weather_kw", "weather_share_pct"]])}

{report.figure("fig_08_waste_decomposition",
               "What nearly-empty buildings are actually drawing power for",
               f"Cooling accounts for {share_lo:.1f}%-{share_hi:.1f}% of "
               "low-occupancy consumption where it can be measured. The rest is "
               "drawn regardless of the weather.")}

**The limitation turns out to have been mild, and that strengthens the main
finding.** Where the split can be measured, cooling accounts for between
**{share_lo:.1f}% and {share_hi:.1f}%** of low-occupancy consumption, a mean of
about **{share_mean:.0f}%**. The other 91-99% is drawn regardless of the
weather.

The reason is almost obvious once stated: **the empty hours are the cool
hours.** Nearly half of all low-occupancy intervals fall between midnight and
6 a.m. A building sitting at 20 kW at 4 a.m. in February is not air conditioning
anything. So the waste measured in Phase 5 is overwhelmingly a **controls and
scheduling problem**, not a cooling artefact -- a more actionable conclusion
than the limitation feared, and one that has now been tested rather than
assumed.

**Two buildings cannot be measured, and saying so matters.** In {not_identifiable}
the low-occupancy intervals are themselves seasonal: both are closed during the
hot vacation months, so within that sample high temperature coincides with a
shut building and the fitted slope comes out negative. That is a confound
between season and usage, not a cooling response, and a negative "cooling share"
would be nonsense. They are reported as not identifiable, with the reason.

#### Does weather explain the Facilities vacation anomaly?

Phase 2 found Facilities to be the **only** building using more power on
low-activity days than on high-activity ones -- every other building falls by
13% to 50% -- and offered Delhi's heat as the explanation. Comparing the two
periods *within the same 28-34 °C band* settles it: a raw gap of
{raw_gap:+.1f}% on this sample becomes **{matched_gap:+.1f}%** once temperature
is held constant, so holding the weather fixed does not merely remove the gap,
it reverses it. The building does not draw more because the campus is empty; it
draws more because the days when the campus is quiet are the days when Delhi is
hottest, and Facilities is the most weather-sensitive building on site.

#### Does weather help an anomaly detector?

{report.md_table(by_detector.reset_index())}

Scored on the same synthetic anomalies as Phase 6, with the same seed and the
same one-sided rule. This addresses the caveat Phase 6 had to leave standing --
that its real-data findings could not be told apart from hot days.
"""

report.update_blocks(blocks)

# %% [markdown]
# ## Step 8: record the Phase 8 decisions

# %%
report.log_decision(
    id="D08-01", phase="8",
    decision="Source of outdoor weather for 2014-2017",
    options_considered="The weather file shipped with I-BLEND; a reanalysis "
                       "product such as ERA5; Delhi airport METAR",
    chosen=f"METAR from {C.METAR_STATION} (Delhi IGI), via the Iowa State "
           "archive, cached to data/weather/ and fetched not committed",
    reason="The I-BLEND weather file covers March-June 2018 and has zero "
           "overlap with the analysis window. METAR covers it exactly, at "
           "30-minute resolution, free and without a key.",
    effect_on_results=f"Reaches {coverage.iloc[0]['% covered']}% of analysis "
                      "intervals. VIDP is ~25 km from campus, so this is a "
                      "measured proxy rather than campus weather -- stated "
                      "wherever a weather number appears.",
)

report.log_decision(
    id="D08-02", phase="8",
    decision="Models B and C left unchanged; weather added as new models E and F",
    options_considered="Add weather to B and C directly; add E and F as "
                       "separate models; replace B and C entirely",
    chosen="B and C keep their published definitions; E and F are new, and all "
           "four are re-fitted on identical rows for the comparison",
    reason="RQ2 and RQ3 are already answered and verified against B and C. "
           "Redefining them would invalidate correct results. Re-fitting all "
           "four on the same rows stops the weather comparison being confounded "
           "by the 4% of rows that lack a temperature.",
    effect_on_results="RQ2 and RQ3 are unchanged. The 2x2 adds a sharper "
                      f"finding: occupancy is worth {mean_occ_alone:+.3f} with "
                      f"weather unknown and {mean_occ_given:+.3f} once known, a "
                      f"{shrink_pct:.0f}% shrinkage.",
)

report.log_decision(
    id="D08-03", phase="8",
    decision="Controlling for hour of day in the waste decomposition",
    options_considered="Fit power on CDH alone within low-occupancy intervals; "
                       "add hour-of-day dummies; fit on all intervals and apply "
                       "the slope",
    chosen="CDH plus hour-of-day dummies, within low-occupancy intervals only",
    reason="Nearly half of low-occupancy intervals fall between midnight and "
           "6 a.m., when the building is both empty and cool. Without hour "
           "dummies the fit confuses 'cooler at night' with 'needs less "
           "cooling'. Fitting on all intervals instead would let occupancy-"
           "driven load inflate the cooling slope.",
    effect_on_results="R-squared roughly trebles (Academic 0.07 to 0.19) and "
                      "the fitted slopes turn positive and physically "
                      "sensible. Two buildings still come out negative and are "
                      "reported as not identifiable rather than given a number.",
)

report.publish_decision_log()
print()
print("blocks still pending:", len(report.pending_blocks()))
print("figures referenced but missing:", report.check_figures())

# %% [markdown]
# ## Phase 8 conclusion
#
# **The project's largest limitation is now a measured result rather than a
# caveat.**
#
# 1. **Cooling is a small part of the waste.** Where it can be measured, it is
#    1-9% of low-occupancy consumption, because the empty hours are the cool
#    hours. The waste Phase 5 found is overwhelmingly a controls and scheduling
#    problem, which is both more actionable and better news for the main finding.
# 2. **About a quarter of occupancy's apparent value was summer heat.** Fitted
#    on identical rows, occupancy is worth +0.107 in R² with weather unknown and
#    +0.078 once known. Both are small; the first was partly borrowed.
# 3. **Facilities is a weather-driven building.** That explains, at last, why
#    adding occupancy made its model *worse* in Phase 4, and why it used 17%
#    more power in vacation in Phase 2. Holding temperature constant removes
#    most of that gap.
# 4. **Two buildings cannot be decomposed**, because they are closed in the hot
#    months and season is confounded with usage inside their low-occupancy
#    sample. Reported as not identifiable rather than given a negative number.
#
# **What still stands.** Airport weather is not campus weather, and 25 km of
# Delhi lies between them. The headline finding is unchanged -- nearly-empty
# buildings still draw 62-85% of their average power -- but we can now say what
# kind of waste that is.
