#!/bin/bash

# Clinical ToDo Viewer Startup Script

echo "=========================================="
echo "Clinical ToDo Viewer - AI-Powered"
echo "=========================================="
echo ""

# Activate virtual environment
source venv/bin/activate

# Check if synthetic patients exist
if [ ! -f "synthetic_patients.json" ]; then
    echo "⚠️  No synthetic patients found!"
    echo ""
    echo "Using sample patients (3 patients)."
    echo "To generate 20 full patients, edit .env with your OpenAI API key, then run:"
    echo "  python generate_patients.py"
    echo ""
fi

echo "Starting ToDo Viewer..."
echo ""

# Run the application
python todo_viewer.py
