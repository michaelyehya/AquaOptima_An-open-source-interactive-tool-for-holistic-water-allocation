@echo off
cd /d "%~dp0"
echo Starting Water Allocation Model GUI...
echo.
py -m streamlit run app.py
pause
