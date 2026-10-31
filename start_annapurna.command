#!/bin/bash
# Annapurna 1-Click Desktop Launcher for macOS
# Double-click this file anytime to launch Annapurna and open your browser!

cd "$(dirname "$0")" || exit 1

echo "=================================================="
echo "  🍲 Starting Annapurna Community Platform...     "
echo "  🇮🇳 Stop Food Waste. Feed People.                "
echo "=================================================="
echo ""

# Check if already running on port 8501
if lsof -ti:8501 >/dev/null 2>&1; then
    echo "Annapurna server is already running!"
    echo "Opening http://localhost:8501 in your browser..."
    open "http://localhost:8501"
else
    echo "Starting Annapurna on http://localhost:8501 ..."
    (sleep 2 && open "http://localhost:8501") &
    python3 -m streamlit run app.py --server.port=8501
fi
