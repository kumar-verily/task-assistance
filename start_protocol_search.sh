#!/bin/bash

# Clinical Protocol Search Interface Startup Script

echo "=========================================="
echo "Clinical Protocol RAG Search Interface"
echo "=========================================="
echo ""
echo "Starting the search interface..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Run the search interface
python protocol_search.py
