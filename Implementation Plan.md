# Implementation Plan

Sep 29, 2026 · @Rajwardhan Shinde

The step-by-step build of SMARTGRID-X: what each phase does, how to do it, and when it counts as done. Each phase ends with something we can show.

## Setup

One shared GitHub repo, one environment, the same folder layout for everyone.

**Repo structure**

```
smartgrid-x/
├── data/
│   ├── raw/          # I-BLEND files as downloaded (NOT pushed to GitHub, too big)
│   └── processed/    # our 10-min merged files, saved as .parquet
├── notebooks/
│   ├── 00_rough_pipeline.ipynb
│   ├── 01_data_prep.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_pca.ipynb
│   ├── 04_regression.ipynb
│   ├── 05_waste.ipynb
│   └── 06_anomaly.ipynb
├── src/              # shared functions: load, clean, merge, plot
├── dashboard/app.py  # Streamlit
├── figures/          # every chart used in the report
├── progress.md
└── requirements.txt
```

**Libraries:** pandas, numpy, pyarrow, matplotlib, seaborn, scikit-learn, scipy, streamlit, plotly.

**Rules**

- Add `data/raw/` to `.gitignore`. Each member downloads I-BLEND locally.
- Functions used in more than one notebook go in `src/`, not copy-pasted.
- Every saved chart goes into `figures/` with a clear name (`fig_03_hourly_profile_academic.png`).

**Syllabus additions (Unit I, Tutorial 6)**

- Document the Python environment in the notebook: Python version, `pip`/virtual environment, Jupyter, and why each library is used.
- Write the loading and cleaning code as **functions** in `src/` (for example `load_building(name)`, `clean(df)`), and use a `for` loop with `if` conditions to process all buildings. This covers functions and control structures.

**Done when:** everyone can clone the repo, install `requirements.txt`, and load one CSV.

## Phase 0: Rough pipeline on one building

Build a crude but complete version on the **Academic building** first, so there is always a working project to show.

1. Load `acad_build_mains.csv` and `ACB.csv` (occupancy).
2. Convert timestamps to Asia/Kolkata time.
3. Average power into 10-minute blocks and merge with occupancy on timestamp.
4. Drop rows with missing values (proper cleaning comes in Phase 1).
5. Plot power and occupancy over one week on the same chart.
6. Fit one linear regression: power \~ occupancy.
7. Flag readings whose residual is more than 3 standard deviations away.
8. Compute one number: % of energy used when occupancy is in the lowest 10% of values.

**Done when:** `00_rough_pipeline.ipynb` runs top to bottom and produces the week chart, the regression result and the low-occupancy %. Everything later replaces a crude step here with a proper one.

## Phase 1: Data preparation

Turn 1.6 GB of raw files into one clean, merged 10-minute table per building. Syllabus: Unit III, IV, V.

**Steps**

1. **Load one building at a time.** Read only the columns needed; convert `timestamp` with `pd.to_datetime(..., unit='s', utc=True).dt.tz_convert('Asia/Kolkata')`.
2. **Missing data report.** Use `data_present_status_buildings.csv` to count missing minutes per building per month. Plot it as a heatmap.
3. **Invalid values.**
   - Negative `power_factor` → investigate per meter (may be a meter wiring sign issue); take the absolute value or set to NaN, and document the choice.
   - Negative or impossible `power` → NaN.
   - Voltage outside 180–270 V → NaN.
4. **Dead meter periods.** Flag stretches where power is exactly 0 for more than 6 hours (e.g. Lecture). Mark them as "meter off", not as zero consumption.
5. **Outliers.** Detect with IQR and Z-score, but **flag, don't delete**: real spikes are what the anomaly phase looks for.
6. **Resample.** Average power into 10-minute blocks (`.resample('10min').mean()`) to match occupancy.
7. **Merge** energy with occupancy on timestamp (inner join). Occupancy only covers **16 Feb 2014 – 3 Nov 2017**, so that is our working period.
8. **Fill small gaps** (≤ 30 min) by interpolation; leave longer gaps as missing.
9. **Add features:** hour, day of week, month, weekend flag, and semester/vacation flag (from the I-BLEND calendar file on the project's GitHub site).
10. **Save** each building to `data/processed/<building>.parquet`.

**Hostels:** keep mains and UPS as separate columns, plus a total. The mains vs. UPS split is used in Phase 5.

**Syllabus additions (Unit III, IV, V)**

- **Data inspection:** show `head()`, `tail()`, `info()` and `describe()` for every raw file.
- **Lists & dictionaries:** read one occupancy CSV with Python's `csv` module into a dictionary of lists (no pandas), and compute count, min, max and mean by hand. This is the syllabus task "analyze a CSV dataset using lists and dictionaries".
- **Categorical data:** convert building, day of week and semester flag to `pd.Categorical`. Show category levels and `value_counts()` summaries. Make day of week an **ordered** category.
- **`loc` / `iloc`:** use both for selecting date ranges and columns, and explain the difference in a markdown cell.
- **Extending and sorting DataFrames:** add derived columns (energy in kWh = power × time, hour, weekday); sort by timestamp and by power.
- **Concatenating:** `pd.concat` all 7 processed buildings into one long table with a `building` column (used for cross-building EDA).
- **Aggregation and grouping:** `groupby` building, hour and month for averages and totals.
- **Data transformation:** apply a **log transform** to skewed power values and compare histograms before and after.
- **Data scaling:** show Min-Max scaling and standardisation side by side, and explain which models need it.
- **Feature extraction:** lag features (power 1 hour and 1 day earlier) and rolling features (24-hour rolling mean and standard deviation).

**Done when:** 7 processed files exist, plus a data-quality table (rows, % missing, dead-meter hours, invalid values fixed) per building.

## Phase 2: Statistics and EDA

Describe the data before modelling it. Syllabus: Unit I, II, V, VI.

1. **Population vs. sample.** State that the 7 buildings over \~3.7 years are a sample of campus energy use, and what that limits us to claiming.
2. **Attribute types table.** Classify every column: timestamp (interval), building (nominal), semester flag (binary), weekend (binary), day of week (ordinal), occupancy\_count (discrete numeric), power / voltage / current (continuous).
3. **Descriptive statistics per building:** mean, median, mode, range, variance, standard deviation, quartiles, IQR for power and occupancy.
4. **Distributions:** histograms and box plots of power per building. Check skewness.
5. **Patterns:**
   - Average power by hour of day (one line per building)
   - Weekday vs. weekend
   - Semester vs. vacation
   - Monthly trend across the years
   - Hostel vs. academic buildings (hostels peak at night, academic in the day)
6. **Power vs. occupancy:** scatter plot and Pearson correlation per building. Compare with the correlations reported in the I-BLEND paper as a sanity check.
7. **Correlation matrix** of all numeric features.

**Syllabus additions (Unit I, II, III, VI; Tutorials 1–3)**

- **Population vs. sample simulation (Tutorial 1):** treat all days as the population. Draw 1,000 random samples of 30 days, plot the distribution of sample means, and compare it with the population mean. This demonstrates statistical inference.
- **Manual calculation (Tutorial 2):** compute mean, median, mode, variance, standard deviation and IQR by hand with NumPy formulas for one building, then check against pandas.
- **Probability distributions and model fitting:** fit Normal and Log-normal distributions to power with `scipy.stats`, overlay them on the histogram, and compare with a Q-Q plot and a Kolmogorov–Smirnov test. State which fits better.
- **Attribute classification in full (Tutorial 3):** the attribute table must also mark each column by number of values (discrete vs. continuous) and include **asymmetric binary** attributes (the anomaly flag and the meter-off flag, where only the "1" case matters).
- **Hypothesis testing vs. EDA:** after EDA suggests a pattern, test it formally. For example, a t-test or Mann–Whitney U test on semester vs. vacation power, and on weekday vs. weekend power. Report the p-values.
- **Required chart types (Unit VI):**
  - **Pie chart with legend:** each building's share of total campus energy
  - **Bar chart:** average daily energy per building
  - **Box plot:** power per building
  - **Histogram:** power distribution
  - **Multi-line graph:** hourly profile, one line per building
  - **Scatter plot:** power vs. occupancy

**Done when:** `02_eda.ipynb` has a statistics table per building and about 8–10 labelled charts saved in `figures/`, each with a one-line takeaway written under it.

## Phase 3: PCA on daily load profiles

Find the typical "shapes" of a day. This is supporting analysis, not a novelty claim: day clustering on this campus has already been published. Syllabus: Unit IV.

1. For one building, build a matrix with **one row per day and 24 columns** (hourly average power) using NumPy arrays.
2. Drop days with missing hours. Scale each column (`StandardScaler`).
3. Run `PCA`. Plot the **scree plot** (variance explained per component).
4. Plot days on PC1 vs. PC2, **coloured by** weekday/weekend and by semester/vacation.
5. Interpret the components in plain words: PC1 is usually overall level, PC2 the day–night shape.
6. Optionally, group days with k-means on the first 2–3 components and name the groups (e.g. "working day", "holiday", "exam period").
7. Optional extra: use PCA **reconstruction error** as a simple anomaly score for whole days, and compare it with Phase 6.

**Syllabus additions (Unit IV, VI)**

- **NumPy arrays:** build the day matrix with NumPy, not pandas. Take the 10-minute power series as a 1-D array and **reshape** it to (days × 144).
- **Indexing, slicing and matrix subsetting:** select weekdays only, or working hours only, with `array[row_slice, col_slice]`.
- **Vectorized operations:** average each group of 6 columns to get the 24 hourly values without a loop, and compare timing against a Python loop.
- **PCA by hand:** compute the covariance matrix and its eigenvectors with `np.linalg.eig`, then confirm the result matches `sklearn.decomposition.PCA`.
- **3D visualization:** 3D scatter plot of days on PC1, PC2 and PC3, coloured by day type.

**Done when:** scree plot, PC1–PC2 scatter and a short written interpretation exist for at least the Academic and one hostel building.

## Phase 4: Regression models

Predict expected power so we have a baseline to compare against. Syllabus: Unit I, V, VI.

**Split by time, not randomly.** Train on the earlier \~80% of dates and test on the last \~20%. A random split leaks future data into training.

| Model | Inputs | Purpose |
| --- | --- | --- |
| A. Simple linear | occupancy | Intercept = load at zero occupancy; slope = kW per extra person (used in Phase 5) |
| B. Multiple linear, time only | hour, day of week, month, weekend, semester flag (one-hot encoded) | Baseline without occupancy |
| C. Multiple linear, time + occupancy | B's inputs + occupancy | Our main model |
| D. Random forest (optional) | same as C | Checks whether a non-linear model is much better; gives feature importance |

**Evaluate each model:** MAE, RMSE and R² on the test set. Add k-fold cross-validation on the training set using `TimeSeriesSplit`.

**Charts:** actual vs. predicted over one test week; residual histogram; coefficients or feature importance.

**Key question to answer:** does adding occupancy (C vs. B) improve accuracy? A published LBNL study found occupancy adds little to baseline accuracy. Whichever way it goes on I-BLEND, it is a result worth reporting.

**Syllabus additions (Unit I, III, V)**

- **Training, validation and testing sets:** use a three-way time-based split (about 70 / 15 / 15). Tune on validation and report final results on test only.
- **Train-test split using scikit-learn:** use `train_test_split(..., shuffle=False)` so the split stays in time order.
- **Feature selection:** rank features with a correlation filter and `SelectKBest` (or `RFE`), and show which features were kept and why.
- **Feature encoding:** one-hot encode day of week and month (`pd.get_dummies` or `OneHotEncoder`).
- **Feature scaling:** standardise inputs inside a scikit-learn `Pipeline`.
- **Overfitting:** fit polynomial regression of degree 1 to 10 (or random forests of increasing depth), plot training vs. validation error, and mark where overfitting starts.

**Done when:** a results table of MAE / RMSE / R² for models A–C (and D if done) for every building.

## Phase 5: Wasted-energy analysis (headline finding)

Measure how much energy each building uses when it is nearly empty. Syllabus: Unit II, VI.

**Important:** I-BLEND occupancy almost never reaches zero. It is a residential campus, and WiFi counts include idle devices, which adds about 20 extra counts (about 50 in Academic). So we use a **low-occupancy threshold**, not "zero".

**Steps**

1. **Define low occupancy per building:** occupancy ≤ 5% of that building's 95th-percentile occupancy. Report the threshold value used for each building.
2. **Low-occupancy energy share** = energy used in low-occupancy intervals ÷ total energy, as a %.
3. **Sensitivity curve:** recompute the share as the threshold moves from 0% to 20%. Plot one line per building. This shows how robust the result is, and nobody has published it for I-BLEND.
4. **Base load vs. responsiveness:** from Model A (power = a + b × occupancy):
   - *a* = load at zero occupancy
   - *b* = kW per extra occupant
   - Compare *a* with each building's night-time minimum power.
   - Rank buildings by responsiveness (high *b*, low *a* = efficient).
5. **Comparisons unique to this dataset:**
   - Semester vs. vacation: does the low-occupancy share rise in vacations?
   - Hostel mains vs. UPS: which supply keeps running when rooms empty out?
   - Commercial vs. residential buildings
6. **Compare with published numbers:** 56% of energy used out of hours in audited commercial buildings, and 27.5–31.5% used while unoccupied in dormitories.

**Headline output:** one table with, per building, the threshold, low-occupancy energy share, *a*, *b* and responsiveness rank, plus one sentence per building.

**Done when:** the table, the sensitivity curve and the semester/vacation and mains/UPS charts exist.

## Phase 6: Anomaly detection experiment

Test whether knowing occupancy helps catch abnormal usage. Set up as an experiment with a clear answer, not just a pipeline. Syllabus: Unit III, V.

**Two detectors, same test period**

- **Detector T (time only):** residuals from Model B
- **Detector O (time + occupancy):** residuals from Model C

For each detector: residual = actual − predicted. Flag with a Z-score on residuals (NORMAL < 2, WARNING 2–3, ANOMALY > 3) and cross-check with IQR fences.

**Injected test anomalies** (on a copy of the test data only)

| Type | What we add | Simulates |
| --- | --- | --- |
| Spike | +50–100% power for 10–30 min at random times | Sudden equipment surge |
| Waste | +15–30% constant extra load for 2–6 hours, **only during low-occupancy periods** | Lights or AC left on in an empty building |

Inject a few hundred of each, record exactly where they are (these are the labels), then run both detectors.

**Evaluation, per detector and per anomaly type:** confusion matrix, accuracy, precision, recall, F1.

**Hypothesis:** Detector O catches more waste anomalies and raises fewer false alarms on busy-but-normal days. If it doesn't, that is still a valid finding.

**On real data:** run Detector O on the untouched data and list the top 10 real anomalies with date, building and deviation. Call them "unusual patterns worth inspecting", never confirmed faults.

**Done when:** a 2 × 2 results table (detector × anomaly type) with precision, recall and F1, plus the top-10 real anomalies list.

**Must state in the report:** the injected anomalies are synthetic and used for testing only.

## Phase 7: Dashboard, report and presentation

**Streamlit dashboard (one page)**

- Building selector and date range picker
- Power and occupancy over time on one chart
- Anomalies marked on the chart (colour by NORMAL / WARNING / ANOMALY)
- Key numbers: low-occupancy energy share, base load *a*, responsiveness *b*
- The sensitivity curve for the selected building

The dashboard reads the saved `.parquet` files and results. It does not re-run models live.

**Report structure**

1. Introduction and problem statement
2. Related work: the I-BLEND paper, the IIIT-Delhi anomaly papers, Masoso & Grobler, Anderson et al. (see Sources)
3. Dataset and data quality
4. Methodology (Phases 1–6)
5. Results: EDA, PCA, regression, **wasted energy**, anomaly experiment
6. Discussion and limitations: WiFi overcounting, no weather data (seasonal AC mixed in), synthetic anomalies
7. Conclusion and future scope
8. Syllabus / CO mapping table

**Presentation:** about 10–12 slides, led by the headline finding. Each member presents the part they built. End with a live dashboard demo.

**Syllabus additions (Unit I)**

The report introduction must cover: what data science is, the big-data hype and getting past it, and **datafication**, using smart meters turning campus electricity use into data as the example. Link the current landscape of data science to energy analytics in one paragraph.

**Done when:** the dashboard runs with `streamlit run dashboard/app.py`, the report is complete with every figure coming from the notebooks, and the team has rehearsed once.

## Syllabus coverage checklist

Every topic in MD3135 Units I–VI and every tutorial, mapped to where the plan implements it. Tick each one when it is done in the notebook.

| Unit | Topic | Where |
| --- | --- | --- |
| I | Data science definition, big-data hype, datafication, current landscape | Report introduction (Phase 7) |
| I | Statistical inference, populations and samples | Sampling simulation (Phase 2) |
| I | Probability distributions, fitting a model | Normal / Log-normal fit, Q-Q, KS test (Phase 2) |
| I | Statistical modelling, overfitting | Regression models; polynomial degree vs. error curve (Phase 4) |
| I | Python environment for data science | Setup |
| II | Attributes: nominal, ordinal, binary, asymmetric, numeric, discrete vs. continuous | Attribute table (Phase 2) |
| II | Mean, median, mode; range, quartiles, variance, SD, IQR | Statistics table + manual calculation (Phase 2) |
| II | Graphic displays of statistical descriptions | Histograms, box plots, Q-Q plots (Phase 2) |
| III | Data sources and data quality | Data-quality table, missing-data heatmap (Phase 1) |
| III | Data cleaning, identifying outliers | Invalid values, dead meters, IQR / Z-score flags (Phase 1) |
| III | Hypothesis testing vs. EDA | t-test / Mann–Whitney on semester and weekday patterns (Phase 2) |
| III | Data transformation, data scaling | Log transform; Min-Max vs. standardisation (Phase 1) |
| III | Feature selection | Correlation filter + SelectKBest / RFE (Phase 4) |
| IV | NumPy arrays: creating, indexing, slicing, reshaping, vectorized operations | Day matrix (Phase 3) |
| IV | Multi-dimensional arrays, matrices, matrix subsetting | Days × 144 matrix, `array[row_slice, col_slice]` (Phase 3) |
| IV | PCA | By hand with eigenvectors + scikit-learn (Phase 3) |
| IV | Categorical data, category levels and summaries | `pd.Categorical`, ordered day of week (Phase 1) |
| IV | DataFrames: `loc` / `iloc`, extending, sorting | Phase 1 |
| IV | Lists and dictionaries; analyse a CSV with them | Occupancy CSV with the `csv` module (Phase 1) |
| V | Importing data; `head` / `tail` / `info` / `describe` | Phase 1 |
| V | Aggregation, grouping, merging, concatenating | `groupby`, energy + occupancy merge, `concat` of buildings (Phase 1) |
| V | EDA: descriptive statistics, distributions, correlation, trends, Matplotlib / Seaborn | Phase 2 |
| V | Feature selection, extraction, encoding, scaling | Lag / rolling features (Phase 1); one-hot, Pipeline scaling (Phase 4) |
| V | Training, validation and testing sets; cross-validation | 70 / 15 / 15 time split, `TimeSeriesSplit` (Phase 4) |
| V | Train-test split using scikit-learn | `train_test_split(shuffle=False)` (Phase 4) |
| V | Confusion matrix, accuracy, precision, recall | Anomaly experiment (Phase 6) |
| VI | Pie chart with legend, bar chart, box plot, histogram | Phase 2 |
| VI | Line graph with multiple lines, scatter plot | Hourly profiles, power vs. occupancy (Phase 2) |
| VI | 2D and 3D visualization | PC1–PC2 scatter, 3D PCA plot (Phase 3) |
| VI | Linear regression, multiple linear regression | Models A–C (Phase 4) |

**Tutorials**

| Tutorial | Where |
| --- | --- |
| 1. Population vs. sample, data type identification | Phase 2 |
| 2. Central tendency and dispersion by hand, distribution check | Phase 2 |
| 3. Classify attributes | Phase 2 |
| 4. Data cleaning and pre-processing | Phase 1 |
| 5. Vectors, matrices, arrays, DataFrames | Phases 1 and 3 |
| 6. Lists, functions, control structures | Setup, Phase 1 |
| 7. Data visualization | Phases 2, 3 and 7 |
| 8. Linear regression and predictive analytics | Phase 4 |

## Risks and how we handle them

| Risk | Effect | What we do |
| --- | --- | --- |
| 1.6 GB is slow on laptops | Notebooks crash or take hours | Load one building at a time, only needed columns; save 10-min `.parquet` files once and reuse them |
| Occupancy rarely hits zero | "Empty building" result is fragile | Relative low-occupancy threshold + sensitivity curve (Phase 5) |
| WiFi counts ≠ people | Occupancy is overestimated | State it as a limitation; the threshold is relative per building, which reduces the effect |
| No weather data | Seasonal AC load mixes into results | Include month and semester features; state it clearly as a limitation |
| Occupancy may not improve the model | Detector experiment shows no gain | Report it honestly: it matches a published finding and is still a result |
| Examiner asks "what's new?" | Weak answer undermines the project | Use the one-line novelty claim from the Overview tab and cite the prior work ourselves |
| Someone's part breaks the notebook | Nothing to show at a check-in | One notebook per phase; never push a notebook that doesn't run |

## Sources

**Dataset**

- [Rashid, Singh & Singh, I-BLEND, Scientific Data (2019)](https://www.nature.com/articles/sdata201915)
- [I-BLEND data on figshare](https://doi.org/10.6084/m9.figshare.c.3893581)
- [I-BLEND GitHub site (reading scripts, calendar)](https://github.com/i-blend/i-blend.github.io)

**Prior work on this campus**

- [Rashid & Singh, Monitor: day clustering + anomaly detection on IIIT-Delhi loads (2018)](https://loneharoon.github.io/files/monitor.pdf)
- [Arjunan et al., multi-user anomaly detection with partial context (BuildSys 2015)](https://www.samy101.com/projects/energy-anomaly-detection/)
- [Mishra, Lone & Mishra, DECODE: forecasting on I-BLEND with occupancy (2024)](https://arxiv.org/abs/2309.02908)

**Energy used when unoccupied (our comparison numbers)**

- [Masoso & Grobler, The dark side of occupants' behaviour (2010): 56% out of hours](https://www.osti.gov/etdeweb/biblio/21341871)
- [Anderson et al., Energy consumption in dormitories while unoccupied (2015): 27.5–31.5%](https://www.sciencedirect.com/science/article/abs/pii/S0378778814010299)

**Occupancy and energy**

- [Martani et al., ENERNET: WiFi occupancy vs. energy at MIT (2012)](https://www.researchgate.net/publication/257227046)
- [Zhan & Chong, Building occupancy and energy consumption across building types (2021)](https://www.sciencedirect.com/science/article/pii/S2666123320300829)
- [LBNL: baseline models with occupancy data (2016)](https://www.researchgate.net/publication/388952602)
- [Bourdeau et al., daily load profile classification on a campus (2021)](https://www.sciencedirect.com/science/article/abs/pii/S0378778820334563)
