import os
import io
# removed unused pickle import
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ----------------- CONFIG via secrets/.env ----------------- #

def _has_streamlit_secrets() -> bool:
    home_path = os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(project_root, ".streamlit", "secrets.toml")
    return os.path.exists(home_path) or os.path.exists(project_path)


def _get_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(var_name, default)


def _get_secret(section: str, key: str, env_var: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    """Prefer .env first to avoid Streamlit warning when secrets.toml is missing, then fallback to st.secrets if exists."""
    if env_var:
        env_val = _get_env(env_var, None)
        if env_val is not None and env_val != "":
            return env_val
    if _has_streamlit_secrets():
        try:
            return st.secrets[section][key]
        except Exception:
            pass
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
# removed TOKEN_FILE usage: credentials are now read from secrets/.env
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
    """Create Google Drive service using non-interactive credentials only.
    Requires GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_TOKEN, GOOGLE_REFRESH_TOKEN.
    """
    token = _get_secret("google", "token", env_var="GOOGLE_TOKEN")
    refresh_token = _get_secret("google", "refresh_token", env_var="GOOGLE_REFRESH_TOKEN")
    token_uri = _get_secret("google", "token_uri", env_var="GOOGLE_TOKEN_URI", default="https://oauth2.googleapis.com/token")
    client_id = _get_secret("google", "client_id", env_var="GOOGLE_CLIENT_ID")
    client_secret = _get_secret("google", "client_secret", env_var="GOOGLE_CLIENT_SECRET")
    redirect_uri = _get_secret("google", "redirect_uri", env_var="GOOGLE_REDIRECT_URI", default="http://localhost")
    scopes_raw = _get_secret("google", "scopes", env_var="GOOGLE_SCOPES")

    scopes = SCOPES
    if scopes_raw:
        if isinstance(scopes_raw, list):
            scopes = scopes_raw
        elif isinstance(scopes_raw, str):
            scopes = [s.strip(" `\"'") for s in scopes_raw.replace(",", " ").split() if s.strip(" `\"'")]

    missing = []
    if not client_id:
        missing.append("GOOGLE_CLIENT_ID")
    if not client_secret:
        missing.append("GOOGLE_CLIENT_SECRET")
    if not token:
        missing.append("GOOGLE_TOKEN")
    if not refresh_token:
        missing.append("GOOGLE_REFRESH_TOKEN")
    if missing:
        raise RuntimeError("Google Drive credentials are missing. Please set: " + ", ".join(missing))

    creds = Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )

    if not creds.valid:
        if getattr(creds, 'expired', False) and getattr(creds, 'refresh_token', None):
            try:
                creds.refresh(Request())
            except Exception as e:
                raise RuntimeError(f"Failed to refresh Google token. Ensure GOOGLE_REFRESH_TOKEN is valid. Error: {e}")
        else:
            raise RuntimeError("Provided Google credentials are invalid and cannot be refreshed. Check GOOGLE_TOKEN/GOOGLE_REFRESH_TOKEN.")

    return build('drive', 'v3', credentials=creds)


def get_file_id_by_name(filename: str, service, folder_id: Optional[str] = None) -> Optional[str]:
    query_parts = ["name = '{}'".format(filename), "trashed = false"]
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")
    q = " and ".join(query_parts)

    res = service.files().list(q=q, spaces="drive", fields="files(id, name)", pageSize=5).execute()
    files = res.get("files", [])
    if not files:
        return None
    return files[0]['id']


@st.cache_data(show_spinner=False, ttl=600)
def read_csv_from_drive_by_id(file_id: str, _service) -> pd.DataFrame:
    request = _service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh)


def upload_or_update_csv_on_drive(file_name: str, df: pd.DataFrame, folder_id: Optional[str] = None, _service=None) -> str:
    if _service is None:
        _service = get_drive_service()
    if folder_id is None:
        folder_id = _get_drive_folder_id()

    # Try find existing
    existing_id = get_file_id_by_name(file_name, _service, folder_id)

    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    media = MediaIoBaseUpload(buf, mimetype='text/csv')

    if existing_id:
        file_metadata = {"name": file_name}
        updated = _service.files().update(
            fileId=existing_id,
            media_body=media,
            body=file_metadata,
            fields="id"
        ).execute()
        return updated["id"]
    else:
        file_metadata = {
            "name": file_name,
            "parents": [folder_id] if folder_id else []
        }
        created = _service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        return created["id"]


def export_incremental_tables_to_drive(tables: List[str], _service=None, folder_id: Optional[str] = None) -> Dict[str, str]:
    if _service is None:
        _service = get_drive_service()
    if folder_id is None:
        folder_id = _get_drive_folder_id()

    exported: Dict[str, str] = {}

    engine = get_engine()
    for table_name in tables:
        df = pd.read_sql(f"SELECT * FROM janssencrm.{table_name}", con=engine)
        file_name = f"{table_name}.csv"
        file_id = upload_or_update_csv_on_drive(file_name, df, folder_id=folder_id, _service=_service)
        exported[table_name] = file_id

    return exported


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
        try:
            engine = get_engine()
            query = text(f"SELECT COUNT(*) FROM janssencrm.{tbl} WHERE id > :last_id")
            last_id_value = last_id_on_drive if last_id_on_drive is not None else -1
            with engine.connect() as conn:
                new_rows = conn.execute(query, {"last_id": last_id_value}).scalar()
        except Exception as e:
            print(f"⚠️ Failed to check new rows for table {tbl}: {e}. Defaulting to full refresh.")
            new_rows = None

        # Export logic
        try:
            engine = get_engine()
            df = pd.read_sql(text(f"SELECT * FROM janssencrm.{tbl}"), con=engine)

            uploaded_file_id = upload_or_update_csv_on_drive(df, filename, folder_id, service, existing_file_id)
            summary[tbl] = {"new_rows": int(new_rows or df.shape[0]), "file_id": uploaded_file_id}
            print(f"✅ Uploaded {filename} to Drive. File ID: {uploaded_file_id}")
        except Exception as e:
            summary[tbl] = {"error": str(e)}
            print(f"❌ Failed to upload {filename} to Drive: {e}")

    return summary


if __name__ == "__main__":
    result = export_incremental_tables_to_drive()
    if result:
        print(f"\n✅ Export completed successfully! Processed {len(result)} tables.")
        for table, info in result.items():
            print(f"   - {table}: {info['new_rows']} new rows")
    else:
        print("\n❌ Export failed. Please check the error messages above.")