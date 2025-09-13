import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import plotly.express as px

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from process.data_loader import load_all_data

# Set page config
st.set_page_config(page_title="Customer Call Analysis", layout="wide")

# Import authentication module
from auth.authentication import check_authentication

@st.cache_data
def get_call_analysis_data(dataframes):
    """
    Merges customercall data with related tables for analysis.
    """
    customercall_df = dataframes['customercall'].copy()
    customers_df = dataframes['customers'].copy()
    users_df = dataframes['users'].copy()
    call_types_df = dataframes['call_types'].copy()
    call_categories_df = dataframes['call_categories'].copy()
    governorates_df = dataframes['governorates'].copy()

    # Rename columns for merging to avoid conflicts
    users_df = users_df.rename(columns={'name': 'user_name'})
    call_types_df = call_types_df.rename(columns={'name': 'call_type_name'})
    call_categories_df = call_categories_df.rename(columns={'name': 'call_category_name'})
    governorates_df = governorates_df.rename(columns={'name': 'governorate_name'})

    # Add company mapping to customers_df
    company_mapping = {1: "Englander", 2: "Janssen"}
    customers_df['company_name'] = customers_df['company_id'].map(company_mapping).fillna("NULL")

    # Merge governorate into customers
    customers_df = customers_df.merge(governorates_df[['id', 'governorate_name']], left_on='governomate_id', right_on='id', how='left', suffixes=('', '_gov'))

    # Merge dataframes
    customers_df['id'] = pd.to_numeric(customers_df['id'], errors='coerce')
    customercall_df['customer_id'] = pd.to_numeric(customercall_df['customer_id'], errors='coerce')
    merged_df = customercall_df.merge(customers_df[['id', 'name', 'company_name', 'governorate_name']], left_on='customer_id', right_on='id', how='left', suffixes=('', '_customer'))
    merged_df = merged_df.merge(users_df[['id', 'user_name']], left_on='created_by', right_on='id', how='left', suffixes=('', '_user'))
    merged_df = merged_df.merge(call_types_df[['id', 'call_type_name']], left_on='call_type', right_on='id', how='left', suffixes=('', '_call_type'))
    merged_df = merged_df.merge(call_categories_df[['id', 'call_category_name']], left_on='category_id', right_on='id', how='left', suffixes=('', '_call_cat'))

    # Rename columns for clarity
    merged_df = merged_df.rename(columns={'name': 'customer_name'})

    # Handle potential missing values from merges
    merged_df['customer_name'] = merged_df['customer_name'].fillna('Unknown Customer')
    merged_df['user_name'] = merged_df['user_name'].fillna('Unknown User')
    merged_df['call_type_name'] = merged_df['call_type_name'].fillna('Unknown Type')
    merged_df['call_category_name'] = merged_df['call_category_name'].fillna('Unknown Category')
    merged_df['company_name'] = merged_df['company_name'].fillna('Unknown Company')
    merged_df['governorate_name'] = merged_df['governorate_name'].fillna('Unknown Governorate')
    
    # Convert created_at to datetime
    merged_df['created_at'] = pd.to_datetime(merged_df['created_at'])
    
    return merged_df

def main():
    check_authentication()
    
    st.title("Customer Call Analysis")

    if 'all_data_loaded' not in st.session_state or not st.session_state.all_data_loaded:
        with st.spinner("Loading data..."):
            dataframes = load_all_data()
            st.session_state.dataframes = dataframes
            st.session_state.all_data_loaded = True
    else:
        dataframes = st.session_state.dataframes

    if 'customercall' not in dataframes or dataframes['customercall'].empty:
        st.warning("No customer call data available.")
        return

    call_data = get_call_analysis_data(dataframes)

    with st.sidebar:
        st.header("Filters")

        # Date range filter
        min_date = call_data['created_at'].min().date()
        max_date = call_data['created_at'].max().date()
        default_start = max_date - timedelta(days=30)
        
        start_date = st.date_input("Start Date", value=default_start, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

        # Company filter
        company_list = ["All"] + call_data['company_name'].unique().tolist()
        selected_company = st.selectbox("Select Company", options=company_list)

        # User filter
        user_list = ["All"] + call_data['user_name'].unique().tolist()
        selected_user = st.selectbox("Select User", options=user_list)

    # Apply filters
    mask = (call_data['created_at'].dt.date >= start_date) & (call_data['created_at'].dt.date <= end_date)
    if selected_company != "All":
        mask &= (call_data['company_name'] == selected_company)
    if selected_user != "All":
        mask &= (call_data['user_name'] == selected_user)
    filtered_calls = call_data[mask].copy()

    if filtered_calls.empty:
        st.warning("No data available for the selected filters.")
        return

    # --- Metrics ---
    st.header("Call Metrics")
    total_calls = filtered_calls.shape[0]
    avg_duration = filtered_calls['call_duration'].mean()
    inbound_calls = filtered_calls[filtered_calls['call_type_name'] == 'صادر'].shape[0]
    outbound_calls = total_calls - inbound_calls
    avg_calls_per_customer = total_calls / filtered_calls['customer_id'].nunique() if filtered_calls['customer_id'].nunique() > 0 else 0

    # Calculate Avg. of Monthly Max Calls
    if not filtered_calls.empty:
        monthly_max_calls = filtered_calls.groupby(pd.Grouper(key='created_at', freq='M')).size()
        avg_of_monthly_max_calls = monthly_max_calls.mean()
    else:
        avg_of_monthly_max_calls = 0


    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Calls", total_calls)
    col2.metric("Inbound Calls", inbound_calls)
    col3.metric("Outbound Calls", outbound_calls)
    col4.metric("Avg. Duration (sec)", f"{avg_duration:.2f}")
    col5.metric("Avg. Calls per Customer", f"{avg_calls_per_customer:.2f}")
    col6.metric("Avg. of Monthly Max Calls", f"{avg_of_monthly_max_calls:.2f}")

    # Monthly Analysis
# 📊 Monthly Call Analysis
    st.header("Monthly Call Analysis")

    # 🗓️ تحويل تاريخ المكالمة إلى شهر
    filtered_calls['month'] = filtered_calls['created_at'].dt.to_period('M')

    # 📈 حساب إجمالي المكالمات والمتوسط اليومي لكل شهر
    monthly_stats = (
        filtered_calls.groupby('month')
        .agg(
            total_calls=('customer_id', 'count'),
            avg_daily_calls=('created_at', lambda x: x.dt.date.nunique() / x.dt.to_period('M').nunique())
        )
        .reset_index()
    )

    # تحويل الشهر إلى نص للعرض
    monthly_stats['month'] = monthly_stats['month'].astype(str)

    # 🔎 استخراج اليوم الذروة (أكثر يوم مكالمات) لكل شهر
    peak_days = (
        filtered_calls.groupby([
            filtered_calls['created_at'].dt.to_period('M').rename('month'),
            filtered_calls['created_at'].dt.date.rename('date')
        ])
        .size()
        .reset_index(name='daily_calls')
    )

    peak_days_per_month = peak_days.loc[peak_days.groupby('month')['daily_calls'].idxmax()]
    peak_days_per_month = peak_days_per_month.rename(
        columns={'date': 'peak_day', 'daily_calls': 'peak_day_calls'}
    )
    peak_days_per_month['month'] = peak_days_per_month['month'].astype(str)

    # 📊 دمج بيانات الذروة مع التحليل الشهري
    monthly_stats = monthly_stats.merge(
        peak_days_per_month[['month', 'peak_day', 'peak_day_calls']],
        on='month',
        how='left'
    )

    # عرض الجدول
    st.subheader("📋 Detailed Monthly Call Statistics")
    st.dataframe(monthly_stats)

    # 🎨 رسم بياني يوضح إجمالي المكالمات لكل شهر
    fig_monthly = px.bar(
        monthly_stats,
        x='month',
        y='total_calls',
        text='total_calls',
        title='Total Calls per Month',
        labels={'month': 'Month', 'total_calls': 'Total Calls'},
        color='total_calls',
        color_continuous_scale='Blues'
    )
    fig_monthly.update_traces(textposition='outside')

    st.plotly_chart(fig_monthly, use_container_width=True)


    # --- Charts ---
    st.header("Analysis")

    col1, col2 = st.columns(2)

    with col1:
        # Call Type Distribution
        st.subheader("Call Type Distribution")
        call_type_dist = filtered_calls['call_type_name'].value_counts().reset_index()
        call_type_dist.columns = ['Call Type', 'Count']
        fig = px.pie(call_type_dist, names='Call Type', values='Count', title='Call Types')
        st.plotly_chart(fig, use_container_width=True)

        # Calls by Hour
        st.subheader("Calls by Hour of Day")
        filtered_calls['hour'] = filtered_calls['created_at'].dt.hour
        calls_by_hour = filtered_calls['hour'].value_counts().sort_index().reset_index()
        calls_by_hour.columns = ['Hour', 'Number of Calls']
        fig = px.bar(calls_by_hour, x='Hour', y='Number of Calls', title='Peak Call Times')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Call Category Distribution
        st.subheader("Call Category Distribution")
        call_cat_dist = filtered_calls['call_category_name'].value_counts().reset_index()
        call_cat_dist.columns = ['Call Category', 'Count']
        fig = px.bar(call_cat_dist, x='Count', y='Call Category', orientation='h', title='Call Categories')
        st.plotly_chart(fig, use_container_width=True)

        # Calls by Day of Week
        st.subheader("Calls by Day of Week")
        filtered_calls['day_of_week'] = filtered_calls['created_at'].dt.day_name()
        calls_by_day = filtered_calls['day_of_week'].value_counts().reset_index()
        calls_by_day.columns = ['Day of Week', 'Number of Calls']
        days_order = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        calls_by_day['Day of Week'] = pd.Categorical(calls_by_day['Day of Week'], categories=days_order, ordered=True)
        calls_by_day = calls_by_day.sort_values('Day of Week')
        fig = px.bar(calls_by_day, x='Day of Week', y='Number of Calls', title='Busiest Days')
        st.plotly_chart(fig, use_container_width=True)

    # Calls Over Time
    st.subheader("Daily Call Volume")
    calls_over_time = filtered_calls.resample('W', on='created_at').size().reset_index(name='count')
    fig = px.line(calls_over_time, x='created_at', y='count', title='Call Volume Over Time')
    st.plotly_chart(fig, use_container_width=True)

    # --- Treemap Analysis ---
    st.header("Call Reasons by Governorate")
    treemap_data = filtered_calls.groupby(['governorate_name', 'call_category_name']).size().reset_index(name='count')
    if not treemap_data.empty:
        fig = px.treemap(treemap_data, path=['governorate_name', 'call_category_name'], values='count',
                         title='Call Reasons Distribution by Governorate',
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available for the treemap.")
    
    # Display Raw Data
    with st.expander("View Raw Data"):
        st.dataframe(filtered_calls)

if __name__ == "__main__":
    main()