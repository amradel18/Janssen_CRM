import os
import io
import pickle
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ----------------- CONFIG via secrets/.env ----------------- #

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
    folder_id = _get_secret("drive", "folder_id", env_var="DRIVE_FOLDER_ID")
    if not folder_id:
        raise RuntimeError("DRIVE folder_id is not set. Please set [drive].folder_id in .streamlit/secrets.toml or DRIVE_FOLDER_ID in .env")
    return folder_id


def _get_db_config() -> dict:
    host = _get_secret("db", "host", env_var="DB_HOST", default="localhost")
    port = int(_get_secret("db", "port", env_var="DB_PORT", default="3306"))
    user = _get_secret("db", "user", env_var="DB_USER", default="root")
    password = _get_secret("db", "password", env_var="DB_PASSWORD", default="")
    autocommit = str(_get_secret("db", "autocommit", env_var="DB_AUTOCOMMIT", default="true")).lower() in ("1", "true", "yes")
    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'autocommit': autocommit,
    }

DB_CONFIG = _get_db_config()

SCOPES = ['https://www.googleapis.com/auth/drive']
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client_secret.json")
TOKEN_FILE = _get_env('GOOGLE_TOKEN_FILE', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token.pkl"))
# ----------------------------------------------------------- #


def get_engine():
    password_encoded = quote_plus(DB_CONFIG['password'])
    connection_string = f"mysql+pymysql://{DB_CONFIG['user']}:{password_encoded}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/janssencrm"
    return create_engine(connection_string, connect_args={'connect_timeout': 20})

# --- Added: Streamlit-cached helpers expected by utils.py ---

def get_database_connection():
    """Return a SQLAlchemy engine for the Janssen CRM database."""
    return get_engine()


@st.cache_data(show_spinner=False, ttl=600)
def cached_query(sql: str, params: Optional[tuple] = None, database_name: str = 'janssencrm') -> pd.DataFrame:
    """Execute a SQL query with optional params and cache the result for faster reloads."""
    engine = get_engine()
    return pd.read_sql(sql, con=engine, params=params)


@st.cache_data(show_spinner=False, ttl=600)
def cached_table_query(table_name: str, database_name: str = 'janssencrm') -> pd.DataFrame:
    """Load an entire table from the database with caching."""
    engine = get_engine()
    return pd.read_sql(f"SELECT * FROM {database_name}.{table_name}", con=engine)

# ------------------------------------------------------------


def get_drive_service():
    SCOPES = ['https://www.googleapis.com/auth/drive']
    # Load credentials from Streamlit secrets or environment variables
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
        # Fallback to interactive flow for local/dev if secrets are not provided
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
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes)
        creds = flow.run_local_server(port=0)

    return build('drive', 'v3', credentials=creds)


def get_file_id_by_name(filename: str, service, folder_id: Optional[str] = None) -> Optional[str]:
    q = f"name = '{filename}' and trashed = false"
    if folder_id:
        q += f" and '{folder_id}' in parents"
    # Order by modification time descending to get the latest version if duplicates exist
    res = service.files().list(q=q, spaces="drive", fields="files(id, name, modifiedTime)", orderBy="modifiedTime desc", pageSize=1).execute()
    files = res.get("files", [])
    if not files:
        return None
    
    # The query returns the most recently modified file first.
    return files[0]['id']


def read_csv_from_drive_by_id(file_id: str, service) -> pd.DataFrame:
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh)


def upload_or_update_csv_on_drive(df: pd.DataFrame, filename: str, folder_id: str, _service, existing_file_id: Optional[str] = None) -> str:
    """
    Upload or update a CSV file on Google Drive.
    If an existing_file_id is provided, it DELETES the old file and uploads a new one.
    
    Args:
        df: DataFrame to upload
        filename: File name
        folder_id: Folder ID
        _service: Google Drive API service (prefixed with underscore to prevent caching)
        existing_file_id: Existing file ID (optional)
        
    Returns:
        ID of the uploaded or updated file
    """
    # If the file exists, delete it first as requested.
    if existing_file_id:
        try:
            _service.files().delete(fileId=existing_file_id).execute()
            print(f"🗑️ Successfully deleted old version of file: {filename} (ID: {existing_file_id})")
        except Exception as e:
            print(f"⚠️ Could not delete old file version (ID: {existing_file_id}): {e}. Will attempt to overwrite.")


    # Convert DataFrame to BytesIO
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    media = MediaIoBaseUpload(buffer, mimetype='text/csv', resumable=True)

    # Always create a new file now
    metadata = {'name': filename, 'parents': [folder_id]}
    created = _service.files().create(body=metadata, media_body=media, fields='id').execute()
    return created.get('id')


def export_incremental_tables_to_drive(
    pk_column_map: Optional[Dict[str, str]] = None
) -> Dict[str, Dict]:
    """
    Exports tables to Google Drive. If new data exists in the database table
    compared to the version on Drive, it replaces the entire file on Drive with
    the full, up-to-date table from the database.

    Args:
        pk_column_map: Map of table name -> primary key column name
                      (defaults to 'id' for all tables)

    Returns:
        Dictionary containing export information for each table.
    """
    # --- Configure table names and folder here ---
    table_names = [
        "call_categories", "call_types", "cities", "companies", "customer_phones",
        "customers", "governorates", "product_info", "request_reasons", 'customercall',
        "ticket_categories", "ticket_item_change_another", "ticket_item_change_same",
        "ticket_item_maintenance", "ticket_items", "ticketcall", "tickets", "users"
    ]
    folder_id = _get_drive_folder_id()
    # ---------------------------------------

    if pk_column_map is None:
        pk_column_map = {}

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).fetchone()
        print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Please ensure:")
        print("   1. MySQL server is running")
        print("   2. Database credentials are correct in DB_CONFIG")
        print("   3. Database 'janssencrm' exists")
        print("   4. User has proper permissions")
        return {}

    try:
        service = get_drive_service()
        print("✅ Google Drive authentication successful!")
    except Exception as e:
        print(f"❌ Google Drive authentication failed: {e}")
        return {}

    summary = {}

    for tbl in table_names:
        pk = pk_column_map.get(tbl, "id")
        filename = f"{tbl}.csv"
        print(f"\n🔁 Processing table: {tbl} (pk='{pk}')")

        existing_file_id = get_file_id_by_name(filename, service, folder_id)
        last_id_on_drive = None
        
        if existing_file_id:
            try:
                df_existing = read_csv_from_drive_by_id(existing_file_id, service)
                if pk in df_existing.columns and not df_existing.empty and not df_existing[pk].isnull().all():
                    max_id = pd.to_numeric(df_existing[pk], errors='coerce').max()
                    if pd.notna(max_id):
                        last_id_on_drive = int(max_id)
                        print(f"✅ Found last ID on Drive for table {tbl}: {last_id_on_drive}")
            except Exception as e:
                print(f"⚠️ Could not read or process existing file {filename}: {e}. Will perform a full refresh.")
        
        # Check if there are new rows in the database
        new_rows_exist = False
        if last_id_on_drive is not None:
            try:
                # Efficiently check for any row with a higher ID
                query = f"SELECT 1 FROM janssencrm.{tbl} WHERE {pk} > %s LIMIT 1"
                df_check = pd.read_sql(query, engine, params=(last_id_on_drive,))
                if not df_check.empty:
                    new_rows_exist = True
                    print(f"🔥 New rows detected for table: {tbl}.")
            except Exception as e:
                print(f"⚠️ Error checking for new rows: {e}. Assuming a refresh is needed.")
                new_rows_exist = True
        else:
            # No last ID means no existing file or an issue reading it, so a refresh is required.
            new_rows_exist = True
            print(f"ℹ️ No valid last ID found for {tbl}. A full refresh is required.")

        # If new rows exist (or if it's the first time), perform a full refresh.
        if new_rows_exist:
            print(f"🔄 Performing a full refresh for table: {tbl}...")
            try:
                # Fetch the entire table from the database
                df_to_upload = pd.read_sql(f"SELECT * FROM janssencrm.{tbl}", engine)
                print(f"✅ Fetched {df_to_upload.shape[0]} total rows from the database.")

                # Upload the full table, replacing the old file if it exists
                file_id = upload_or_update_csv_on_drive(df_to_upload, filename, folder_id, _service=service, existing_file_id=existing_file_id)
                print(f"✅ Full refresh successful. File ID: {file_id}")
                summary[tbl] = {"new_rows": "N/A (Full Refresh)", "total_rows": df_to_upload.shape[0], "file_id": file_id}
            
            except Exception as e:
                print(f"❌ An error occurred during the refresh of table {tbl}: {e}")
                summary[tbl] = {"new_rows": "Error", "file_id": existing_file_id}
                continue
        else:
            # No new rows found
            print("➡️ No new rows found. Skipping.")
            summary[tbl] = {"new_rows": 0, "file_id": existing_file_id}

    return summary

# To run this script successfully, you need to:
# 1. Start your MySQL server
# 2. Update DB_CONFIG with your actual database credentials
# 3. Ensure the 'janssencrm' database exists
# 4. Make sure you have proper Google Drive API credentials in client_secret.json or in secrets/.env

if __name__ == "__main__":
    result = export_incremental_tables_to_drive()
    if result:
        print(f"\n✅ Export completed successfully! Processed {len(result)} tables.")
        for table, info in result.items():
            print(f"   - {table}: {info['new_rows']} new rows")
    else:
        print("\n❌ Export failed. Please check the error messages above.")