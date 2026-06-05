@echo off
REM run_demo_offline.bat
REM
REM Windows batch script to launch Streamlit dashboard directly in offline fallback demo mode.
REM Bypasses scoring API loading and runs purely on pre-baked validation datasets.

echo ==================================================
echo 📦 Starting FraudGraph Shield Offline Fallback Demo...
echo ==================================================

REM Get absolute path to the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Detect correct virtual environment python path
set VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    set VENV_PYTHON=python
)

echo Using Python: %VENV_PYTHON%

REM Start dashboard
echo 📈 Starting Streamlit Analyst Dashboard on port 8501 (Demo Mode)...
cd "%SCRIPT_DIR%phase4\dashboard"
"%VENV_PYTHON%" -m streamlit run app.py --server.port 8501
