#!/bin/bash
# startup.sh — HHH Judge Streamlit dashboard

set -euo pipefail

echo "====================================================="
echo " Starting HHH Judge (Streamlit)"
echo "====================================================="

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Install Python 3.11+ and try again."
    exit 1
fi

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
    # shellcheck source=/dev/null
    source ".venv/bin/activate"
fi

if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "Installing dependencies (first run)..."
    python3 -m pip install -r requirements.txt
fi

if [ -f ".streamlit.pid" ]; then
    OLD_PID=$(cat .streamlit.pid)
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping previous instance (PID $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f .streamlit.pid
fi

echo "Starting Streamlit..."
nohup streamlit run streamlit_app.py --server.headless true > streamlit.log 2>&1 &
PID=$!
echo "$PID" > .streamlit.pid

echo "Streamlit started with PID $PID."
echo "Initializing..."
sleep 2
echo "Open the UI at: http://localhost:8501"
echo "(Logs: streamlit.log)"
