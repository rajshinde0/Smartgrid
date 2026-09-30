"""SMARTGRID-X central configuration.

Everything that more than one notebook needs to agree on lives here: where the
files are, which meter belongs to which building, and every numeric threshold
the analysis uses. Nothing here is a magic number buried in a notebook -- each
threshold is named, and each one appears in the Decision log of
docs/PROJECT_REPORT.md.

Import it from any notebook with:

    import sys; sys.path.insert(0, "..")
    from src import config as C
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# config.py lives in <project>/src/, so the project root is two levels up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_DIR = PROJECT_ROOT / "Dataset"          # READ-ONLY. Never written to.
ENERGY_DIR = DATASET_DIR / "energy_dataset"
OCCUPANCY_DIR = DATASET_DIR / "IIITD_occupancy_dataset"

DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"          # parquet cache (gitignored)
FIGURES_DIR = PROJECT_ROOT / "figures"          # every chart used in the report
RESULTS_DIR = PROJECT_ROOT / "results"          # small CSV/JSON tables (committed)
DOCS_DIR = PROJECT_ROOT / "docs"
REPORT_PATH = DOCS_DIR / "PROJECT_REPORT.md"

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42

# ---------------------------------------------------------------------------
# Time handling
# ---------------------------------------------------------------------------
# The I-BLEND readme is explicit: UNIX timestamps must be read as Asia/Kolkata
# (UTC+05:30). IST is a whole number of 10-minute blocks off UTC, so 10-minute
# bins line up in both zones -- energy and occupancy timestamps agree exactly.
TIMEZONE = "Asia/Kolkata"
RAW_FREQ = "1min"       # native resolution of the energy meters
TARGET_FREQ = "10min"   # native resolution of the occupancy counts -> our grid

# ---------------------------------------------------------------------------
# Data-quality thresholds (Phase 1). Each is logged in the Decision log.
# ---------------------------------------------------------------------------
VOLTAGE_MIN_V = 180.0       # below this a 230 V single-phase reading is not credible
VOLTAGE_MAX_V = 270.0       # above this likewise
POWER_MAX_W = 200_000.0     # campus-meter sanity ceiling; observed max is ~99 kW
DEAD_METER_HOURS = 6        # power == 0 for longer than this  =>  "meter off"
INTERPOLATE_LIMIT_MIN = 30  # fill gaps up to 30 min; leave longer gaps missing
INTERPOLATE_LIMIT_STEPS = INTERPOLATE_LIMIT_MIN // 10   # in 10-min steps
ZSCORE_OUTLIER = 3.0        # |z| above this is *flagged* (never deleted)

# ---------------------------------------------------------------------------
# Wasted-energy thresholds (Phase 5)
# ---------------------------------------------------------------------------
# "Low occupancy" is relative, not absolute: I-BLEND occupancy never reaches 0
# (WiFi counts idle devices), so a per-building fraction of its own 95th
# percentile is the only defensible definition.
LOW_OCC_FRACTION = 0.05          # headline threshold: 5% of the building p95
LOW_OCC_PERCENTILE = 95          # which percentile the fraction is taken of
SENSITIVITY_FRACTIONS = [f / 100 for f in range(0, 21)]   # 0% .. 20%

# Documented WiFi over-count of idle devices (I-BLEND paper). Used ONLY for the
# secondary "corrected occupancy" robustness check -- never for the headline.
IDLE_DEVICE_BASELINE = {
    "Academic": 50,
    "Boys_Hostel": 20,
    "Girls_Hostel": 20,
    "Mess": 20,
    "Library": 20,
    "Lecture": 20,
    "Facilities": 20,
}

# ---------------------------------------------------------------------------
# Modelling (Phase 4) and anomaly experiment (Phase 6)
# ---------------------------------------------------------------------------
SPLIT_TRAIN = 0.70          # chronological, never shuffled
SPLIT_VAL = 0.15
SPLIT_TEST = 0.15
CV_SPLITS = 5               # TimeSeriesSplit folds on the training set

Z_WARNING = 2.0             # NORMAL < 2 <= WARNING < 3 <= ANOMALY
Z_ANOMALY = 3.0

# Synthetic anomaly injection (Phase 6). SYNTHETIC -- never real faults.
SPIKE_MAGNITUDE = (0.50, 1.00)      # +50% .. +100% of actual power
SPIKE_DURATION_MIN = (10, 30)       # minutes
WASTE_MAGNITUDE = (0.15, 0.30)      # +15% .. +30%
WASTE_DURATION_HOURS = (2, 6)       # hours, injected only in low-occupancy periods
N_SPIKES = 200
N_WASTE = 200

# ---------------------------------------------------------------------------
# Meter registry: one entry per raw energy CSV we treat as a meter.
# ---------------------------------------------------------------------------
METERS = {
    "acad_mains": "acad_build_mains.csv",
    "boys_mains": "boys_hostel_mains.csv",
    "boys_ups": "boys_hostel_ups.csv",
    "girls_mains": "girls_hostel_mains.csv",
    "girls_ups": "girls_hostel_ups.csv",
    "library_mains": "library_build_mains.csv",
    "mess_mains": "mess_build_mains.csv",
    "lecture_mains": "lecture_build_mains.csv",
    "facilities_mains": "facilities_build_mains.csv",
}

TRANSFORMERS = {
    "transformer_1": "transformer_1.csv",
    "transformer_2": "transformer_2.csv",
    "transformer_3": "transformer_3.csv",
}

# Combined / status files
ALL_BUILDINGS_POWER_CSV = ENERGY_DIR / "all_buildings_power.csv"
ALL_TRANSFORMER_POWER_CSV = ENERGY_DIR / "all_transformer_power.csv"
STATUS_BUILDINGS_CSV = ENERGY_DIR / "data_present_status_buildings.csv"
STATUS_TRANSFORMERS_CSV = ENERGY_DIR / "data_present_status_transformers.csv"

# ---------------------------------------------------------------------------
# Building registry: the mapping that ties energy meters to occupancy files.
# Source: Dataset/IIITD_occupancy_dataset/Readme.txt + energy_dataset/Readme.txt
# ---------------------------------------------------------------------------
# kind: "commercial"  = non-residential (offices, classrooms, library, services)
#       "residential" = dormitories where people also sleep
BUILDINGS: dict[str, dict] = {
    "Academic": {
        "occ_code": "ACB",
        "meters": ["acad_mains"],
        "kind": "commercial",
        "label": "Academic Building",
    },
    "Boys_Hostel": {
        "occ_code": "BH",
        "meters": ["boys_mains", "boys_ups"],
        "kind": "residential",
        "label": "Boys Dormitory",
    },
    "Girls_Hostel": {
        "occ_code": "GH",
        "meters": ["girls_mains", "girls_ups"],
        "kind": "residential",
        "label": "Girls Dormitory",
    },
    "Mess": {
        "occ_code": "DB",
        "meters": ["mess_mains"],
        "kind": "commercial",
        "label": "Dining Building (Mess)",
    },
    "Library": {
        "occ_code": "LB",
        "meters": ["library_mains"],
        "kind": "commercial",
        "label": "Library Building",
    },
    "Lecture": {
        "occ_code": "LCB",
        "meters": ["lecture_mains"],
        "kind": "commercial",
        "label": "Lecture Building",
    },
    "Facilities": {
        "occ_code": "SRB",
        "meters": ["facilities_mains"],
        "kind": "commercial",
        "label": "Facilities Building",
    },
}

BUILDING_ORDER = list(BUILDINGS)          # stable order for every table and chart
OCC_CODES = {b: v["occ_code"] for b, v in BUILDINGS.items()}

# Column names used in all_buildings_power.csv / data_present_status_buildings.csv,
# mapped to our meter keys. Used for the independent cross-check.
WIDE_COL_TO_METER = {
    "Academic": "acad_mains",
    "Boys_main": "boys_mains",
    "Boys_backup": "boys_ups",
    "Girls_main": "girls_mains",
    "Girls_backup": "girls_ups",
    "Library": "library_mains",
    "Mess": "mess_mains",
    "Lecture": "lecture_mains",
    "Facilities": "facilities_mains",
}

# ---------------------------------------------------------------------------
# Academic calendar (Phase 1)
# ---------------------------------------------------------------------------
# The dataset authors publish the real IIIT-Delhi calendar as part of the same
# figshare collection as the energy and occupancy data -- one CSV per year,
# 2013 to 2017, covering our analysis window exactly. Columns:
#
#   Date          the day
#   working_day   1 = a working day, 0 = not
#   activity      "H" = high-activity (term-time working day)
#                 "L" = low-activity  (vacation, weekend or holiday)
#
# This is ground truth and it is what the pipeline uses. `tools/get_data.py`
# downloads it alongside the energy and occupancy data.
CALENDAR_GLOB = "calender_year_*.csv"


def calendar_files() -> list[Path]:
    """The per-year calendar CSVs shipped with I-BLEND, if they are present."""
    return sorted(DATASET_DIR.glob(CALENDAR_GLOB))


# Fallback only. If the calendar files are missing, Phase 1 falls back to these
# approximate windows and says so loudly. They agree with the real calendar on
# only about 67% of days, which is why they are a fallback and not the default.
#
# Each window is ((start_month, start_day), (end_month, end_day)), inclusive.
VACATION_WINDOWS = [
    ((5, 16), (7, 31)),     # summer vacation: mid-May to end-July
    ((12, 16), (12, 31)),   # winter break: second half of December
    ((1, 1), (1, 1)),       # New Year day sits inside the winter break
]

SEMESTER_NOTE = (
    "Semester and vacation flags come from the official IIIT-Delhi calendar "
    "published with I-BLEND on figshare (one CSV per year, 2013-2017), which "
    "marks each day as a working day or not and as high- or low-activity."
)

SEMESTER_NOTE_FALLBACK = (
    "FALLBACK IN USE: the official calendar files were not found, so semester "
    "and vacation are approximated as 16 May - 31 Jul and 16 - 31 Dec. Run "
    "tools/get_data.py to fetch the real calendar."
)


def ensure_dirs() -> None:
    """Create every output directory we write to (safe to call repeatedly)."""
    for d in (PROCESSED_DIR, FIGURES_DIR, RESULTS_DIR, DOCS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def meter_path(meter_key: str) -> Path:
    """Absolute path of a raw meter CSV."""
    return ENERGY_DIR / METERS[meter_key]


def occupancy_path(building: str) -> Path:
    """Absolute path of the raw occupancy CSV for one building."""
    return OCCUPANCY_DIR / f"{BUILDINGS[building]['occ_code']}.csv"


def energy_parquet(meter_key: str) -> Path:
    """Where the 10-minute cache for one meter lives."""
    return PROCESSED_DIR / f"energy_10min_{meter_key}.parquet"


def building_parquet(building: str) -> Path:
    """Where the merged, feature-engineered table for one building lives."""
    return PROCESSED_DIR / f"{building}_10min.parquet"


LONG_TABLE_PARQUET = PROCESSED_DIR / "all_buildings_long_10min.parquet"


def building_of_meter(meter_key: str) -> str:
    """Reverse lookup: which building does this meter belong to."""
    for name, spec in BUILDINGS.items():
        if meter_key in spec["meters"]:
            return name
    raise KeyError(f"meter {meter_key!r} belongs to no building")
