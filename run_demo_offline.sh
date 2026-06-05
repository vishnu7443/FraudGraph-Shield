#!/bin/bash
# run_demo_offline.sh
#
# Startup script to launch Streamlit dashboard directly in offline fallback demo mode.
# Bypasses scoring API loading and runs purely on pre-baked validation datasets.

echo "=================================================="
echo "📦 Starting FraudGraph Shield Offline Fallback Demo..."
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

# Start dashboard directly (Radio toggles default to Demo Data)
echo "📈 Starting Streamlit Analyst Dashboard on port 8501 (Demo Mode)..."
cd "$SCRIPT_DIR/phase4/dashboard"
"$VENV_PYTHON" -m streamlit run app.py --server.port 8501
