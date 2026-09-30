#### 1. Get the code and the environment

```bash
git clone https://github.com/rajshinde0/Smartgrid.git
cd Smartgrid
python -m pip install -r requirements.txt
python -m ipykernel install --user --name python3
```

Built and tested on **Python 3.14.3**, Windows 11. The pinned versions in
`requirements.txt` were read from the environment the notebooks were actually
executed in, not typed by hand.

#### 2. Get the data

The I-BLEND dataset is about 1.6 GB and is **deliberately not in this
repository**. Download it from <https://doi.org/10.6084/m9.figshare.c.3893581>
and unzip so that these exist:

```
Dataset/energy_dataset/            (16 CSVs + Readme.txt)
Dataset/IIITD_occupancy_dataset/   (7 CSVs + Readme.txt)
```

`Dataset/` is read-only throughout: nothing in this project ever writes to it.

#### 3. Run the notebooks in order

```bash
python tools/build_and_run.py 00_explore
python tools/build_and_run.py 01_data_prep
python tools/build_and_run.py 02_stats_eda
python tools/build_and_run.py 03_pca
python tools/build_and_run.py 04_regression
python tools/build_and_run.py 05_waste
python tools/build_and_run.py 06_anomaly
python tools/build_and_run.py 07_final
```

Each notebook is authored as a percent-format `.py` file in `notebooks/src_py/`.
`tools/build_and_run.py` converts it to a real `.ipynb` and executes it end to
end with `nbconvert`, failing loudly if any cell raises. To execute an existing
notebook directly instead:

```bash
python -m nbconvert --to notebook --execute --inplace notebooks/00_explore.ipynb
```

**Order matters.** Phase 1 builds the parquet cache every later phase reads;
Phase 4 writes the model-A coefficients Phase 5 needs; Phase 5 writes the
headline table the dashboard shows. Phase 1 takes a few minutes on first run
because it reads all 1.6 GB once; after that everything reads the cache. Phase 4
is the slowest at roughly four minutes.

#### 4. Run the dashboard

```bash
streamlit run dashboard/app.py
```

It reads the parquet files and the CSVs in `results/`, and trains nothing. If
the parquet files are missing, run notebook 07 first, or:

```bash
python -c "import sys; sys.path.insert(0, '.'); from src import dashboard; dashboard.export_all()"
```

#### 5. Check nothing leaked into git

```bash
python tools/check_no_data.py
```

Fails if any file under `Dataset/` or `data/`, any `.parquet`, or any file over
50 MB has been staged.

#### Reproducibility notes

* **Seed 42** is used for every random operation -- the sampling simulation,
  k-means, the random forest and the anomaly injection -- so every number in the
  report is exactly reproducible.
* **Every number in the report comes from executed code.** The report contains
  named blocks that the notebooks fill through `src/report.py`; nothing is typed
  by hand. Re-running a notebook rewrites its blocks, so the report cannot drift
  out of step with the analysis.
* **Nothing is committed unless it runs.** A notebook only reaches the repository
  after `tools/build_and_run.py` exits 0.