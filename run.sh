#!/bin/bash
# Quick runner script
cd "$(dirname "$0")" || exit 1
python3 -m streamlit run app.py --server.port=8501
