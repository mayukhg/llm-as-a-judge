#!/bin/bash
# shutdown.sh — stop HHH Judge Streamlit

echo "====================================================="
echo " Shutting down HHH Judge (Streamlit)"
echo "====================================================="

cd "$(dirname "$0")"

if [ -f ".streamlit.pid" ]; then
    PID=$(cat .streamlit.pid)
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        echo "Stopped Streamlit (PID $PID)."
    else
        echo "Process $PID not running. Removing stale PID file."
    fi
    rm -f .streamlit.pid
else
    echo "No .streamlit.pid found. Trying pkill for this app..."
    if pkill -f "streamlit run streamlit_app.py" 2>/dev/null; then
        echo "Matching streamlit processes stopped."
    else
        echo "No matching streamlit processes found."
    fi
fi

echo "Shutdown complete."
