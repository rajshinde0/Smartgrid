"""Chart style and saving helpers, so every figure in the report looks the same.

Palette
-------
The seven building colours are the first seven slots of a validated categorical
palette, assigned in fixed slot order and never cycled. The ordering was checked
with a colour-vision-deficiency validator on the adjacent pairlist (the one that
applies to lines, bars and stacks):

    Lightness band       PASS  all 7 inside L 0.43-0.77
    Chroma floor         PASS  all 7 >= 0.1
    CVD separation       PASS  worst adjacent pair dE 9.1 (protanopia)
    Normal-vision floor  PASS  worst adjacent pair dE 19.6
    Contrast vs surface  WARN  aqua/yellow/magenta below 3:1

The contrast warning obliges "relief": the reader must be able to recover the
numbers without relying on colour. Every figure in this project is published in
docs/PROJECT_REPORT.md directly beside the markdown table of the same numbers,
which is that relief.

Two rules we follow deliberately
--------------------------------
1. **No dual-axis charts.** Power (W) and occupancy (people) never share a y
   axis. Where both must be read against the same clock we use two stacked
   panels with a shared x axis -- see `power_occupancy_panels`.
2. **Colour follows the building, not its rank.** A chart that drops a building
   does not repaint the others, because the colour is looked up by name.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")                      # notebooks run headless under nbconvert
import matplotlib.pyplot as plt     # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from . import config as C           # noqa: E402

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
# Categorical slots, in the validated order. Do not reorder.
CATEGORICAL = [
    "#2a78d6",   # 1 blue
    "#eb6834",   # 2 orange
    "#1baf7a",   # 3 aqua
    "#eda100",   # 4 yellow
    "#e87ba4",   # 5 magenta
    "#008300",   # 6 green
    "#4a3aa7",   # 7 violet
    "#e34948",   # 8 red
]

# Building -> colour, fixed for the whole project.
BUILDING_COLORS = {
    name: CATEGORICAL[i] for i, name in enumerate(C.BUILDING_ORDER)
}

# Chart chrome (light surface)
SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# Status colours -- reserved. Never used as a series colour.
STATUS = {
    "NORMAL": "#0ca30c",
    "WARNING": "#fab219",
    "SERIOUS": "#ec835a",
    "ANOMALY": "#d03b3b",
}

# Sequential single-hue blue ramp (magnitude: heatmaps, missing-data maps)
BLUE_STEPS = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
    "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
    "#184f95", "#104281", "#0d366b",
]
SEQ_BLUE = LinearSegmentedColormap.from_list("seq_blue", BLUE_STEPS)

# Diverging blue <-> red with a neutral grey midpoint (never a hue at the middle)
DIVERGING = LinearSegmentedColormap.from_list(
    "div_blue_red", ["#0d366b", "#2a78d6", "#f0efec", "#d03b3b", "#7a1f1f"]
)


def setup_style() -> None:
    """Apply the project chart style. Call once near the top of each notebook."""
    plt.rcParams.update(
        {
            # surfaces
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            # type: one UI sans everywhere, no display or serif face
            "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "semibold",
            "axes.titlelocation": "left",
            "axes.labelsize": 10,
            "axes.labelcolor": INK_SECONDARY,
            "text.color": INK,
            # recessive grid and axes
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.edgecolor": AXIS,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelcolor": INK_SECONDARY,
            "ytick.labelcolor": INK_SECONDARY,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            # thin marks
            "lines.linewidth": 2.0,
            "lines.markersize": 4,
            "patch.linewidth": 0,
            # legend: present for every multi-series chart, never a box shout
            "legend.frameon": False,
            "legend.fontsize": 9,
            "legend.labelcolor": INK_SECONDARY,
            # output
            "figure.dpi": 110,
            "savefig.dpi": 140,
            "savefig.bbox": "tight",
            "figure.autolayout": False,
        }
    )


def color_for(building: str) -> str:
    """Colour of one building. Looked up by name so filtering never repaints."""
    return BUILDING_COLORS.get(building, CATEGORICAL[7])


def save_fig(fig, name: str, *, close: bool = True) -> Path:
    """Save a figure to figures/<name>.png and print the report-ready link."""
    C.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    if not name.endswith(".png"):
        name = name + ".png"
    path = C.FIGURES_DIR / name
    fig.savefig(path)
    if close:
        plt.close(fig)
    print(f"saved  figures/{name}   ->  ![...](../figures/{name})")
    return path


def annotate_takeaway(ax, text: str) -> None:
    """Put a one-line plain-English takeaway under a chart."""
    ax.figure.text(
        0.01, -0.03, text, ha="left", va="top",
        fontsize=9, color=INK_SECONDARY, wrap=True,
    )


def power_occupancy_panels(figsize=(11, 5.5)):
    """Two stacked panels sharing one time axis: power on top, occupancy below.

    Deliberately NOT a dual-axis chart. Watts and people are different
    quantities; putting them on one y axis invents a visual relationship that
    does not exist. Stacked panels keep the clock shared and the scales honest.
    """
    fig, (ax_p, ax_o) = plt.subplots(
        2, 1, figsize=figsize, sharex=True,
        gridspec_kw={"height_ratios": [2, 1], "hspace": 0.12},
    )
    ax_p.set_ylabel("Power (kW)")
    ax_o.set_ylabel("Occupancy\n(devices seen)")
    return fig, ax_p, ax_o


def power_occupancy_weather_panels(figsize=(13, 7)):
    """Three stacked panels sharing one time axis: power, occupancy, temperature.

    The same principle as `power_occupancy_panels`, extended. Watts, people and
    degrees are three different quantities; stacking them keeps the clock shared
    and every scale honest, where a second or third y axis would invent
    relationships that are not in the data.

    Reading down the three panels is the whole point: it is how you see that a
    building's overnight power is flat while the temperature swings, or that a
    hot afternoon and a power peak line up.
    """
    fig, (ax_p, ax_o, ax_t) = plt.subplots(
        3, 1, figsize=figsize, sharex=True,
        gridspec_kw={"height_ratios": [3, 1.2, 1.2], "hspace": 0.12},
    )
    ax_p.set_ylabel("Power (kW)")
    ax_o.set_ylabel("Occupancy\n(devices seen)")
    ax_t.set_ylabel("Outdoor\ntemperature (C)")
    return fig, ax_p, ax_o, ax_t


def thousands(ax, axis: str = "y") -> None:
    """Readable thousands separators on an axis."""
    fmt = mpl.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)
