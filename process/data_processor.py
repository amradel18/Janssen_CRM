import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta


def calculate_ticket_metrics(tickets_df):
    """
    Calculate key metrics for tickets
    """
    metrics = {}
    
    # Total tickets
    metrics['total_tickets'] = len(tickets_df)
    
    # Open and closed tickets
    if 'status' in tickets_df.columns:
        # Assuming status 0 is open and 1 is closed
        open_tickets = tickets_df[tickets_df['status'] == 0]
        closed_tickets = tickets_df[tickets_df['status'] == 1]
        metrics['open_tickets'] = len(open_tickets)
        metrics['closed_tickets'] = len(closed_tickets)
        
        # Calculate percentage
        if metrics['total_tickets'] > 0:
            metrics['open_percentage'] = (metrics['open_tickets'] / metrics['total_tickets']) * 100
            metrics['closed_percentage'] = (metrics['closed_tickets'] / metrics['total_tickets']) * 100
        else:
            metrics['open_percentage'] = 0
            metrics['closed_percentage'] = 0
    else:
        metrics['open_tickets'] = 0
        metrics['closed_tickets'] = 0
        metrics['open_percentage'] = 0
        metrics['closed_percentage'] = 0
    
    # Average resolution time (for closed tickets)
    if 'created_at' in tickets_df.columns and 'closed_at' in tickets_df.columns and 'status' in tickets_df.columns:
        closed_tickets_df = tickets_df[tickets_df['status'] == 1].copy()
        if not closed_tickets_df.empty:
            # Ensure date columns are in datetime format
            closed_tickets_df['created_at'] = pd.to_datetime(closed_tickets_df['created_at'], errors='coerce')
            closed_tickets_df['closed_at'] = pd.to_datetime(closed_tickets_df['closed_at'], errors='coerce')
            
            # Drop rows where conversion resulted in NaT
            closed_tickets_df.dropna(subset=['created_at', 'closed_at'], inplace=True)
            
            closed_tickets_df['resolution_time'] = (closed_tickets_df['closed_at'] - closed_tickets_df['created_at']).dt.total_seconds() / 3600  # in hours
            metrics['avg_resolution_time'] = closed_tickets_df['resolution_time'].mean()
        else:
            metrics['avg_resolution_time'] = 0
    else:
        metrics['avg_resolution_time'] = 0
    
    # Tickets by priority
    if 'priority' in tickets_df.columns:
        priority_counts = tickets_df['priority'].value_counts().to_dict()
        metrics['priority_counts'] = priority_counts
    
    # Tickets by category
    if 'ticket_cat_id' in tickets_df.columns:
        category_counts = tickets_df['ticket_cat_id'].value_counts().to_dict()
        metrics['category_counts'] = category_counts
    
    return metrics


def calculate_call_metrics(calls_df):
    """
    Calculate key metrics for calls (works with ticketcall)
    """
    metrics = {}
    
    # Total calls
    metrics['total_calls'] = len(calls_df)
    
    # Open and closed calls
    if 'status' in calls_df.columns:
        # Assuming status 0 is open and 1 is closed
        open_calls = calls_df[calls_df['status'] == 0]
        closed_calls = calls_df[calls_df['status'] == 1]
        metrics['open_calls'] = len(open_calls)
        metrics['closed_calls'] = len(closed_calls)
    else:
        metrics['open_calls'] = 0
        metrics['closed_calls'] = 0
    
    # Calls by type (using call_type instead of direction)
    if 'call_type' in calls_df.columns:
        type_counts = calls_df['call_type'].value_counts().to_dict()
        metrics['type_counts'] = type_counts
        
        # Inbound vs Outbound percentages (assuming call_type 1 is inbound, 2 is outbound)
        # Adjust these values based on your actual data
        inbound_calls = calls_df[calls_df['call_type'] == 1]
        outbound_calls = calls_df[calls_df['call_type'] == 2]
        
        metrics['inbound_calls'] = len(inbound_calls)
        metrics['outbound_calls'] = len(outbound_calls)
        
        if metrics['total_calls'] > 0:
            metrics['inbound_percentage'] = (metrics['inbound_calls'] / metrics['total_calls']) * 100
            metrics['outbound_percentage'] = (metrics['outbound_calls'] / metrics['total_calls']) * 100
        else:
            metrics['inbound_percentage'] = 0
            metrics['outbound_percentage'] = 0
    
    # Average call duration
    if 'call_duration' in calls_df.columns:
        calls_df['call_duration'] = pd.to_numeric(calls_df['call_duration'], errors='coerce')
        metrics['avg_call_duration'] = calls_df['call_duration'].mean()
    else:
        metrics['avg_call_duration'] = 0
    
    # Calls by category
    if 'call_cat_id' in calls_df.columns:
        category_counts = calls_df['call_cat_id'].value_counts().to_dict()
        metrics['category_counts'] = category_counts
    
    # Calls by agent (created_by)
    if 'created_by' in calls_df.columns:
        agent_counts = calls_df['created_by'].value_counts().to_dict()
        metrics['agent_counts'] = agent_counts
        
        # Top agents
        top_agents = calls_df['created_by'].value_counts().nlargest(5).to_dict()
        metrics['top_agents'] = top_agents
    
    return metrics


def calculate_customer_metrics(customers_df, tickets_df=None, calls_df=None):
    """
    Calculate key metrics for customers
    """
    metrics = {}
    
    # Total customers
    metrics['total_customers'] = len(customers_df)
    
    # Customers by company
    if 'company_id' in customers_df.columns:
        company_counts = customers_df['company_id'].value_counts().to_dict()
        metrics['company_counts'] = company_counts
    
    # Customers with tickets
    if tickets_df is not None and 'customer_id' in tickets_df.columns:
        customers_with_tickets = tickets_df['customer_id'].unique()
        metrics['customers_with_tickets'] = len(customers_with_tickets)
        
        if metrics['total_customers'] > 0:
            metrics['ticket_coverage'] = (metrics['customers_with_tickets'] / metrics['total_customers']) * 100
        else:
            metrics['ticket_coverage'] = 0
    
    # Customers with calls
    if calls_df is not None and 'customer_id' in calls_df.columns:
        customers_with_calls = calls_df['customer_id'].unique()
        metrics['customers_with_calls'] = len(customers_with_calls)
        
        if metrics['total_customers'] > 0:
            metrics['call_coverage'] = (metrics['customers_with_calls'] / metrics['total_customers']) * 100
        else:
            metrics['call_coverage'] = 0
    
    return metrics


def calculate_request_metrics(requests_df):
    """
    Calculate key metrics for requests
    """
    metrics = {}
    
    # Total requests
    metrics['total_requests'] = len(requests_df)
    
    # Requests by status
    if 'status' in requests_df.columns:
        status_counts = requests_df['status'].value_counts().to_dict()
        metrics['status_counts'] = status_counts
    
    # Requests by reason
    if 'request_reason_id' in requests_df.columns:
        reason_counts = requests_df['request_reason_id'].value_counts().to_dict()
        metrics['reason_counts'] = reason_counts
    
    # Average processing time
    if 'created_at' in requests_df.columns and 'completed_at' in requests_df.columns:
        completed_requests = requests_df[requests_df['status'] == 'completed'].copy()
        if not completed_requests.empty:
            completed_requests['processing_time'] = (completed_requests['completed_at'] - completed_requests['created_at']).dt.total_seconds() / 3600  # in hours
            metrics['avg_processing_time'] = completed_requests['processing_time'].mean()
        else:
            metrics['avg_processing_time'] = 0
    
    return metrics


def join_request_data(ticket_items_df, product_info_df, request_reasons_df):
    """
    Joins ticket_items with product_info and request_reasons.
    """
    if ticket_items_df.empty:
        return pd.DataFrame()

    # Merge with product_info
    if not product_info_df.empty and 'product_id' in ticket_items_df.columns and 'id' in product_info_df.columns:
        merged_df = pd.merge(ticket_items_df, product_info_df.add_suffix('_product'), left_on='product_id', right_on='id_product', how='left')
    else:
        merged_df = ticket_items_df

    # Merge with request_reasons
    if not request_reasons_df.empty and 'request_reason_id' in merged_df.columns and 'id' in request_reasons_df.columns:
        merged_df = pd.merge(merged_df, request_reasons_df.add_suffix('_reason'), left_on='request_reason_id', right_on='id_reason', how='left')

    return merged_df


def calculate_combined_call_metrics(ticketcall_df, customercall_df, customers_df):
    """
    Calculate key metrics for both ticket calls and customer calls.
    """
    metrics = {}

    # Ticket calls
    total_ticket_calls = len(ticketcall_df)
    unique_customers_ticket_calls = ticketcall_df['customer_id'].nunique() if 'customer_id' in ticketcall_df.columns else 0
    avg_ticket_calls_per_customer = total_ticket_calls / unique_customers_ticket_calls if unique_customers_ticket_calls > 0 else 0

    # Customer calls
    total_customer_calls = len(customercall_df)
    unique_customers_customer_calls = customercall_df['customer_id'].nunique() if 'customer_id' in customercall_df.columns else 0
    avg_customer_calls_per_customer = total_customer_calls / unique_customers_customer_calls if unique_customers_customer_calls > 0 else 0

    # Combined metrics
    total_calls = total_ticket_calls + total_customer_calls
    total_customers = len(customers_df)
    avg_calls_per_customer = total_calls / total_customers if total_customers > 0 else 0


    metrics['total_ticket_calls'] = total_ticket_calls
    metrics['avg_ticket_calls_per_customer'] = avg_ticket_calls_per_customer
    metrics['total_customer_calls'] = total_customer_calls
    metrics['avg_customer_calls_per_customer'] = avg_customer_calls_per_customer
    metrics['total_calls'] = total_calls
    metrics['avg_calls_per_customer'] = avg_calls_per_customer

    return metrics


def join_customer_ticket_data(customers_df, tickets_df):
    """
    Join customer and ticket data
    """
    if customers_df.empty or tickets_df.empty:
        return pd.DataFrame()
    
    # Make copies to avoid warnings
    customers = customers_df.copy()
    tickets = tickets_df.copy()
    
    # Ensure customer_id is present in both dataframes
    if 'id' in customers.columns and 'customer_id' in tickets.columns:
        # Rename customer id column for the join
        customers = customers.rename(columns={'id': 'customer_id'})
        
        # Join the dataframes
        joined_df = pd.merge(
            tickets,
            customers,
            on='customer_id',
            how='left',
            suffixes=('_ticket', '_customer')
        )
        
        return joined_df
    
    return pd.DataFrame()


def join_customer_call_data(customers_df, ticketcall_df):
    """
    Join customer and call data for analysis
    """
    if customers_df.empty or ticketcall_df.empty:
        return pd.DataFrame()

    # Make copies to avoid warnings
    customers = customers_df.copy()
    calls = ticketcall_df.copy()
    
    # First, we need to join ticketcall with tickets to get customer_id
    # Check if ticket_id exists in ticketcall dataframe
    if 'ticket_id' in calls.columns:
        # Get tickets dataframe from session state if available
        if 'dataframes' in st.session_state and 'tickets' in st.session_state.dataframes:
            tickets = st.session_state.dataframes['tickets'].copy()
            
            # Join ticketcall with tickets
            if not tickets.empty and 'id' in tickets.columns and 'customer_id' in tickets.columns:
                # Rename ticket id column for the join
                tickets = tickets.rename(columns={'id': 'ticket_id'})
                
                # Join ticketcall with tickets
                calls = pd.merge(
                    calls,
                    tickets[['ticket_id', 'customer_id']],
                    on='ticket_id',
                    how='left'
                )
                
                # Now join with customers
                if 'id' in customers.columns and 'customer_id' in calls.columns:
                    # Rename customer id column for the join
                    customers = customers.rename(columns={'id': 'customer_id'})
                    
                    # Join the dataframes
                    joined_df = pd.merge(
                        calls,
                        customers,
                        on='customer_id',
                        how='left',
                        suffixes=('_call', '_customer')
                    )
                    
                    # Drop rows where customer_id is null after join
                    joined_df.dropna(subset=['customer_id'], inplace=True)
                    
                    return joined_df
    
    return pd.DataFrame()


def join_customer_user_data(customers_df, users_df):
    """
    Join customer and user data for analysis
    """
    if customers_df.empty or users_df.empty:
        return pd.DataFrame()
    
    # Make copies to avoid warnings
    customers = customers_df.copy()
    users = users_df.copy()
    
    # Check if user_id exists in customers dataframe
    if 'user_id' in customers.columns and 'id' in users.columns:
        # Rename user id column for the join
        users = users.rename(columns={'id': 'user_id'})
        
        # Join the dataframes
        joined_df = pd.merge(
            customers,
            users,
            on='user_id',
            how='left',
            suffixes=('_customer', '_user')
        )
        
        return joined_df
    
    return pd.DataFrame()


def join_customer_request_data(customers_df, requests_df):
    """
    Join customer and request data for analysis
    """
    if customers_df.empty or requests_df.empty:
        return pd.DataFrame()
    
    # Make copies to avoid warnings
    customers = customers_df.copy()
    requests = requests_df.copy()
    
    # Ensure customer_id is present in both dataframes
    if 'id' in customers.columns and 'customer_id' in requests.columns:
        # Rename customer id column for the join
        customers = customers.rename(columns={'id': 'customer_id'})
        
        # Join the dataframes
        joined_df = pd.merge(
            requests,
            customers,
            on='customer_id',
            how='left',
            suffixes=('_request', '_customer')
        )
        
        return joined_df
    
    return pd.DataFrame()


def time_series_analysis(df, date_column, value_column, freq='D'):
    """
    Perform time series analysis on a dataframe
    
    Args:
        df: DataFrame containing the data
        date_column: Column name containing dates
        value_column: Column name containing values to aggregate
        freq: Frequency for resampling ('D' for daily, 'W' for weekly, 'M' for monthly)
        
    Returns:
        DataFrame with time series data
    """
    if df.empty or date_column not in df.columns:
        return pd.DataFrame()
    
    # Make a copy
    df_copy = df.copy()
    
    # Ensure date column is datetime
    df_copy[date_column] = pd.to_datetime(df_copy[date_column], errors='coerce')
    
    # Set date as index
    df_copy = df_copy.set_index(date_column)
    
    # Resample and count
    if value_column in df_copy.columns:
        time_series = df_copy[value_column].resample(freq).count()
        time_series.name = 'count'  # Explicitly name the series
    else:
        time_series = df_copy.resample(freq).size()
        time_series.name = 'count'  # Explicitly name the series
    
    # Reset index to get date as a column
    time_series = time_series.reset_index()
    
    return time_series


def join_ticket_and_call_data(tickets_df, ticketcall_df, users_df, ticket_categories_df, call_types_df, customers_df, call_categories_df):
    """
    Joins tickets, ticket calls, and related supplementary data into a single dataframe.
    """
    # Ensure dataframes are not empty
    if tickets_df.empty or ticketcall_df.empty:
        return pd.DataFrame()

    # Make copies to avoid modifying original dataframes
    tickets_df = tickets_df.copy()
    ticketcall_df = ticketcall_df.copy()

    # Rename description columns before merge to avoid conflicts
    if 'description' in tickets_df.columns:
        tickets_df.rename(columns={'description': 'description_ticket'}, inplace=True)
    if 'description' in ticketcall_df.columns:
        ticketcall_df.rename(columns={'description': 'description_call'}, inplace=True)

    # --- Main Join: tickets and ticketcall ---
    # Use an outer join to include tickets with no calls and calls with no tickets (if that's possible)
    # A left join from tickets is probably safer to start with the main entity.
    combined_df = pd.merge(
        tickets_df,
        ticketcall_df,
        left_on='id',
        right_on='ticket_id',
        how='left',
        suffixes=('_ticket', '_call')
    )

    # --- Join with Customers ---
    if not customers_df.empty and 'customer_id' in combined_df.columns:
        customers_df = customers_df.rename(columns={'id': 'customer_id', 'name': 'customer_name'})
        combined_df = pd.merge(
            combined_df,
            customers_df[['customer_id', 'customer_name']],
            on='customer_id',
            how='left'
        )

    # --- Join with Users (for ticket creator) ---
    if not users_df.empty and 'created_by_ticket' in combined_df.columns:
        user_ticket_creator_df = users_df.rename(columns={'id': 'created_by_ticket', 'name': 'ticket_creator_name'})
        combined_df = pd.merge(
            combined_df,
            user_ticket_creator_df[['created_by_ticket', 'ticket_creator_name']],
            on='created_by_ticket',
            how='left'
        )

    # --- Join with Users (for call creator) ---
    if not users_df.empty and 'created_by_call' in combined_df.columns:
        user_call_creator_df = users_df.rename(columns={'id': 'created_by_call', 'name': 'call_creator_name'})
        combined_df = pd.merge(
            combined_df,
            user_call_creator_df[['created_by_call', 'call_creator_name']],
            on='created_by_call',
            how='left'
        )

    # --- Join with Ticket Categories ---
    if not ticket_categories_df.empty and 'ticket_cat_id' in combined_df.columns:
        ticket_cat_df = ticket_categories_df.rename(columns={'id': 'ticket_cat_id', 'name': 'ticket_category_name'})
        combined_df = pd.merge(
            combined_df,
            ticket_cat_df[['ticket_cat_id', 'ticket_category_name']],
            on='ticket_cat_id',
            how='left'
        )

    # --- Join with Call Types ---
    if not call_types_df.empty and 'call_type' in combined_df.columns:
        call_type_df = call_types_df.rename(columns={'id': 'call_type', 'name': 'call_type_name'})
        combined_df = pd.merge(
            combined_df,
            call_type_df[['call_type', 'call_type_name']],
            on='call_type',
            how='left'
        )

    # --- Join with Call Categories ---
    if not call_categories_df.empty and 'call_cat_id' in combined_df.columns:
        call_cat_df = call_categories_df.rename(columns={'id': 'call_cat_id', 'name': 'call_category_name'})
        combined_df = pd.merge(
            combined_df,
            call_cat_df[['call_cat_id', 'call_category_name']],
            on='call_cat_id',
            how='left'
        )

    if 'status' in combined_df.columns and 'status_ticket' not in combined_df.columns:
        combined_df.rename(columns={'status': 'status_ticket'}, inplace=True)

    return combined_df