import os
import pickle
import pandas as pd
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import io
from typing import Optional
import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials

load_dotenv()

# ---------------- Helpers for secrets/env -----------------
def _get_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(var_name, default)

def _get_secret(section: str, key: str, env_var: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    try:
        return st.secrets[section][key]
    except Exception:
        if env_var:
            return _get_env(env_var, default)
        return default

def _get_drive_folder_id() -> str:
    folder_id = _get_secret("drive", "folder_id", env_var="DRIVE_FOLDER_ID", default=None)
    if not folder_id:
        raise RuntimeError("DRIVE folder_id is not set. Please set [drive].folder_id in .streamlit/secrets.toml or DRIVE_FOLDER_ID in .env")
    return folder_id

# ----------------------------------------------------------

def get_drive_service():
    SCOPES = ['https://www.googleapis.com/auth/drive']
    # Prefer credentials from Streamlit secrets or environment variables
    token = _get_secret("google", "token", env_var="GOOGLE_TOKEN")
    refresh_token = _get_secret("google", "refresh_token", env_var="GOOGLE_REFRESH_TOKEN")
    token_uri = _get_secret("google", "token_uri", env_var="GOOGLE_TOKEN_URI", default="https://oauth2.googleapis.com/token")
    client_id = _get_secret("google", "client_id", env_var="GOOGLE_CLIENT_ID")
    client_secret = _get_secret("google", "client_secret", env_var="GOOGLE_CLIENT_SECRET")
    scopes = _get_secret("google", "scopes", env_var="GOOGLE_SCOPES", default=SCOPES)

    # Normalize scopes to a list
    if isinstance(scopes, str):
        scopes = [s.strip(" `\"'") for s in scopes.replace(",", " ").split() if s.strip(" `\"'")]
    if not scopes:
        scopes = SCOPES

    creds = None
    if token and client_id and client_secret:
        creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
        if not creds.valid:
            try:
                if getattr(creds, 'expired', False) and getattr(creds, 'refresh_token', None):
                    creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ Failed to refresh Google token: {e}")
    else:
        from google_auth_oauthlib.flow import InstalledAppFlow
        redirect_uri = _get_secret("google", "redirect_uri", env_var="GOOGLE_REDIRECT_URI", default="http://localhost")
        if client_id and client_secret:
            client_config = {
                'installed': {
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': token_uri,
                    'redirect_uris': [redirect_uri]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, scopes)
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', scopes)
        creds = flow.run_local_server(port=0)

    return build('drive', 'v3', credentials=creds)

def get_file_id_by_name(filename: str, service, folder_id: Optional[str] = None) -> Optional[str]:
    """
    Search for a file in Google Drive by name and return the file ID.
    
    Args:
        filename: Name of the file to search for
        service: Google Drive API service
        folder_id: Folder ID to search in (optional)
        
    Returns:
        File ID if found, otherwise None
    """
    q = f"name = '{filename}' and trashed = false"
    if folder_id:
        q += f" and '{folder_id}' in parents"
    res = service.files().list(q=q, spaces="drive", fields="files(id, name)", pageSize=5).execute()
    files = res.get("files", [])
    if not files:
        return None
    return files[0]['id']  # First result (if duplicates exist, you can improve the strategy)


@st.cache_data
def read_csv_from_drive_by_name(filename, _service, folder_id=None, cache_key=None):
    """
    Read a CSV file from Google Drive directly into a DataFrame using the file name.
    If the file is not found in Google Drive, try to read it from the local project directory.
    
    Args:
        filename: File name in Google Drive
        _service: Google Drive API service
        folder_id: Folder ID to search in (default is the main project folder)
        cache_key: A parameter to manually bust the cache.
        
    Returns:
        DataFrame containing the file data, or None if the file was not found
    """
    if folder_id is None:
        folder_id = _get_drive_folder_id()
    file_id = get_file_id_by_name(filename, _service, folder_id)
    if not file_id:
        print(f"File not found on Drive: {filename}")
        # Try to read from local directory
        local_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(local_path):
            print(f"Reading from local file: {local_path}")
            return pd.read_csv(local_path)
        return None
    request = _service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh)

def lode_drive(display_in_streamlit=False, cache_key=None):
    file_name_mapping = {
        'call_categories': 'call_categories.csv',
        'call_types': 'call_types.csv',
        'cities': 'cities.csv',
        'companies': 'companies.csv',
        'customer_phones': 'customer_phones.csv',
        'customercall': 'customercall.csv',
        'customers': 'customers.csv',
        'governorates': 'governorates.csv',
        'product_info': 'product_info.csv',
        'request_reasons': 'request_reasons.csv',
        'ticket_categories': 'ticket_categories.csv',
        'ticket_item_change_another': 'ticket_item_change_another.csv',
        'ticket_item_change_same': 'ticket_item_change_same.csv',
        'ticket_item_maintenance': 'ticket_item_maintenance.csv',
        'ticket_items': 'ticket_items.csv',
        'ticketcall': 'ticketcall.csv',
        'tickets': 'tickets.csv',
        'users': 'users.csv',
        }
    service = get_drive_service()
    folder_id = _get_drive_folder_id()

    # Store all DataFrames in a dict with the same key names
    dataframes = {}

    for key, filename in file_name_mapping.items():
        print(f"Downloading: {filename} ...")
        df = read_csv_from_drive_by_name(filename, _service=service, folder_id=folder_id, cache_key=cache_key)
        if df is not None:
            if display_in_streamlit:
                st.dataframe(df)
            dataframes[key] = df
        else:
            print(f"⚠️ File {filename} not found on Drive")
    st.session_state.dataframes = dataframes
    return dataframes

def load_tables_from_drive(table_names, cache_key=None):
    """
    Load specific tables from Google Drive.
    
    Args:
        table_names: List of table names to load
        cache_key: A parameter to manually bust the cache.
        
    Returns:
        Dictionary containing the requested tables as DataFrames
    """
    # Initialize session state if not already done
    if 'dataframes' not in st.session_state:
        st.session_state.dataframes = lode_drive(cache_key=cache_key)
    
    # Create a dictionary with only the requested tables
    result = {}
    for table in table_names:
        if table in st.session_state.dataframes:
            result[table] = st.session_state.dataframes[table]
        else:
            # If table not in session state, try to load it individually
            file_name_mapping = {
                'call_categories': 'call_categories.csv',
                'call_types': 'call_types.csv',
                'cities': 'cities.csv',
                'companies': 'companies.csv',
                'customer_phones': 'customer_phones.csv',
                'customercall': 'customercall.csv',
                'customers': 'customers.csv',
                'governorates': 'governorates.csv',
                'product_info': 'product_info.csv',
                'request_reasons': 'request_reasons.csv',
                'ticket_categories': 'ticket_categories.csv',
                'ticket_item_change_another': 'ticket_item_change_another.csv',
                'ticket_item_change_same': 'ticket_item_change_same.csv',
                'ticket_item_maintenance': 'ticket_item_maintenance.csv',
                'ticket_items': 'ticket_items.csv',
                'ticketcall': 'ticketcall.csv',
                'tickets': 'tickets.csv',
                'users': 'users.csv',
                'calls': 'calls.csv',
            }
            
            if table in file_name_mapping:
                service = get_drive_service()
                folder_id = _get_drive_folder_id()
                filename = file_name_mapping[table]
                print(f"Downloading: {filename} ...")
                df = read_csv_from_drive_by_name(filename, _service=service, folder_id=folder_id, cache_key=cache_key)
                if df is not None:
                    result[table] = df
                    # Update session state
                    st.session_state.dataframes[table] = df
                else:
                    print(f"⚠️ File {filename} not found on Drive")
                    result[table] = pd.DataFrame()  # Return empty DataFrame
            else:
                print(f"⚠️ Unknown table: {table}")
                result[table] = pd.DataFrame()  # Return empty DataFrame
    
    return result

if __name__ == '__main__':
    st.session_state.dataframes = lode_drive()
