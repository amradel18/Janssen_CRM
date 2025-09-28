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
    st.title("Tickets Analysis")
    
    # Load data
    if 'all_data_loaded' not in st.session_state or not st.session_state.all_data_loaded:
        with st.spinner("Loading data..."):
            all_dataframes = load_all_data()
            st.session_state.all_dataframes = all_dataframes
            st.session_state.all_data_loaded = True
    
    # Safely get dataframes from session state
    dataframes = getattr(st.session_state, 'all_dataframes', {})
    
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
    
    # Ticket category name will be attached later via join_ticket_and_call_data using ticket_cat_id.
    
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
    ticketcall_df = dataframes.get('ticketcall', pd.DataFrame())
     
    joined_data = join_ticket_and_call_data(
    tickets_df, 
    ticketcall_df,
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
        
        # Determine date range from ticket created date if available
        if not joined_data.empty:
            if 'created_at_ticket' in joined_data.columns:
                _dates = pd.to_datetime(joined_data['created_at_ticket'], errors='coerce').dropna()
            elif 'created_at' in joined_data.columns:
                _dates = pd.to_datetime(joined_data['created_at'], errors='coerce').dropna()
            else:
                _dates = pd.Series([], dtype='datetime64[ns]')
        else:
            _dates = pd.Series([], dtype='datetime64[ns]')
        if not _dates.empty:
            min_date = _dates.min().date()
            max_date = _dates.max().date()
        else:
            min_date = datetime.now().date() - timedelta(days=30)
            max_date = datetime.now().date()
            
        start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
        
        # Company filter
        st.subheader("Company")
        company_mapping = {1: "Englander", 2: "Janssen"}
        company_options = ["All"] + list(company_mapping.values())
        selected_company = st.selectbox("Select Company", company_options)
    
    # Convert to datetime for filtering
    start_datetime = pd.Timestamp(start_date)
    end_datetime = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    
    # Filter by date range using appropriate tickets date column
    if not joined_data.empty:
        date_col = 'created_at_ticket' if 'created_at_ticket' in joined_data.columns else ('created_at' if 'created_at' in joined_data.columns else None)
        if date_col is not None:
            filtered_tickets_data = joined_data[
                (pd.to_datetime(joined_data[date_col], errors='coerce') >= start_datetime) & 
                (pd.to_datetime(joined_data[date_col], errors='coerce') <= end_datetime)
            ].copy()
        else:
            filtered_tickets_data = joined_data.copy()
    else:
        filtered_tickets_data = pd.DataFrame()
    
    # Filter calls data by the same date range safely
    if not merged_data.empty and 'created_at' in merged_data.columns:
        filtered_calls_data = merged_data[
            (merged_data['created_at'] >= start_datetime) & 
            (merged_data['created_at'] <= end_datetime)
        ].copy()
    else:
        filtered_calls_data = merged_data.copy() if not merged_data.empty else pd.DataFrame()
    
    # Apply company filter consistently using the sidebar selection
    if 'selected_company' in locals() and selected_company != "All":
        inverse_company_mapping = {"Englander": 1, "Janssen": 2}
        selected_company_id = inverse_company_mapping.get(selected_company)
        if selected_company_id is not None:
            if 'company_id' in filtered_tickets_data.columns:
                filtered_tickets_data = filtered_tickets_data[filtered_tickets_data['company_id'] == selected_company_id]
            elif 'company_id_ticket' in filtered_tickets_data.columns:
                filtered_tickets_data = filtered_tickets_data[filtered_tickets_data['company_id_ticket'] == selected_company_id]
            
            if 'company_id' in filtered_calls_data.columns:
                filtered_calls_data = filtered_calls_data[filtered_calls_data['company_id'] == selected_company_id]
            elif 'company_id_call' in filtered_calls_data.columns:
                filtered_calls_data = filtered_calls_data[filtered_calls_data['company_id_call'] == selected_company_id]
    
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
            
            # Create a copy of filtered_calls_data with a standardized ticket_id column
            if ticket_id_col_calls is not None:
                filtered_calls_data['_standard_ticket_id'] = filtered_calls_data[ticket_id_col_calls].copy()
                
            # Create a copy of filtered_tickets_data with a standardized ticket_id column
            if ticket_id_col_tickets is not None:
                filtered_tickets_data['_standard_ticket_id'] = filtered_tickets_data[ticket_id_col_tickets].copy()
        except Exception as e:
            st.warning(f"Error standardizing ticket IDs: {str(e)}")

    # Tickets Analysis
    st.header("Tickets Overview")

    # Filters for tickets
    if not filtered_tickets_data.empty:
        # Check if status_ticket column exists
        if 'status_ticket' in filtered_tickets_data.columns:
            selected_status = st.selectbox("Select Ticket Status", ["All"] + list(filtered_tickets_data['status_ticket'].dropna().unique()), key='ticket_status')
        else:
            selected_status = "All"
            
        # Check if ticket_category_name column exists
        if 'ticket_category_name' in filtered_tickets_data.columns:
            selected_ticket_category = st.selectbox("Select Ticket Category", ["All"] + list(filtered_tickets_data['ticket_category_name'].dropna().unique()), key='ticket_cat')
        else:
            # Try to get ticket_category_id if available
            if 'ticket_category_id' in filtered_tickets_data.columns:
                selected_ticket_category = st.selectbox("Select Ticket Category ID", ["All"] + list(filtered_tickets_data['ticket_category_id'].dropna().unique()), key='ticket_cat')
            else:
                selected_ticket_category = "All"
                st.warning("Ticket category information is not available")

        # Apply these filters
        tab_filtered_tickets = filtered_tickets_data.copy()
        if selected_status != "All" and 'status_ticket' in tab_filtered_tickets.columns:
            tab_filtered_tickets = tab_filtered_tickets[tab_filtered_tickets['status_ticket'] == selected_status]
        if selected_ticket_category != "All":
            if 'ticket_category_name' in tab_filtered_tickets.columns:
                tab_filtered_tickets = tab_filtered_tickets[tab_filtered_tickets['ticket_category_name'] == selected_ticket_category]
            elif 'ticket_category_id' in tab_filtered_tickets.columns:
                tab_filtered_tickets = tab_filtered_tickets[tab_filtered_tickets['ticket_category_id'] == selected_ticket_category]
    else:
        tab_filtered_tickets = filtered_tickets_data

    if tab_filtered_tickets.empty:
        st.warning("No ticket data available for the selected filters.")
    else:
        # The join with ticketcall_df creates duplicates for tickets with multiple calls.
        # For ticket-centric analysis in this tab, we must use a dataframe with unique tickets.
        unique_tab_filtered_tickets = tab_filtered_tickets.drop_duplicates(subset=['id_ticket']).copy()

        # Calculate metrics using the unique tickets dataframe
        metrics_df = unique_tab_filtered_tickets.rename(columns={
            'status_ticket': 'status',
            'created_at_ticket': 'created_at',
            'closed_at_ticket': 'closed_at'
        })
        ticket_metrics = calculate_ticket_metrics(metrics_df)

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tickets", ticket_metrics['total_tickets'])
        with col2:
            st.metric("Open Tickets", ticket_metrics['open_tickets'])
        with col3:
            st.metric("Closed Tickets", ticket_metrics['closed_tickets'])
        with col4:
            st.metric("Avg. Resolution Time (days)", f"{ticket_metrics['avg_resolution_time']:.1f}")

        # Ticket status distribution
        st.subheader("Ticket Status Distribution")
        status_counts = unique_tab_filtered_tickets['status_ticket'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        fig = px.pie(status_counts, values='Count', names='Status', title='Ticket Status Distribution')
        st.plotly_chart(fig, use_container_width=True)

        # Ticket category distribution
        st.subheader("Ticket Category Distribution")
        if 'ticket_category_name' in unique_tab_filtered_tickets.columns:
            category_counts = unique_tab_filtered_tickets['ticket_category_name'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Count']
            
            fig = px.pie(category_counts, values='Count', names='Category', title='Ticket Category Distribution')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("معلومات فئة التذكرة غير متوفرة")

        # Tickets over time
        st.subheader("Tickets Over Time")
        
        # Ensure created_at_ticket is datetime
        unique_tab_filtered_tickets['created_at_ticket'] = pd.to_datetime(unique_tab_filtered_tickets['created_at_ticket'])
        
        # Group by date and count
        tickets_by_date = unique_tab_filtered_tickets.groupby(unique_tab_filtered_tickets['created_at_ticket'].dt.date).size().reset_index()
        tickets_by_date.columns = ['Date', 'Count']
        
        fig = px.line(tickets_by_date, x='Date', y='Count', title='Tickets Created Over Time')
        st.plotly_chart(fig, use_container_width=True)

        # Top customers by ticket count
        st.header("Top 10 Customers by Ticket Count")

        # Fallback: reconstruct customer_name if missing
        if 'customer_name' not in unique_tab_filtered_tickets.columns:
            try:
                if 'customer_id' in unique_tab_filtered_tickets.columns:
                    _cust_df = dataframes.get('customers', pd.DataFrame())
                    if not _cust_df.empty and 'id' in _cust_df.columns and 'name' in _cust_df.columns:
                        _cust_map = _cust_df.set_index('id')['name'].to_dict()
                        unique_tab_filtered_tickets['customer_name'] = unique_tab_filtered_tickets['customer_id'].map(_cust_map)
                        unique_tab_filtered_tickets['customer_name'] = unique_tab_filtered_tickets['customer_name'].fillna('Unknown Customer')
            except Exception as _e:
                st.info(f"Could not reconstruct customer names: {_e}")

        if 'customer_name' in unique_tab_filtered_tickets.columns:
            customer_counts = unique_tab_filtered_tickets['customer_name'].value_counts().reset_index()
            customer_counts.columns = ['Customer', 'Count']
            customer_counts = customer_counts.head(10)  # Top 10
            
            fig = px.bar(customer_counts, x='Customer', y='Count', title='Top 10 Customers by Ticket Count')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Also show table like in the old page
            top_customers_by_ticket = unique_tab_filtered_tickets['customer_name'].value_counts().nlargest(10).reset_index()
            top_customers_by_ticket.columns = ['Customer Name', 'Number of Tickets']
            st.dataframe(top_customers_by_ticket)

            # Ensure description column exists for ticket details (align with requested snippet)
            if 'description' not in unique_tab_filtered_tickets.columns and 'description_ticket' in unique_tab_filtered_tickets.columns:
                unique_tab_filtered_tickets['description'] = unique_tab_filtered_tickets['description_ticket']

            # Precompute call counts per ticket to show `call_count` in details
            call_counts_map = {}
            if 'id_ticket' in unique_tab_filtered_tickets.columns and not filtered_calls_data.empty:
                use_ticket_id = '_standard_ticket_id' if '_standard_ticket_id' in filtered_calls_data.columns else (
                    'ticket_id' if 'ticket_id' in filtered_calls_data.columns else (
                    'id_ticket' if 'id_ticket' in filtered_calls_data.columns else None))
                if use_ticket_id is not None:
                    call_counts_map = filtered_calls_data.groupby(use_ticket_id).size().to_dict()

            # Optional details per top customer (similar to old page)
            for customer_name in top_customers_by_ticket['Customer Name']:
                with st.expander(f"Details for {customer_name}"):
                    customer_tickets = unique_tab_filtered_tickets[unique_tab_filtered_tickets['customer_name'] == customer_name]
                    st.write(f"Total Tickets: {len(customer_tickets)}")
                    st.write("Ticket Details:")
                    # Build ticket details with call_count as requested
                    base_cols = [c for c in ['id_ticket', 'status_ticket', 'created_at_ticket', 'description'] if c in customer_tickets.columns]
                    if base_cols:
                        ticket_details = customer_tickets[base_cols].copy()
                        if 'id_ticket' in ticket_details.columns and call_counts_map:
                            ticket_details['call_count'] = ticket_details['id_ticket'].map(call_counts_map).fillna(0).astype(int)
                        st.dataframe(ticket_details)

                    # Show call details for each ticket if available
                    if not filtered_calls_data.empty:
                        ticket_id_col_calls = 'ticket_id' if 'ticket_id' in filtered_calls_data.columns else ( 'id_ticket' if 'id_ticket' in filtered_calls_data.columns else None )
                        if ticket_id_col_calls:
                            for ticket_id in customer_tickets['id_ticket'].dropna().unique() if 'id_ticket' in customer_tickets.columns else []:
                                ticket_calls = filtered_calls_data[filtered_calls_data[ticket_id_col_calls] == ticket_id]
                                if not ticket_calls.empty:
                                    st.write(f"Calls for Ticket #{int(ticket_id)}:")
                                    call_cols = [c for c in ['id', 'created_at', 'call_type_name', 'call_category_name', 'callresult', 'user_name'] if c in ticket_calls.columns]
                                    if call_cols:
                                        st.dataframe(ticket_calls[call_cols])
        else:
            st.warning("Customer name information is not available in the dataset.")

        # Display sample tickets
        st.subheader("Sample Tickets (Top 10)")
        
        # Verificar qué columnas están disponibles
        available_columns = []
        column_mapping = {}
        
        # Verificar cada columna y agregarla si existe
        if 'id_ticket' in unique_tab_filtered_tickets.columns:
            available_columns.append('id_ticket')
            column_mapping['id_ticket'] = 'Ticket ID'
            
        if 'customer_name' in unique_tab_filtered_tickets.columns:
            available_columns.append('customer_name')
            column_mapping['customer_name'] = 'Customer'
            
        if 'status_ticket' in unique_tab_filtered_tickets.columns:
            available_columns.append('status_ticket')
            column_mapping['status_ticket'] = 'Status'
            
        if 'ticket_category_name' in unique_tab_filtered_tickets.columns:
            available_columns.append('ticket_category_name')
            column_mapping['ticket_category_name'] = 'Category'
            
        if 'created_at_ticket' in unique_tab_filtered_tickets.columns:
            available_columns.append('created_at_ticket')
            column_mapping['created_at_ticket'] = 'Created At'
            
        if 'closed_at_ticket' in unique_tab_filtered_tickets.columns:
            available_columns.append('closed_at_ticket')
            column_mapping['closed_at_ticket'] = 'Closed At'
            
        if 'description' in unique_tab_filtered_tickets.columns:
            available_columns.append('description')
            column_mapping['description'] = 'Description'
        
        if available_columns:
            sample_tickets = unique_tab_filtered_tickets[available_columns].head(10)
            sample_tickets.columns = [column_mapping[col] for col in available_columns]
            st.dataframe(sample_tickets)
        else:
            st.warning("No hay columnas disponibles para mostrar en la muestra de tickets.")

if __name__ == "__main__":
    main()