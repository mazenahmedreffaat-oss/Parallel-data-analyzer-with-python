import io
import multiprocessing
import time

import pandas as pd
import streamlit as st

from concurrency.thread_pool import ThreadPool
from data.data_loader import clean, make_chunks
from workers.data_worker import aggregate_results, analyze_chunk

st.set_page_config(
    page_title="Parallel Data Analyzer",
    page_icon="📊",
    layout="wide",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Configuration")
    num_batches = st.slider("Number of batches", 1, 8, 4)
    num_chunks = st.slider("Chunks per batch", 1, 8, 4)
    max_cores = multiprocessing.cpu_count()
    num_workers = st.slider("Worker threads", 1, max_cores, max_cores)
    st.markdown("---")
    st.markdown(f"**Total chunks:** {num_batches * num_chunks}")
    st.markdown(f"**Available CPU cores:** {max_cores}")

# ── Header ───────────────────────────────────────────────────────────────────
st.title("Parallel Data Analyzer")
st.caption("Online Retail II UCI Dataset — Sequential vs Parallel Performance")

# ── File upload ───────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload online_retail_II.csv",
    type=["csv"],
    help="Download from: https://archive.ics.uci.edu/dataset/502/online+retail+ii",
)

if uploaded_file is None:
    st.info("Upload the dataset CSV file above to get started.")
    st.stop()

if st.button("Run Analysis", type="primary", use_container_width=True):
    with st.spinner("Loading and cleaning data..."):
        df = pd.read_csv(uploaded_file, encoding="latin-1")
        original_rows = len(df)
        df = clean(df)
        cleaned_rows = len(df)
        chunks = make_chunks(df, num_batches, num_chunks)

    pool = ThreadPool(num_workers)

    with st.spinner("Running sequential analysis..."):
        seq_start = time.time()
        seq_results = aggregate_results(pool.run_sequential(analyze_chunk, chunks))
        seq_time = time.time() - seq_start

    with st.spinner("Running parallel analysis..."):
        par_start = time.time()
        par_results = aggregate_results(pool.run_parallel(analyze_chunk, chunks))
        par_time = time.time() - par_start

    speedup = seq_time / par_time

    st.session_state.update(
        ran=True,
        par_results=par_results,
        seq_results=seq_results,
        original_rows=original_rows,
        cleaned_rows=cleaned_rows,
        total_chunks=len(chunks),
        seq_time=seq_time,
        par_time=par_time,
        speedup=speedup,
        num_workers=num_workers,
    )

# ── Results ───────────────────────────────────────────────────────────────────
if not st.session_state.get("ran"):
    st.stop()

s = st.session_state
par = s["par_results"]

st.markdown("---")

# Top-level metrics
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Rows Loaded", f"{s['original_rows']:,}")
c2.metric("Rows Removed", f"{s['original_rows'] - s['cleaned_rows']:,}")
c3.metric("Rows Analysed", f"{s['cleaned_rows']:,}")
c4.metric("Total Revenue", f"£{par['total_revenue']:,.2f}")
c5.metric("Speed Improvement", f"{s['speedup']:.2f}x")

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Top Products", "Revenue by Country", "Top Customers", "Monthly Sales", "Performance"]
)

with tab1:
    st.subheader("Top 10 Products by Quantity Sold")
    chart_data = par["top_products"].set_index("Description")["Total Quantity"]
    st.bar_chart(chart_data)
    st.dataframe(par["top_products"].reset_index(drop=True), use_container_width=True)

with tab2:
    st.subheader("Revenue by Country (£)")
    chart_data = par["revenue_by_country"].set_index("Country")["Total Revenue"]
    st.bar_chart(chart_data)
    st.dataframe(par["revenue_by_country"].reset_index(drop=True), use_container_width=True)

with tab3:
    st.subheader("Top 10 Customers by Total Spent")
    top_cust = par["top_customers"].copy()
    top_cust["Customer ID"] = top_cust["Customer ID"].astype(str)
    chart_data = top_cust.set_index("Customer ID")["Total Spent"]
    st.bar_chart(chart_data)
    st.dataframe(top_cust.reset_index(drop=True), use_container_width=True)

with tab4:
    st.subheader("Monthly Revenue Trend")
    chart_data = par["monthly_sales"].set_index("Month")["Monthly Revenue"]
    st.line_chart(chart_data)
    st.dataframe(par["monthly_sales"].reset_index(drop=True), use_container_width=True)

with tab5:
    st.subheader("Sequential vs Parallel")
    p1, p2, p3 = st.columns(3)
    p1.metric("Sequential Time", f"{s['seq_time']:.4f}s")
    p2.metric("Parallel Time", f"{s['par_time']:.4f}s")
    p3.metric("Speedup", f"{s['speedup']:.2f}x faster")

    perf_df = pd.DataFrame(
        {"Time (seconds)": [round(s["seq_time"], 4), round(s["par_time"], 4)]},
        index=["Sequential", "Parallel"],
    )
    st.bar_chart(perf_df)
    st.caption(
        f"Used {s['num_workers']} worker threads across {s['total_chunks']} chunks."
    )

# ── Download report ───────────────────────────────────────────────────────────
st.markdown("---")

buf = io.StringIO()
perf_export = pd.DataFrame({
    "Method": ["Sequential Processing", "Parallel Processing"],
    "Execution Time (seconds)": [round(s["seq_time"], 4), round(s["par_time"], 4)],
    "Speed Improvement": ["Baseline", f"{round(s['speedup'], 2)}x faster"],
})
buf.write("=== PERFORMANCE COMPARISON ===\n")
perf_export.to_csv(buf, index=False)
buf.write("\n=== TOTAL REVENUE ===\n")
buf.write(f"Total Revenue (£),{round(par['total_revenue'], 2)}\n")
buf.write(f"Average Order Value (£),{round(par['avg_order_value'], 2)}\n")
buf.write("\n=== TOP 10 PRODUCTS BY QUANTITY ===\n")
par["top_products"].to_csv(buf, index=False)
buf.write("\n=== REVENUE BY COUNTRY ===\n")
par["revenue_by_country"].to_csv(buf, index=False)
buf.write("\n=== TOP 10 CUSTOMERS BY REVENUE ===\n")
par["top_customers"].to_csv(buf, index=False)
buf.write("\n=== MONTHLY SALES TREND ===\n")
par["monthly_sales"].to_csv(buf, index=False)

st.download_button(
    label="Download Full Report as CSV",
    data=buf.getvalue(),
    file_name="analysis_report.csv",
    mime="text/csv",
    use_container_width=True,
)
