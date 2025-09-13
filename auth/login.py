import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

def _has_streamlit_secrets() -> bool:
    """Check if a Streamlit secrets.toml file exists to avoid triggering warnings."""
    home_path = os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(project_root, ".streamlit", "secrets.toml")
    return os.path.exists(home_path) or os.path.exists(project_path)


def _get_auth_credentials():
    """Fetch auth credentials from Streamlit secrets first, then from environment variables."""
    if _has_streamlit_secrets():
        try:
            username = st.secrets["auth"]["username"]
            password = st.secrets["auth"]["password"]
            if username and password:
                return username, password
        except Exception:
            pass
    return os.getenv("AUTH_USERNAME"), os.getenv("AUTH_PASSWORD")


def login_user(username, password):
    """
    Verify login credentials using secrets or environment variables
    """
    stored_username, stored_password = _get_auth_credentials()
    return (username == stored_username) and (password == stored_password)


def login_form():
    """
    Display login form and manage session state
    """
    # Check authentication status
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if login_user(username, password):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        return False
    
    return True


def logout_user():
    """
    Log out user and reset session state
    """
    if "authenticated" in st.session_state:
        st.session_state["authenticated"] = False
    if "username" in st.session_state:
        del st.session_state["username"]