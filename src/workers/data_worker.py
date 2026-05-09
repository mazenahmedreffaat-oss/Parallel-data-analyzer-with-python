import pandas as pd


def analyze_chunk(chunk):
    chunk = chunk.copy()
    chunk['Revenue'] = chunk['Quantity'] * chunk['Price']

    top_products = (
        chunk.groupby('Description')['Quantity']
        .sum()
        .reset_index()
        .rename(columns={'Quantity': 'Total Quantity'})
    )

    revenue_by_country = (
        chunk.groupby('Country')['Revenue']
        .sum()
        .reset_index()
        .rename(columns={'Revenue': 'Total Revenue'})
    )

    active_customers = (
        chunk.dropna(subset=['Customer ID'])
        .groupby('Customer ID')['Revenue']
        .sum()
        .reset_index()
        .rename(columns={'Revenue': 'Total Spent'})
    )

    chunk['Month'] = pd.to_datetime(chunk['InvoiceDate']).dt.to_period('M')
    monthly_sales = (
        chunk.groupby('Month')['Revenue']
        .sum()
        .reset_index()
        .rename(columns={'Revenue': 'Monthly Revenue'})
    )
    monthly_sales['Month'] = monthly_sales['Month'].astype(str)

    return {
        'total_revenue': chunk['Revenue'].sum(),
        'avg_order_value': chunk.groupby('Invoice')['Revenue'].sum().mean(),
        'top_products': top_products,
        'revenue_by_country': revenue_by_country,
        'active_customers': active_customers,
        'monthly_sales': monthly_sales,
    }


def aggregate_results(chunk_results):
    total_revenue = sum(r['total_revenue'] for r in chunk_results)
    avg_order_value = sum(r['avg_order_value'] for r in chunk_results) / len(chunk_results)

    top_products = (
        pd.concat([r['top_products'] for r in chunk_results])
        .groupby('Description')['Total Quantity']
        .sum()
        .reset_index()
        .sort_values('Total Quantity', ascending=False)
        .head(10)
    )

    revenue_by_country = (
        pd.concat([r['revenue_by_country'] for r in chunk_results])
        .groupby('Country')['Total Revenue']
        .sum()
        .reset_index()
        .sort_values('Total Revenue', ascending=False)
    )

    top_customers = (
        pd.concat([r['active_customers'] for r in chunk_results])
        .groupby('Customer ID')['Total Spent']
        .sum()
        .reset_index()
        .sort_values('Total Spent', ascending=False)
        .head(10)
    )

    monthly_sales = (
        pd.concat([r['monthly_sales'] for r in chunk_results])
        .groupby('Month')['Monthly Revenue']
        .sum()
        .reset_index()
        .sort_values('Month')
    )

    return {
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'top_products': top_products,
        'revenue_by_country': revenue_by_country,
        'top_customers': top_customers,
        'monthly_sales': monthly_sales,
    }
