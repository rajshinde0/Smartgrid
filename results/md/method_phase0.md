
Exploration was done before any cleaning, to find out what the data actually
contains rather than what the documentation promises.

**What we did.** We listed every file with its size; read both `Readme.txt` files
and the ISA-Tab metadata that records the instruments used; printed the first and
last rows of all 9 energy meters and all 7 occupancy
files; and profiled each file for coverage, gaps and data-quality counts.

**How we handled the size.** The energy folder is about 1.5 GB, so no step ever
loads it all. Files are read one at a time, in chunks of 500,000 rows, keeping
only the needed columns. Reading the last rows of a 125 MB file, for example, is
done by streaming through it and keeping only the final chunk.

**Timestamps.** All UNIX timestamps are converted with
`pd.to_datetime(..., unit="s", utc=True).dt.tz_convert("Asia/Kolkata")`, which is
what the dataset readme requires. Getting this wrong by 5.5 hours would put every
"night-time" reading in the afternoon and silently invalidate the entire project.

**Coverage measurement.** Rather than drawing a bar from each meter's first to its
last timestamp -- which makes a meter that went silent for 200 days look
continuous -- we counted readings per calendar month and divided by how many that
month should contain (1440 per day for the 1-minute energy files, 144 per day for
the 10-minute occupancy files). That is what the heatmap in section 4.8 shows.

**Notebook:** `notebooks/00_explore.ipynb`.
