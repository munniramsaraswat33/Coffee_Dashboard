import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from datetime import datetime

# -------------------------
# Streamlit app config
# -------------------------
st.set_page_config(page_title="Coffee Sales Dashboard", layout="wide", page_icon="☕")

# -------------------------
# CSS for light/dark themes
# -------------------------
DARK_CSS = '''
body { background-color: #0d1117; color: #e6edf3; }
.stApp { background-color: #0d1117; }
div[data-testid="stMetric"] { background: #161b22; padding: 18px; border-radius: 10px; }
div[data-testid="stMetricValue"] { color: #58a6ff; font-size: 26px; font-weight: 700; }
'''

LIGHT_CSS = '''
body { background-color: #ffffff; color: #0b0b0b; }
.stApp { background-color: #ffffff; }
div[data-testid="stMetric"] { background: #f3f6f9; padding: 18px; border-radius: 10px; }
div[data-testid="stMetricValue"] { color: #0b69ff; font-size: 26px; font-weight: 700; }
'''

# -------------------------
# Helpers
# -------------------------
@st.cache_data
def load_csv(path):
    return pd.read_csv(path)

@st.cache_data
def read_uploaded(uploaded_file):
    return pd.read_csv(uploaded_file)


def validate_and_prepare(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize column names
    df = df.rename(columns=lambda c: c.strip())

    # Necessary columns
    expected_cols = set(["Date", "coffee_name", "money"])
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # Parse Date
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True, infer_datetime_format=True)


    # Drop fully empty rows
    df = df.dropna(how='all')

    # Ensure money is numeric and remove negatives
    df['money'] = pd.to_numeric(df['money'], errors='coerce').fillna(0)
    df.loc[df['money'] < 0, 'money'] = 0

    # Ensure coffee_name is string
    df['coffee_name'] = df['coffee_name'].astype(str)

    # Weekday column
    # Always ensure Weekday column exists
    df['Weekday'] = df['Date'].dt.day_name()


    # Payment type column normalization
    if 'cash_type' in df.columns:
        df['cash_type'] = df['cash_type'].astype(str)

    return df

# -------------------------
# Load data: try multiple filenames for robustness
# -------------------------
file_candidates = ["Coffe_sales.csv", "Coffee_sales.csv", "coffee_sales.csv", "coffee.csv"]
file_path = None
for f in file_candidates:
    if os.path.exists(f):
        file_path = f
        break

uploaded_df = None
if file_path:
    try:
        df_raw = load_csv(file_path)
        data_source = f"Loaded from {file_path}"
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        df_raw = pd.DataFrame()
        data_source = "Failed to load file from disk"
else:
    uploaded = st.file_uploader("Upload coffee sales CSV file", type=['csv'])
    if uploaded is not None:
        try:
            df_raw = read_uploaded(uploaded)
            data_source = "Loaded from uploaded file"
        except Exception as e:
            st.error(f"Error reading uploaded file: {e}")
            st.stop()
    else:
        st.info("No CSV found on disk. Upload a file or place one in the app folder named 'Coffee_sales.csv' (case-sensitive).")
        st.stop()

# -------------------------
# Validate and prepare dataframe
# -------------------------
try:
    df = validate_and_prepare(df_raw.copy())
except Exception as e:
    st.error(f"Data validation error: {e}")
    st.stop()

# -------------------------
# Top-level controls
# -------------------------
with st.sidebar:
    st.header("Settings & Filters")
    theme = st.radio("Theme", ["Dark", "Light"], index=0)
    if theme == "Dark":
        st.markdown(f"<style>{DARK_CSS}</style>", unsafe_allow_html=True)
    else:
        st.markdown(f"<style>{LIGHT_CSS}</style>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"**Data source:** {data_source}")

    # Date range filter
    if df['Date'].notna().any():
        min_date = df['Date'].min().date()
        max_date = df['Date'].max().date()
        start_date, end_date = st.date_input("Date range", [min_date, max_date], min_value=min_date, max_value=max_date)
    else:
        start_date, end_date = None, None

    # Coffee type filter
    coffee_types = sorted(df['coffee_name'].dropna().unique())
    selected_types = st.multiselect("Coffee Type(s)", coffee_types, default=coffee_types)

    # Payment type filter (if available)
    payment_types = []
    if 'cash_type' in df.columns:
        payment_types = sorted(df['cash_type'].dropna().unique())
        selected_payments = st.multiselect("Payment Type(s)", payment_types, default=payment_types)
    else:
        selected_payments = None

    # Price slider
    money_min = float(df['money'].min()) if not df['money'].empty else 0.0
    money_max = float(df['money'].max()) if not df['money'].empty else 100.0
    price_range = st.slider("Price range", min_value=money_min, max_value=money_max, value=(money_min, money_max))

    st.markdown("---")
    st.write("Download & Export")
    st.download_button("Download full dataset", df.to_csv(index=False), file_name="coffee_full_dataset.csv")

# -------------------------
# Apply filters
# -------------------------
filtered = df.copy()
if start_date and end_date:
    filtered = filtered[(filtered['Date'] >= pd.to_datetime(start_date)) & (filtered['Date'] <= pd.to_datetime(end_date))]
if selected_types:
    filtered = filtered[filtered['coffee_name'].isin(selected_types)]
if selected_payments is not None:
    filtered = filtered[filtered['cash_type'].isin(selected_payments)]
if price_range:
    filtered = filtered[(filtered['money'] >= price_range[0]) & (filtered['money'] <= price_range[1])]

# -------------------------
# Top KPIs
# -------------------------
st.title("☕ Coffee Shop Sales Dashboard")
st.markdown("---")

col1, col2, col3, col4 = st.columns([1.8, 1.2, 1.2, 1.2])

total_sales = filtered['money'].sum() if 'money' in filtered.columns else 0
avg_transaction = filtered['money'].mean() if 'money' in filtered.columns and len(filtered) > 0 else 0
total_orders = len(filtered)
unique_products = filtered['coffee_name'].nunique() if 'coffee_name' in filtered.columns else 0

col1.metric("Total Sales", f"${total_sales:,.2f}")
col2.metric("Avg Transaction", f"${avg_transaction:,.2f}")
col3.metric("Total Orders", total_orders)
col4.metric("Unique Products", unique_products)

# Quick insights
with st.expander("Quick Insights"):
    if not filtered.empty:
        top_coffee = filtered.groupby('coffee_name')['money'].sum().sort_values(ascending=False).head(3)
        st.write("**Top 3 coffees by revenue:**")
        st.write(top_coffee)
        if 'cash_type' in filtered.columns:
            st.write("**Payment distribution:**")
            st.write(filtered['cash_type'].value_counts())
    else:
        st.write("No data in the current filter range.")

st.markdown("---")

# -------------------------
# Tabs for organization
# -------------------------
tab1, tab2, tab3 = st.tabs(["Sales Overview", "Trends & Breakdown", "Raw Data & Export"])

with tab1:
    st.header("Sales by Product & Price Distribution")
    c1, c2 = st.columns([2, 1])
    with c1:
        if not filtered.empty:
            coffee_sales = (filtered.groupby('coffee_name')['money'].sum().reset_index().sort_values(by='money', ascending=False))
            fig = px.bar(coffee_sales, x='coffee_name', y='money', title='Revenue by Coffee Product', hover_data={'money':':,.2f', 'coffee_name':True})
            fig.update_layout(xaxis_title='Coffee', yaxis_title='Revenue', height=500, margin=dict(t=60))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales to show for selected filters.")
    with c2:
        st.subheader("Price distribution")
        if not filtered.empty:
            fig2 = px.histogram(filtered, x='money', nbins=25, title='Price / Transaction Distribution', marginal='box')
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No price data available.")

with tab2:
    st.header("Time Trends & Weekday Analysis")
    r1, r2 = st.columns(2)
    with r1:
        st.subheader("Sales Trend")
        if filtered['Date'].notna().any():
            daily = filtered.groupby('Date')['money'].sum().reset_index()
            fig_trend = px.line(daily, x='Date', y='money', markers=True, title='Daily Revenue')
            fig_trend.update_layout(height=420)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No date information available to show trend.")
    with r2:
        st.subheader("Avg Order Value by Weekday")
        if 'Weekday' in filtered.columns and filtered['Weekday'].notna().any():
            weekday_avg = filtered.groupby('Weekday')['money'].mean().reindex(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']).reset_index()
            weekday_avg = weekday_avg.dropna()
            fig_w = px.bar(weekday_avg, x='Weekday', y='money', title='Average Order Value by Weekday')
            fig_w.update_layout(height=420)
            st.plotly_chart(fig_w, use_container_width=True)
        else:
            st.info("Weekday data not available.")

    st.subheader("Payment Type Breakdown")
    if 'cash_type' in filtered.columns and filtered['cash_type'].notna().any():
        pay_counts = filtered['cash_type'].value_counts().reset_index()
        pay_counts.columns = ['payment', 'count']
        fig_pie = px.pie(pay_counts, names='payment', values='count', title='Payment Type Distribution')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No payment type information available.")

with tab3:
    st.header("Raw Data")
    st.write("Download the filtered dataset or inspect the table below.")
    st.download_button("Download filtered data", filtered.to_csv(index=False), file_name="coffee_filtered.csv")
    st.dataframe(filtered.reset_index(drop=True))

st.markdown("---")
st.caption("Dashboard created with Streamlit — upgrades: robust validation, caching, filters, downloads, and organized layout.")
