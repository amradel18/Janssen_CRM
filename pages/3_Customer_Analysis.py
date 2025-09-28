import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import plotly.express as px

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the centralized modules
from process.data_loader import load_all_data
from auth.authentication import check_authentication

# Set page config
st.set_page_config(page_title="Customer Analysis", layout="wide")

# Main function
def main():
    # Check authentication
    check_authentication()
    
    # Page title
    st.title("Customer Analysis")
    
    # Load data
    if 'dataframes' not in st.session_state:
        with st.spinner("Loading data..."):
            st.session_state.dataframes = load_all_data()
    
    # Safely get dataframes from session state
    dataframes = getattr(st.session_state, 'dataframes', {})
    
    customers_df = dataframes.get('customers', pd.DataFrame())
    governorates_df = dataframes.get('governorates', pd.DataFrame())
    cities_df = dataframes.get('cities', pd.DataFrame())

    if customers_df.empty:
        st.warning("No customer data to display.")
        return

    # Merge dataframes
    if not governorates_df.empty:
        customers_df = pd.merge(customers_df, governorates_df, left_on='governomate_id', right_on='id', how='left', suffixes=('', '_gov'))
        customers_df.rename(columns={'name_gov': 'governorate_name'}, inplace=True)
    if not cities_df.empty:
        customers_df = pd.merge(customers_df, cities_df, left_on='city_id', right_on='id', how='left', suffixes=('', '_city'))
        customers_df.rename(columns={'name_city': 'city_name'}, inplace=True)

    # Handle missing values for geographic data
    customers_df['governorate_name'] = customers_df['governorate_name'].fillna('Unknown Governorate')
    customers_df['city_name'] = customers_df['city_name'].fillna('Unknown City')

    # Map company_id to company_name
    company_mapping = {1: "Englander", 2: "Janssen"}
    customers_df['company_name'] = customers_df['company_id'].map(company_mapping).fillna("NULL")

    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        
        # Date range filter
        min_date = customers_df['created_at'].min().date()
        max_date = customers_df['created_at'].max().date()
        
        start_date = st.date_input("From Date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("To Date", max_date, min_value=min_date, max_value=max_date)
        
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Governorate filter
        if 'governorate_name' in customers_df.columns:
            governorates = ["All"] + list(customers_df['governorate_name'].unique())
            selected_governorate = st.selectbox("Select Governorate", governorates)
        else:
            selected_governorate = "All"

        # Company filter
        if 'company_name' in customers_df.columns:
            companies = list(customers_df['company_name'].unique())
            selected_companies = st.multiselect("Select Companies", companies, default=companies)
        else:
            selected_companies = []

    # Filter data
    filtered_customers = customers_df[
        (customers_df['created_at'] >= start_datetime) & 
        (customers_df['created_at'] <= end_datetime)
    ]
    if selected_governorate != "All":
        filtered_customers = filtered_customers[filtered_customers['governorate_name'] == selected_governorate]
    
    if selected_companies:
        filtered_customers = filtered_customers[filtered_customers['company_name'].isin(selected_companies)]

    if filtered_customers.empty:
        st.warning("No data matches the selected filters.")
        return

    # KPIs
    total_customers = filtered_customers.shape[0]
    
    # Calculate monthly average customers
    filtered_customers['month'] = filtered_customers['created_at'].dt.to_period('M')
    monthly_customers = filtered_customers.groupby('month').size().mean()
    
    total_cities = filtered_customers['city_name'].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Customers", f"{total_customers}")
    col2.metric("Average Customers per Month", f"{monthly_customers:.2f}")
    col3.metric("Number of Cities", f"{total_cities}")

    st.markdown("---")

    # Charts
    st.subheader("Customer Growth Over Time (Weekly)")

    # تجميع العملاء الجدد على مستوى الأسابيع
    customer_growth = (
        filtered_customers
        .set_index('created_at')
        .resample('W')  # Weekly
        .size()
        .reset_index()
    )

    # إعادة تسمية الأعمدة
    customer_growth.columns = ['week', 'new_customers']

    # رسم Line chart
    fig_growth = px.line(
        customer_growth, 
        x='week', 
        y='new_customers', 
        title='Weekly New Customers', 
        markers=True
    )

    st.plotly_chart(fig_growth, use_container_width=True)

    
    st.subheader("Customer Growth Over Time")
    customer_growth = filtered_customers.set_index('created_at').resample('M').size().reset_index()
    customer_growth.columns = ['date', 'new_customers']
    fig_growth = px.bar(customer_growth, x='date', y='new_customers', title='Monthly New Customers')
    st.plotly_chart(fig_growth, use_container_width=True)

    st.subheader("Geographic Distribution of Customers")
    if 'governorate_name' in filtered_customers.columns and 'city_name' in filtered_customers.columns:
        geo_dist = filtered_customers.groupby(['governorate_name', 'city_name']).size().reset_index(name='customer_count')
        fig_treemap = px.treemap(geo_dist, path=[px.Constant("All"), 'governorate_name', 'city_name'], values='customer_count',
                                 title='Customer Distribution by Governorate and City',
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_treemap.update_layout(margin = dict(t=50, l=25, r=25, b=25))
        st.plotly_chart(fig_treemap, use_container_width=True)
        
        st.subheader("Customer Distribution by Governorate")

        # حساب عدد العملاء في كل محافظة
        governorate_dist = (
            filtered_customers.groupby('governorate_name')
            .size()
            .reset_index(name='count')
        )

        # حساب النسبة المئوية بناءً على الإجمالي
        total = governorate_dist['count'].sum()
        governorate_dist['percentage'] = (governorate_dist['count'] / total) * 100

        governorate_dist = governorate_dist.sort_values('percentage', ascending=True)

        fig_gov_dist = px.bar(
            governorate_dist,
            y='governorate_name',
            x='percentage',
            orientation='h',
            title='Percentage of Customers by Governorate',
            text=governorate_dist['percentage'].apply(lambda x: f'{x:.2f}%')
        )
        st.plotly_chart(fig_gov_dist, use_container_width=True)

    else:
        st.info("Governorate or city data is not available.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An error occurred: {e}")