# SMARTGRID-X Project Plan

Sep 29, 2026 · @Rajwardhan Shinde

We measure how much electricity a real Indian campus wastes when buildings are nearly empty, and build a system that flags it automatically.

## Project at a glance

**SMARTGRID-X: occupancy-aware energy analysis of a real Indian campus.** We combine 4 years of electricity readings with WiFi-based occupancy counts for 7 buildings at IIIT Delhi to find energy used when nobody is there.

Every chart, model and finding in the project must answer one of these three questions:

1. **Main question:** how much of each building's energy is used when occupancy is near zero?
2. How well do occupancy and time of day predict a building's power use?
3. Can we flag abnormal usage automatically, and how accurately?

If a piece of work does not serve one of these, we cut it.

## Dataset

We use **I-BLEND**, a public dataset from IIIT Delhi ([paper](https://www.nature.com/articles/sdata201915), [data](https://doi.org/10.6084/m9.figshare.c.3893581)). Both parts are downloaded and in the `Dataset` folder.

| Part | Files | Columns | Resolution | Period |
| --- | --- | --- | --- | --- |
| Energy | 9 building meters + 3 transformers + 2 combined files (\~1.6 GB) | timestamp, power (W), current, voltage, frequency, power\_factor | 1 minute | Aug 2013 – Dec 2017 |
| Occupancy | 7 CSVs, one per building (\~21 MB) | timestamp, occupancy\_count | 10 minutes | Feb 2014 – Nov 2017 |
| Data status | 2 CSVs | 1 = reading present, 0 = missing, per building per minute | 1 minute | same as energy |

**Buildings:** Academic, Boys' Hostel, Girls' Hostel, Dining (Mess), Library, Lecture, Facilities. The hostels have separate mains and UPS meters.

**Start with** `all_buildings_power.csv`: it has every building's power side by side in one file.

**Known data problems (these become our cleaning work):**

- `current` is empty (NA) in the early rows of most files
- `power_factor` is sometimes negative, which is not physically valid
- The Lecture building shows 0 power for long stretches, which suggests a dead meter
- The Facilities and Mess meters start months later than the others
- Timestamps are UNIX format and must be converted to Asia/Kolkata time
- Energy is per minute and occupancy is per 10 minutes, so energy must be averaged into 10-minute blocks before merging

**Not in the dataset:** weather, floor area, reactive power, equipment IDs. We do not use or claim any of these.

## Final output

We submit three things, all in Python.

| Deliverable | What it contains | Who it's for |
| --- | --- | --- |
| **Report** | Problem, data, method, findings with charts, limitations, future scope | Examiner (this is what is graded) |
| **Jupyter notebook** | The full pipeline, one section per phase below, runs top to bottom | Examiner and teacher, to verify the work |
| **Streamlit dashboard** | One page: pick a building, see power vs. occupancy, flagged anomalies and its wasted-energy % | Live demo during the presentation |

**The headline result** we are working toward is one sentence per building, for example: *"The Library uses X% of its electricity when fewer than 5 people are inside."*

## Plan of action

**Phase 0 comes first:** a rough version of the whole pipeline on one building (Academic), so we can always show a working project. Phases 1–7 then extend and improve it.

| Phase | Work | What it produces | Syllabus |
| --- | --- | --- | --- |
| 0. Rough pipeline | Academic building only: load, merge, basic cleaning, a few charts, simple regression, basic anomaly flags | A working end-to-end demo | All units, lightly |
| 1. Data prep | Convert timestamps, average to 10-min blocks, merge with occupancy, handle NAs, invalid values, dead meters | One clean merged table per building + data quality summary | Unit III, IV, V |
| 2. Statistics + EDA | Attribute types, descriptive statistics, distributions, hourly/weekly/semester patterns, power vs. occupancy | EDA charts and statistics tables | Unit I, II, V, VI |
| 3. PCA | 24-hour daily load vectors, PCA, day-type groups | Scree plot + day-type chart | Unit IV |
| 4. Regression | Simple and multiple linear regression, time-based split, MAE/RMSE/R² | Baseline models and results table | Unit V, VI |
| 5. Wasted energy | Low-occupancy energy share, sensitivity curve, base load vs. per-person load | **The headline finding** | Unit II, VI |
| 6. Anomaly experiment | Time-only vs. time + occupancy detector, injected anomalies, confusion matrix/precision/recall | Detector comparison + top real anomalies | Unit III, V |
| 7. Deliver | Streamlit dashboard, report, presentation | Final submission | Unit VI |

The injected anomalies in phase 5 are for testing only. The report must say clearly that they are synthetic and never present them as real faults.

## Novelty

**Our claim: the first occupancy-aware energy-waste and anomaly analysis of the I-BLEND campus dataset.** The methods are standard, and measuring energy use in unoccupied buildings has been studied before. What we found no published work doing is applying them to I-BLEND.

| Idea | Status in published work | How we use it |
| --- | --- | --- |
| % of energy used at low occupancy, per building | Done elsewhere (56% in commercial buildings, 27.5–31.5% in dormitories), not on I-BLEND | Main finding. We add a threshold sensitivity curve and a base-load vs. per-person split, which aren't published for I-BLEND. |
| Occupancy-aware anomaly detection | Detection methods exist, including on this campus, but none uses the WiFi occupancy data | A controlled experiment: time-only vs. time + occupancy detector on injected "waste" anomalies |
| PCA day-type clustering | Already done on this campus by the dataset's authors | Supporting analysis only, not claimed as novel |

If asked "what's new here?": *we measure how much energy empty campus buildings use, and test whether occupancy data helps detect that waste automatically.* Full sources are in the Implementation Plan tab.

## Team roles

Fill in names. Everyone helps with Phase 0.

| Role | Owns | Name |
| --- | --- | --- |
| Data lead | Phase 1: loading, merging, cleaning, data quality summary |  |
| Analysis lead | Phases 2–3: statistics, EDA, PCA |  |
| Modelling lead | Phases 4–5: regression, anomaly detection, evaluation |  |
| Insight lead | Phase 6: wasted-energy analysis and headline findings |  |
| Delivery lead | Phase 7: dashboard, report, slides |  |

## How we work

The teacher can ask to see progress at any time, so the project must always be in a showable state.

- [ ] **One notebook that always runs top to bottom.** Never leave it broken overnight.
- [ ] **Shared GitHub repo.** Everyone commits their own work, so progress and contributions are visible.
- [ ] **`progress.md` in the repo.** Three lines per update: what was done, what we found, what's next.
- [ ] **Load one building at a time.** 1.6 GB of 1-minute data is slow in pandas; average it into 10-minute blocks first and save the result.
- [ ] **Never invent numbers.** Every figure in the report comes from the notebook.

## Out of scope

These were in the original project description but are dropped. They go in the report as one line each under **Future scope**.

- Weather integration and floor-area energy intensity (not in the dataset)
- Fault intelligence, Energy Health Index, recommendation engine
- Gradient boosting and other advanced models
- Real-time IoT, streaming, cloud, API or production architecture
