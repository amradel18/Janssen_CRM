import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the centralized modules
from process.data_loader import load_all_data, get_filtered_data, get_company_list, get_customer_list
from process.data_processor import calculate_ticket_metrics, calculate_call_metrics, calculate_customer_metrics, calculate_request_metrics, calculate_combined_call_metrics
from process.error_handler import ErrorHandler, try_except_decorator
from visualize.chart_generator import create_pie_chart, create_bar_chart, create_line_chart, create_multi_metric_row, create_time_series

# Set page config
st.set_page_config(page_title="CRM Dashboard", layout="wide")

# Add custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
    }
    h1, h2, h3 {
        color: #1E3A8A;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1E3A8A;
    }
    .metric-label {
        font-size: 1rem;
        color: #6c757d;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #F0F2F6;
        border-radius: 4px 4px 0 0;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Import authentication module
from auth.authentication import check_authentication

# Main function
def main():
    # Check authentication
    check_authentication()
    
    # Page title
    st.title("CRM Dashboard")
    
    # Load all data once
    try:
        with st.spinner("Loading data..."):
            dataframes = load_all_data()
    except Exception as e:
        error_details = ErrorHandler.log_error(e, {"function": "main", "section": "data_loading"})
        ErrorHandler.display_error(error_details)
        st.error("Failed to load data. Please check the logs for details.")
        return
    
    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        
        # Date range filter
        st.subheader("Date Range")
        # Get min and max dates from tickets dataframe
        if 'tickets' in dataframes and not dataframes['tickets'].empty and 'created_at' in dataframes['tickets'].columns:
            min_date = dataframes['tickets']['created_at'].min().date()
            max_date = dataframes['tickets']['created_at'].max().date()
        else:
            min_date = datetime.now().date() - timedelta(days=30)
            max_date = datetime.now().date()
        
        start_date = st.date_input("Start Date", min_date)
        end_date = st.date_input("End Date", max_date)
        
        # Convert to datetime for filtering
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        date_range = (start_datetime, end_datetime)
        
        # Company filter (without relying on companies.csv)
        st.subheader("Company")
        if 'customers' in dataframes and not dataframes['customers'].empty:
            companies = get_company_list(dataframes['customers'])
            selected_company = st.selectbox("Select Company", ["All"] + companies)
            company_filter = None if selected_company == "All" else selected_company
        else:
            company_filter = None
        
        # Customer filter
        st.subheader("Customer")
        if 'customers' in dataframes and not dataframes['customers'].empty:
            customers = get_customer_list(dataframes['customers'], company_filter)
            selected_customer = st.selectbox("Select Customer", ["All"] + customers)
            customer_filter = None if selected_customer == "All" else selected_customer
        else:
            customer_filter = None
    
    # Apply filters to data
    filtered_data = get_filtered_data(
        dataframes,
        start_date=start_datetime,
        end_date=end_datetime,
        date_column='created_at',
        customer=customer_filter,
        company=company_filter
    )
    
    # Calculate metrics
    try:
        # Ensure call_duration is numeric before calculations
        ticketcall_df = filtered_data.get('ticketcall', pd.DataFrame()).copy()
        if 'call_duration' in ticketcall_df.columns:
            ticketcall_df['call_duration'] = pd.to_numeric(ticketcall_df['call_duration'], errors='coerce')

        customercall_df = filtered_data.get('customercall', pd.DataFrame()).copy()
        if 'call_duration' in customercall_df.columns:
            customercall_df['call_duration'] = pd.to_numeric(customercall_df['call_duration'], errors='coerce')

        ticket_metrics = calculate_ticket_metrics(filtered_data.get('tickets', pd.DataFrame()))
        call_metrics = calculate_call_metrics(ticketcall_df)
        combined_call_metrics = calculate_combined_call_metrics(
            ticketcall_df,
            customercall_df,
            filtered_data.get('customers', pd.DataFrame())
        )
        customer_metrics = calculate_customer_metrics(
            filtered_data.get('customers', pd.DataFrame()),
            filtered_data.get('tickets', pd.DataFrame()),
            ticketcall_df
        )
        request_metrics = calculate_request_metrics(filtered_data.get('ticket_items', pd.DataFrame()))
    except Exception as e:
        error_details = ErrorHandler.log_error(e, {"function": "main", "section": "metric_calculation"})
        ErrorHandler.display_error(error_details)
        st.error("An error occurred during metric calculation. Some charts may be unavailable.")
        # Initialize metrics to empty dicts to prevent downstream errors
        ticket_metrics, call_metrics, combined_call_metrics, customer_metrics, request_metrics = {}, {}, {}, {}, {}
    
    # Dashboard tabs
    tabs = st.tabs(["Overview", "Tickets", "Calls", "Customers", "Requests"])
    
    # Overview Tab
    with tabs[0]:
        st.header("Dashboard Overview")
        
        # Key metrics row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Customers", customer_metrics.get('total_customers', 0))
        with col2:
            st.metric("Total Tickets", ticket_metrics.get('total_tickets', 0))
        with col3:
            st.metric("Total Calls", call_metrics.get('total_calls', 0))

        st.divider()
        
        st.subheader("Tickets Status")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Open Tickets", ticket_metrics.get('open_tickets', 0))
        with col2:
            st.metric("Closed Tickets", ticket_metrics.get('closed_tickets', 0))

        st.divider()

        st.subheader("Calls Status")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Open Calls", call_metrics.get('open_calls', 0))
        with col2:
            st.metric("Closed Calls", call_metrics.get('closed_calls', 0))

        st.divider()

        st.subheader("Combined Call Analysis")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Ticket Calls", combined_call_metrics.get('total_ticket_calls', 0))
            st.metric("Avg Ticket Calls per Customer", f"{combined_call_metrics.get('avg_ticket_calls_per_customer', 0):.2f}")
        with col2:
            st.metric("Total Customer Calls", combined_call_metrics.get('total_customer_calls', 0))
            st.metric("Avg Customer Calls per Customer", f"{combined_call_metrics.get('avg_customer_calls_per_customer', 0):.2f}")
        
        st.metric("Total Combined Calls", combined_call_metrics.get('total_calls', 0))
        st.metric("Average Combined Calls per Customer", f"{combined_call_metrics.get('avg_calls_per_customer', 0):.2f}")

    # Tickets Tab
    with tabs[1]:
        st.header("Ticket Analysis")
        
        if 'tickets' in filtered_data and not filtered_data['tickets'].empty:
            tickets_df = filtered_data['tickets'].copy()
            
            # Merge with customers
            if 'customers' in dataframes and not dataframes['customers'].empty:
                customers_df_subset = dataframes['customers'][['id', 'name']].copy()
                customers_df_subset['id'] = pd.to_numeric(customers_df_subset['id'], errors='coerce')
                tickets_df['customer_id'] = pd.to_numeric(tickets_df['customer_id'], errors='coerce')
                tickets_df = pd.merge(tickets_df, customers_df_subset, left_on='customer_id', right_on='id', how='left', suffixes=('', '_cust'))
                tickets_df.rename(columns={'name': 'customer_name'}, inplace=True)
                tickets_df.drop(columns=['id_cust', 'customer_id'], inplace=True, errors='ignore')

            # Merge with ticket categories
            if 'ticket_categories' in dataframes and not dataframes['ticket_categories'].empty:
                tickets_df = pd.merge(tickets_df, dataframes['ticket_categories'][['id', 'name']], left_on='ticket_cat_id', right_on='id', how='left', suffixes=('', '_cat'))
                tickets_df.rename(columns={'name_cat': 'category_name'}, inplace=True)
                tickets_df.drop(columns=['id_cat', 'ticket_cat_id'], inplace=True, errors='ignore')

            # Merge with users for created_by
            if 'users' in dataframes and not dataframes['users'].empty:
                users_df = dataframes['users'].copy()
                users_df['id'] = pd.to_numeric(users_df['id'], errors='coerce')
                tickets_df['created_by'] = pd.to_numeric(tickets_df['created_by'], errors='coerce')
                tickets_df = pd.merge(tickets_df, users_df[['id', 'name']], left_on='created_by', right_on='id', how='left', suffixes=('', '_user'))
                tickets_df.rename(columns={'name_user': 'created_by_name'}, inplace=True)
                tickets_df.drop(columns=['id_user', 'created_by'], inplace=True, errors='ignore')

            # Merge with users for closed_by
            if 'users' in dataframes and not dataframes['users'].empty:
                tickets_df = pd.merge(tickets_df, dataframes['users'][['id', 'name']], left_on='closed_by', right_on='id', how='left', suffixes=('', '_closed_user'))
                tickets_df.rename(columns={'name_closed_user': 'closed_by_name'}, inplace=True)
                tickets_df.drop(columns=['id_closed_user', 'closed_by'], inplace=True, errors='ignore')

            # Select and reorder columns
            display_columns = [
                'id', 'customer_name', 'category_name', 'status', 'priority', 
                'description', 'created_by_name', 'created_at', 'closed_at'
            ]
            
            # Filter for existing columns
            existing_display_columns = [col for col in display_columns if col in tickets_df.columns]
            
            st.dataframe(tickets_df[existing_display_columns])
        else:
            st.info("No ticket data available for the selected filters.")
    
    # Calls Tab
    with tabs[2]:
        st.header("Call Analysis")
        
        # --- Ticket Calls ---
        if 'ticketcall' in filtered_data and not filtered_data['ticketcall'].empty:
            st.subheader("Ticket Calls")
            ticketcall_df = filtered_data['ticketcall'].copy()
            
            if 'users' in dataframes:
                users_df = dataframes['users'].copy()
                users_df['id'] = pd.to_numeric(users_df['id'], errors='coerce')
                ticketcall_df['created_by'] = pd.to_numeric(ticketcall_df['created_by'], errors='coerce')
                ticketcall_df = pd.merge(ticketcall_df, users_df, left_on='created_by', right_on='id', how='left', suffixes=('', '_user'))
            if 'tickets' in dataframes:
                # Ensure consistent data types for merging
                tickets_df = dataframes['tickets'].copy()
                tickets_df['id'] = pd.to_numeric(tickets_df['id'], errors='coerce')
                ticketcall_df['ticket_id'] = pd.to_numeric(ticketcall_df['ticket_id'], errors='coerce')
                ticketcall_df = pd.merge(ticketcall_df, tickets_df, left_on='ticket_id', right_on='id', how='left', suffixes=('', '_ticket'))
            if 'call_types' in dataframes:
                call_types_df = dataframes['call_types'].copy()
                call_types_df['id'] = pd.to_numeric(call_types_df['id'], errors='coerce')
                ticketcall_df['call_type'] = pd.to_numeric(ticketcall_df['call_type'], errors='coerce')
                ticketcall_df = pd.merge(ticketcall_df, call_types_df, left_on='call_type', right_on='id', how='left', suffixes=('', '_type'))
            if 'call_categories' in dataframes:
                ticketcall_df = pd.merge(ticketcall_df, dataframes['call_categories'], left_on='call_cat_id', right_on='id', how='left', suffixes=('', '_category'))

            # Rename columns for clarity
            ticketcall_df.rename(columns={
                'name': 'created_by_name',
                'name_type': 'call_type_name',
                'name_category': 'call_category_name',
                'description_ticket': 'ticket_description'
            }, inplace=True)

            st.dataframe(ticketcall_df)
        else:
            st.info("No ticket call data available for the selected filters.")

        # --- Customer Calls ---
        if 'customercall' in filtered_data and not filtered_data['customercall'].empty:
            st.subheader("Customer Calls")
            customercall_df = filtered_data['customercall'].copy()

            if 'users' in dataframes:
                customercall_df = pd.merge(customercall_df, dataframes['users'], left_on='created_by', right_on='id', how='left', suffixes=('', '_user'))
            if 'customers' in dataframes:
                customers_df = dataframes['customers'].copy()
                customers_df['id'] = pd.to_numeric(customers_df['id'], errors='coerce')
                customercall_df['customer_id'] = pd.to_numeric(customercall_df['customer_id'], errors='coerce')
                customercall_df = pd.merge(customercall_df, customers_df, left_on='customer_id', right_on='id', how='left', suffixes=('', '_customer'))
            if 'call_types' in dataframes:
                customercall_df = pd.merge(customercall_df, dataframes['call_types'], left_on='call_type', right_on='id', how='left', suffixes=('', '_type'))
            if 'call_categories' in dataframes:
                customercall_df = pd.merge(customercall_df, dataframes['call_categories'], left_on='category_id', right_on='id', how='left', suffixes=('', '_category'))
            
            # Rename columns for clarity
            customercall_df.rename(columns={
                'name': 'created_by_name',
                'name_customer': 'customer_name',
                'name_type': 'call_type_name',
                'name_category': 'call_category_name'
            }, inplace=True)

            st.dataframe(customercall_df)
        else:
            st.info("No customer call data available for the selected filters.")

    # Customers Tab
    with tabs[3]:
        st.header("Customer Analysis")
        
        if 'customers' in filtered_data and not filtered_data['customers'].empty:
            customers_df = filtered_data['customers'].copy()
            
            # Merge with governorates
            if 'governorates' in dataframes and not dataframes['governorates'].empty:
                governorates_df_subset = dataframes['governorates'].copy()
                governorates_df_subset['id'] = pd.to_numeric(governorates_df_subset['id'], errors='coerce')
                customers_df['governomate_id'] = pd.to_numeric(customers_df['governomate_id'], errors='coerce')
                customers_df = pd.merge(customers_df, governorates_df_subset[['id', 'name']], left_on='governomate_id', right_on='id', how='left', suffixes=('', '_gov'))
                customers_df.rename(columns={'name_gov': 'governorate_name'}, inplace=True)
                customers_df.drop(columns=['id_gov', 'governomate_id'], inplace=True, errors='ignore')

            # Merge with cities
            if 'cities' in dataframes and not dataframes['cities'].empty:
                cities_df_subset = dataframes['cities'].copy()
                cities_df_subset['id'] = pd.to_numeric(cities_df_subset['id'], errors='coerce')
                customers_df['city_id'] = pd.to_numeric(customers_df['city_id'], errors='coerce')
                customers_df = pd.merge(customers_df, cities_df_subset[['id', 'name']], left_on='city_id', right_on='id', how='left', suffixes=('', '_city'))
                customers_df.rename(columns={'name_city': 'city_name'}, inplace=True)
                customers_df.drop(columns=['id_city', 'city_id'], inplace=True, errors='ignore')

            st.dataframe(customers_df)
        else:
            st.info("No customer data available for the selected filters.")
    
    # Requests Tab
    with tabs[4]:
        st.header("Request Analysis")
        
        if 'ticket_items' in filtered_data and not filtered_data['ticket_items'].empty:
            requests_df = filtered_data['ticket_items'].copy()
            
            # Merge with products
            if 'product_info' in dataframes and not dataframes['product_info'].empty:
                requests_df = pd.merge(requests_df, dataframes['product_info'][['id', 'product_name']], left_on='product_id', right_on='id', how='left')
                requests_df.drop(columns=['id', 'product_id'], inplace=True, errors='ignore')

            # Merge with request reasons
            if 'request_reasons' in dataframes and not dataframes['request_reasons'].empty:
                requests_df = pd.merge(requests_df, dataframes['request_reasons'][['id', 'name']], left_on='request_reason_id', right_on='id', how='left', suffixes=('', '_reason'))
                requests_df.rename(columns={'name': 'request_reason'}, inplace=True)
                requests_df.drop(columns=['id_reason', 'request_reason_id'], inplace=True, errors='ignore')

            st.dataframe(requests_df)
        else:
            st.info("No request data available for the selected filters.")

# Run the app
if __name__ == "__main__":
    main()