import os

import pandas as pd


def print_summary(seq_results, par_results, stats):
    print("=" * 55)
    print("       PARALLEL DATA ANALYZER")
    print("       Online Retail II UCI Dataset")
    print("=" * 55)
    print(f"CPU Cores: {stats['num_workers']}")
    print(f"Dataset:   {stats['original_rows']:,} rows loaded  |  "
          f"{stats['removed_rows']:,} removed  |  "
          f"{stats['cleaned_rows']:,} remaining")
    print(f"Chunks:    {stats['total_chunks']} total")

    print("\n" + "=" * 55)
    print("           ANALYSIS RESULTS")
    print("=" * 55)
    print(f"\nTotal Revenue:    £{par_results['total_revenue']:,.2f}")
    print(f"Avg Order Value:  £{par_results['avg_order_value']:,.2f}")

    print("\nTop 5 Products:")
    for _, row in par_results['top_products'].head(5).iterrows():
        print(f"  {row['Description'][:40]:<40}  {int(row['Total Quantity']):>8} units")

    print("\nTop 5 Countries by Revenue:")
    for _, row in par_results['revenue_by_country'].head(5).iterrows():
        print(f"  {row['Country']:<30}  £{row['Total Revenue']:>12,.2f}")

    print("\n" + "=" * 55)
    print("           PERFORMANCE COMPARISON")
    print("=" * 55)
    print(f"  Sequential Time:   {stats['seq_time']:.4f} seconds")
    print(f"  Parallel Time:     {stats['par_time']:.4f} seconds")
    print(f"  Speed Improvement: {stats['seq_time'] / stats['par_time']:.2f}x faster")
    print("=" * 55)


def save_report(par_results, stats, report_path):
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    performance_df = pd.DataFrame({
        'Method': ['Sequential Processing', 'Parallel Processing'],
        'Execution Time (seconds)': [round(stats['seq_time'], 4), round(stats['par_time'], 4)],
        'Speed Improvement': ['Baseline', f"{round(stats['seq_time'] / stats['par_time'], 2)}x faster"],
    })

    with open(report_path, 'w') as f:
        f.write("=== PERFORMANCE COMPARISON ===\n")
        performance_df.to_csv(f, index=False)

        f.write("\n=== TOTAL REVENUE ===\n")
        f.write(f"Total Revenue (£),{round(par_results['total_revenue'], 2)}\n")
        f.write(f"Average Order Value (£),{round(par_results['avg_order_value'], 2)}\n")

        f.write("\n=== TOP 10 PRODUCTS BY QUANTITY ===\n")
        par_results['top_products'].to_csv(f, index=False)

        f.write("\n=== REVENUE BY COUNTRY ===\n")
        par_results['revenue_by_country'].to_csv(f, index=False)

        f.write("\n=== TOP 10 CUSTOMERS BY REVENUE ===\n")
        par_results['top_customers'].to_csv(f, index=False)

        f.write("\n=== MONTHLY SALES TREND ===\n")
        par_results['monthly_sales'].to_csv(f, index=False)

    print(f"\nReport saved to: {report_path}")
