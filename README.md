# Parallel Data Analyzer

A data analysis pipeline built to demonstrate how **parallel processing** cuts analysis time on large datasets. It takes the Online Retail II UCI dataset (~1 million rows), runs the full analysis twice — once sequentially and once in parallel — then reports how much time was saved.

The parallel engine uses Python's `multiprocessing` module with a **fork-based worker pool**. Instead of serializing data and sending it over pipes (which is slow), it forks child processes that inherit the parent's memory directly. Each worker gets its own chunk of data and its own CPU core, so all chunks are analyzed at the same time.

---

## What it analyzes

Given a retail transactions CSV, the pipeline computes:

| Output | Description |
|---|---|
| Total Revenue | Sum of `Quantity × Price` across all valid transactions |
| Average Order Value | Mean revenue per invoice number |
| Top 10 Products | Products ranked by total units sold |
| Revenue by Country | Total revenue grouped by customer country |
| Top 10 Customers | Customers ranked by total amount spent |
| Monthly Sales Trend | Revenue aggregated by calendar month |

All results are shown in the Streamlit UI with interactive charts and tables, and can be downloaded as a CSV report.

---

## Libraries used

| Library | Version | Purpose |
|---|---|---|
| `pandas` | any recent | Loading the CSV, cleaning rows, splitting into chunks, all groupby aggregations |
| `multiprocessing` | stdlib | Forking worker processes and mapping chunks to them in parallel |
| `concurrent.futures` | stdlib | Used as a fallback reference; the parallel engine was moved to `multiprocessing.Pool` |
| `streamlit` | 1.x | The entire web UI — file uploader, sliders, charts, tables, download button |
| `time` | stdlib | Timing the sequential and parallel runs to compute the speedup ratio |

No machine learning libraries are used. All analysis is pure aggregation with pandas.

---

## Requirements

- Python 3.10+
- pandas
- streamlit

```bash
pip install pandas streamlit
```

---

## Setup

1. **Get the dataset**

   Download `online_retail_II.csv` from the [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/502/online+retail+ii) and place it in the `data/` folder:

   ```
   Parallel project/
   └── data/
       └── online_retail_II.csv
   ```

2. **Run the Streamlit UI**

   ```bash
   cd src
   streamlit run app.py
   ```

   Then open **http://localhost:8501** in your browser, upload the CSV, and click **Run Analysis**.

3. **Or run from the terminal (no UI)**

   ```bash
   cd src
   python main.py
   ```

---

## Project structure

```
Parallel project/
├── data/
│   └── online_retail_II.csv          # raw dataset (you provide this)
├── results/
│   └── analysis_report.csv           # generated after each run
└── src/
    ├── main.py                        # terminal entry point
    ├── app.py                         # Streamlit UI entry point
    ├── concurrency/
    │   └── thread_pool.py             # fork-based parallel pool + sequential runner
    ├── data/
    │   └── data_loader.py             # CSV loading, row cleaning, chunk splitting
    ├── services/
    │   └── analysis_service.py        # orchestrates the full pipeline
    ├── workers/
    │   └── data_worker.py             # per-chunk analysis + result aggregation
    └── presentation/
        └── reporter.py                # terminal printer + CSV report writer
```

---

## How the pipeline works

### Step 1 — Load (`data_loader.py: load`)

Reads the CSV into a pandas DataFrame with Latin-1 encoding (required by this dataset).

```
online_retail_II.csv  →  DataFrame with ~1,067,371 rows
```

### Step 2 — Clean (`data_loader.py: clean`)

Four filters are applied to remove bad data:

| Filter | Reason |
|---|---|
| Drop rows where `Invoice` starts with `C` | These are cancellations, not real sales |
| Drop rows where `Quantity <= 0` | Returns and data errors |
| Drop rows where `Price <= 0` | Free or erroneous entries |
| Drop rows where `Description` is null | Incomplete records |

```
~1,067,371 rows  →  ~955,548 rows  (removes ~111,823 bad rows)
```

### Step 3 — Split (`data_loader.py: make_chunks`)

The cleaned DataFrame is divided into **16 independent chunks** (4 batches × 4 chunks per batch). Each chunk is a slice of roughly 60,000 rows. The chunks do not overlap — every row appears in exactly one chunk.

```
955,548 rows  →  16 chunks of ~60,000 rows each
```

This is what makes parallel processing possible: since the chunks are independent, they can be analyzed simultaneously without any coordination between workers.

### Step 4 — Analyze (`data_worker.py: analyze_chunk`)

Each chunk goes through the same set of computations:

```python
Revenue = Quantity × Price          # new column per row

groupby('Description') → sum Quantity      # product totals
groupby('Country')     → sum Revenue       # country totals
groupby('Customer ID') → sum Revenue       # customer totals
groupby('Month')       → sum Revenue       # monthly totals
```

Each call to `analyze_chunk` returns a dictionary with the partial results for that chunk.

### Step 5 — Aggregate (`data_worker.py: aggregate_results`)

After all chunks are processed, their partial results are merged:

- Revenue totals are summed across all chunks
- Product tables are concatenated and re-grouped to get global top 10
- Country, customer, and monthly tables are merged the same way

This is the **reduce** half of a map-reduce pattern: map = analyze each chunk, reduce = merge all results.

### Step 6 — Compare (`analysis_service.py`)

Steps 4 and 5 are executed **twice**:

**Sequential run** — processes one chunk at a time in a plain Python loop:
```python
results = [analyze_chunk(chunk) for chunk in chunks]
```

**Parallel run** — all 16 chunks are dispatched to a fork-based worker pool simultaneously:
```python
with mp.Pool(processes=num_workers) as pool:
    results = pool.map(_dispatch, range(len(chunks)))
```

Both runs are timed with `time.time()`. The ratio `sequential_time / parallel_time` is the speedup.

---

## Why parallel processing saves time

Without parallelism, chunks are processed one after another on a single CPU core:

```
Core 0: [chunk 1] → [chunk 2] → [chunk 3] → ... → [chunk 16]
         ←────────────── total time ──────────────────────────→
```

With parallelism, all cores work simultaneously:

```
Core 0: [chunk 1 ] → [chunk 5 ] → [chunk 9 ] → [chunk 13]
Core 1: [chunk 2 ] → [chunk 6 ] → [chunk 10] → [chunk 14]
Core 2: [chunk 3 ] → [chunk 7 ] → [chunk 11] → [chunk 15]
Core 3: [chunk 4 ] → [chunk 8 ] → [chunk 12] → [chunk 16]
         ←──── total time (≈ 1/4 of sequential) ──────────→
```

On an 8-core machine you can expect roughly 4–6x speedup in practice (not a perfect 8x because of process startup overhead and the final aggregation step which is always sequential).

### Why not threads?

Python threads share one GIL (Global Interpreter Lock), which means only one thread can execute Python code at a time. For CPU-bound work like `groupby` aggregations, threads add context-switching overhead without gaining any parallelism — making things *slower* than sequential.

### Why not `ProcessPoolExecutor`?

`ProcessPoolExecutor` is process-based (no GIL problem), but it sends data to workers by **pickling** it through a pipe. Pickling a 60,000-row DataFrame takes longer than computing the analysis on it, so the overhead dominates and parallel is again slower than sequential.

### The actual solution: fork + global memory

The `ThreadPool` class stores the chunks in a **module-level global variable** before forking workers:

```python
_g_items = items   # set BEFORE the fork
_g_func  = func

with mp.get_context('fork').Pool(processes=N) as pool:
    pool.map(_dispatch, range(len(items)))  # only integers go through the pipe
```

On Linux, `fork` copies the parent process's entire memory into each child instantly using **copy-on-write** — the OS marks the pages as shared and only makes a real copy if a worker writes to them. The chunks are already in memory before the fork, so workers read them for free. The only data that travels through the pipe is a list of small integers (chunk indices).

This is what makes the parallel run genuinely faster than sequential.

---

## Expected terminal output

```
=======================================================
       PARALLEL DATA ANALYZER
       Online Retail II UCI Dataset
=======================================================
CPU Cores: 8
Dataset:   1,067,371 rows loaded  |  111,823 removed  |  955,548 remaining
Chunks:    16 total

=======================================================
           ANALYSIS RESULTS
=======================================================

Total Revenue:    £9,747,747.93
Avg Order Value:  £...

Top 5 Products:
  WHITE HANGING HEART T-LIGHT HOLDER        70,306 units
  ...

Top 5 Countries by Revenue:
  United Kingdom                    £8,187,806.36
  ...

=======================================================
           PERFORMANCE COMPARISON
=======================================================
  Sequential Time:   8.3241 seconds
  Parallel Time:     2.1057 seconds
  Speed Improvement: 3.95x faster
=======================================================
```
