"""SMARTGRID-X -- the reusable half of the project.

Everything here is imported by the notebooks in `notebooks/src_py/`. The split
is deliberate and worth stating once: **this package holds logic, the notebooks
hold narrative.** A function lives here if it is used more than once, needs to
be tested, or would bury the argument of a notebook in mechanics. Anything that
exists to tell the story -- the prose, the figures, the decision log entries --
stays in the notebook.

That is why no module here prints a conclusion or writes to the report. They
return values; the notebooks decide what those values mean.

The layers
----------
Modules only ever import downwards in this list, so the package has no cycles.

**Foundation**

- `config`    -- paths, the building registry, and *every* threshold in the
                project. If a number governs behaviour, it is defined here and
                nowhere else, so a reader can audit the assumptions in one file.

**Reading raw data** (one building at a time; the 1.6 GB is never all in memory)

- `ingest`    -- chunked CSV -> 10-minute parquet cache for the energy meters
- `occupancy` -- WiFi-derived occupancy counts, and what "low occupancy" means
- `weather`   -- Delhi airport METAR, cooling degree hours, base-temperature fit

**Turning readings into a table**

- `clean`     -- dead meters, outliers, and which gaps may be interpolated
- `features`  -- calendar features, the semester flag, lags and rolling stats
- `build`     -- the convergence point: assembles one clean, merged,
                feature-engineered 10-minute table per building. Most analysis
                starts with `build.build_building(name)`.

**Analysis** (each answers one research question, and none depends on another)

- `explore`   -- Phase 0 profiling: describe a raw file without loading it all
- `stats`     -- descriptive statistics, distribution fitting, hypothesis tests
- `pca`       -- daily load profiles as a matrix, and their principal components
- `models`    -- the regression models that predict expected power (RQ2)
- `waste`     -- the headline calculation: energy used while nearly empty (RQ1)
- `anomaly`   -- the detector experiment: does occupancy help? (RQ3)

**Output**

- `viz`       -- chart style, the validated palette, and the no-dual-axis rule
- `report`    -- writes generated tables into docs/PROJECT_REPORT.md
- `dashboard` -- scores every interval once and saves it for the Streamlit app
- `nbbuild`   -- percent-format .py -> .ipynb (stands alone; imports nothing)

Two conventions that hold throughout
------------------------------------
1. **Timestamps are tz-aware `Asia/Kolkata`**, as the dataset readme requires.
   A naive timestamp anywhere in this package is a bug.
2. **Nothing writes to `Dataset/`.** It is read-only input. Generated files go
   to `data/`, `figures/` or `results/`, and `tools/check_no_data.py` fails the
   build if any of them is ever staged for commit.
"""
