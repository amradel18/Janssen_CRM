import streamlit as st
import pandas as pd
import plotly.express as px
from process.data_loader import load_all_data, get_companies_data, get_company_mapping
from process.session_manager import ensure_data_loaded, get_dataframes
from auth.authentication import check_authentication
import numpy as np

# Ensure page config is set before any other Streamlit calls
# Page config is set in the main app

# Function to check authentication
check_authentication()

st.title("User Performance Analysis")

try:
    # Ensure data is loaded
    ensure_data_loaded()

    # Get dataframes safely
    dataframes = get_dataframes()

    users_df = dataframes.get('users')
    tickets_df = dataframes.get('tickets')
    customercall_df = dataframes.get('customercall')
    ticketcall_df = dataframes.get('ticketcall')
    customers_df = dataframes.get('customers')

    if users_df is None or tickets_df is None or customercall_df is None or ticketcall_df is None or customers_df is None:
        st.error("Failed to load data. Please check the source.")
        st.stop()

    # Convert created_at to datetime
    tickets_df['created_at'] = pd.to_datetime(tickets_df['created_at'], errors='coerce')
    customercall_df['created_at'] = pd.to_datetime(customercall_df['created_at'], errors='coerce')
    ticketcall_df['created_at'] = pd.to_datetime(ticketcall_df['created_at'], errors='coerce')
    # Ensure customers_df has datetime for date filtering
    customers_df['created_at'] = pd.to_datetime(customers_df.get('created_at', pd.Series(dtype='datetime64[ns]')), errors='coerce')

    # Add company_id to customercall_df from customers_df
    if 'company_id' in customercall_df.columns:
        customercall_df = customercall_df.drop('company_id', axis=1)
    customer_company_info = customers_df[['id', 'company_id']].rename(columns={'id': 'customer_id_ref'})
    customercall_df = pd.merge(customercall_df, customer_company_info, left_on='customer_id', right_on='customer_id_ref', how='left')
    if 'customer_id_ref' in customercall_df.columns:
        customercall_df = customercall_df.drop(columns=['customer_id_ref'])

    # Add company_id to ticketcall_df from tickets_df
    if 'company_id' in ticketcall_df.columns:
        ticketcall_df = ticketcall_df.drop('company_id', axis=1)
    ticket_company_info = tickets_df[['id', 'company_id']].rename(columns={'id': 'ticket_id_ref'})
    ticketcall_df = pd.merge(ticketcall_df, ticket_company_info, left_on='ticket_id', right_on='ticket_id_ref', how='left')
    if 'ticket_id_ref' in ticketcall_df.columns:
        ticketcall_df = ticketcall_df.drop(columns=['ticket_id_ref'])

    # Sidebar filter for company# Filter Options
    st.sidebar.header("Filter by Company")
    
    company_mapping = get_company_mapping()
    company_list = ['All'] + list(company_mapping.values())
    selected_company = st.sidebar.selectbox('Select Company', company_list)
    
    # Sidebar filter for users
    st.sidebar.header("Filter by User")
    user_list = ['All'] + users_df['name'].unique().tolist()
    selected_user = st.sidebar.selectbox('Select User', user_list)

    # Sidebar filter for date range
    st.sidebar.header("Filter by Date Range")
    valid_dates = tickets_df['created_at'].dropna()
    if valid_dates.empty:
        st.info("No valid ticket dates found to filter by.")
        st.stop()
    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()
    start_date = st.sidebar.date_input('Start date', min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input('End date', max_date, min_value=start_date, max_value=max_date)

    # Convert start_date and end_date to datetime
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Filter data based on selected company
    if selected_company != 'All':
        # Get company_id from the company name
        company_id = [k for k, v in company_mapping.items() if v == selected_company][0]
        
        # Filter dataframes by company_id
        tickets_df = tickets_df.loc[tickets_df['company_id'] == company_id].copy()
        
        # For customercall and ticketcall, check if company_id exists
        if 'company_id' in customercall_df.columns:
            customercall_df = customercall_df.loc[customercall_df['company_id'] == company_id].copy()
        
        if 'company_id' in ticketcall_df.columns:
            ticketcall_df = ticketcall_df.loc[ticketcall_df['company_id'] == company_id].copy()
        
        # Filter customers by company_id
        if 'company_id' in customers_df.columns:
            customers_df = customers_df.loc[customers_df['company_id'] == company_id].copy()
    
    # Filter data based on selected user
    if selected_user != 'All':
        user_id = users_df.loc[users_df['name'] == selected_user, 'id'].iloc[0]
        tickets_df = tickets_df.loc[tickets_df['created_by'] == user_id].copy()
        customercall_df = customercall_df.loc[customercall_df['created_by'] == user_id].copy()
        ticketcall_df = ticketcall_df.loc[ticketcall_df['created_by'] == user_id].copy()
        # Filter customers created by user
        if 'created_by' in customers_df.columns:
            customers_df = customers_df.loc[customers_df['created_by'] == user_id].copy()

    # Filter data based on date range
    tickets_df = tickets_df.loc[(tickets_df['created_at'] >= start_date) & (tickets_df['created_at'] <= end_date)].copy()
    customercall_df = customercall_df.loc[(customercall_df['created_at'] >= start_date) & (customercall_df['created_at'] <= end_date)].copy()
    ticketcall_df = ticketcall_df.loc[(ticketcall_df['created_at'] >= start_date) & (ticketcall_df['created_at'] <= end_date)].copy()
    if 'created_at' in customers_df.columns:
        customers_df = customers_df.loc[(customers_df['created_at'] >= start_date) & (customers_df['created_at'] <= end_date)].copy()

    # --- Counts Summary ---
    st.header("Counts Summary")

    # Totals metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Customer Calls", len(customercall_df))
    with m2:
        st.metric("Total Ticket Calls", len(ticketcall_df))
    with m3:
        st.metric("Total Customers Created", len(customers_df) if not customers_df.empty else 0)
    with m4:
        st.metric("Total Tickets Created", len(tickets_df))

    # --- Visualizations ---
    st.header("Calls Visualizations")
    tab_cust, tab_ticket = st.tabs(["Customer Calls", "Ticket Calls"])

    # Map for call direction
    call_type_map = {1: "Outbound", 2: "Inbound"}

    with tab_cust:
        st.subheader("Inbound vs Outbound (Donut)")
        if not customercall_df.empty and 'call_type' in customercall_df.columns:
            call_dir = customercall_df['call_type'].map(call_type_map).fillna('Unknown')
            call_counts = call_dir.value_counts().reset_index()
            call_counts.columns = ['Direction', 'Count']
            fig_cust_pie = px.pie(
                call_counts,
                values='Count',
                names='Direction',
                hole=0.5,
                title='Customer Calls by Direction',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_cust_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_cust_pie, use_container_width=True)
        else:
            st.info("No customer call data to display.")

        st.subheader("Calls by Hour of Day (Bar)")
        if not customercall_df.empty and 'created_at' in customercall_df.columns:
            df_hours = customercall_df.dropna(subset=['created_at']).copy()
            if not df_hours.empty:
                df_hours.loc[:, 'hour'] = df_hours['created_at'].dt.hour
                calls_by_hour = df_hours['hour'].value_counts().sort_index().reset_index()
                calls_by_hour.columns = ['Hour', 'Number of Calls']
                fig_cust_bar = px.bar(calls_by_hour, x='Hour', y='Number of Calls', title='Customer Calls by Hour')
                st.plotly_chart(fig_cust_bar, use_container_width=True)
            else:
                st.info("No customer call data with valid timestamps.")
        else:
            st.info("No customer call data to display.")

    with tab_ticket:
        st.subheader("Inbound vs Outbound (Donut)")
        if not ticketcall_df.empty and 'call_type' in ticketcall_df.columns:
            ticket_dir = ticketcall_df['call_type'].map(call_type_map).fillna('Unknown')
            ticket_counts = ticket_dir.value_counts().reset_index()
            ticket_counts.columns = ['Direction', 'Count']
            fig_ticket_pie = px.pie(
                ticket_counts,
                values='Count',
                names='Direction',
                hole=0.5,
                title='Ticket Calls by Direction',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_ticket_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_ticket_pie, use_container_width=True)
        else:
            st.info("No ticket call data to display.")

        st.subheader("Calls by Hour of Day (Bar)")
        if not ticketcall_df.empty and 'created_at' in ticketcall_df.columns:
            df_hours_t = ticketcall_df.dropna(subset=['created_at']).copy()
            if not df_hours_t.empty:
                df_hours_t.loc[:, 'hour'] = df_hours_t['created_at'].dt.hour
                calls_by_hour_t = df_hours_t['hour'].value_counts().sort_index().reset_index()
                calls_by_hour_t.columns = ['Hour', 'Number of Calls']
                fig_ticket_bar = px.bar(calls_by_hour_t, x='Hour', y='Number of Calls', title='Ticket Calls by Hour')
                st.plotly_chart(fig_ticket_bar, use_container_width=True)
            else:
                st.info("No ticket call data with valid timestamps.")
        else:
            st.info("No ticket call data to display.")

    # Helper to show counts per user as side-by-side charts (bar + donut)
    def show_counts_per_user(df, users_df, title, count_col_name):
        st.subheader(title)
        if df.empty or 'created_by' not in df.columns:
            st.info("No data to display.")
            return
        counts = df.groupby('created_by').size().reset_index(name=count_col_name)
        counts = counts.merge(users_df[['id', 'name']], left_on='created_by', right_on='id', how='left')
        counts['user'] = counts['name'].fillna('Unknown')
        counts = counts.drop(columns=['id', 'name'], errors='ignore')
        counts = counts.sort_values(count_col_name, ascending=False)

        c1, c2 = st.columns(2)
        with c1:
            fig_bar = px.bar(
                counts,
                x='user',
                y=count_col_name,
                title=f"{title} (Bar)",
            )
            fig_bar.update_layout(xaxis_title='User', yaxis_title='Count')
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_pie = px.pie(
                counts,
                values=count_col_name,
                names='user',
                hole=0.5,
                title=f"{title} (Donut)",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

    # Customer calls per user
    show_counts_per_user(customercall_df, users_df, "Customer Calls per User", "customer_calls")
    # Ticket calls per user
    show_counts_per_user(ticketcall_df, users_df, "Ticket Calls per User", "ticket_calls")
    # Customers created per user
    show_counts_per_user(customers_df, users_df, "Customers Created per User", "customers_created")
    # Tickets created per user
    show_counts_per_user(tickets_df, users_df, "Tickets Created per User", "tickets_created")

except Exception as e:
    st.error(f"An error occurred: {e}")