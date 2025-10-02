import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Load environment variables from .env file
load_dotenv()

company_mapping = {1: "Englander", 2: "Janssen"}

def get_companies_data():
    """
    Load companies data from the database and return as DataFrame.
    Returns a DataFrame with company information including id and name columns.
    """
    try:
        companies_df = cached_table_query('companies')
        if companies_df.empty:
            # Fallback to hardcoded mapping if database is empty
            companies_df = pd.DataFrame([
                {'id': 1, 'name': 'Englander'},
                {'id': 2, 'name': 'Janssen'}
            ])
        return companies_df
    except Exception as e:
        st.error(f"خطأ في تحميل بيانات الشركات: {str(e)}")
        # Return fallback data
        return pd.DataFrame([
            {'id': 1, 'name': 'Englander'},
            {'id': 2, 'name': 'Janssen'}
        ])

def get_company_mapping():
    """
    Get company mapping as dictionary from companies table.
    Returns dict with company_id as key and company_name as value.
    """
    try:
        companies_df = get_companies_data()
        if not companies_df.empty and 'id' in companies_df.columns and 'name' in companies_df.columns:
            return dict(zip(companies_df['id'], companies_df['name']))
        else:
            return company_mapping  # Fallback to hardcoded mapping
    except Exception as e:
        st.error(f"خطأ في إنشاء mapping الشركات: {str(e)}")
        return company_mapping  # Fallback to hardcoded mapping

def _has_streamlit_secrets() -> bool:
    home_path = os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(project_root, ".streamlit", "secrets.toml")
    return os.path.exists(home_path) or os.path.exists(project_path)


def _get_env(var_name: str, default = None):
    return os.getenv(var_name, default)


def _get_secret(section: str, key: str, env_var = None, default = None):
    """Read from Streamlit secrets if present (works on Streamlit Cloud even without a local secrets.toml file),
    otherwise fall back to environment variables, then default."""
    # Try Streamlit Secrets first (available on Streamlit Cloud even without a local secrets.toml file)
    try:
        val = st.secrets[section][key]
        if val is not None and str(val) != "":
            return val
    except Exception:
        pass
    # Fall back to env var if provided
    if env_var:
        env_val = _get_env(env_var, None)
        if env_val is not None and env_val != "":
            return env_val
    return default


def _get_db_config() -> dict:
    host = _get_secret("db", "host", env_var="DB_HOST", default="localhost")
    port = int(_get_secret("db", "port", env_var="DB_PORT", default="3306"))
    user = _get_secret("db", "user", env_var="DB_USER", default="root")
    password = _get_secret("db", "password", env_var="DB_PASSWORD", default="")
    database = _get_secret("db", "database", env_var="DB_DATABASE", default="janssencrm")
    autocommit = str(_get_secret("db", "autocommit", env_var="DB_AUTOCOMMIT", default="true")).lower() in ("1", "true", "yes")
    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database,
        'autocommit': autocommit,
    }

DB_CONFIG = _get_db_config()

def get_database_connection():
    """Return a SQLAlchemy engine for the database."""
    password_encoded = quote_plus(DB_CONFIG['password'])
    connection_string = f"mysql+pymysql://{DB_CONFIG['user']}:{password_encoded}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/janssencrm"
    return create_engine(connection_string, connect_args={'connect_timeout': 20})

@st.cache_data(show_spinner=False, ttl=600)
def cached_query(sql: str, params = None, database_name: str = 'janssencrm') -> pd.DataFrame:
    """Execute a SQL query with optional params and cache the result for faster reloads."""
    engine = get_database_connection()
    return pd.read_sql(sql, con=engine, params=params)


@st.cache_data(show_spinner=False, ttl=600)
def cached_table_query(table_name: str, database_name: str = 'janssencrm', force_reload: bool = False) -> pd.DataFrame:
    """Load an entire table from the database with caching.
    
    This function first checks if the table is already loaded in session_state.
    If it is and force_reload is False, it returns the cached version. 
    Otherwise, it loads from the database.
    
    Args:
        table_name: Name of the table to load
        database_name: Database name (default: 'janssencrm')
        force_reload: If True, reload from database even if cached (default: False)
    """
    # Check if we already have this table loaded in session state and not forcing reload
    if not force_reload and 'loaded_tables' in st.session_state and table_name in st.session_state.loaded_tables:
        return st.session_state.loaded_tables[table_name]
    
    # If not in session state or forcing reload, load from database
    engine = get_database_connection()
    df = pd.read_sql(f"SELECT * FROM {database_name}.{table_name}", con=engine)
    
    # Store in session state for future use
    if 'loaded_tables' not in st.session_state:
        st.session_state.loaded_tables = {}
    
    st.session_state.loaded_tables[table_name] = df
    
    return df

def load_data(table_name, cache_key=None):
    """
    Loads a single table directly from the database.
    """
    try:
        # Use cached query for better performance
        df = cached_table_query(table_name)
        
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
    except Exception as e:
        st.error(f"خطأ في تحميل جدول {table_name}: {str(e)}")
        return pd.DataFrame()

def load_all_data(force_reload=False, cache_key=None):
    """
    Centralized function to load all data directly from the database.
    Returns a dictionary of all dataframes.
    
    This function checks if data is already loaded in session_state to avoid
    reloading data unnecessarily when navigating between pages.
    """
    try:
        # Check if data is already loaded and we're not forcing a reload
        if not force_reload and 'all_data_loaded' in st.session_state and st.session_state.all_data_loaded:
            if 'dataframes' in st.session_state:
                print("✅ Using already loaded data from session state")
                return st.session_state.dataframes
            elif 'loaded_tables' in st.session_state:
                print("✅ Using already loaded tables from session state")
                return st.session_state.loaded_tables
        
        # Define all tables to load
        all_tables = [
            'call_categories', 'call_types', 'cities', 'companies', 'customer_phones',
            'customers', 'governorates', 'product_info',
            'request_reasons', 'ticket_categories', 'ticket_item_change_another',
            'ticket_item_change_same', 'ticket_item_maintenance', 'ticket_items',
            'ticketcall', 'tickets', 'users', 'customercall'
        ]
        
        # Check if we already have loaded_tables in session state
        if not force_reload and 'loaded_tables' in st.session_state:
            # Check which tables are already loaded
            missing_tables = [table for table in all_tables if table not in st.session_state.loaded_tables]
            
            if not missing_tables:  # All tables are already loaded
                print("✅ All tables already loaded in session state")
                st.session_state.all_data_loaded = True
                return st.session_state.loaded_tables
            
            # Only load missing tables
            print(f"⚠️ Loading {len(missing_tables)} missing tables")
            all_tables = missing_tables
        
        # Initialize loaded_tables if not exists
        if 'loaded_tables' not in st.session_state:
            st.session_state.loaded_tables = {}
        
        # Load tables using cached_table_query (which now checks session state first)
        for table in all_tables:
            try:
                st.session_state.loaded_tables[table] = cached_table_query(table, force_reload=force_reload)
                print(f"✅ Loaded table: {table}")
            except Exception as e:
                print(f"❌ Error loading table {table}: {str(e)}")
                st.session_state.loaded_tables[table] = pd.DataFrame()
        
        # Process dataframes to fix common issues
        processed_dataframes = process_dataframes(st.session_state.loaded_tables)
        
        # Store processed dataframes back in session state
        st.session_state.loaded_tables = processed_dataframes
        st.session_state.dataframes = processed_dataframes  # For backward compatibility
        st.session_state.all_data_loaded = True
        st.session_state.last_load_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return processed_dataframes
    except Exception as e:
        st.error(f"Error loading data from database: {str(e)}")
        
        # Return empty data to prevent further errors
        return {}

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
        
        # Special handling for call_duration column
        if 'call_duration' in processed_df.columns:
            try:
                # Try to convert to numeric, replace invalid values with NaN
                processed_df['call_duration'] = pd.to_numeric(processed_df['call_duration'], errors='coerce')
                
                # Replace NaN with 0 or another default value
                processed_df['call_duration'] = processed_df['call_duration'].fillna(0)
            except Exception as e:
                print(f"Error processing call_duration column: {str(e)}")
                # If conversion fails completely, create a new column with zeros
                processed_df['call_duration'] = 0
        
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