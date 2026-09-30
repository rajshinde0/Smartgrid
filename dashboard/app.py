"""SMARTGRID-X dashboard.

    streamlit run dashboard/app.py

Reads only saved outputs -- the parquet files written by `src/dashboard.py` and
the CSV tables in `results/`. **It does not train anything.** Every model in this
project is fitted in the notebooks; refitting here would be slow during a
demonstration and, worse, would let the numbers on screen drift away from the
numbers in the report.

If the parquet files are missing, run this first:

    python -c "import sys; sys.path.insert(0, '.'); from src import dashboard; dashboard.export_all()"
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config as C          # noqa: E402
from src import dashboard as D       # noqa: E402
from src import viz                  # noqa: E402

viz.setup_style()

st.set_page_config(page_title="SMARTGRID-X", page_icon="⚡", layout="wide")


# ---------------------------------------------------------------------------
# Loading -- cached so moving a slider does not re-read 170,000 rows
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_building(building: str) -> pd.DataFrame:
    return pd.read_parquet(D.dashboard_path(building))


@st.cache_data(show_spinner=False)
def load_results() -> dict[str, pd.DataFrame]:
    wanted = {
        "headline": "phase5_headline.csv",
        "sensitivity": "phase5_sensitivity_curve.csv",
        "model_a": "phase4_model_a_coefficients.csv",
        "base_load": "phase5_base_load.csv",
        "published": "phase5_published_comparison.csv",
        "detectors": "phase6_pooled_answer.csv",
        "quality": "phase1_data_quality.csv",
    }
    out = {}
    for key, filename in wanted.items():
        path = C.RESULTS_DIR / filename
        if path.is_file():
            out[key] = pd.read_csv(path)
    return out


available = D.available_buildings()
if not available:
    st.error(
        "No dashboard data found. Run the notebooks first, then:\n\n"
        "```\npython -c \"import sys; sys.path.insert(0, '.'); "
        "from src import dashboard; dashboard.export_all()\"\n```"
    )
    st.stop()

results = load_results()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("SMARTGRID-X")
st.caption(
    "Occupancy-aware energy-waste and anomaly analysis of the I-BLEND campus "
    "dataset (IIIT Delhi, 7 buildings, Feb 2014 – Nov 2017)"
)

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Controls")
    building = st.selectbox(
        "Building", available, format_func=lambda b: b.replace("_", " ")
    )

    data = load_building(building)
    first_day = data.index.min().date()
    last_day = data.index.max().date()

    st.caption(f"Data available {first_day} to {last_day}")

    # Default to the first fortnight of the held-out test period rather than to
    # the final fortnight of the record. Both are test data, but consumption on
    # this campus rose steadily and the models were fitted on 2014-2016, so the
    # very end of the record is the most drifted stretch there is -- opening on
    # it would show a wall of anomaly flags that says more about the model's age
    # than about the building. The drift is surfaced explicitly below instead.
    test_days = data.index[data["split"] == "test"]
    anchor = test_days.min().date() if len(test_days) else first_day
    default_start = max(first_day, anchor)
    default_end = min(last_day, default_start + pd.Timedelta(days=14))

    date_range = st.date_input(
        "Date range",
        value=(default_start, default_end),
        min_value=first_day,
        max_value=last_day,
    )

    show_expected = st.checkbox("Show expected power", value=True)
    show_low_occ = st.checkbox("Shade low-occupancy periods", value=True)

    st.divider()
    st.caption(
        "This dashboard reads saved model output. It does not retrain anything, "
        "so the numbers here match the report exactly."
    )

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
else:                                   # the widget returns one date mid-edit
    start = end = date_range if not isinstance(date_range, tuple) else date_range[0]

window = data.loc[str(start) : str(pd.Timestamp(end) + pd.Timedelta(days=1))]

# ---------------------------------------------------------------------------
# Key numbers
# ---------------------------------------------------------------------------
headline = results.get("headline", pd.DataFrame())
row = headline[headline["building"] == building]

col1, col2, col3, col4 = st.columns(4)

if not row.empty:
    entry = row.iloc[0]
    share = entry["low-occupancy energy share %"]
    ratio = entry["intensity ratio"]

    col1.metric(
        "Energy used at low occupancy",
        "no qualifying interval" if pd.isna(ratio) else f"{share:.1f}%",
        help=f"Occupancy at or below {entry['threshold']:.1f} devices "
             f"({C.LOW_OCC_FRACTION:.0%} of this building's 95th percentile)",
    )
    col2.metric(
        "Power when nearly empty",
        "n/a" if pd.isna(ratio) else f"{ratio:.0%} of average",
        help="Mean power during low-occupancy intervals, as a share of mean "
             "power overall. This is the headline number.",
    )
    col3.metric(
        "Base load",
        f"{entry['base load a (kW)']:.1f} kW",
        help="Model A intercept: power drawn with nobody present.",
    )
    col4.metric(
        "Per extra occupant",
        f"{entry['watts per occupant b']:.0f} W",
        help="Model A slope: how much each additional occupant adds.",
    )

if not row.empty and pd.isna(row.iloc[0]["intensity ratio"]):
    st.warning(
        f"**{building.replace('_', ' ')}** has no interval at or below the "
        f"standard threshold ({row.iloc[0]['threshold']:.2f} occupants, below "
        "its own minimum observed count of 1). The rule is kept identical for "
        "every building rather than bent for one; see the sensitivity curve "
        "below for where this building does become measurable.",
        icon="⚠️",
    )

# ---------------------------------------------------------------------------
# Main chart -- two panels sharing a time axis, never two y-axes
# ---------------------------------------------------------------------------
st.subheader("Power and occupancy")

if window.empty:
    st.info("No data in the selected range.")
else:
    fig, ax_p, ax_o = viz.power_occupancy_panels(figsize=(13, 5.5))

    ax_p.plot(window.index, window["power_w"] / 1000, color=viz.INK,
              linewidth=1.3, label="actual power")
    if show_expected:
        ax_p.plot(window.index, window["expected_w"] / 1000,
                  color=viz.CATEGORICAL[0], linewidth=1.2, alpha=0.9,
                  label="expected (time + occupancy)")

    for band, colour, size in (("WARNING", viz.STATUS["WARNING"], 12),
                               ("ANOMALY", viz.STATUS["ANOMALY"], 22)):
        hits = window[window["band"] == band]
        if not hits.empty:
            ax_p.scatter(hits.index, hits["power_w"] / 1000, s=size,
                         color=colour, zorder=4, label=band.title(),
                         edgecolors="none")

    if show_low_occ:
        ax_p.fill_between(window.index, 0, 1,
                          where=window["low_occupancy"],
                          transform=ax_p.get_xaxis_transform(),
                          color=viz.INK_MUTED, alpha=0.10, linewidth=0,
                          step="mid")

    ax_p.set_title(f"{building.replace('_', ' ')}   {start} to {end}")
    ax_p.legend(ncol=4, loc="upper left", fontsize=8)

    ax_o.plot(window.index, window["occupancy"], color=viz.CATEGORICAL[2],
              linewidth=1.2)
    threshold_row = row.iloc[0]["threshold"] if not row.empty else None
    if threshold_row is not None:
        ax_o.axhline(threshold_row, color=viz.INK_MUTED, linestyle="--",
                     linewidth=1)
    plt.setp(ax_o.get_xticklabels(), rotation=20, ha="right")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    st.caption(
        "Two stacked panels rather than two y-axes: watts and people are "
        "different quantities, and a shared axis would invent a relationship "
        "that does not exist. Shaded columns are low-occupancy intervals; the "
        "dashed line on the lower panel is the threshold."
    )

    window_rate = 100 * float(window["band"].eq("ANOMALY").mean())
    overall_rate = 100 * float(data["band"].eq("ANOMALY").mean())

    summary = st.columns(4)
    summary[0].metric("Intervals shown", f"{len(window):,}")
    summary[1].metric(
        "Flagged ANOMALY",
        f"{int(window['band'].eq('ANOMALY').sum()):,}",
        delta=f"{window_rate:.1f}% vs {overall_rate:.1f}% overall",
        delta_color="off",
        help="Share of intervals flagged in this window, against the share "
             "across this building's whole record.",
    )
    summary[2].metric("Low-occupancy intervals",
                      f"{int(window['low_occupancy'].sum()):,}")
    summary[3].metric("Energy in window",
                      f"{window['power_w'].sum() / 1000 * (10 / 60):,.0f} kWh")

    # If this window is flagging far more than the building normally does, say
    # why rather than letting the reader assume the building is on fire.
    if overall_rate > 0 and window_rate > max(3 * overall_rate, 5.0):
        st.warning(
            f"**This window flags {window_rate:.0f}% of intervals against "
            f"{overall_rate:.1f}% across the whole record — that is the model "
            "ageing, not a fault.** These models are fitted on 2014–2016, and "
            "campus consumption grew 32–48% over the record. From around August "
            "2017 the Academic building also began drawing power in the small "
            "hours, and a fixed historical baseline re-reports that same change "
            "every day. Section 9 of the report covers it; a deployed detector "
            "would need periodic refitting.",
            icon="📈",
        )

# ---------------------------------------------------------------------------
# Sensitivity curve
# ---------------------------------------------------------------------------
st.subheader("How much does the answer depend on the threshold?")

sensitivity = results.get("sensitivity")
if sensitivity is not None:
    fig, ax = plt.subplots(figsize=(11, 4))
    for name, group in sensitivity.groupby("building"):
        is_current = name == building
        ax.plot(
            100 * group["fraction_of_p95"], group["share_pct"],
            color=viz.color_for(name) if is_current else "#d8d7d1",
            linewidth=2.4 if is_current else 1.2,
            zorder=3 if is_current else 1,
            label=name.replace("_", " ") if is_current else None,
        )
    ax.axvline(100 * C.LOW_OCC_FRACTION, color=viz.STATUS["ANOMALY"],
               linestyle="--", linewidth=1.3)
    ax.annotate("threshold used in the report",
                xy=(100 * C.LOW_OCC_FRACTION, ax.get_ylim()[1] * 0.9),
                xytext=(6, 0), textcoords="offset points", fontsize=8,
                color=viz.STATUS["ANOMALY"])
    ax.set_xlabel("Threshold as % of the building's 95th-percentile occupancy")
    ax.set_ylabel("% of energy used at or below the threshold")
    ax.set_title(f"{building.replace('_', ' ')} highlighted against the other buildings")
    ax.legend(loc="upper left", fontsize=9)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)
    st.caption(
        "The headline uses 5%. This curve shows what every other threshold from "
        "0% to 20% would have given, so the finding can be judged independently "
        "of that choice."
    )

# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------
with st.expander("Headline table -- all buildings"):
    if not headline.empty:
        st.dataframe(headline, use_container_width=True, hide_index=True)

with st.expander("Does occupancy help an anomaly detector?"):
    detectors = results.get("detectors")
    if detectors is not None:
        st.dataframe(detectors, use_container_width=True, hide_index=True)
        st.caption(
            "Detector T uses time only; Detector O adds occupancy. All five fair "
            "comparisons favour O, by one to three percentage points each, with "
            "the largest gains on the waste anomalies. The anomalies used to "
            "score them were SYNTHETIC, injected with a fixed seed purely to "
            "create known labels."
        )

with st.expander("Comparison with published figures"):
    published = results.get("published")
    if published is not None:
        st.dataframe(published, use_container_width=True, hide_index=True)
        st.caption(
            "Applying Masoso & Grobler's clock-based definition to this data "
            "gives 55.2% for the Academic building and 55.0% for the Library, "
            "against their published 56%."
        )

with st.expander("Data quality"):
    quality = results.get("quality")
    if quality is not None:
        st.dataframe(quality, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Data: I-BLEND (Rashid, Singh & Singh, Scientific Data 2019). "
    "Occupancy is a count of WiFi-associated devices, not people, and never "
    "reaches zero — which is why every result here uses a relative "
    "low-occupancy threshold rather than 'empty'. Full method and caveats in "
    "docs/PROJECT_REPORT.md."
)
