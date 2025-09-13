import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import the load functions
from lode_data.load_data_in_drive import load_tables_from_drive, read_csv_from_drive_by_name, get_drive_service

company_mapping = {1: "Englander", 2: "Janssen"}

def load_data(table_name, cache_key=None):
    """
    Loads a single table from Google Drive.
    """
    service = get_drive_service()
    df = read_csv_from_drive_by_name(f"{table_name}.csv", _service=service, cache_key=cache_key)
    
    # Process dataframe to fix common issues
    processed_df = df.copy()
    date_columns = [
        'date', 'created_at', 'updated_at', 'deleted_at',
        'call_date', 'ticket_date', 'request_date', 'pull_date', 'delivery_date'
    ]
    
    for col in date_columns:
        if col in processed_df.columns:
            processed_df[col] = pd.to_datetime(processed_df[col], errors='coerce')
            
    return processed_df

def load_all_data(force_reload=False, cache_key=None):
    """
    Centralized function to load all data once and store in session state.
    Returns a dictionary of all dataframes.
    """
    # Check if data is already loaded
    if not force_reload and 'all_data_loaded' in st.session_state and st.session_state.all_data_loaded:
        return st.session_state.dataframes
    
    # Define all tables to load
    all_tables = [
        'call_categories', 'call_types', 'cities', 'customer_phones',
        'customers', 'governorates', 'product_info',
        'request_reasons', 'ticket_categories', 'ticket_item_change_another',
        'ticket_item_change_same', 'ticket_item_maintenance', 'ticket_items',
        'ticketcall', 'tickets', 'users', 'customercall'
    ]
    
    # Note: 
    # - 'calls' table doesn't exist, using 'ticketcall' instead
    
    # Load all tables
    dataframes = load_tables_from_drive(all_tables, cache_key=cache_key)
    
    # Process dataframes to fix common issues
    processed_dataframes = process_dataframes(dataframes)
    
    # Store in session state
    st.session_state.dataframes = processed_dataframes
    st.session_state.all_data_loaded = True
    
    return processed_dataframes

def process_dataframes(dataframes):
    """
    Process all dataframes to fix common issues like date conversion
    and create proper copies to avoid SettingWithCopyWarning.
    """
    processed = {}
    
    # Process each dataframe
    for key, df in dataframes.items():
        # Create a proper copy
        processed_df = df.copy()
        
        # Convert date columns if they exist
        date_columns = [
            'date', 'created_at', 'updated_at', 'deleted_at',
            'call_date', 'ticket_date', 'request_date'
        ]
        
        for col in date_columns:
            if col in processed_df.columns:
                processed_df[col] = pd.to_datetime(processed_df[col], errors='coerce')
        
        # Store the processed dataframe
        processed[key] = processed_df
    
    return processed

def get_filtered_data(df, start_date=None, end_date=None, date_column='date', customer=None, company=None, status=None, category=None):
    """
    Apply common filters to a dataframe or dictionary of dataframes.
    
    Args:
        df: DataFrame to filter or dictionary of dataframes
        start_date: Start date for filtering
        end_date: End date for filtering
        date_column: Column name to use for date filtering
        customer: Customer ID or name to filter by
        company: Company ID or name to filter by
        status: Status to filter by
        category: Category to filter by
        
    Returns:
        Filtered dataframe or dictionary of filtered dataframes
    """
    # Handle dictionary of dataframes
    if isinstance(df, dict):
        filtered_dict = {}

        # Normalize filters when working with a dictionary of tables
        norm_company = str(company) if company is not None else None
        norm_customer = customer
        norm_status = status
        norm_category = category

        # Filter customers first if a company filter is applied
        if norm_company and 'customers' in df:
            customers_df = df['customers']
            company_customers = customers_df[customers_df['company_id'] == norm_company]['id'].tolist()
            # If a customer filter is also applied, it should be within the company's customers
            if norm_customer and norm_customer not in company_customers:
                norm_customer = None # Or handle as an invalid selection
        else:
            company_customers = None

        # Iterate over each dataframe in the dictionary
        for key, data in df.items():
            filtered_df = data.copy()

            # Date filter
            if start_date and end_date and date_column in filtered_df.columns:
                filtered_df = filtered_df[(filtered_df[date_column] >= start_date) & (filtered_df[date_column] <= end_date)]

            # Customer filter
            if norm_customer and 'customer_id' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['customer_id'] == norm_customer]
            elif company_customers and 'customer_id' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['customer_id'].isin(company_customers)]

            # Status filter
            if norm_status and 'status' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['status'] == norm_status]

            # Category filter
            if norm_category and 'category_id' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['category_id'] == norm_category]

            filtered_dict[key] = filtered_df
        
        return filtered_dict

    # Handle single dataframe
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return pd.DataFrame()
    
    # Use the filter_single_dataframe function for the single dataframe case
    return filter_single_dataframe(df, start_date, end_date, date_column, customer, company, status)

def filter_single_dataframe(df, start_date=None, end_date=None, date_column='date', customer=None, company=None, status=None):
    """
    Apply common filters to a single dataframe.
    
    Args:
        df: DataFrame to filter
        start_date: Start date for filtering
        end_date: End date for filtering
        date_column: Column name to use for date filtering
        customer: Customer ID or name to filter by
        company: Company ID or name to filter by
        status: Status to filter by
        
    Returns:
        Filtered dataframe
    """
    # Create a proper copy
    filtered_df = df.copy()
    
    # Apply date filter if applicable
    if start_date and end_date and date_column in filtered_df.columns:
        filtered_df = filtered_df[(filtered_df[date_column] >= pd.Timestamp(start_date)) & 
                                  (filtered_df[date_column] <= pd.Timestamp(end_date))]
    
    # Apply customer filter if applicable
    if customer is not None:
        if 'customer_id' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['customer_id'].astype(str) == str(customer)]
        elif 'customer' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['customer'] == customer]
    
    # Apply company filter if applicable
    if company is not None:
        if 'company_id' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['company_id'].astype(str) == str(company)]
        elif 'company' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['company'] == company]
    
    # Apply status filter if applicable
    if status and 'status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['status'] == status]
    
    return filtered_df

def get_company_list(dataframes):
    """
    Get a list of company names from the data.
    Accepts either a dictionary of dataframes or a single dataframe/series.
    """
    # Extract company IDs from various tables
    company_ids = set()
    
    # Check if dataframes is a dictionary or a single dataframe/series
    if isinstance(dataframes, dict):
        # Extract company IDs from various tables
        for key, df in dataframes.items():
            if hasattr(df, 'columns') and 'company_id' in df.columns:
                company_ids.update(df['company_id'].dropna().unique().tolist())
    else:
        # Handle single dataframe or series
        df = dataframes
        if hasattr(df, 'columns') and 'company_id' in df.columns:
            company_ids.update(df['company_id'].dropna().unique().tolist())
        elif hasattr(df, 'name') and df.name == 'company_id':
            # Handle case where a Series is passed directly
            company_ids.update(df.dropna().unique().tolist())
    
    # Convert to list of strings
    return [str(company_id) for company_id in sorted(company_ids)]

def get_customer_list(dataframes, company_id=None):
    """
    Get a list of unique customers from the customers dataframe
    Accepts either a dictionary of dataframes or a single dataframe/series.
    """
    # Check if dataframes is a dictionary
    if isinstance(dataframes, dict):
        if 'customers' not in dataframes or dataframes['customers'].empty:
            return []
        customers_df = dataframes['customers']
    else:
        # Handle single dataframe
        customers_df = dataframes
        if customers_df.empty:
            return []
    
    # Filter by company if specified
    if company_id is not None and hasattr(customers_df, 'columns') and 'company_id' in customers_df.columns:
        filtered_customers = customers_df[customers_df['company_id'].astype(str) == str(company_id)]
    else:
        filtered_customers = customers_df
    
    # Get customer names if available, otherwise use IDs
    if 'name' in filtered_customers.columns:
        customers = filtered_customers['name'].unique().tolist()
    elif 'id' in filtered_customers.columns:
        customers = filtered_customers['id'].unique().tolist()
    else:
        customers = []
    
    return customers


# Add more helper functions as needed for common data operations