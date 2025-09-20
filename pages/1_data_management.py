import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the authentication module
from auth.authentication import check_authentication
from process.data_loader import cached_table_query, load_all_data

# Set page config
st.set_page_config(page_title="CRM Data Management", layout="wide")

# Add custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
    }
    h1, h2, h3 {
        color: #1E3A8A;
    }
    .data-card {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1.5rem;
        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #1E3A8A;
        color: white;
    }
    .table-container {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Check authentication
check_authentication()

# Main content
st.title("Data Management")

# Navigation
st.sidebar.title("Navigation")
if st.sidebar.button("Back to Dashboard", key="back_to_dashboard_btn"):
    st.switch_page("pages/1_dashboard.py")

# Define table names
TABLE_NAMES = [
    "call_categories", "call_types", "cities", "companies", "customer_phones",
    "customers", "governorates", "product_info", "request_reasons", 'customercall',
    "ticket_categories", "ticket_item_change_another", "ticket_item_change_same",
    "ticket_item_maintenance", "ticket_items", "ticketcall", "tickets", "users"
]

# Data update section
st.header("Load Data from Database")

with st.container():
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    
    st.write("This tool loads data directly from the MySQL database and stores it in the application memory for all pages to use.")
    
    # Check if data is already loaded
    if 'all_data_loaded' in st.session_state and st.session_state.all_data_loaded:
        st.success("✅ Data is already loaded and available to all pages!")
        
        # Display last load time if available
        if 'last_load_time' in st.session_state:
            st.info(f"Last loaded: {st.session_state.last_load_time}")
            
        # Show reload button
        if st.button("Reload Data", key="reload_data_btn"):
            with st.spinner("Reloading data from database..."):
                 try:
                     # Import required modules
                     from process.data_loader import load_all_data
                     from datetime import datetime
                     
                     # Force reload data from database
                     load_all_data(force_reload=True)
                     
                     # Mark data as loaded
                     st.session_state.all_data_loaded = True
                     
                     # Record sync time
                     current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                     st.session_state.last_sync_time = current_time
                     st.session_state.last_load_time = current_time
                     
                     st.success("Data reloaded successfully and available to all pages!")
                     
                     # Force rerun to update the UI
                     st.experimental_rerun()
                     
                 except Exception as e:
                     st.error(f"Error reloading data: {str(e)}")
                     st.error("Please check your database connection and try again.")
    else:
        # Display last sync time if available
        if 'last_sync_time' in st.session_state:
            st.info(f"Last update: {st.session_state.last_sync_time}")
        
        # Initial load button
        if st.button("Load Data", key="sync_data_btn"):
            with st.spinner("Connecting to database and loading data..."):
                try:
                    # Load data from database
                    from process.data_loader import load_all_data
                    load_all_data()
                    
                    # Mark data as loaded
                    st.session_state.all_data_loaded = True
                    
                    # Record sync time
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.last_sync_time = current_time
                    st.session_state.last_load_time = current_time
                    
                    st.success("Data loaded successfully and available to all pages!")
                    
                    # Force rerun to update the UI
                    st.experimental_rerun()
                    
                except Exception as e:
                     st.error(f"❌ Error loading data: {str(e)}")
                     print(f"❌ Error loading data: {str(e)}")
                     st.error("Please check your database connection and try again.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Display loaded tables information
if 'loaded_tables' in st.session_state and st.session_state.loaded_tables:
    st.header("Loaded Tables Information")
    
    # Get current user
    current_user = st.session_state.get('username', 'Unknown User')
    
    # Create a list to store table loading information
    table_loading_info = []
    
    # Collect information about loaded tables
    for table_name, df in st.session_state.loaded_tables.items():
        table_loading_info.append({
            "Table Name": table_name,
            "Loaded By": current_user,
            "Load Time": st.session_state.get('last_load_time', st.session_state.get('last_sync_time', 'Unknown')),
            "Record Count": len(df)
        })
    
    # Create a DataFrame with the loading information
    loading_info_df = pd.DataFrame(table_loading_info)
    
    # Display the loading information
    st.write("### Tables Loaded in Current Session")
    st.dataframe(loading_info_df, use_container_width=True)
    
    # Add information about data sharing
    st.success("✅ These tables are loaded in memory and shared across all pages!")

# Cache management section
st.header("Cache Management")
with st.container():
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.write("If you've updated data in the database, you may need to clear the cache to see the changes.")
    if st.button("Clear Cache and Reload Data", key="clear_cache_btn"):
        with st.spinner("Clearing cache and reloading all data..."):
            st.cache_data.clear()
            st.cache_resource.clear()
            if 'loaded_tables' in st.session_state:
                del st.session_state.loaded_tables
            if 'all_data_loaded' in st.session_state:
                del st.session_state.all_data_loaded
            
            # Generate a unique cache key to bust the cache
            cache_key = datetime.now().timestamp()
            
            # Force reload of data with the new cache key
            load_all_data(force_reload=True, cache_key=cache_key)
            
            st.success("Cache cleared and data reloaded successfully! Please return to the dashboard.")
    st.markdown("</div>", unsafe_allow_html=True)

# Data management tips
with st.expander("Data Management Tips"):
    st.markdown("""
    ### Best Practices
    - Load data regularly to keep information up-to-date
    - Ensure database connection is stable before loading
    - Large tables may take longer to load
    
    ### Troubleshooting
    - If loading fails, check database connection settings
    - Verify network connectivity
    - Review logs for detailed error messages
    """)

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>CRM Data Management © 2024</p>", unsafe_allow_html=True)