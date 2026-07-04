@echo off
rem Streamlit 앱 실행 (더블클릭으로 실행 가능)
cd /d "%~dp0"
".venv\Scripts\python.exe" -m streamlit run app.py
pause
