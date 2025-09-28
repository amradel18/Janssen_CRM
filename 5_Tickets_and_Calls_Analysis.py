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
from process.data_processor import calculate_ticket_metrics, join_ticket_and_call_data
from visualize.chart_generator import create_pie_chart, create_multi_metric_row

# Import authentication module
from auth.authentication import check_authentication

@st.cache_data
def get_ticket_call_analysis_data(dataframes):
    """
    Merges ticketcall data with related tables for analysis.
    """
    ticketcall_df = dataframes.get('ticketcall', pd.DataFrame()).copy()
    if ticketcall_df.empty:
        return pd.DataFrame()

    tickets_df = dataframes.get('tickets', pd.DataFrame()).copy()
    customers_df = dataframes.get('customers', pd.DataFrame()).copy()
    users_df = dataframes.get('users', pd.DataFrame()).copy()
    call_types_df = dataframes.get('call_types', pd.DataFrame()).copy()
    call_categories_df = dataframes.get('call_categories', pd.DataFrame()).copy()
    governorates_df = dataframes.get('governorates', pd.DataFrame()).copy()

    # Rename columns for merging
    users_df = users_df.rename(columns={'name': 'user_name'})
    call_types_df = call_types_df.rename(columns={'name': 'call_type_name'})
    call_categories_df = call_categories_df.rename(columns={'name': 'call_category_name'})
    governorates_df = governorates_df.rename(columns={'name': 'governorate_name'})

    # Rename description to callresult for display purposes
    ticketcall_df = ticketcall_df.rename(columns={'description': 'callresult'})
    
    # Merge with tickets to get customer_id and company_id
    merged_df = ticketcall_df.merge(tickets_df[['id', 'customer_id', 'description', 'company_id']], left_on='ticket_id', right_on='id', how='left', suffixes=('', '_ticket'))
    
    # Ensure company_id is properly transferred from tickets
    if 'company_id' in merged_df.columns and 'company_id_ticket' not in merged_df.columns:
        merged_df.rename(columns={'company_id': 'company_id_call'}, inplace=True)
    
    if 'company_id' in tickets_df.columns:
        merged_df['company_id'] = merged_df['company_id_ticket'] if 'company_id_ticket' in merged_df.columns else tickets_df.loc[tickets_df['id'].isin(merged_df['ticket_id']), 'company_id'].values

    # Merge with customers to get governorate
    merged_df = merged_df.merge(customers_df[['id', 'name', 'governomate_id', 'company_id']], left_on='customer_id', right_on='id', how='left', suffixes=('', '_customer'))
    merged_df = merged_df.rename(columns={'name': 'customer_name'})
    
    # If company_id is missing, try to get it from customer
    if 'company_id' not in merged_df.columns or merged_df['company_id'].isna().all():
        merged_df['company_id'] = merged_df['company_id_customer']

    # Merge with governorates
    merged_df = merged_df.merge(governorates_df[['id', 'governorate_name']], left_on='governomate_id', right_on='id', how='left', suffixes=('', '_gov'))

    # Merge with other dimension tables
    merged_df = merged_df.merge(users_df[['id', 'user_name']], left_on='created_by', right_on='id', how='left', suffixes=('', '_user'))
    merged_df = merged_df.merge(call_types_df[['id', 'call_type_name']], left_on='call_type', right_on='id', how='left', suffixes=('', '_call_type'))
    merged_df = merged_df.merge(call_categories_df[['id', 'call_category_name']], left_on='call_cat_id', right_on='id', how='left', suffixes=('', '_call_cat'))

    # Fill NA
    merged_df['customer_name'] = merged_df['customer_name'].fillna('Unknown Customer')
    merged_df['user_name'] = merged_df['user_name'].fillna('Unknown User')
    merged_df['call_type_name'] = merged_df['call_type_name'].fillna('Unknown Type')
    merged_df['call_category_name'] = merged_df['call_category_name'].fillna('Unknown Category')
    merged_df['governorate_name'] = merged_df['governorate_name'].fillna('Unknown Governorate')
    
    # Ensure company_id is available for filtering
    if 'company_id' not in merged_df.columns:
        # Try to get company_id from tickets
        if 'ticket_id' in merged_df.columns and 'company_id' in tickets_df.columns:
            company_id_map = tickets_df.set_index('id')['company_id'].to_dict()
            merged_df['company_id'] = merged_df['ticket_id'].map(company_id_map)

    # Convert created_at to datetime
    merged_df['created_at'] = pd.to_datetime(merged_df['created_at'], errors='coerce')
    merged_df.dropna(subset=['created_at'], inplace=True)

    return merged_df

# Main function
def main():
    # Check authentication
    check_authentication()
    
    # Page title
    st.title("Tickets and Calls Analysis")
    
    # Load data
    if 'all_data_loaded' not in st.session_state or not st.session_state.all_data_loaded:
        with st.spinner("Loading data..."):
            dataframes = load_all_data()
            st.session_state.dataframes = dataframes
            st.session_state.all_data_loaded = True
    else:
        # Safely get dataframes from session state
    dataframes = getattr(st.session_state, 'dataframes', {})
    
    # --- Process Data ---
    with st.spinner("Processing data..."):
        tickets_df = dataframes.get('tickets', pd.DataFrame()).copy()
        ticketcall_df = dataframes.get('ticketcall', pd.DataFrame()).copy()

        # Calculate call counts per ticket and merge into a copy of tickets_df
        if not ticketcall_df.empty:
            call_counts = ticketcall_df.groupby('ticket_id').size().reset_index(name='call_count')
            tickets_with_counts_df = pd.merge(tickets_df, call_counts, left_on='id', right_on='ticket_id', how='left')
            if 'ticket_id' in tickets_with_counts_df.columns:
                 tickets_with_counts_df = tickets_with_counts_df.drop(columns=['ticket_id'])
            tickets_with_counts_df['call_count'] = tickets_with_counts_df['call_count'].fillna(0).astype(int)
        else:
            tickets_with_counts_df = tickets_df.copy()
            tickets_with_counts_df['call_count'] = 0

        tickets_analysis_data = join_ticket_and_call_data(
            tickets_with_counts_df,
            ticketcall_df,
            dataframes.get('users', pd.DataFrame()),
            dataframes.get('ticket_categories', pd.DataFrame()),
            dataframes.get('call_types', pd.DataFrame()),
            dataframes.get('customers', pd.DataFrame()),
            dataframes.get('call_categories', pd.DataFrame())
        )
        calls_analysis_data = get_ticket_call_analysis_data(dataframes)

    if 'description_ticket' in tickets_analysis_data.columns:
        tickets_analysis_data.rename(columns={'description_ticket': 'description'}, inplace=True)

    if 'status' in tickets_analysis_data.columns and 'status_ticket' not in tickets_analysis_data.columns:
        tickets_analysis_data = tickets_analysis_data.rename(columns={'status': 'status_ticket'})

    # --- Sidebar Filters ---
    with st.sidebar:
        st.header("Filters")
        
        # Date range filter
        st.subheader("Date Range")
        
        min_date_ticket = pd.to_datetime(tickets_analysis_data['created_at_ticket'], errors='coerce').min().date() if not tickets_analysis_data.empty and 'created_at_ticket' in tickets_analysis_data.columns else datetime.now().date() - timedelta(days=30)
        max_date_ticket = pd.to_datetime(tickets_analysis_data['created_at_ticket'], errors='coerce').max().date() if not tickets_analysis_data.empty and 'created_at_ticket' in tickets_analysis_data.columns else datetime.now().date()
        min_date_call = calls_analysis_data['created_at'].min().date() if not calls_analysis_data.empty else datetime.now().date() - timedelta(days=30)
        max_date_call = calls_analysis_data['created_at'].max().date() if not calls_analysis_data.empty else datetime.now().date()

        min_date = min(min_date_ticket, min_date_call)
        max_date = max(max_date_ticket, max_date_call)

        start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
        
        # Company filter
        st.subheader("Company")
        company_mapping = {1: "Englander", 2: "Janssen"}
        company_options = ["All"] + list(company_mapping.values())
        selected_company = st.selectbox("Select Company", company_options)
        
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

    # --- Filter Data based on common date range and company ---
    tickets_analysis_data['created_at_ticket'] = pd.to_datetime(tickets_analysis_data['created_at_ticket'], errors='coerce')
    filtered_tickets_data = tickets_analysis_data[tickets_analysis_data['created_at_ticket'].between(start_datetime, end_datetime)]

    calls_analysis_data['created_at'] = pd.to_datetime(calls_analysis_data['created_at'], errors='coerce')
    filtered_calls_data = calls_analysis_data[calls_analysis_data['created_at'].between(start_datetime, end_datetime)]
    
    # Apply company filter if selected
    if selected_company != "All":
        # Get company_id from the mapping
        company_id = [k for k, v in company_mapping.items() if v == selected_company][0]
        
        # Filter tickets data by company_id
        if 'company_id' in filtered_tickets_data.columns:
            filtered_tickets_data = filtered_tickets_data[filtered_tickets_data['company_id'] == company_id]
        elif 'company_id_ticket' in filtered_tickets_data.columns:
            filtered_tickets_data = filtered_tickets_data[filtered_tickets_data['company_id_ticket'] == company_id]
        
        # Filter calls data by company_id
        if 'company_id' in filtered_calls_data.columns:
            filtered_calls_data = filtered_calls_data[filtered_calls_data['company_id'] == company_id]
        elif 'company_id_call' in filtered_calls_data.columns:
            filtered_calls_data = filtered_calls_data[filtered_calls_data['company_id_call'] == company_id]
        
        # Log the number of records after filtering
        st.sidebar.write(f"Filtered tickets: {len(filtered_tickets_data)}")
        st.sidebar.write(f"Filtered calls: {len(filtered_calls_data)}")
            
            # Log the number of records after filtering
        st.sidebar.write(f"Filtered tickets: {len(filtered_tickets_data)}")
        st.sidebar.write(f"Filtered calls: {len(filtered_calls_data)}")
            
    # Ensure proper joining between tickets and calls
    if not filtered_calls_data.empty and not filtered_tickets_data.empty:
        # Create a mapping between ticket IDs in both dataframes
        ticket_id_mapping = {}
        
        # Check which columns to use for joining
        ticket_id_col_tickets = 'id_ticket' if 'id_ticket' in filtered_tickets_data.columns else 'id'
        ticket_id_col_calls = 'ticket_id' if 'ticket_id' in filtered_calls_data.columns else 'id_ticket'
        
        # Create a copy of filtered_calls_data with a standardized ticket_id column
        if ticket_id_col_calls in filtered_calls_data.columns:
            filtered_calls_data['_standard_ticket_id'] = filtered_calls_data[ticket_id_col_calls]
            
        # Create a copy of filtered_tickets_data with a standardized ticket_id column
        if ticket_id_col_tickets in filtered_tickets_data.columns:
            filtered_tickets_data['_standard_ticket_id'] = filtered_tickets_data[ticket_id_col_tickets]

    # Dashboard tabs
    tabs = st.tabs(["Tickets Analysis", "Calls Analysis"])
    
    with tabs[0]:
        st.header("Tickets Overview")

        # Filters for this tab
        if not filtered_tickets_data.empty:
            selected_status = st.selectbox("Select Ticket Status", ["All"] + list(filtered_tickets_data['status_ticket'].dropna().unique()), key='ticket_status')
            selected_ticket_category = st.selectbox("Select Ticket Category", ["All"] + list(filtered_tickets_data['ticket_category_name'].dropna().unique()), key='ticket_cat')

            # Apply these filters
            tab_filtered_tickets = filtered_tickets_data.copy()
            if selected_status != "All":
                tab_filtered_tickets = tab_filtered_tickets[tab_filtered_tickets['status_ticket'] == selected_status]
            if selected_ticket_category != "All":
                tab_filtered_tickets = tab_filtered_tickets[tab_filtered_tickets['ticket_category_name'] == selected_ticket_category]
        else:
            tab_filtered_tickets = filtered_tickets_data

        if tab_filtered_tickets.empty:
            st.warning("No ticket data available for the selected filters.")
        else:
            # The join with ticketcall_df creates duplicates for tickets with multiple calls.
            # For ticket-centric analysis in this tab, we must use a dataframe with unique tickets.
            unique_tab_filtered_tickets = tab_filtered_tickets.drop_duplicates(subset=['id_ticket'])

            # Calculate metrics using the unique tickets dataframe
            metrics_df = unique_tab_filtered_tickets.rename(columns={
                'status_ticket': 'status',
                'created_at_ticket': 'created_at',
                'closed_at_ticket': 'closed_at'
            })
            ticket_metrics = calculate_ticket_metrics(metrics_df)

            # --- Custom Metrics ---
            # Sum the 'call_count' from the unique tickets dataframe to get total calls.
            total_calls_on_tickets = unique_tab_filtered_tickets['call_count'].sum()
            unique_customers = unique_tab_filtered_tickets['customer_id'].nunique()
            avg_tickets_per_customer = ticket_metrics.get('total_tickets', 0) / unique_customers if unique_customers > 0 else 0

            # Key metrics row
            metrics_data = [
                {"label": "Total Tickets", "value": ticket_metrics.get('total_tickets', 0)},
                {"label": "Open Tickets", "value": ticket_metrics.get('open_tickets', 0)},
                {"label": "Closed Tickets", "value": ticket_metrics.get('closed_tickets', 0)},
                {"label": "Total Calls", "value": int(total_calls_on_tickets)},
                {"label": "Avg. Tickets Per Customer", "value": f"{avg_tickets_per_customer:.2f}"}
            ]
            create_multi_metric_row(metrics_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'status_ticket' in unique_tab_filtered_tickets.columns:
                    status_counts = unique_tab_filtered_tickets['status_ticket'].value_counts().reset_index()
                    status_counts.columns = ['status', 'count']
                    fig = create_pie_chart(status_counts, 'status', 'count', 'Ticket Status Distribution')
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if 'ticket_category_name' in unique_tab_filtered_tickets.columns:
                    category_counts = unique_tab_filtered_tickets['ticket_category_name'].value_counts().reset_index()
                    category_counts.columns = ['category', 'count']
                    fig = create_pie_chart(category_counts, 'category', 'count', 'Ticket Category Distribution')
                    st.plotly_chart(fig, use_container_width=True)

            # Tickets over time
            st.header("Tickets Over Time")
            tickets_over_time = unique_tab_filtered_tickets.resample('W', on='created_at_ticket').size().reset_index(name='count')
            fig_time = px.line(tickets_over_time, x='created_at_ticket', y='count', title='Weekly Ticket Volume')
            st.plotly_chart(fig_time, use_container_width=True)

            # --- Top 10 Customers by Ticket Count ---
            st.header("Top 10 Customers by Ticket Count")
            top_customers_by_ticket = unique_tab_filtered_tickets['customer_name'].value_counts().nlargest(10).reset_index()
            top_customers_by_ticket.columns = ['Customer Name', 'Number of Tickets']
            st.dataframe(top_customers_by_ticket)

            for customer_name in top_customers_by_ticket['Customer Name']:
                with st.expander(f"Details for {customer_name}"):
                    customer_tickets = unique_tab_filtered_tickets[unique_tab_filtered_tickets['customer_name'] == customer_name]
                    st.write(f"Total Tickets: {len(customer_tickets)}")
                    
                    # Display ticket details
                    st.write("Ticket Details:")
                    st.dataframe(customer_tickets[['id_ticket', 'status_ticket', 'created_at_ticket', 'description', 'call_count']])
                    
                    # Display call details with callresult for each ticket
                    st.write("Call Details:")
                    for ticket_id in customer_tickets['id_ticket']:
                        ticket_calls = filtered_calls_data[filtered_calls_data['ticket_id'] == ticket_id]
                        if not ticket_calls.empty:
                            st.write(f"Calls for Ticket #{ticket_id}:")
                            st.dataframe(ticket_calls[['id', 'created_at', 'call_type_name', 'call_category_name', 'callresult', 'user_name']])

            #with st.expander("View Tickets Data"):
                #st.dataframe(unique_tab_filtered_tickets)

    with tabs[1]:
        st.header("Ticket Calls Overview")

        # Filters for this tab
        if not filtered_calls_data.empty:
            selected_call_category = st.selectbox("Select Call Category", ["All"] + list(filtered_calls_data['call_category_name'].dropna().unique()), key='call_cat')
            selected_user = st.selectbox("Select User", ["All"] + list(filtered_calls_data['user_name'].dropna().unique()), key='call_user')

            # Apply filters
            tab_filtered_calls = filtered_calls_data.copy()
            if selected_call_category != "All":
                tab_filtered_calls = tab_filtered_calls[tab_filtered_calls['call_category_name'] == selected_call_category]
            if selected_user != "All":
                tab_filtered_calls = tab_filtered_calls[tab_filtered_calls['user_name'] == selected_user]
                
            # Debug information
            st.write(f"Number of calls after filtering: {len(tab_filtered_calls)}")
            if '_standard_ticket_id' in tab_filtered_calls.columns:
                st.write(f"Unique ticket IDs in calls data: {tab_filtered_calls['_standard_ticket_id'].nunique()}")
        else:
            tab_filtered_calls = filtered_calls_data

        if tab_filtered_calls.empty:
            st.warning("No ticket call data available for the selected filters.")
        else:
            # --- Metrics ---
            total_calls = tab_filtered_calls.shape[0]
            inbound_calls = tab_filtered_calls[tab_filtered_calls['call_type_name'] != 'صادر'].shape[0]
            outbound_calls = total_calls - inbound_calls
            tab_filtered_calls['call_duration'] = pd.to_numeric(tab_filtered_calls['call_duration'], errors='coerce').fillna(0)
            avg_duration = tab_filtered_calls['call_duration'].mean()

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Total Calls", total_calls)
            m_col2.metric("Inbound Calls", inbound_calls)
            m_col3.metric("Outbound Calls", outbound_calls)
            m_col4.metric("Avg. Duration (sec)", f"{avg_duration:.2f}")

            # --- NEW METRIC ---
            st.subheader("Average Calls per Customer by Call Category")
            if 'customer_id' in tab_filtered_calls.columns and 'call_category_name' in tab_filtered_calls.columns:
                calls_per_customer_category = tab_filtered_calls.groupby(['call_category_name', 'customer_id']).size().reset_index(name='call_count')
                avg_calls = calls_per_customer_category.groupby('call_category_name')['call_count'].mean().reset_index()
                avg_calls = avg_calls.rename(columns={'call_count': 'Avg Calls per Customer'})
                st.dataframe(avg_calls)

            # --- Charts ---
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                st.subheader("Call Type Distribution")
                call_type_dist = tab_filtered_calls['call_type_name'].value_counts().reset_index()
                call_type_dist.columns = ['Call Type', 'Count']
                fig_pie_calls = px.pie(call_type_dist, names='Call Type', values='Count', title='Call Types')
                st.plotly_chart(fig_pie_calls, use_container_width=True)

                st.subheader("Calls by Hour of Day")
                tab_filtered_calls['hour'] = tab_filtered_calls['created_at'].dt.hour
                calls_by_hour = tab_filtered_calls['hour'].value_counts().sort_index().reset_index()
                calls_by_hour.columns = ['Hour', 'Number of Calls']
                fig_hour = px.bar(calls_by_hour, x='Hour', y='Number of Calls', title='Peak Call Times')
                st.plotly_chart(fig_hour, use_container_width=True)

            with c_col2:
                st.subheader("Call Category Distribution")
                call_cat_dist = tab_filtered_calls['call_category_name'].value_counts().reset_index()
                call_cat_dist.columns = ['Call Category', 'Count']
                fig_cat = px.bar(call_cat_dist, x='Count', y='Call Category', orientation='h', title='Call Categories')
                st.plotly_chart(fig_cat, use_container_width=True)

                st.subheader("Calls by Day of Week")
                tab_filtered_calls['day_of_week'] = tab_filtered_calls['created_at'].dt.day_name()
                calls_by_day = tab_filtered_calls['day_of_week'].value_counts().reset_index()
                calls_by_day.columns = ['Day of Week', 'Number of Calls']
                days_order = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                calls_by_day['Day of Week'] = pd.Categorical(calls_by_day['Day of Week'], categories=days_order, ordered=True)
                calls_by_day = calls_by_day.sort_values('Day of Week')
                fig_day = px.bar(calls_by_day, x='Day of Week', y='Number of Calls', title='Busiest Days')
                st.plotly_chart(fig_day, use_container_width=True)

            st.subheader("Daily Call Volume")
            calls_over_time = tab_filtered_calls.resample('W', on='created_at').size().reset_index(name='count')
            fig_line_calls = px.line(calls_over_time, x='created_at', y='count', title='Call Volume Over Time')
            st.plotly_chart(fig_line_calls, use_container_width=True)

            st.header("Call Reasons by Governorate")
            treemap_data = tab_filtered_calls.groupby(['governorate_name', 'call_category_name']).size().reset_index(name='count')
            if not treemap_data.empty:
                fig_tree = px.treemap(treemap_data, path=['governorate_name', 'call_category_name'], values='count',
                                 title='Call Reasons Distribution by Governorate',
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.warning("No data available for the treemap.")

            # --- Top Customers by Call Volume ---
            st.header("Top Customers by Call Volume")
            top_customers = tab_filtered_calls['customer_name'].value_counts().nlargest(5).reset_index()
            top_customers.columns = ['Customer Name', 'Number of Calls']

            st.dataframe(top_customers)

            for customer_name in top_customers['Customer Name']:
                with st.expander(f"Details for {customer_name}"):
                    customer_calls = tab_filtered_calls[tab_filtered_calls['customer_name'] == customer_name]
                    st.write(f"Total Calls: {len(customer_calls)}")
                    
                    # Display call reasons
                    st.write("Call Reasons:")
                    reasons = customer_calls['call_category_name'].value_counts().reset_index()
                    reasons.columns = ['Reason', 'Count']
                    st.dataframe(reasons)

                    # Display call details
                    st.write("Call Details:")
                    st.dataframe(customer_calls[['created_at', 'call_duration', 'call_type_name', 'user_name', 'callresult']])

            with st.expander("View Ticket Calls Data"):
                st.dataframe(tab_filtered_calls)


# Run the app
if __name__ == "__main__":
    main()
