#!/bin/bash
# SmartFood 1-Click Launcher for macOS
# Double-click this file anytime to launch SmartFood and open your browser!

cd "$(dirname "$0")" || exit 1

echo "=================================================="
echo "  🍲 Starting SmartFood Community Platform...     "
echo "=================================================="
echo ""

# Check if already running on port 8501
if lsof -ti:8501 >/dev/null 2>&1; then
    echo "SmartFood server is already running!"
    echo "Opening http://localhost:8501 in your browser..."
    open "http://localhost:8501"
else
    echo "Starting server on http://localhost:8501 ..."
    # Open browser after server starts
    (sleep 2 && open "http://localhost:8501") &
    python3 -m streamlit run app.py --server.port=8501
fi
