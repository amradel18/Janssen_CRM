import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the authentication module
from auth.authentication import check_authentication
from lode_data.load_database_and_upload_drive import export_incremental_tables_to_drive
from process.data_loader import load_all_data

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

# Data update section
st.header("Database to Google Drive Sync")

with st.container():
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    
    st.write("This tool synchronizes data from the MySQL database to Google Drive.")
    st.write("It will update all tables incrementally, adding only new records since the last sync.")
    
    # Display last sync time if available
    if 'last_sync_time' in st.session_state:
        st.info(f"Last synchronized: {st.session_state.last_sync_time}")
    
    # Sync button with confirmation
    if st.button("Synchronize Data", key="sync_data_btn"):
        with st.spinner("Connecting to database and syncing data to Google Drive..."):
            try:
                # Call the export function
                result = export_incremental_tables_to_drive()
                
                if result:
                    # Create a DataFrame to display results
                    results_data = []
                    for table, info in result.items():
                        results_data.append({
                            "Table": table,
                            "New Records": info['new_rows'],
                            "Status": "✅ Success" if 'file_id' in info else "❌ Failed"
                        })
                    
                    results_df = pd.DataFrame(results_data)
                    
                    # Store sync time
                    st.session_state.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.last_sync_results = results_df
                    st.dataframe(results_df)
                    st.success(f"Synchronization completed successfully! Updated {len(result)} tables.")

                else:
                    st.error("Synchronization failed. Please check the logs for details.")
            except Exception as e:
                st.error(f"Error during synchronization: {str(e)}")
    
    # Display previous results if available


    
    st.markdown("</div>", unsafe_allow_html=True)

# Cache management section
st.header("Cache Management")
with st.container():
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.write("If you have updated the data files in Google Drive directly, you may need to clear the cache to see the changes.")
    if st.button("Clear Cache and Reload Data", key="clear_cache_btn"):
        with st.spinner("Clearing cache and reloading all data..."):
            st.cache_data.clear()
            st.cache_resource.clear()
            if 'dataframes' in st.session_state:
                del st.session_state['dataframes']
            if 'all_data_loaded' in st.session_state:
                del st.session_state['all_data_loaded']
            
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
    - Run synchronization regularly to keep Google Drive data up to date
    - Ensure database connection is stable before syncing
    - Large tables may take longer to synchronize
    - The process is incremental, so only new records are added
    
    ### Troubleshooting
    - If sync fails, check database connection settings
    - Verify Google Drive API credentials are valid
    - Check network connectivity
    - Review logs for detailed error messages
    """)

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>CRM Data Management © 2024</p>", unsafe_allow_html=True)