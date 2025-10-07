import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import plotly.express as px

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the centralized modules
from process.data_loader import load_all_data, get_companies_data, get_company_mapping
from process.data_processor import calculate_call_metrics, join_ticket_and_call_data
from process.session_manager import ensure_data_loaded, get_dataframes
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

    # Merge with other dimension tables - using unique suffixes for each merge
    # First, ensure users_df has a unique id column for merging
    users_df_merge = users_df.copy()
    users_df_merge = users_df_merge.rename(columns={'id': 'user_id'})
    
    # Ensure data types match before merging
    if 'created_by' in merged_df.columns:
        # Convert created_by to integer if it's not already
        merged_df['created_by'] = pd.to_numeric(merged_df['created_by'], errors='coerce')
        # Convert user_id to the same type as created_by
        users_df_merge['user_id'] = pd.to_numeric(users_df_merge['user_id'], errors='coerce')
    
    merged_df = merged_df.merge(users_df_merge[['user_id', 'user_name']], left_on='created_by', right_on='user_id', how='left')
    
    # Then ensure call_types_df has a unique id column for merging
    call_types_df_merge = call_types_df.copy()
    call_types_df_merge = call_types_df_merge.rename(columns={'id': 'call_type_id'})
    
    # Ensure data types match before merging
    if 'call_type' in merged_df.columns:
        # Convert call_type to integer if it's not already
        merged_df['call_type'] = pd.to_numeric(merged_df['call_type'], errors='coerce')
        # Convert call_type_id to the same type as call_type
        call_types_df_merge['call_type_id'] = pd.to_numeric(call_types_df_merge['call_type_id'], errors='coerce')
    
    merged_df = merged_df.merge(call_types_df_merge[['call_type_id', 'call_type_name']], left_on='call_type', right_on='call_type_id', how='left')
    
    # Finally ensure call_categories_df has a unique id column for merging
    call_categories_df_merge = call_categories_df.copy()
    call_categories_df_merge = call_categories_df_merge.rename(columns={'id': 'call_category_id'})
    
    # Ensure data types match before merging
    if 'call_cat_id' in merged_df.columns:
        # Convert call_cat_id to integer if it's not already
        merged_df['call_cat_id'] = pd.to_numeric(merged_df['call_cat_id'], errors='coerce')
        # Convert call_category_id to the same type as call_cat_id
        call_categories_df_merge['call_category_id'] = pd.to_numeric(call_categories_df_merge['call_category_id'], errors='coerce')
    
    merged_df = merged_df.merge(call_categories_df_merge[['call_category_id', 'call_category_name']], left_on='call_cat_id', right_on='call_category_id', how='left')

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
    st.title("Calls Analysis")
    
    # Ensure data is loaded
    ensure_data_loaded()
    
    # Get dataframes safely
    dataframes = get_dataframes()
    
    # Get the merged data
    merged_data = get_ticket_call_analysis_data(dataframes)
    
    if merged_data.empty:
        st.warning("No data available. Please check your data sources.")
        return
    
    # Get tickets data
    tickets_df = dataframes.get('tickets', pd.DataFrame()).copy()
    
    if tickets_df.empty:
        st.warning("No tickets data available.")
        return
    
    # Merge tickets with customers and other dimension tables
    customers_df = dataframes.get('customers', pd.DataFrame()).copy()
    ticket_categories_df = dataframes.get('ticket_categories', pd.DataFrame()).copy()
    users_df = dataframes.get('users', pd.DataFrame()).copy()
    
    # Rename columns for merging
    users_df = users_df.rename(columns={'name': 'user_name'})
    ticket_categories_df = ticket_categories_df.rename(columns={'name': 'ticket_category_name'})
    
    # Merge tickets with dimensions
    tickets_df = tickets_df.merge(customers_df[['id', 'name', 'company_id']], left_on='customer_id', right_on='id', how='left', suffixes=('', '_customer'))
    tickets_df = tickets_df.rename(columns={'name': 'customer_name'})
    
    tickets_df = tickets_df.merge(users_df[['id', 'user_name']], left_on='created_by', right_on='id', how='left', suffixes=('', '_user'))
    
    # Check if ticket_category_id exists before merging
    if 'ticket_category_id' in tickets_df.columns:
        tickets_df = tickets_df.merge(ticket_categories_df[['id', 'ticket_category_name']], left_on='ticket_category_id', right_on='id', how='left', suffixes=('', '_ticket_cat'))
        tickets_df['ticket_category_name'] = tickets_df['ticket_category_name'].fillna('Unknown Category')
    else:
        # Add ticket_category_name column with default value if ticket_category_id doesn't exist
        tickets_df['ticket_category_name'] = 'Unknown Category'
    
    # Fill NA
    tickets_df['customer_name'] = tickets_df['customer_name'].fillna('Unknown Customer')
    tickets_df['user_name'] = tickets_df['user_name'].fillna('Unknown User')
    
    # Convert date columns to datetime
    tickets_df['created_at'] = pd.to_datetime(tickets_df['created_at'], errors='coerce')
    tickets_df['closed_at'] = pd.to_datetime(tickets_df['closed_at'], errors='coerce')
    
    # Join tickets with calls data
    users_df = dataframes.get('users', pd.DataFrame())
    ticket_categories_df = dataframes.get('ticket_categories', pd.DataFrame())
    call_types_df = dataframes.get('call_types', pd.DataFrame())
    customers_df = dataframes.get('customers', pd.DataFrame())
    call_categories_df = dataframes.get('call_categories', pd.DataFrame())
    
    joined_data = join_ticket_and_call_data(
        tickets_df, 
        merged_data,
        users_df,
        ticket_categories_df,
        call_types_df,
        customers_df,
        call_categories_df
    )
    
    # Filters section
    # --- Sidebar Filters ---
    with st.sidebar:
        st.header("Filters")
        
        # Date range filter
        st.subheader("Date Range")
        
        # Check if 'created_at' column exists (use calls created_at from merged_data)
        if not merged_data.empty and 'created_at' in merged_data.columns:
            min_date = merged_data['created_at'].min().date()
            max_date = merged_data['created_at'].max().date()
        else:
            min_date = datetime.now().date() - timedelta(days=30)
            max_date = datetime.now().date()
            
        start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
        
        # Company filter
        st.subheader("Company")
        company_mapping = get_company_mapping()
        company_options = ["All"] + list(company_mapping.values())
        selected_company = st.selectbox("Select Company", company_options)
    
    # Convert to datetime for filtering
    start_datetime = pd.Timestamp(start_date)
    end_datetime = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    
    # Filter by date range
    if not joined_data.empty and 'created_at' in joined_data.columns:
        filtered_tickets_data = joined_data[
            (joined_data['created_at'] >= start_datetime) & 
            (joined_data['created_at'] <= end_datetime)
        ].copy()
    else:
        filtered_tickets_data = joined_data.copy() if not joined_data.empty else pd.DataFrame()
    
    # Filter calls data by the same date range
    if not merged_data.empty and 'created_at' in merged_data.columns:
        filtered_calls_data = merged_data[
            (merged_data['created_at'] >= start_datetime) & 
            (merged_data['created_at'] <= end_datetime)
        ].copy()
    else:
        filtered_calls_data = merged_data.copy() if not merged_data.empty else pd.DataFrame()
    
    # Apply the selected company filter consistently to both datasets
    if 'selected_company' in locals() and selected_company != "All":
        company_rev = {v: k for k, v in company_mapping.items()}
        selected_company_id = company_rev.get(selected_company)
        if selected_company_id is not None:
            if 'company_id' in filtered_calls_data.columns:
                filtered_calls_data = filtered_calls_data[filtered_calls_data['company_id'] == selected_company_id].copy()
            if 'company_id' in filtered_tickets_data.columns:
                filtered_tickets_data = filtered_tickets_data[filtered_tickets_data['company_id'] == selected_company_id].copy()
    
    if not filtered_calls_data.empty and not filtered_tickets_data.empty:
        # Create a mapping between ticket IDs in both dataframes
        ticket_id_mapping = {}
        
        # Check which columns to use for joining - safely handle potential errors
        try:
            # First check if these columns exist
            ticket_id_col_tickets = None
            if 'id_ticket' in filtered_tickets_data.columns:
                ticket_id_col_tickets = 'id_ticket'
            elif 'id' in filtered_tickets_data.columns:
                ticket_id_col_tickets = 'id'
                
            ticket_id_col_calls = None
            if 'ticket_id' in filtered_calls_data.columns:
                ticket_id_col_calls = 'ticket_id'
            elif 'id_ticket' in filtered_calls_data.columns:
                ticket_id_col_calls = 'id_ticket'
            
            # Create a copy of filtered_calls_data with a standardized ticket_id column (robust to duplicate columns)
            if ticket_id_col_calls is not None and ticket_id_col_calls in filtered_calls_data.columns:
                selected_calls = filtered_calls_data.loc[:, ticket_id_col_calls]
                if isinstance(selected_calls, pd.DataFrame):
                    # If duplicate columns with the same name exist, take the first
                    selected_calls = selected_calls.iloc[:, 0]
                filtered_calls_data['_standard_ticket_id'] = selected_calls
                
            # Create a copy of filtered_tickets_data with a standardized ticket_id column (robust to duplicate columns)
            if ticket_id_col_tickets is not None and ticket_id_col_tickets in filtered_tickets_data.columns:
                selected_tickets = filtered_tickets_data.loc[:, ticket_id_col_tickets]
                if isinstance(selected_tickets, pd.DataFrame):
                    # If duplicate columns with the same name exist, take the first
                    selected_tickets = selected_tickets.iloc[:, 0]
                filtered_tickets_data['_standard_ticket_id'] = selected_tickets
        except Exception as e:
            st.warning(f"Error standardizing ticket IDs: {str(e)}")

    # Calls Analysis
    st.header("Calls Overview")

    # Filters for calls
    if not filtered_calls_data.empty:
        # Call Type filter removed per request; will visualize it as a donut chart below
        selected_call_category = st.selectbox("Select Call Category", ["All"] + list(filtered_calls_data['call_category_name'].dropna().unique()), key='call_cat')

        # Apply these filters
        tab_filtered_calls = filtered_calls_data.copy()
        # removed selected_call_type filter per request
        if selected_call_category != "All":
            tab_filtered_calls = tab_filtered_calls[tab_filtered_calls['call_category_name'] == selected_call_category]
    else:
        tab_filtered_calls = filtered_calls_data

    if tab_filtered_calls.empty:
        st.warning("No call data available for the selected filters.")
    else:
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Calls", len(tab_filtered_calls))
        with col2:
            st.metric("Unique Tickets with Calls", tab_filtered_calls['ticket_id'].nunique())
        with col3:
            st.metric("Avg. Calls per Ticket", f"{len(tab_filtered_calls) / tab_filtered_calls['ticket_id'].nunique():.1f}" if tab_filtered_calls['ticket_id'].nunique() > 0 else "0")

        # Call type distribution
        # Small charts side-by-side
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Call Type Distribution")
            call_type_counts = tab_filtered_calls['call_type_name'].value_counts().reset_index()
            call_type_counts.columns = ['Call Type', 'Count']
            fig = px.pie(call_type_counts, values='Count', names='Call Type', title='Call Type Distribution', hole=0.4)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            # Call category distribution
            st.subheader("Call Category Distribution")
            call_category_counts = tab_filtered_calls['call_category_name'].value_counts().reset_index()
            call_category_counts.columns = ['Call Category', 'Count']
            fig = px.pie(call_category_counts, values='Count', names='Call Category', title='Call Category Distribution')
            st.plotly_chart(fig, use_container_width=True)

        # Calls over time
        st.subheader("Calls Over Time")
        
        # Ensure created_at is datetime
        tab_filtered_calls['created_at'] = pd.to_datetime(tab_filtered_calls['created_at'])
        
        # Group by date and count
        calls_by_date = tab_filtered_calls.groupby(tab_filtered_calls['created_at'].dt.date).size().reset_index()
        calls_by_date.columns = ['Date', 'Count']
        
        fig = px.line(calls_by_date, x='Date', y='Count', title='Calls Made Over Time')
        st.plotly_chart(fig, use_container_width=True)

        # Call Tree: Year > Month > Call Reason (with counts)
        st.subheader("Call Tree: Year > Month > Call Reason")
        df_tree = tab_filtered_calls.copy()
        df_tree['Year'] = df_tree['created_at'].dt.year
        df_tree['MonthNum'] = df_tree['created_at'].dt.month
        df_tree['Month'] = df_tree['created_at'].dt.strftime('%b')
        df_tree['Month Label'] = df_tree['MonthNum'].astype(str).str.zfill(2) + '-' + df_tree['Month']
        df_tree['Call Reason'] = df_tree['call_category_name'].fillna('Unknown Category')
        
        tree_counts = df_tree.groupby(['Year', 'Month Label', 'Call Reason']).size().reset_index(name='Count')
        
        fig_tree = px.treemap(
            tree_counts,
            path=['Year', 'Month Label', 'Call Reason'],
            values='Count',
            color='Count',
            color_continuous_scale='Blues',
            title='Calls by Year > Month > Reason'
        )
        st.plotly_chart(fig_tree, use_container_width=True)

        # Top users by call count and Calls by Day of Week side-by-side
        col_c, col_d = st.columns(2)
        with col_c:
            st.subheader("Top Users by Call Count")
            user_counts = tab_filtered_calls['user_name'].value_counts().reset_index()
            user_counts.columns = ['User', 'Count']
            user_counts = user_counts.head(10)  # Top 10
            fig = px.bar(user_counts, x='User', y='Count', title='Top 10 Users by Call Count')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        with col_d:
            st.subheader("Calls by Day of Week")
            tab_filtered_calls['day_of_week'] = tab_filtered_calls['created_at'].dt.day_name()
            calls_by_day = tab_filtered_calls['day_of_week'].value_counts().reset_index()
            calls_by_day.columns = ['Day of Week', 'Number of Calls']
            days_order = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            calls_by_day['Day of Week'] = pd.Categorical(calls_by_day['Day of Week'], categories=days_order, ordered=True)
            calls_by_day = calls_by_day.sort_values('Day of Week')
            fig_day = px.bar(calls_by_day, x='Day of Week', y='Number of Calls', title='Busiest Days')
            st.plotly_chart(fig_day, use_container_width=True)

        # Top customers by call count
        st.subheader("Top Customers by Call Count")
        customer_counts = tab_filtered_calls['customer_name'].value_counts().reset_index()
        customer_counts.columns = ['Customer', 'Count']
        customer_counts = customer_counts.head(10)  # Top 10
        
        fig = px.bar(customer_counts, x='Customer', y='Count', title='Top 10 Customers by Call Count')
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # --- Top Customers by Call Volume ---
        st.header("Top Customers by Call Volume")
        top_customers = tab_filtered_calls['customer_name'].value_counts().nlargest(10).reset_index()
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
                details_cols = [c for c in ['created_at', 'call_duration', 'call_type_name', 'user_name', 'callresult'] if c in customer_calls.columns]
                if details_cols:
                    st.dataframe(customer_calls[details_cols])
                else:
                    st.info("No detailed call columns available to display.")

        # Display sample calls
        st.subheader("Sample Calls (Top 10)")
        sample_calls = tab_filtered_calls[['id', 'ticket_id', 'customer_name', 'call_type_name', 'call_category_name', 'created_at', 'user_name', 'callresult']].head(10)
        sample_calls.columns = ['Call ID', 'Ticket ID', 'Customer', 'Call Type', 'Call Category', 'Created At', 'User', 'Call Result']
        st.dataframe(sample_calls)

if __name__ == "__main__":
    main()