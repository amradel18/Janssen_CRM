import streamlit as st
import os
import sys

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import the authentication module
from auth.login import login_form, logout_user

# Set page config
st.set_page_config(page_title="CRM Login", layout="wide")

# Add custom CSS
st.markdown("""
<style>
    .main .block-container {
        max-width: 500px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #1E3A8A;
        text-align: center;
    }
    .login-container {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 2rem;
        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
        margin-top: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1E3A8A;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Display logo or header
st.image("https://via.placeholder.com/150x80?text=CRM+Logo", use_column_width=True)

# Main login container
with st.container():
    st.title("CRM Dashboard")
    
    # Call the login form function from auth.login
    if login_form():
        st.success("You are logged in!")
        
        # Navigation buttons after login
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Go to Dashboard", key="dashboard_btn"):
                import os
                os.system("streamlit run dashboard.py")
                st.stop()
        with col2:
            if st.button("Data Management", key="data_management_btn"):
                import os
                os.system("streamlit run data_management.py")
                st.stop()
        st.write(f"Welcome, {st.session_state.get('username', 'User')}!")
        
        # Logout button
        if st.button("Logout", key="logout_btn"):
            logout_user()
            st.rerun()