@echo off
REM run_demo.bat
REM
REM Windows batch script to launch live FraudGraph Shield demo:
REM CFMS mock registry, FastAPI scoring engine, cache pre-warming, and Streamlit.

echo ==================================================
echo 🛡️ Starting FraudGraph Shield Live Demo...
echo ==================================================

REM Get absolute path to the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Detect correct virtual environment python path
set VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    set VENV_PYTHON=python
)

echo Using Python: %VENV_PYTHON%

REM Start CFMS mock on port 8001
echo 🚀 Launching CFMS Mock Alert Registry (port 8001)...
start "CFMS Mock" /B "%VENV_PYTHON%" -m uvicorn phase3.core.cfms_mock:cfms_app --port 8001 > NUL 2>&1

REM Start main API on port 8000
echo 🚀 Launching FastAPI Scoring API Engine (port 8000)...
start "Scoring API" /B "%VENV_PYTHON%" -m uvicorn phase3.api.main:app --port 8000 > NUL 2>&1

REM Wait for API to load models
echo ⏱️ Waiting 8 seconds for scoring engine and models to initialize...
timeout /t 8 /nobreak > NUL

REM Warm the feature store cache
echo 🔥 Pre-warming Redis feature store cache...
"%VENV_PYTHON%" "%SCRIPT_DIR%phase3\warm_cache.py"

REM Start dashboard
echo 📈 Starting Streamlit Analyst Dashboard on port 8501...
cd "%SCRIPT_DIR%phase4\dashboard"
"%VENV_PYTHON%" -m streamlit run app.py --server.port 8501

echo Done.
