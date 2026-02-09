#!/bin/bash

# Clinical ToDo Viewer Enhanced - Startup Script

echo "=========================================="
echo "Clinical ToDo Viewer - AI-Powered"
echo "ENHANCED VERSION"
echo "=========================================="
echo ""
echo "New Features:"
echo "  ✓ Patient chart editing & persistence"
echo "  ✓ Protocol reference display"
echo ""
echo "Available Clinical ToDos (38 total):"
echo ""
echo "HYPERGLYCEMIA (6):"
echo "  • BGM-104, BGM-103, BGM-102, BGM-107, BGM-106, BGM-105"
echo ""
echo "HYPOGLYCEMIA (2):"
echo "  • BGM-100, BGM-101"
echo ""
echo "A1C MANAGEMENT (1):"
echo "  • A1c-101"
echo ""
echo "HYPERTENSION (5):"
echo "  • BP-105, BP-104, BP-103, BP-102, BP-101"
echo ""
echo "HYPOTENSION (1):"
echo "  • BP-106"
echo ""
echo "BP MONITORING (1):"
echo "  • BP-100"
echo ""
echo "PATIENT ENGAGEMENT (3):"
echo "  • ENG-100, ENG-101, ENG-110"
echo ""
echo "MENTAL HEALTH (3):"
echo "  • PHQ-9, PHQ-101, PHQ-100"
echo ""
echo "HEALTH ASSESSMENT (4):"
echo "  • PRM-101, PRM-102, PRM-103, PRM-104"
echo ""
echo "SURVEYS (4):"
echo "  • SRV-100, SRV-101, SRV-102, SRV-103"
echo ""
echo "CUSTOM TASKS (1):"
echo "  • TODO-100"
echo ""

# Activate virtual environment
source venv/bin/activate

echo "Starting Enhanced ToDo Viewer..."
echo ""

# Kill any existing instances
pkill -f "todo_viewer_enhanced.py" 2>/dev/null
sleep 1

# Run the enhanced application
python todo_viewer_enhanced.py
