| Unit | Topic | Where it is implemented |
|---|---|---|
| I | What data science is; the big-data hype and getting past it | Report section 2.1-2.2 |
| I | Datafication (smart meters as the example) | Report section 2.3 |
| I | The current landscape of data science | Report section 2.4 |
| I | Statistical inference: populations and samples | 02_stats_eda.ipynb, Steps 1 and 5 |
| I | Probability distributions; fitting a model | 02_stats_eda.ipynb, Step 6 (Normal vs Log-normal, Q-Q, KS) |
| I | Statistical modelling; overfitting | 04_regression.ipynb, Step 11 (polynomial degree and forest depth curves) |
| I | Python environment for data science | 00_explore.ipynb, Step 0; requirements.txt |
| II | Attribute types: nominal, ordinal, binary, asymmetric binary, numeric, discrete vs continuous | 02_stats_eda.ipynb, Step 2 (full attribute table) |
| II | Mean, median, mode; range, quartiles, variance, SD, IQR | 02_stats_eda.ipynb, Steps 3-4 (pandas, then by hand in NumPy) |
| II | Graphic displays of statistical descriptions | 02_stats_eda.ipynb, Step 8 (histograms, box plots, Q-Q plots) |
| III | Data sources and data quality | 00_explore.ipynb, Steps 5-10; 01_data_prep.ipynb, Step 2 |
| III | Data cleaning; identifying outliers | 01_data_prep.ipynb, Steps 3-6 (invalid values, dead meters, IQR and Z-score flags) |
| III | Hypothesis testing and its relation to EDA | 02_stats_eda.ipynb, Step 7 (t-test and Mann-Whitney with effect sizes) |
| III | Data transformation; data scaling | 01_data_prep.ipynb, Steps 13-14 (log transform; Min-Max vs standardisation) |
| III | Feature selection | 04_regression.ipynb, Step 5 (correlation filter + SelectKBest) |
| IV | NumPy arrays: creating, indexing, slicing, reshaping | 03_pca.ipynb, Step 1 (10-min series reshaped to days x 144) |
| IV | Vectorized operations | 03_pca.ipynb, Step 2 (vectorized vs looped, timed and asserted identical) |
| IV | Multi-dimensional arrays, matrices, matrix subsetting | 03_pca.ipynb, Step 1 (array[row_slice, col_slice]) |
| IV | Principal component analysis | 03_pca.ipynb, Steps 4-6 (by hand with np.linalg.eig, verified against scikit-learn) |
| IV | Categorical data: category levels and summaries | 01_data_prep.ipynb, Step 12 (ordered pd.Categorical for weekday) |
| IV | DataFrames: loc / iloc, extending, sorting | 01_data_prep.ipynb, Step 11 |
| IV | Lists and dictionaries; analysing a CSV with them | 01_data_prep.ipynb, Step 15 (csv module only, asserted equal to pandas) |
| V | Importing data; head / tail / info / describe | 01_data_prep.ipynb, Step 1 |
| V | Aggregation, grouping, merging, concatenating | 01_data_prep.ipynb, Steps 8 and 10 (merge with occupancy; pd.concat long table; groupby summaries) |
| V | EDA: descriptive statistics, distributions, correlation, trends; Matplotlib / Seaborn | 02_stats_eda.ipynb, Steps 3-8 |
| V | Feature extraction, encoding, scaling | 01_data_prep.ipynb, Step 8 (lags, rolling, kWh); 04_regression.ipynb, Step 4 (one-hot, scaler inside a Pipeline) |
| V | Training, validation and testing sets; cross-validation | 04_regression.ipynb, Steps 1 and 8 (chronological 70/15/15; TimeSeriesSplit) |
| V | Train-test split using scikit-learn | 04_regression.ipynb, Step 1 (train_test_split with shuffle=False) |
| V | Confusion matrix, accuracy, precision, recall | 06_anomaly.ipynb, Steps 3-5 |
| VI | Pie chart with legend | 02_stats_eda.ipynb, Step 8.1 |
| VI | Bar chart | 02_stats_eda.ipynb, Step 8.2 |
| VI | Box plot | 02_stats_eda.ipynb, Step 8.3 |
| VI | Histogram | 02_stats_eda.ipynb, Step 8.4 |
| VI | Line graph with multiple lines | 02_stats_eda.ipynb, Step 8.5 |
| VI | Scatter plot | 02_stats_eda.ipynb, Step 8.6 |
| VI | 2D and 3D visualization | 03_pca.ipynb, Steps 7-8 (PC1-PC2 scatter; 3D PC1-PC3) |
| VI | Linear regression; multiple linear regression | 04_regression.ipynb, Steps 6 and 9 (models A, B, C) |
| VI | Dashboards and communicating results | dashboard/app.py; docs/PROJECT_REPORT.md |
| III | Integrating an external data source; confounding variables | 08_weather.ipynb, Steps 1-4 (METAR join; separating weather from occupancy with a 2x2 on identical rows) |
| V | Controlling for a confounder in a regression | 08_weather.ipynb, Step 4 (hour-of-day dummies in the cooling-degree fit) |