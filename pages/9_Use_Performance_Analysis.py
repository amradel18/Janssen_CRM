import streamlit as st
import pandas as pd
import plotly.express as px
from process.data_loader import load_all_data
from auth.login import login_form
import numpy as np

# Ensure page config is set before any other Streamlit calls
st.set_page_config(page_title="User Performance Analysis", layout="wide")

# Function to check authentication
if not login_form():
    st.stop()

st.title("User Performance Analysis")

# Load data
try:
    if 'dataframes' not in st.session_state:
        with st.spinner("Loading data..."):
            st.session_state.dataframes = load_all_data()
    dataframes = st.session_state.dataframes

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

    # Sidebar filter for company
    st.sidebar.header("Filter by Company")
    # Create company mapping
    company_mapping = {1: "Englander", 2: "Janssen"}
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
    
    # Filter data based on selected user
    if selected_user != 'All':
        user_id = users_df.loc[users_df['name'] == selected_user, 'id'].iloc[0]
        tickets_df = tickets_df.loc[tickets_df['created_by'] == user_id].copy()
        customercall_df = customercall_df.loc[customercall_df['created_by'] == user_id].copy()
        ticketcall_df = ticketcall_df.loc[ticketcall_df['created_by'] == user_id].copy()

    # Filter data based on date range
    tickets_df = tickets_df.loc[(tickets_df['created_at'] >= start_date) & (tickets_df['created_at'] <= end_date)].copy()
    customercall_df = customercall_df.loc[(customercall_df['created_at'] >= start_date) & (customercall_df['created_at'] <= end_date)].copy()
    ticketcall_df = ticketcall_df.loc[(ticketcall_df['created_at'] >= start_date) & (ticketcall_df['created_at'] <= end_date)].copy()

    # --- Visualizations ---

    tab1, tab2 = st.tabs(["Customer Calls", "Ticket Calls"])

    with tab1:
        st.header("Customer Call Analysis")

        # Donut chart for Inbound vs Outbound calls
        st.subheader("Inbound vs Outbound Calls")
        if not customercall_df.empty:
            # Create a column for call direction based on call_type
            # Assuming call_type 1 is outbound and 2 is inbound (based on sample data)
            call_type_counts = customercall_df['call_type'].value_counts().reset_index()
            call_type_counts.columns = ['Call Type', 'Count']
            
            # Map call types to readable names
            call_type_map = {1: "Outbound", 2: "Inbound"}
            call_type_counts['Call Direction'] = call_type_counts['Call Type'].map(call_type_map)
            
            # Create donut chart
            fig_call_types = px.pie(
                call_type_counts, 
                values='Count', 
                names='Call Direction',
                title='Call Distribution by Direction',
                hole=0.4,  # This makes it a donut chart
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_call_types.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_call_types, use_container_width=True)
        else:
            st.info("No customer call data to display.")
            
        # Calls by Hour of Day
        st.subheader("Calls by Hour of Day")
        if not customercall_df.empty:
            customercall_df.loc[:, 'hour'] = customercall_df['created_at'].dt.hour
            calls_by_hour = customercall_df['hour'].value_counts().sort_index().reset_index()
            calls_by_hour.columns = ['Hour', 'Number of Calls']
            fig = px.bar(calls_by_hour, x='Hour', y='Number of Calls', title='Peak Call Times')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No customer call data to display.")

        # 2. Average Customer Calls per Customer
        st.subheader("Average Customer Calls per Customer by User")
        if not customercall_df.empty:
            avg_calls_per_customer = customercall_df.groupby(['created_by', 'customer_id']).size().reset_index(name='num_calls')
            avg_calls_per_user = avg_calls_per_customer.groupby('created_by')['num_calls'].mean().reset_index(name='avg_calls')
            avg_calls_per_user = avg_calls_per_user.merge(users_df[['id', 'name']], left_on='created_by', right_on='id')
            fig_avg_calls = px.bar(avg_calls_per_user, x='name', y='avg_calls', title='Average Customer Calls per Customer by User')
            st.plotly_chart(fig_avg_calls, use_container_width=True)
        else:
            st.info("No customer call data to display for average calculation.")
# minutes
    with tab2:
        st.header("Ticket Call Analysis")

        # Merge with tickets_df to get customer_id
        ticketcall_df_merged = pd.merge(ticketcall_df, tickets_df[['id', 'customer_id']], left_on='ticket_id', right_on='id', how='left')

        # Donut chart for Inbound vs Outbound ticket calls
        st.subheader("Inbound vs Outbound Ticket Calls")
        if not ticketcall_df.empty:
            # Create a column for call direction based on call_type
            # Assuming call_type 1 is outbound and 2 is inbound (based on sample data)
            ticket_call_type_counts = ticketcall_df['call_type'].value_counts().reset_index()
            ticket_call_type_counts.columns = ['Call Type', 'Count']
            
            # Map call types to readable names
            call_type_map = {1: "Outbound", 2: "Inbound"}
            ticket_call_type_counts['Call Direction'] = ticket_call_type_counts['Call Type'].map(call_type_map)
            
            # Create donut chart
            fig_ticket_call_types = px.pie(
                ticket_call_type_counts, 
                values='Count', 
                names='Call Direction',
                title='Ticket Call Distribution by Direction',
                hole=0.4,  # This makes it a donut chart
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_ticket_call_types.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_ticket_call_types, use_container_width=True)
        else:
            st.info("No ticket call data to display.")

        # Calls by Hour of Day for tickets
        st.subheader("Ticket Calls by Hour of Day")
        if not ticketcall_df.empty:
            ticketcall_df_merged['hour'] = ticketcall_df_merged['created_at'].dt.hour
            calls_by_hour_ticket = ticketcall_df_merged['hour'].value_counts().sort_index().reset_index()
            calls_by_hour_ticket.columns = ['Hour', 'Number of Calls']
            fig_ticket = px.bar(calls_by_hour_ticket, x='Hour', y='Number of Calls', title='Peak Ticket Call Times')
            st.plotly_chart(fig_ticket, use_container_width=True)
        else:
            st.info("No ticket call data to display.")

        # 2. Average Ticket Calls per Customer by User
        st.subheader("Average Ticket Calls per Customer by User")
        if not ticketcall_df.empty:
            avg_ticket_calls_per_customer = ticketcall_df_merged.groupby(['created_by', 'customer_id']).size().reset_index(name='num_calls')
            avg_ticket_calls_per_user = avg_ticket_calls_per_customer.groupby('created_by')['num_calls'].mean().reset_index(name='avg_calls')
            avg_ticket_calls_per_user = avg_ticket_calls_per_user.merge(users_df[['id', 'name']], left_on='created_by', right_on='id')
            fig_avg_calls = px.bar(avg_ticket_calls_per_user, x='name', y='avg_calls', title='Average Ticket Calls per Customer by User')
            st.plotly_chart(fig_avg_calls, use_container_width=True)
        else:
            st.info("No ticket call data to display for average calculation.")

    # 3. Users and Number of Tickets
    st.header("Number of Tickets per User")
    if not tickets_df.empty:
        tickets_by_user = tickets_df.groupby('created_by').size().reset_index(name='ticket_count')
        tickets_by_user = tickets_by_user.merge(users_df[['id', 'name']], left_on='created_by', right_on='id')
        fig_tickets = px.bar(tickets_by_user, x='name', y='ticket_count', title='Number of Tickets per User')
        st.plotly_chart(fig_tickets, use_container_width=True)
    else:
        st.info("No ticket data to display.")

    # 4. Ticket Creation Over Time
    st.header("Ticket Creation Over Time")
    if not tickets_df.empty:
        tickets_over_time = tickets_df.set_index('created_at').resample('D').size().reset_index(name='ticket_count')
        fig_tickets_time = px.line(tickets_over_time, x='created_at', y='ticket_count', title='Daily Registered Tickets')
        st.plotly_chart(fig_tickets_time, use_container_width=True)
    else:
        st.info("No ticket data to display.")

except Exception as e:
    st.error(f"An error occurred: {e}")