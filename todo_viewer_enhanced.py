#!/usr/bin/env python3
"""
AI-Powered Clinical ToDo Viewer

A self-contained web application for viewing clinical ToDos with AI-generated
patient-specific detail views based on protocols and patient charts.
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pinecone import Pinecone
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

# Load environment
load_dotenv()

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Initialize clients
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
protocol_index = pc.Index("clinical-protocols-rag")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load synthetic patients
PATIENTS_FILE = 'synthetic_patients.json'

def load_patients():
    with open(PATIENTS_FILE, 'r') as f:
        return json.loads(f.read())

def save_patients(patients):
    timestamp = datetime.now().isoformat()
    for patient in patients:
        if 'metadata' not in patient:
            patient['metadata'] = {}
        patient['metadata']['last_modified'] = timestamp
    with open(PATIENTS_FILE, 'w') as f:
        json.dump(patients, f, indent=2)
    return timestamp

PATIENTS = load_patients()

# Create output directory for task assistance saves
OUTPUT_DIR = Path('task_assistance_outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

def get_task_assistance_filename(todo_id, patient_index):
    """Get the standard filename for task assistance"""
    return f"{todo_id}_patient{patient_index}.json"

def load_task_assistance(todo_id, patient_index):
    """Load existing task assistance if available"""
    filename = get_task_assistance_filename(todo_id, patient_index)
    filepath = OUTPUT_DIR / filename

    if filepath.exists():
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    return None

def save_task_assistance(todo_id, patient_index, patient_name, detail_view):
    """Save task assistance output to file"""
    filename = get_task_assistance_filename(todo_id, patient_index)
    filepath = OUTPUT_DIR / filename

    output_data = {
        'timestamp': datetime.now().isoformat(),
        'todo_id': todo_id,
        'patient_index': patient_index,
        'patient_name': patient_name,
        'detail_view': detail_view
    }

    with open(filepath, 'w') as f:
        json.dump(output_data, f, indent=2)

    return str(filepath)

# Load prompts
with open('detail_view_prompt.txt', 'r') as f:
    DETAIL_VIEW_PROMPT = f.read()

# Define ToDo list (easily extensible)
TODOS = [
    # Hyperglycemia
    {"id": "BGM-104", "name": "Hyperglycemia > 400, daily", "priority": "P0", "category": "Hyperglycemia"},
    {"id": "BGM-103", "name": "Hyperglycemia > 250", "priority": "P2", "category": "Hyperglycemia"},
    {"id": "BGM-102", "name": "Hyperglycemia > 180", "priority": "P3", "category": "Hyperglycemia"},
    {"id": "BGM-107", "name": "BG Average > 220 for 2 weeks (A1c 8-8.9)", "priority": "P2", "category": "Hyperglycemia"},
    {"id": "BGM-106", "name": "BG Average > 190 for 2 weeks (A1c 7-7.9)", "priority": "P2", "category": "Hyperglycemia"},
    {"id": "BGM-105", "name": "BG Average > 170 for 2 weeks (A1c<7)", "priority": "P2", "category": "Hyperglycemia"},

    # Hypoglycemia
    {"id": "BGM-100", "name": "Hypoglycemia < 54", "priority": "P0", "category": "Hypoglycemia"},
    {"id": "BGM-101", "name": "Hypoglycemia < 70", "priority": "P1", "category": "Hypoglycemia"},

    # A1C Management
    {"id": "A1c-101", "name": "Review A1c ingested > 7.0%", "priority": "P2", "category": "A1C Management"},

    # Hypertension
    {"id": "BP-105", "name": "Hypertension (High): BP > 180/120", "priority": "P0", "category": "Hypertension"},
    {"id": "BP-104", "name": "Hypertension: BP > 160/100", "priority": "P1", "category": "Hypertension"},
    {"id": "BP-103", "name": "Hypertension: BP > 150/90", "priority": "P1", "category": "Hypertension"},
    {"id": "BP-102", "name": "Hypertension: BP > 140/90", "priority": "P1", "category": "Hypertension"},
    {"id": "BP-101", "name": "Hypertension: BP > 130/80", "priority": "P2", "category": "Hypertension"},

    # Hypotension
    {"id": "BP-106", "name": "Hypotension (Low): BP < 90/60", "priority": "P1", "category": "Hypotension"},

    # Blood Pressure Monitoring
    {"id": "BP-100", "name": "Remind member to take initial BP reading", "priority": "P2", "category": "BP Monitoring"},

    # Patient Engagement
    {"id": "ENG-100", "name": "Greet new member", "priority": "P2", "category": "Engagement"},
    {"id": "ENG-101", "name": "Schedule telehealth visit", "priority": "P2", "category": "Engagement"},
    {"id": "ENG-110", "name": "Greet new member - WL Program", "priority": "P2", "category": "Engagement"},

    # Mental Health Screening (PHQ-9)
    {"id": "PHQ-9", "name": "PHQ-9 Self-harm risk (Q9: answer 1-3)", "priority": "P0", "category": "Mental Health"},
    {"id": "PHQ-101", "name": "Review PHQ-9 score >= 10", "priority": "P1", "category": "Mental Health"},
    {"id": "PHQ-100", "name": "Review PHQ-9 Question 9", "priority": "P1", "category": "Mental Health"},

    # PROMIS-10 Health Assessment
    {"id": "PRM-101", "name": "Review PROMIS-10 Question 4", "priority": "P2", "category": "Health Assessment"},
    {"id": "PRM-102", "name": "Review PROMIS-10 Question 10", "priority": "P2", "category": "Health Assessment"},
    {"id": "PRM-103", "name": "Review PROMIS-10 Question 6", "priority": "P2", "category": "Health Assessment"},
    {"id": "PRM-104", "name": "Review PROMIS-10 Question 7", "priority": "P2", "category": "Health Assessment"},

    # Surveys
    {"id": "SRV-100", "name": "Review DDAS - T1D", "priority": "P3", "category": "Surveys"},
    {"id": "SRV-101", "name": "Review DDAS - T2D", "priority": "P3", "category": "Surveys"},
    {"id": "SRV-102", "name": "Review PROMIS-10", "priority": "P3", "category": "Surveys"},
    {"id": "SRV-103", "name": "Review Nutrition Baseline", "priority": "P3", "category": "Surveys"},

    # Custom Tasks
    {"id": "TODO-100", "name": "Custom Task", "priority": "P3", "category": "Custom"},
]

# HTML Template (embedded - self-contained)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clinical ToDo Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            line-height: 1.6;
        }

        .app-container {
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Left Sidebar - Patients */
        .sidebar {
            width: 320px;
            background: white;
            border-right: 1px solid #e1e8ed;
            display: flex;
            flex-direction: column;
        }

        /* Middle Pane - Tasks */
        .tasks-pane {
            width: 400px;
            background: white;
            border-right: 1px solid #e1e8ed;
            display: flex;
            flex-direction: column;
        }

        .sidebar-header {
            padding: 24px;
            border-bottom: 1px solid #e1e8ed;
        }

        .sidebar-header h1 {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .pickers-section {
            padding: 20px;
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }

        .pickers-section .todo-list {
            flex: 1;
            overflow-y: auto;
        }

        .picker-group {
            margin-bottom: 24px;
        }

        .picker-label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            color: #64748b;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }

        .picker-select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 14px;
            background: white;
            cursor: pointer;
            transition: border-color 0.2s;
        }

        .picker-select:hover {
            border-color: #94a3b8;
        }

        .picker-select:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .load-button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-top: 16px;
        }

        .load-button:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .load-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .todo-list {
            margin-top: 20px;
            background: #f8fafc;
            border-radius: 8px;
            padding: 12px;
        }

        .todo-list-header {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: #64748b;
            margin-bottom: 8px;
            padding: 0 8px;
        }

        .patient-item {
            padding: 14px 16px;
            background: white;
            border-radius: 6px;
            margin-bottom: 6px;
            cursor: pointer;
            border: 1px solid #e2e8f0;
            transition: all 0.2s;
        }

        .patient-item:hover {
            border-color: #3b82f6;
            background: #f8fafc;
        }

        .patient-item.selected {
            border-color: #3b82f6;
            background: #eff6ff;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .patient-item-name {
            font-size: 14px;
            font-weight: 500;
            color: #1e293b;
            margin-bottom: 4px;
        }

        .patient-item-info {
            font-size: 12px;
            color: #64748b;
        }

        .todo-item {
            padding: 12px;
            background: white;
            border-radius: 6px;
            margin-bottom: 8px;
            cursor: pointer;
            border: 1px solid #e2e8f0;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .todo-item:hover {
            border-color: #3b82f6;
            background: #f8fafc;
        }

        .todo-item.selected {
            border-color: #3b82f6;
            background: #eff6ff;
        }

        .todo-item.cached {
            background: #d1fae5;
            border-color: #10b981;
        }

        .todo-item.cached:hover {
            background: #a7f3d0;
        }

        .todo-item.cached.selected {
            background: #6ee7b7;
            border-color: #059669;
        }

        .cached-badge {
            background: #059669;
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            margin-left: 8px;
            display: inline-block;
        }

        .category-header {
            font-size: 11px;
            font-weight: 600;
            color: #64748b;
            margin: 16px 8px 8px 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 6px;
        }

        .category-header:first-child {
            margin-top: 0;
        }

        .todo-item-title {
            font-size: 14px;
            font-weight: 500;
            color: #1e293b;
        }

        .priority-badge {
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }

        .priority-p0 {
            background: #fee2e2;
            color: #991b1b;
        }

        .priority-p1 {
            background: #fef3c7;
            color: #92400e;
        }

        .priority-p2 {
            background: #e0e7ff;
            color: #3730a3;
        }

        .priority-p3 {
            background: #e5e7eb;
            color: #374151;
        }

        /* Main Content Area - Right Pane */
        .main-content {
            flex: 1;
            overflow-y: auto;
            background: #f5f7fa;
            min-width: 0; /* Allow flex shrink */
        }

        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #64748b;
            padding: 40px;
            text-align: center;
        }

        .empty-state h2 {
            font-size: 24px;
            margin-bottom: 8px;
            color: #475569;
        }

        .empty-state p {
            font-size: 14px;
        }

        .detail-view {
            padding: 32px;
            max-width: 1000px;
            margin: 0 auto;
        }

        .detail-header {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .detail-title-section {
            flex: 1;
        }

        .detail-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #1e293b;
        }

        .patient-info {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 12px;
        }

        .patient-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 14px;
        }

        .patient-name {
            font-size: 14px;
            color: #475569;
        }

        .section-card {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        .section-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
        }

        .section-icon {
            font-size: 18px;
        }

        .section-title {
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
        }

        .beta-badge {
            padding: 2px 8px;
            background: #dbeafe;
            color: #1e40af;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .ai-insight-box {
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            border-left: 4px solid #10b981;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .ai-insight-header {
            font-weight: 600;
            margin-bottom: 8px;
            color: #065f46;
        }

        .ai-insight-text {
            color: #064e3b;
            line-height: 1.6;
            margin-bottom: 12px;
        }

        .key-points {
            margin-top: 12px;
        }

        .key-point {
            padding: 8px 0;
            color: #065f46;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }

        .key-point:before {
            content: "•";
            font-weight: bold;
            flex-shrink: 0;
        }

        .overview-list {
            list-style: none;
        }

        .overview-item {
            padding: 8px 0;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }

        .overview-item:before {
            content: "•";
            font-weight: bold;
            flex-shrink: 0;
        }

        .clinic-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }

        .clinic-badge-yes {
            background: #dbeafe;
            color: #1e40af;
        }

        .clinic-badge-no {
            background: #fef3c7;
            color: #92400e;
        }

        .timeline-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
        }

        .timeline-table th {
            text-align: left;
            padding: 12px;
            background: #f8fafc;
            font-weight: 600;
            font-size: 13px;
            color: #475569;
            border-bottom: 2px solid #e2e8f0;
        }

        .timeline-table td {
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
            font-size: 14px;
            color: #1e293b;
        }

        .timeline-table tr:last-child td {
            border-bottom: none;
        }

        .message-card {
            background: #f8fafc;
            border-left: 3px solid #3b82f6;
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 12px;
            transition: all 0.2s;
        }

        .message-card:hover {
            background: #eff6ff;
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .message-category {
            font-size: 12px;
            font-weight: 600;
            color: #3b82f6;
        }

        .message-type {
            font-size: 11px;
            padding: 2px 8px;
            background: #dbeafe;
            color: #1e40af;
            border-radius: 12px;
        }

        .message-text {
            color: #334155;
            line-height: 1.6;
            margin-bottom: 8px;
        }

        .message-rationale {
            font-size: 12px;
            color: #64748b;
            font-style: italic;
        }

        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #e2e8f0;
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.95);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }

        .loading-text {
            margin-top: 16px;
            font-size: 16px;
            color: #475569;
        }

        .error-message {
            background: #fee2e2;
            border-left: 4px solid #dc2626;
            padding: 16px;
            border-radius: 6px;
            color: #991b1b;
            margin: 20px;
        }

        .protocol-step {
            padding: 12px;
            background: #f8fafc;
            border-radius: 6px;
            margin-bottom: 8px;
            border-left: 3px solid #6366f1;
            transition: all 0.2s;
        }

        .protocol-step:hover {
            background: #f1f5f9;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 12px;
        }

        .info-item {
            background: #f8fafc;
            padding: 12px;
            border-radius: 6px;
        }

        .info-label {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 4px;
        }

        .info-value {
            font-size: 14px;
            font-weight: 500;
            color: #1e293b;
        }

        /* Patient Editor Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
        }

        .modal-content {
            background: white;
            border-radius: 12px;
            width: 90%;
            max-width: 800px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        .modal-header {
            padding: 20px 24px;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-title {
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
        }

        .modal-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #64748b;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 6px;
            transition: background 0.2s;
        }

        .modal-close:hover {
            background: #f1f5f9;
        }

        .modal-body {
            padding: 24px;
            overflow-y: auto;
            flex: 1;
        }

        .modal-footer {
            padding: 16px 24px;
            border-top: 1px solid #e2e8f0;
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }

        .btn {
            padding: 10px 20px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: #f1f5f9;
            color: #475569;
        }

        .btn-secondary:hover {
            background: #e2e8f0;
        }

        .patient-editor {
            font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
            font-size: 13px;
            width: 100%;
            min-height: 400px;
            padding: 16px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            background: #f8fafc;
            color: #1e293b;
            resize: vertical;
        }

        .edit-patient-btn {
            padding: 8px 16px;
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 13px;
            color: #475569;
            cursor: pointer;
            margin-top: 8px;
            width: 100%;
            transition: all 0.2s;
        }

        .edit-patient-btn:hover {
            background: #e2e8f0;
            border-color: #94a3b8;
        }

        .last-modified {
            font-size: 11px;
            color: #64748b;
            margin-top: 4px;
            text-align: center;
        }

        .refresh-button {
            width: 100%;
            padding: 12px;
            background: #f59e0b;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .refresh-button:hover {
            background: #d97706;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
        }

        /* Protocol Reference Section */
        .protocol-accordion {
            margin: 0 32px 24px 32px;
        }

        .protocol-accordion-header {
            background: #f8fafc;
            padding: 16px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #e2e8f0;
            transition: all 0.2s;
        }

        .protocol-accordion-header:hover {
            background: #f1f5f9;
            border-color: #cbd5e1;
        }

        .protocol-accordion-title {
            font-weight: 600;
            color: #1e293b;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .protocol-accordion-icon {
            transition: transform 0.3s;
        }

        .protocol-accordion-icon.open {
            transform: rotate(180deg);
        }

        .protocol-accordion-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }

        .protocol-accordion-content.open {
            max-height: 1000px;
            transition: max-height 0.5s ease-in;
        }

        .protocol-content {
            padding: 20px;
            background: white;
            border: 1px solid #e2e8f0;
            border-top: none;
            border-radius: 0 0 8px 8px;
        }

        .protocol-field {
            margin-bottom: 16px;
        }

        .protocol-label {
            font-size: 12px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            margin-bottom: 6px;
            letter-spacing: 0.5px;
        }

        .protocol-value {
            color: #1e293b;
            line-height: 1.6;
            white-space: pre-wrap;
        }

        .protocol-link {
            display: inline-block;
            margin-top: 12px;
            color: #3b82f6;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            transition: color 0.2s;
        }

        .protocol-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            font-size: 13px;
        }

        .protocol-table th {
            background: #0f766e;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
        }

        .protocol-table td {
            padding: 12px;
            border: 1px solid #e2e8f0;
            vertical-align: top;
            line-height: 1.6;
        }

        .protocol-table td:first-child {
            font-weight: 600;
            color: #475569;
            background: #f8fafc;
            width: 180px;
        }

        .protocol-table ul {
            margin: 8px 0 8px 0;
            padding-left: 20px;
            list-style-type: disc;
        }

        .protocol-table ul ul {
            margin: 4px 0;
            padding-left: 24px;
            list-style-type: circle;
        }

        .protocol-table ul ul ul {
            list-style-type: square;
        }

        .protocol-table li {
            margin: 6px 0;
            line-height: 1.5;
        }

        .protocol-table a {
            color: #3b82f6;
            text-decoration: none;
        }

        .protocol-table a:hover {
            text-decoration: underline;
        }

        .protocol-message-template {
            font-style: italic;
            color: #1e40af;
            background: #eff6ff;
            padding: 8px 12px;
            border-radius: 4px;
            margin: 6px 0;
            display: block;
        }

        .protocol-table strong {
            font-weight: 600;
            color: #1e293b;
        }

        .protocol-link:hover {
            color: #2563eb;
            text-decoration: underline;
        }

        .success-message {
            background: #d1fae5;
            border-left: 4px solid #10b981;
            padding: 12px 16px;
            border-radius: 6px;
            color: #065f46;
            margin-bottom: 16px;
            font-size: 14px;
        }

        .step-assistance-button {
            width: 100%;
            padding: 12px;
            margin-top: 16px;
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .step-assistance-button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }

        .step-assistance-button-small {
            padding: 6px 12px;
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
            flex-shrink: 0;
        }

        .step-assistance-button-small:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }

        .message-action-button {
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .message-action-button:hover {
            background: #e2e8f0;
            border-color: #94a3b8;
            transform: scale(1.1);
        }

        .message-editor-modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 3000;
        }

        .message-editor-content {
            background: white;
            border-radius: 12px;
            width: 90%;
            max-width: 700px;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        .message-editor-body {
            padding: 24px;
            overflow-y: auto;
        }

        .message-editor-textarea {
            width: 100%;
            min-height: 150px;
            padding: 12px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 14px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            resize: vertical;
            line-height: 1.6;
        }

        .message-editor-textarea:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .char-counter {
            font-size: 12px;
            color: #64748b;
            text-align: right;
            margin-top: 4px;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Left Sidebar - Patients -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h1>Patients</h1>
                <p style="font-size: 13px; color: #64748b;">Select a patient to view tasks</p>
            </div>

            <div class="pickers-section">
                <!-- Role Picker -->
                <div class="picker-group">
                    <div class="picker-label">Your Role</div>
                    <select id="roleSelect" class="picker-select">
                        <option value="RN">RN - Registered Nurse</option>
                        <option value="HC">HC - Health Coach</option>
                        <option value="RD">RD - Registered Dietitian</option>
                        <option value="PharmD">PharmD - Pharmacist</option>
                    </select>
                </div>

                <button id="editPatientBtn" class="edit-patient-btn" disabled>
                    &#128221; View/Edit Patient Chart
                </button>
                <div id="lastModified" class="last-modified"></div>

                <!-- Patient List -->
                <div class="todo-list">
                    <div class="todo-list-header">All Patients</div>
                    <div id="patientListContainer"></div>
                </div>
            </div>
        </div>

        <!-- Middle Pane - Tasks -->
        <div class="tasks-pane">
            <div class="sidebar-header">
                <h1>Tasks</h1>
                <p style="font-size: 13px; color: #64748b;" id="tasksSubheader">Select a patient to view tasks</p>
            </div>

            <div class="pickers-section">
                <!-- Task List -->
                <div class="todo-list">
                    <div class="todo-list-header">All Clinical Tasks</div>
                    <div id="todoListContainer"></div>
                </div>
            </div>
        </div>

        <!-- Main Content - Right Pane -->
        <div class="main-content" id="mainContent">
            <div class="empty-state">
                <h2>&#128075; Welcome to Clinical ToDo Viewer</h2>
                <p>Select a patient and task to view protocol and generate AI-powered clinical insights</p>
            </div>
        </div>
    </div>

    <!-- Loading Overlay -->
    <div id="loadingOverlay" class="loading-overlay" style="display: none;">
        <div class="loading-spinner"></div>
        <div class="loading-text" id="loadingText">Loading Task Assistance...</div>
        <div style="font-size: 13px; color: #64748b; margin-top: 8px;" id="loadingSubtext"></div>
    </div>

    <script>
        let todos = [];
        let patients = [];
        let selectedTodo = null;
        let selectedPatient = null;
        let selectedPatientIndex = null;
        let cachedTasks = new Set(); // Track which tasks have cached assistance for current patient

        // Load initial data
        async function loadInitialData() {
            try {
                // Load ToDos
                const todoResp = await fetch('/api/todos');
                todos = await todoResp.json();

                // Load Patients
                const patientResp = await fetch('/api/patients');
                patients = await patientResp.json();

                // Render patient list
                renderPatientList();
                renderTodoList();

            } catch (error) {
                console.error('Error loading data:', error);
            }
        }

        function renderPatientList() {
            const container = document.getElementById('patientListContainer');
            container.innerHTML = '';

            patients.forEach((patient, index) => {
                const div = document.createElement('div');
                div.className = 'patient-item';
                div.innerHTML = `
                    <div class="patient-item-name">${patient.demographics.name}</div>
                    <div class="patient-item-info">Age ${patient.demographics.age}, ${patient.demographics.gender}</div>
                `;
                div.onclick = () => selectPatient(index);
                container.appendChild(div);
            });
        }

        async function selectPatient(index) {
            selectedPatientIndex = index;
            selectedPatient = patients[index];
            selectedTodo = null; // Reset task selection

            // Update UI
            document.querySelectorAll('.patient-item').forEach((item, i) => {
                item.classList.toggle('selected', i === index);
            });

            document.getElementById('tasksSubheader').textContent =
                `Tasks for ${selectedPatient.demographics.name}`;

            updateEditButton();
            updateLoadButton();

            // Check which tasks have cached assistance for this patient
            await checkCachedTasks();

            // Re-render todo list with cache indicators
            renderTodoList();
        }

        async function checkCachedTasks() {
            try {
                const response = await fetch('/api/check-cached-tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        patient_index: selectedPatientIndex
                    })
                });
                const data = await response.json();
                cachedTasks = new Set(data.cached_task_ids || []);
            } catch (error) {
                console.error('Error checking cached tasks:', error);
                cachedTasks = new Set();
            }
        }

        function renderTodoList() {
            const container = document.getElementById('todoListContainer');
            container.innerHTML = '';

            if (!selectedPatient) {
                container.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b; font-size: 13px;">Select a patient to view tasks</div>';
                return;
            }

            // Group tasks by priority
            const priorityOrder = ['P0', 'P1', 'P2', 'P3'];
            const groupedTodos = {};
            priorityOrder.forEach(priority => {
                groupedTodos[priority] = todos.filter(t => t.priority === priority);
            });

            // Render grouped tasks
            priorityOrder.forEach(priority => {
                if (groupedTodos[priority].length > 0) {
                    // Priority header
                    const header = document.createElement('div');
                    header.className = 'category-header';
                    header.textContent = `Priority ${priority}`;
                    container.appendChild(header);

                    // Tasks in this priority
                    groupedTodos[priority].forEach(todo => {
                        const isCached = cachedTasks.has(todo.id);
                        const div = document.createElement('div');
                        div.className = 'todo-item' + (isCached ? ' cached' : '');
                        div.innerHTML = `
                            <div style="flex: 1;">
                                <span class="todo-item-title">${todo.name}</span>
                                ${isCached ? '<span class="cached-badge">&#10003; Cached</span>' : ''}
                            </div>
                            <span class="priority-badge priority-${todo.priority.toLowerCase()}">${todo.priority}</span>
                        `;
                        div.onclick = () => selectTodoFromList(todo);
                        container.appendChild(div);
                    });
                }
            });
        }

        async function selectTodoFromList(todo) {
            selectedTodo = todo;
            updateLoadButton();

            // Highlight in list
            document.querySelectorAll('.todo-item').forEach(item => {
                item.classList.remove('selected');
            });
            event.currentTarget.classList.add('selected');

            // Load protocol immediately (no LLM call)
            await loadProtocolView();
        }

        async function loadProtocolView() {
            if (!selectedTodo || !selectedPatient) return;

            try {
                const response = await fetch('/api/get-protocol', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        todo_id: selectedTodo.id,
                        patient_index: selectedPatientIndex
                    })
                });

                const data = await response.json();

                if (data.error) {
                    showError(data.error);
                } else {
                    renderProtocolOnlyView(data);
                }

            } catch (error) {
                showError('Failed to load protocol: ' + error.message);
            }
        }

        // Event listeners
        // (Task Assistance button is now in the detail view, not in sidebar)

        function updateLoadButton() {
            // No longer needed - button is in detail view
        }

        async function loadDetailView(forceRefresh = false) {
            if (!selectedTodo || !selectedPatient) return;

            // Show loading overlay with appropriate message
            const loadingText = document.getElementById('loadingText');
            const loadingSubtext = document.getElementById('loadingSubtext');

            if (forceRefresh) {
                loadingText.textContent = 'Generating fresh AI insights...';
                loadingSubtext.textContent = 'This may take 10-20 seconds';
            } else {
                loadingText.textContent = 'Loading Task Assistance...';
                loadingSubtext.textContent = 'Checking for cached data...';
            }

            document.getElementById('loadingOverlay').style.display = 'flex';

            try {
                const userRole = document.getElementById('roleSelect').value;
                const response = await fetch('/api/generate-detail', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        todo_id: selectedTodo.id,
                        patient_index: selectedPatientIndex,
                        user_role: userRole,
                        refresh: forceRefresh
                    })
                });

                const data = await response.json();

                if (data.error) {
                    showError(data.error);
                } else {
                    renderDetailView(data);

                    // Refresh cached tasks list after generating new assistance
                    if (!data.from_cache) {
                        await checkCachedTasks();
                        renderTodoList();
                    }
                }

            } catch (error) {
                showError('Failed to generate detail view: ' + error.message);
            } finally {
                document.getElementById('loadingOverlay').style.display = 'none';
            }
        }

        function renderDetailView(detail) {
            const mainContent = document.getElementById('mainContent');
            const initial = detail.patient_initial || detail.patient_name.charAt(0);

            // Store messages for editing
            currentMessages = detail.suggested_messages || [];

            mainContent.innerHTML = `
                <div class="detail-view">
                    <!-- Header -->
                    <div class="detail-header">
                        <div class="detail-title-section">
                            <div class="detail-title">${escapeHtml(detail.task_title)}</div>
                            <div class="patient-info">
                                <div class="patient-avatar">${initial}</div>
                                <span class="patient-name">${escapeHtml(detail.patient_name)}</span>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span class="priority-badge priority-${detail.priority.toLowerCase()}">${detail.priority}</span>
                        </div>
                    </div>

                    <!-- Regenerate Button -->
                    <div style="padding: 0 32px; margin-bottom: 24px;">
                        <button class="refresh-button" onclick="refreshTaskAssistance()" title="Regenerate Task Assistance with fresh AI insights">
                            &#128260; Regenerate Task Assistance
                        </button>
                        <div style="font-size: 12px; color: #64748b; margin-top: 8px; text-align: center;">
                            Generate new AI insights with latest data
                        </div>
                    </div>

                    <!-- Verily Intelligence Section -->
                    <div class="section-card">
                        <div class="section-header">
                            <span class="section-icon">&#10024;</span>
                            <span class="section-title">Verily Intelligence</span>
                            <span class="beta-badge">BETA</span>
                        </div>

                        ${detail.from_cache ? `
                            <div style="background: #dbeafe; border-left: 4px solid #3b82f6; padding: 10px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 12px; color: #1e40af;">
                                &#128194; Loaded from cache (generated ${detail.cached_timestamp ? new Date(detail.cached_timestamp).toLocaleString() : 'previously'})
                            </div>
                        ` : ''}
                        ${detail.saved_filepath && !detail.from_cache ? `
                            <div style="background: #d1fae5; border-left: 4px solid #10b981; padding: 10px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 12px; color: #065f46;">
                                &#128190; Generated and saved to: <code style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px;">${escapeHtml(detail.saved_filepath)}</code>
                            </div>
                        ` : ''}

                        ${detail.user_context ? `
                            <div style="background: #f3f4f6; border-left: 4px solid #6b7280; padding: 10px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 12px; color: #374151;">
                                &#128100; <strong>Viewing as:</strong> ${escapeHtml(detail.user_context.role)}
                                ${detail.user_context.role === 'RN' ? '(Registered Nurse)' :
                                  detail.user_context.role === 'HC' ? '(Health Coach)' :
                                  detail.user_context.role === 'RD' ? '(Registered Dietitian)' :
                                  detail.user_context.role === 'PharmD' ? '(Pharmacist)' : ''}
                                | &#128203; <strong>Protocol variant:</strong> ${detail.user_context.clinic_context === 'Clinic' ? 'Clinic Steps' : detail.user_context.clinic_context === 'Non-Clinic' ? 'Non-Clinic Steps' : 'General Steps'}
                            </div>
                        ` : ''}

                        <!-- Confidence Handling -->
                        ${detail.confidence && detail.confidence.decision === 'suppress' ? `
                            <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; border-radius: 6px; margin-bottom: 16px;">
                                <div style="font-weight: 600; color: #991b1b; margin-bottom: 8px; font-size: 14px;">
                                    &#9888; Summary Suppressed - Manual Review Required
                                </div>
                                <div style="color: #7f1d1d; font-size: 13px; line-height: 1.5;">
                                    ${escapeHtml(detail.confidence.suppression_reason)}
                                </div>
                                <div style="margin-top: 12px; font-size: 12px; color: #991b1b; font-weight: 500;">
                                    Please rely on existing clinical UIs and manual chart review for this task.
                                </div>
                            </div>
                        ` : ''}

                        ${detail.confidence && detail.confidence.decision === 'show' && detail.confidence.caveats && detail.confidence.caveats.length > 0 ? `
                            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px;">
                                <div style="font-weight: 600; color: #92400e; margin-bottom: 8px; font-size: 13px;">
                                    &#9889; Data Quality Notes
                                </div>
                                ${detail.confidence.caveats.map(caveat => `
                                    <div style="color: #78350f; font-size: 12px; line-height: 1.5; margin-bottom: 6px;">
                                        • ${escapeHtml(caveat)}
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}

                        <div style="font-size: 12px; color: #64748b; margin-bottom: 16px;">
                            <strong>Note:</strong> Verily Intelligence (VI) is not a substitute for your clinical judgement.
                            It cannot reference any information outside the Console. Do not use VI for diagnoses or medical decisions.
                        </div>

                        ${detail.confidence && detail.confidence.decision === 'show' ? `
                            <div style="font-weight: 600; margin-bottom: 12px; color: #1e293b;">
                                Context for "${escapeHtml(detail.task_title)}"
                            </div>
                        ` : detail.confidence && detail.confidence.decision === 'suppress' ? `
                            <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 12px;">&#128203;</div>
                                <div style="font-weight: 600; color: #6b7280; margin-bottom: 8px;">
                                    Summary Not Available
                                </div>
                                <div style="color: #9ca3af; font-size: 13px;">
                                    Please review the protocol document and patient chart directly.
                                </div>
                            </div>
                        ` : `
                            <div style="font-weight: 600; margin-bottom: 12px; color: #1e293b;">
                                Context for "${escapeHtml(detail.task_title)}"
                            </div>
                        `}

                        ${detail.confidence && detail.confidence.decision === 'show' || !detail.confidence ? `
                        <div style="font-size: 13px; color: #64748b; margin-bottom: 16px;">
                            As of: ${new Date().toLocaleString()}
                        </div>

                        <!-- AI Insight -->
                        <div class="ai-insight-box">
                            <div class="ai-insight-header">AI Insight</div>
                            <div class="ai-insight-text">${escapeHtml(detail.ai_insight.summary)}</div>
                            ${detail.ai_insight.key_points && detail.ai_insight.key_points.length > 0 ? `
                                <div class="key-points">
                                    ${detail.ai_insight.key_points.map(point => `
                                        <div class="key-point">${escapeHtml(point)}</div>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>

                        <!-- Participant Overview -->
                        <div style="font-weight: 600; margin: 20px 0 12px 0; color: #1e293b;">
                            Participant overview
                        </div>
                        <ul class="overview-list">
                            ${detail.participant_overview.conditions.map(c =>
                                `<li class="overview-item">Condition(s): ${escapeHtml(c)}</li>`
                            ).join('')}
                            ${detail.participant_overview.devices.map(d =>
                                `<li class="overview-item">Device(s): ${escapeHtml(d)}</li>`
                            ).join('')}
                            <li class="overview-item">
                                Clinic status:
                                <span class="clinic-badge clinic-badge-${detail.participant_overview.clinic_member.toLowerCase()}">
                                    ${detail.participant_overview.clinic_member === 'Yes' ? '&#127973; Clinic Member' : '&#127968; Non-Clinic'}
                                </span>
                            </li>
                            ${detail.participant_overview.insulin_strategy ?
                                `<li class="overview-item">Insulin strategy: ${escapeHtml(detail.participant_overview.insulin_strategy)}</li>`
                                : ''}
                        </ul>

                        <!-- Clinical Incident Timeline -->
                        ${detail.clinical_incident ? `
                            <div style="font-weight: 600; margin: 20px 0 12px 0; color: #1e293b;">
                                ${escapeHtml(detail.clinical_incident.title)}
                            </div>
                            <table class="timeline-table">
                                <thead>
                                    <tr>
                                        <th>Action</th>
                                        <th>Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${detail.clinical_incident.timeline.map(event => `
                                        <tr>
                                            <td>${escapeHtml(event.action)}</td>
                                            <td>${escapeHtml(event.details)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        ` : ''}
                    </div>

                    <!-- Clinical Assessment -->
                    ${detail.clinical_assessment ? `
                        <div class="section-card">
                            <div class="section-header">
                                <span class="section-icon">&#128202;</span>
                                <span class="section-title">Clinical Assessment</span>
                            </div>
                            <div class="info-grid">
                                <div class="info-item">
                                    <div class="info-label">Severity</div>
                                    <div class="info-value">${escapeHtml(detail.clinical_assessment.severity)}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Urgency</div>
                                    <div class="info-value">${escapeHtml(detail.clinical_assessment.urgency)}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Trends</div>
                                    <div class="info-value">${escapeHtml(detail.clinical_assessment.trends)}</div>
                                </div>
                            </div>
                            ${detail.clinical_assessment.contributing_factors && detail.clinical_assessment.contributing_factors.length > 0 ? `
                                <div style="margin-top: 16px;">
                                    <div style="font-weight: 600; margin-bottom: 8px; color: #475569;">Contributing Factors:</div>
                                    <ul class="overview-list">
                                        ${detail.clinical_assessment.contributing_factors.map(f =>
                                            `<li class="overview-item">${escapeHtml(f)}</li>`
                                        ).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        </div>
                    ` : ''}


                    <!-- Protocol Reference -->
                    ${detail.protocol ? renderProtocolReference(detail.protocol) : ''}

                    <!-- Suggested Messages -->
                    ${detail.suggested_messages && detail.suggested_messages.length > 0 ? `
                        <div class="section-card">
                            <div class="section-header">
                                <span class="section-icon">&#128172;</span>
                                <span class="section-title">Suggested Messages</span>
                            </div>
                            ${detail.suggested_messages.map((msg, idx) => `
                                <div class="message-card">
                                    <div class="message-header">
                                        <span class="message-category">${escapeHtml(msg.category)}</span>
                                        <div style="display: flex; gap: 8px; align-items: center;">
                                            <span class="message-type">${escapeHtml(msg.type.replace('_', ' '))}</span>
                                            <button class="message-action-button" onclick="copyMessage(${idx})" title="Copy to clipboard">
                                                &#128203;
                                            </button>
                                            <button class="message-action-button" onclick="editAndSendMessage(${idx})" title="Edit and send message">
                                                &#9999;
                                            </button>
                                        </div>
                                    </div>
                                    <div class="message-text" id="message-text-${idx}">${escapeHtml(msg.message)}</div>
                                    <div class="message-rationale">Rationale: ${escapeHtml(msg.rationale)}</div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <!-- Protocol Steps -->
                    ${detail.protocol_steps && detail.protocol_steps.length > 0 ? `
                        <div class="section-card">
                            <div class="section-header">
                                <span class="section-icon">&#128203;</span>
                                <span class="section-title">Protocol Steps</span>
                            </div>
                            ${detail.protocol_steps.map((step, idx) => `
                                <div class="protocol-step">
                                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;">
                                        <div style="flex: 1;">
                                            <strong>Step ${idx + 1}:</strong> ${escapeHtml(step)}
                                        </div>
                                        <button class="step-assistance-button-small" onclick="requestStepAssistance(${idx}, '${escapeHtml(step).replace(/'/g, "\\'")}')" title="Get AI assistance for this step">
                                            &#129302; Assist
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    ` : ''}
                </div>
            `;

            // Scroll to top
            mainContent.scrollTop = 0;
        }

        function renderProtocolOnlyView(data) {
            const mainContent = document.getElementById('mainContent');
            const initial = data.patient_name.charAt(0);

            const hasCached = data.has_cached_assistance;
            const buttonText = hasCached ? '&#10003; Load Cached Task Assistance' : '&#129302; Generate Task Assistance';
            const buttonStyle = hasCached ? 'background: #10b981;' : 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);';

            mainContent.innerHTML = `
                <div class="detail-view">
                    <!-- Header -->
                    <div class="detail-header">
                        <div class="detail-title-section">
                            <div class="detail-title">${escapeHtml(data.task_title)}</div>
                            <div class="patient-info">
                                <div class="patient-avatar">${initial}</div>
                                <span class="patient-name">${escapeHtml(data.patient_name)}</span>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span class="priority-badge priority-${data.priority.toLowerCase()}">${data.priority}</span>
                        </div>
                    </div>

                    <!-- Task Assistance Button -->
                    <div style="padding: 0 32px; margin-bottom: 24px;">
                        <button class="load-button" onclick="loadDetailView(false)" style="${buttonStyle}">
                            ${buttonText}
                        </button>
                        <div style="font-size: 12px; color: #64748b; margin-top: 8px; text-align: center;">
                            ${hasCached ? '&#128190; Previously generated - loads instantly' : '&#9200; Will generate AI insights (10-20 seconds)'}
                        </div>
                    </div>

                    <!-- Protocol Reference -->
                    ${data.protocol ? renderProtocolReference(data.protocol) : ''}
                </div>
            `;

            // Auto-expand protocol
            setTimeout(() => {
                const content = document.getElementById('protocolContent');
                const icon = document.getElementById('protocolIcon');
                if (content && icon) {
                    content.classList.add('open');
                    icon.classList.add('open');
                }
            }, 100);

            // Scroll to top
            mainContent.scrollTop = 0;
        }

        function showError(message) {
            const mainContent = document.getElementById('mainContent');
            mainContent.innerHTML = `
                <div class="error-message">
                    <strong>Error:</strong> ${escapeHtml(message)}
                </div>
            `;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }


        function parseMarkdownToHtml(text) {
            if (!text) return '';

            // Convert bold **text** first
            text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

            // Convert italic *text* (single asterisks that aren't part of bold)
            // Use a simpler approach: match single asterisks with non-asterisk content
            text = text.replace(/\*([^*]+?)\*/g, function(match, content) {
                // If it contains a strong tag, it was already processed as bold, skip it
                if (content.includes('<strong>') || content.includes('</strong>')) {
                    return match;
                }
                return '<span class="protocol-message-template">' + content + '</span>';
            });

            // Convert links [text](url)
            text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

            // Convert escaped characters
            text = text.replace(/\\>/g, '&gt;');
            text = text.replace(/\\</g, '&lt;');

            return text;
        }

        function formatProtocolCell(text) {
            if (!text) return '';

            // First check if it starts with a role indicator (HC, RN, RD, PharmD)
            const roleMatch = text.match(/^(HC|RN|RD|PharmD)\s+(.+)$/s);
            let rolePrefix = '';
            if (roleMatch) {
                rolePrefix = '<strong>' + roleMatch[1] + '</strong><br/>';
                text = roleMatch[2];
            }

            // Parse markdown
            text = parseMarkdownToHtml(text);

            // Handle special cases: single line or very short text
            if (!text.includes('  ') && text.length < 100) {
                return rolePrefix + text;
            }

            // Split into segments by common delimiters
            // Use double space as primary delimiter (from markdown)
            const segments = text.split(/\s{2,}/).map(s => s.trim()).filter(s => s);

            if (segments.length <= 1) {
                return rolePrefix + text;
            }

            // Build structured HTML with bullets
            let html = '';
            if (rolePrefix) html += rolePrefix;

            html += '<ul>';

            for (let segment of segments) {
                // Check for nested structures like "No patient case needed if:" or "Yes patient case needed:"
                if (segment.match(/^(No|Yes)\s+patient case/i)) {
                    html += '<li><strong>' + segment.split(':')[0] + ':</strong>';

                    // Extract nested items after the colon
                    const afterColon = segment.substring(segment.indexOf(':') + 1).trim();
                    if (afterColon) {
                        // Split nested items
                        const nestedItems = afterColon.split(/(?=Participant |If a participant |If single )/);
                        if (nestedItems.length > 1) {
                            html += '<ul>';
                            nestedItems.forEach(item => {
                                item = item.trim();
                                if (item) html += '<li>' + item + '</li>';
                            });
                            html += '</ul>';
                        } else {
                            html += ' ' + afterColon;
                        }
                    }

                    html += '</li>';
                } else {
                    // Regular bullet point
                    html += '<li>' + segment + '</li>';
                }
            }

            html += '</ul>';
            return html;
        }

        function renderProtocolReference(protocol) {
            if (!protocol) return '';

            // Parse the markdown table from full_text
            let tableHtml = '';
            if (protocol.full_text) {
                const lines = protocol.full_text.split('\\n').filter(line => line.trim());

                // Skip first line (header row) and second line (separator)
                const rows = lines.slice(2);

                tableHtml = '<table class="protocol-table">';

                // Add header row
                tableHtml += '<tr><th>' + escapeHtml(protocol.task_code) + '</th><th>' +
                            parseMarkdownToHtml(protocol.task_name) + '</th></tr>';

                // Process remaining rows
                for (let row of rows) {
                    if (!row.trim() || row.includes('----')) continue;

                    // Split by pipe, remove first and last empty elements
                    const cells = row.split('|').map(c => c.trim()).filter((c, i, arr) => i !== 0 && i !== arr.length - 1);

                    if (cells.length >= 2) {
                        const label = cells[0];
                        const value = cells[1];

                        tableHtml += '<tr>';
                        tableHtml += '<td>' + parseMarkdownToHtml(label) + '</td>';
                        tableHtml += '<td>' + formatProtocolCell(value) + '</td>';
                        tableHtml += '</tr>';
                    }
                }

                tableHtml += '</table>';
            }

            return '<div class="protocol-accordion">' +
                '<div class="protocol-accordion-header" onclick="toggleProtocol()">' +
                '<div class="protocol-accordion-title">' +
                '<span class="section-icon">&#128214;</span>' +
                '<span>Clinical Protocol Reference</span>' +
                '</div>' +
                '<span class="protocol-accordion-icon" id="protocolIcon">&#9660;</span>' +
                '</div>' +
                '<div class="protocol-accordion-content" id="protocolContent">' +
                '<div class="protocol-content">' +
                tableHtml +
                '</div>' +
                '</div>' +
                '</div>';
        }

        function toggleProtocol() {
            const content = document.getElementById('protocolContent');
            const icon = document.getElementById('protocolIcon');

            if (content.classList.contains('open')) {
                content.classList.remove('open');
                icon.classList.remove('open');
            } else {
                content.classList.add('open');
                icon.classList.add('open');
            }
        }

        function scrollToProtocolSteps() {
            const stepsSection = document.querySelector('.section-card:last-child');
            if (stepsSection) {
                stepsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }

        function refreshTaskAssistance() {
            // Force regeneration by passing refresh flag
            loadDetailView(true);
        }

        // Store current messages for editing
        let currentMessages = [];

        function copyMessage(messageIndex) {
            const messageText = currentMessages[messageIndex].message;

            // Copy to clipboard
            navigator.clipboard.writeText(messageText).then(() => {
                // Show temporary success feedback
                const button = event.currentTarget;
                const originalText = button.innerHTML;
                button.innerHTML = '&#10003;';
                button.style.background = '#d1fae5';
                button.style.borderColor = '#10b981';

                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.style.background = '#f1f5f9';
                    button.style.borderColor = '#cbd5e1';
                }, 1500);
            }).catch(err => {
                console.error('Failed to copy:', err);
                alert('Failed to copy message to clipboard');
            });
        }

        function editAndSendMessage(messageIndex) {
            const message = currentMessages[messageIndex];

            // Create modal
            const modal = document.createElement('div');
            modal.className = 'message-editor-modal';
            modal.onclick = (e) => {
                if (e.target === modal) {
                    closeMessageEditor();
                }
            };
            modal.innerHTML = `
                <div class="message-editor-content" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h3 class="modal-title">Edit Message</h3>
                        <button class="modal-close" onclick="closeMessageEditor()">&times;</button>
                    </div>
                    <div class="message-editor-body">
                        <div style="margin-bottom: 12px;">
                            <div style="font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 4px;">
                                Category: <span style="color: #3b82f6;">${escapeHtml(message.category)}</span>
                            </div>
                            <div style="font-size: 12px; color: #64748b; margin-bottom: 12px;">
                                ${escapeHtml(message.rationale)}
                            </div>
                        </div>
                        <textarea id="messageEditorText" class="message-editor-textarea" placeholder="Edit your message here...">${escapeHtml(message.message)}</textarea>
                        <div class="char-counter">
                            <span id="charCount">${message.message.length}</span> characters
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="closeMessageEditor()">Cancel</button>
                        <button class="btn btn-secondary" onclick="copyEditedMessage()">&#128203; Copy</button>
                        <button class="btn btn-primary" onclick="sendMessage()">&#128228; Send Message</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // Add escape key listener
            const escapeListener = (e) => {
                if (e.key === 'Escape') {
                    closeMessageEditor();
                }
            };
            document.addEventListener('keydown', escapeListener);
            modal.setAttribute('data-has-listener', 'true');

            // Focus textarea
            setTimeout(() => {
                const textarea = document.getElementById('messageEditorText');
                textarea.focus();
                textarea.setSelectionRange(textarea.value.length, textarea.value.length);

                // Add character counter
                textarea.addEventListener('input', () => {
                    document.getElementById('charCount').textContent = textarea.value.length;
                });
            }, 100);
        }

        function closeMessageEditor() {
            const modal = document.querySelector('.message-editor-modal');
            if (modal) {
                // Remove escape key listener
                const escapeListener = (e) => {
                    if (e.key === 'Escape') {
                        closeMessageEditor();
                    }
                };
                document.removeEventListener('keydown', escapeListener);

                modal.remove();
            }
        }

        function copyEditedMessage() {
            const textarea = document.getElementById('messageEditorText');
            const messageText = textarea.value;

            navigator.clipboard.writeText(messageText).then(() => {
                // Show success in button
                const button = event.currentTarget;
                const originalText = button.innerHTML;
                button.innerHTML = '&#10003; Copied';
                button.style.background = '#d1fae5';
                button.style.color = '#065f46';

                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.style.background = '#f1f5f9';
                    button.style.color = '#475569';
                }, 1500);
            }).catch(err => {
                console.error('Failed to copy:', err);
                alert('Failed to copy message');
            });
        }

        function sendMessage() {
            const textarea = document.getElementById('messageEditorText');
            const messageText = textarea.value;

            if (!messageText.trim()) {
                alert('Message cannot be empty');
                return;
            }

            // TODO: Integrate with your messaging system
            // For now, just show a success message
            alert('Message ready to send:\\n\\n' + messageText + '\\n\\n(Integration with messaging system pending)');

            closeMessageEditor();
        }

        function requestStepAssistance(stepIndex, stepText) {
            // TODO: Implement AI agent assistance for protocol steps
            const stepNumber = stepIndex + 1;
            alert('Step Assistance for Step ' + stepNumber + ':\\n\\n' + stepText + '\\n\\n(AI agent integration pending)');

            // When integrated, this will:
            // - Send step text + patient context to AI agent
            // - Get guidance on executing this specific step
            // - Show suggested actions, messages, or chart updates
        }


        // Patient Editor Functions
        let editingPatientIndex = null;

        function updateEditButton() {
            const btn = document.getElementById('editPatientBtn');
            const lastModDiv = document.getElementById('lastModified');

            btn.disabled = selectedPatient === null;

            if (selectedPatient && selectedPatient.metadata && selectedPatient.metadata.last_modified) {
                const date = new Date(selectedPatient.metadata.last_modified);
                lastModDiv.textContent = `Last edited: ${date.toLocaleString()}`;
                lastModDiv.style.display = 'block';
            } else {
                lastModDiv.style.display = 'none';
            }
        }

        document.getElementById('editPatientBtn').addEventListener('click', openPatientEditor);

        async function openPatientEditor() {
            if (!selectedPatient) return;

            editingPatientIndex = patients.indexOf(selectedPatient);

            // Fetch full patient data from server
            try {
                const response = await fetch(`/api/patient/${editingPatientIndex}`);
                const fullPatient = await response.json();

                const editor = document.getElementById('patientDataEditor');
                editor.value = JSON.stringify(fullPatient, null, 2);

                document.getElementById('patientEditorModal').style.display = 'flex';
                document.getElementById('saveSuccess').style.display = 'none';
            } catch (error) {
                alert('Error loading patient data: ' + error.message);
            }
        }

        function closePatientEditor() {
            document.getElementById('patientEditorModal').style.display = 'none';
            editingPatientIndex = null;
        }

        async function savePatientData() {
            const editor = document.getElementById('patientDataEditor');

            try {
                // Parse and validate JSON
                const updatedPatient = JSON.parse(editor.value);

                // Save to backend
                const response = await fetch('/api/save-patient', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        patient_index: editingPatientIndex,
                        patient_data: updatedPatient
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Update local data
                    patients[editingPatientIndex] = updatedPatient;
                    selectedPatient = updatedPatient;

                    // Show success message
                    document.getElementById('saveSuccess').style.display = 'block';

                    // Update last modified display
                    updateEditButton();

                    // Auto-close after 2 seconds
                    setTimeout(() => {
                        closePatientEditor();
                    }, 2000);
                } else {
                    alert('Error saving patient: ' + result.error);
                }

            } catch (error) {
                alert('Invalid JSON format. Please check your syntax. ' + error.message);
            }
        }

        // Load data on page load
        window.addEventListener('load', loadInitialData);
    </script>

    <!-- Patient Editor Modal -->
    <div id="patientEditorModal" class="modal-overlay" style="display: none;">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Edit Patient Chart</h3>
                <button class="modal-close" onclick="closePatientEditor()">&times;</button>
            </div>
            <div class="modal-body">
                <div id="saveSuccess" class="success-message" style="display: none;">
                    &#10003; Patient chart saved successfully!
                </div>
                <p style="margin-bottom: 12px; color: #64748b; font-size: 13px;">
                    Edit the patient chart data below. Changes are saved to <code>synthetic_patients.json</code>.
                </p>
                <textarea id="patientDataEditor" class="patient-editor"></textarea>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closePatientEditor()">Cancel</button>
                <button class="btn btn-primary" onclick="savePatientData()">&#128190; Save Changes</button>
            </div>
        </div>
    </div>

    <!-- Message Editor Modal will be dynamically created -->

</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/todos')
def get_todos():
    """Get list of ToDos"""
    return jsonify(TODOS)

@app.route('/api/patients')
def get_patients():
    """Get list of patients"""
    # Return simplified patient list for dropdown
    return jsonify([{
        'demographics': p['demographics']
    } for p in PATIENTS])

@app.route('/api/generate-detail', methods=['POST'])
def generate_detail():
    """Generate AI-powered detail view"""
    try:
        data = request.json
        todo_id = data.get('todo_id')
        patient_index = data.get('patient_index')
        refresh = data.get('refresh', False)
        user_role = data.get('user_role', 'RN')  # Default to RN if not specified

        # Ensure refresh is actually a boolean
        if isinstance(refresh, dict):
            refresh = False
        refresh = bool(refresh)

        if todo_id is None or patient_index is None:
            return jsonify({'error': 'Missing todo_id or patient_index'}), 400

        print(f"📋 Request for Task Assistance: {todo_id}, patient {patient_index}, role={user_role}, refresh={refresh}")

        # Check for cached data first, unless refresh is requested
        if not refresh:
            cached_data = load_task_assistance(todo_id, patient_index)
            if cached_data:
                filename = get_task_assistance_filename(todo_id, patient_index)
                filepath = str(OUTPUT_DIR / filename)
                print(f"✓ Cache HIT! Using cached Task Assistance from {filepath}")
                result = cached_data['detail_view'].copy()
                result['from_cache'] = True
                result['cached_timestamp'] = cached_data['timestamp']
                result['saved_filepath'] = filepath
                return jsonify(result)
            else:
                print(f"⚠️  Cache MISS - no cached file found for {todo_id}, patient {patient_index}")

        print(f"⚡ Generating NEW Task Assistance with LLM call...")

        # Get patient data
        patient = PATIENTS[patient_index]

        # Search protocol in Pinecone by task code
        protocol_results = protocol_index.search(
            namespace="protocols",
            query={
                "top_k": 1,
                "inputs": {"text": f"task code {todo_id}"},
                "filter": {"task_code": {"$eq": todo_id}}
            }
        )

        # Get protocol data
        if protocol_results['result']['hits']:
            protocol = protocol_results['result']['hits'][0]['fields']
        else:
            # Fallback - search without filter
            protocol_results = protocol_index.search(
                namespace="protocols",
                query={
                    "top_k": 1,
                    "inputs": {"text": todo_id}
                }
            )
            protocol = protocol_results['result']['hits'][0]['fields'] if protocol_results['result']['hits'] else {}

        # Get clinic context from patient data
        clinic_member = patient.get('participant_overview', {}).get('clinic_member', 'Unknown')
        clinic_context = "Clinic" if clinic_member == "Yes" else "Non-Clinic" if clinic_member == "No" else "Unknown"

        # Prepare LLM prompt
        llm_prompt = f"""
{DETAIL_VIEW_PROMPT}

## User Context:
Role: {user_role} (HC=Health Coach, RN=Registered Nurse, RD=Registered Dietitian, PharmD=Pharmacist)
Patient Clinic Status: {clinic_context} (clinic_member: {clinic_member})

IMPORTANT: Based on the clinic status above, select the appropriate protocol variant:
- If "{clinic_context}" is "Clinic", follow "Steps (clinic)" variant
- If "{clinic_context}" is "Non-Clinic", follow "Steps (non_clinic)" variant
- If only "Steps (general)" exists, use that variant

## Patient Chart Data:
{json.dumps(patient, indent=2)}

## Protocol Data:
Task Code: {protocol.get('task_code', 'N/A')}
Task Name: {protocol.get('task_name', 'N/A')}
Priority: {protocol.get('priority', 'N/A')}
Content: {protocol.get('content', 'N/A')}

Generate the detailed clinical view now in JSON format.
"""

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a clinical AI assistant. Generate comprehensive, patient-specific clinical detail views in valid JSON format."},
                {"role": "user", "content": llm_prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )

        # Parse response
        detail_view = json.loads(response.choices[0].message.content)


        # Include protocol in response
        detail_view['protocol'] = {
            'task_code': protocol.get('task_code', 'N/A'),
            'task_name': protocol.get('task_name', 'N/A'),
            'priority': protocol.get('priority', 'N/A'),
            'content': protocol.get('content', 'N/A'),
            'full_text': protocol.get('full_text', '')
        }

        # Include user context metadata
        detail_view['user_context'] = {
            'role': user_role,
            'clinic_context': clinic_context,
            'clinic_member': clinic_member
        }

        # Save task assistance output to file
        patient_name = patient['demographics']['name']
        saved_filepath = save_task_assistance(todo_id, patient_index, patient_name, detail_view)
        detail_view['saved_filepath'] = saved_filepath

        return jsonify(detail_view)


    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/save-patient', methods=['POST'])
def save_patient():
    """Save updated patient data"""
    try:
        data = request.json
        patient_index = data.get('patient_index')
        patient_data = data.get('patient_data')

        if patient_index is None or patient_data is None:
            return jsonify({'success': False, 'error': 'Missing data'}), 400

        # Load current patients
        patients = load_patients()

        # Update the patient
        patients[patient_index] = patient_data

        # Save back to file
        timestamp = save_patients(patients)

        # Reload global PATIENTS
        global PATIENTS
        PATIENTS = patients

        return jsonify({
            'success': True,
            'timestamp': timestamp
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patient/<int:patient_index>')
def get_patient(patient_index):
    """Get full patient data by index"""
    try:
        patients = load_patients()
        if patient_index < 0 or patient_index >= len(patients):
            return jsonify({'error': 'Invalid patient index'}), 404

        return jsonify(patients[patient_index])

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-cached-tasks', methods=['POST'])
def check_cached_tasks():
    """Check which tasks have cached assistance for a patient"""
    try:
        data = request.json
        patient_index = data.get('patient_index')

        if patient_index is None:
            return jsonify({'error': 'Missing patient_index'}), 400

        # Check which task files exist for this patient
        cached_task_ids = []
        for todo in TODOS:
            filename = get_task_assistance_filename(todo['id'], patient_index)
            filepath = OUTPUT_DIR / filename
            if filepath.exists():
                cached_task_ids.append(todo['id'])

        return jsonify({'cached_task_ids': cached_task_ids})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-protocol', methods=['POST'])
def get_protocol():
    """Get protocol data for a task without generating AI assistance"""
    try:
        data = request.json
        todo_id = data.get('todo_id')
        patient_index = data.get('patient_index')

        if todo_id is None or patient_index is None:
            return jsonify({'error': 'Missing todo_id or patient_index'}), 400

        # Get task info
        todo = next((t for t in TODOS if t['id'] == todo_id), None)
        if not todo:
            return jsonify({'error': 'Task not found'}), 404

        # Get patient data
        patient = PATIENTS[patient_index]

        # Search protocol in Pinecone by task code
        protocol_results = protocol_index.search(
            namespace="protocols",
            query={
                "top_k": 1,
                "inputs": {"text": f"task code {todo_id}"},
                "filter": {"task_code": {"$eq": todo_id}}
            }
        )

        # Get protocol data
        if protocol_results['result']['hits']:
            protocol = protocol_results['result']['hits'][0]['fields']
        else:
            # Fallback - search without filter
            protocol_results = protocol_index.search(
                namespace="protocols",
                query={
                    "top_k": 1,
                    "inputs": {"text": todo_id}
                }
            )
            protocol = protocol_results['result']['hits'][0]['fields'] if protocol_results['result']['hits'] else {}

        # Check if task assistance is cached
        cached_data = load_task_assistance(todo_id, patient_index)
        has_cached_assistance = cached_data is not None

        return jsonify({
            'task_id': todo_id,
            'task_name': todo['name'],
            'task_title': todo['name'],
            'priority': todo['priority'],
            'category': todo['category'],
            'patient_name': patient['demographics']['name'],
            'patient_index': patient_index,
            'protocol': {
                'task_code': protocol.get('task_code', 'N/A'),
                'task_name': protocol.get('task_name', 'N/A'),
                'priority': protocol.get('priority', 'N/A'),
                'content': protocol.get('content', 'N/A'),
                'full_text': protocol.get('full_text', '')
            },
            'has_cached_assistance': has_cached_assistance
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy'})

def open_browser():
    """Open browser after a delay"""
    import time
    time.sleep(1.5)
    webbrowser.open('http://localhost:5001')

if __name__ == '__main__':
    print("="*80)
    print("CLINICAL TODO VIEWER - AI-Powered Patient Analysis")
    print("="*80)
    print()
    print("Starting server...")
    print("Opening browser at http://localhost:5001")
    print()
    print("Features:")
    print(f"  ✓ {len(TODOS)} Clinical ToDos (Glucose, BP, A1C, Mental Health, Engagement, Surveys)")
    print(f"  ✓ {len(PATIENTS)} Synthetic Patients")
    print("  ✓ AI-Generated Task Assistance (OpenAI GPT-4)")
    print("  ✓ Protocol RAG Search (Pinecone)")
    print("  ✓ Task Assistance Caching (reuses previous generations)")
    print("  ✓ Patient Chart Editing & Persistence")
    print()
    print("Press Ctrl+C to stop the server")
    print("="*80)
    print()

    port = int(os.environ.get('PORT', 5001))

    # Open browser in background (only locally, not in production)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' and not os.environ.get('RAILWAY_ENVIRONMENT'):
        threading.Thread(target=open_browser, daemon=True).start()

    # Start Flask server
    app.run(debug=not os.environ.get('RAILWAY_ENVIRONMENT'), host='0.0.0.0', port=port)
