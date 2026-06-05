#!/bin/bash
# run_demo.sh
#
# Startup script to launch live FraudGraph Shield system: CFMS mock, scoring API,
# feature store cache warming, and the Streamlit dashboard.

echo "=================================================="
echo "🛡️ Starting FraudGraph Shield Live Demo..."
echo "=================================================="

# Get absolute path to the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Detect correct virtual environment python path absolute
if [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/Scripts/python.exe"
elif [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
else
    VENV_PYTHON="python"
fi

echo "Using Python: $VENV_PYTHON"

# Start CFMS mock on port 8001
echo "🚀 Launching CFMS Mock Alert Registry (port 8001)..."
cd "$SCRIPT_DIR/phase3"
"$VENV_PYTHON" -m uvicorn core.cfms_mock:cfms_app --port 8001 > /dev/null 2>&1 &
CFMS_PID=$!

# Start main API on port 8000
echo "🚀 Launching FastAPI Scoring API Engine (port 8000)..."
"$VENV_PYTHON" -m uvicorn api.main:app --port 8000 > /dev/null 2>&1 &
API_PID=$!

# Wait for API to load GNN/LGBM models
echo "⏱️ Waiting 8 seconds for scoring engine and models to initialize..."
sleep 8

# Warm the feature store cache
echo "🔥 Pre-warming Redis feature store cache..."
"$VENV_PYTHON" warm_cache.py

# Start dashboard
echo "📈 Starting Streamlit Analyst Dashboard on port 8501..."
cd "$SCRIPT_DIR/phase4/dashboard"
"$VENV_PYTHON" -m streamlit run app.py --server.port 8501

# Cleanup background processes on exit
echo "🧹 Cleaning up background servers..."
kill $CFMS_PID $API_PID
echo "Done."
