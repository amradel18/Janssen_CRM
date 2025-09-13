@echo off
REM Run Streamlit app for Customer Service Dashboard
cd /d %~dp0
streamlit run login.py
pause