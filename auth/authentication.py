import streamlit as st
import os

def check_authentication():
    """
    Check if the user is authenticated.
    If not, display a warning and stop the execution of the page.
    """
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        st.warning("You need to login to access this page.")
        st.markdown("<a href='http://localhost:8501/login' target='_self'>Go to Login Page</a>", unsafe_allow_html=True)
        # Add a button to navigate to the login page
        if st.button("Go to Login Page"):
            # Get the root directory of the project
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            # Run the login page
            os.system(f'streamlit run {os.path.join(root_dir, "login.py")}')
        st.stop()