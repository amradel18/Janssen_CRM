import streamlit as st
import pandas as pd
from datetime import datetime
from .data_loader import load_all_data

def ensure_data_loaded(force_reload=False):
    """
    Ensures that data is loaded in session state.
    This function should be called at the beginning of every page.
    
    Args:
        force_reload (bool): If True, forces reloading of data even if already loaded
    """
    # Check if data is already loaded
    if (force_reload or
        'all_data_loaded' not in st.session_state or 
        not st.session_state.all_data_loaded or
        'all_dataframes' not in st.session_state or
        'dataframes' not in st.session_state):
        
        loading_message = "Reloading data..." if force_reload else "Loading data for the first time..."
        with st.spinner(loading_message):
            try:
                # Load all data
                all_dataframes = load_all_data(force_reload=force_reload)
                
                # Store in both formats for compatibility
                st.session_state.all_dataframes = all_dataframes
                st.session_state.dataframes = all_dataframes
                st.session_state.all_data_loaded = True
                
                # Record load time
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.last_load_time = current_time
                
                st.success("Data loaded successfully!")
                
            except Exception as e:
                st.error(f"Error loading data: {str(e)}")
                st.error("Please check your database connection.")
                # Set empty dataframes to prevent crashes
                st.session_state.all_dataframes = {}
                st.session_state.dataframes = {}
                st.session_state.all_data_loaded = False
                return False
    
    return True

def get_dataframes():
    """
    Safely get dataframes from session state.
    Returns empty dict if not available.
    """
    # Ensure data is loaded first
    ensure_data_loaded()
    
    # Return dataframes with fallback
    return getattr(st.session_state, 'all_dataframes', 
                   getattr(st.session_state, 'dataframes', {}))

def reset_data():
    """
    Reset all data in session state.
    Useful for forcing a reload.
    """
    keys_to_remove = [
        'all_dataframes', 
        'dataframes', 
        'all_data_loaded', 
        'last_load_time',
        'loaded_tables'
    ]
    
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]