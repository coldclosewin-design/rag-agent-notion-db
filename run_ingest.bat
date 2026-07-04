@echo off
rem Notion 재수집 + 색인 (더블클릭으로 실행 가능)
cd /d "%~dp0"
".venv\Scripts\python.exe" scripts\ingest.py
pause
