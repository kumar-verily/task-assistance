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
with open('synthetic_patients.json', 'r') as f:
    PATIENTS = json.loads(f.read())

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

    # Hypertension
    {"id": "BP-104", "name": "Hypertension: BP > 160/100", "priority": "P1", "category": "Hypertension"},
    {"id": "BP-103", "name": "Hypertension: BP > 150/90", "priority": "P1", "category": "Hypertension"},
    {"id": "BP-102", "name": "Hypertension: BP > 140/90", "priority": "P1", "category": "Hypertension"},
    {"id": "BP-101", "name": "Hypertension: BP > 130/80", "priority": "P2", "category": "Hypertension"},

    # Note: Hypotension protocols not found in current dataset
    # Can be added when available by adding to this list
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

        /* Left Sidebar */
        .sidebar {
            width: 420px;
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

        /* Main Content Area */
        .main-content {
            flex: 1;
            overflow-y: auto;
            background: #f5f7fa;
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
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Left Sidebar -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h1>Clinical ToDo Viewer</h1>
                <p style="font-size: 13px; color: #64748b;">AI-Powered Patient Analysis</p>
            </div>

            <div class="pickers-section">
                <!-- ToDo Picker -->
                <div class="picker-group">
                    <div class="picker-label">Select ToDo</div>
                    <select id="todoSelect" class="picker-select">
                        <option value="">Choose a clinical ToDo...</option>
                    </select>
                </div>

                <!-- Patient Picker -->
                <div class="picker-group">
                    <div class="picker-label">Select Patient</div>
                    <select id="patientSelect" class="picker-select">
                        <option value="">Choose a patient...</option>
                    </select>
                </div>

                <button id="loadDetailBtn" class="load-button" disabled>
                    Load Detail View
                </button>

                <!-- ToDo List -->
                <div class="todo-list">
                    <div class="todo-list-header">Quick Access - Open ToDos</div>
                    <div id="todoListContainer"></div>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-content" id="mainContent">
            <div class="empty-state">
                <h2>👋 Welcome to Clinical ToDo Viewer</h2>
                <p>Select a ToDo and Patient from the left sidebar to view AI-powered clinical insights</p>
            </div>
        </div>
    </div>

    <!-- Loading Overlay -->
    <div id="loadingOverlay" class="loading-overlay" style="display: none;">
        <div class="loading-spinner"></div>
        <div class="loading-text">Generating AI insights...</div>
        <div style="font-size: 13px; color: #64748b; margin-top: 8px;">This may take 10-20 seconds</div>
    </div>

    <script>
        let todos = [];
        let patients = [];
        let selectedTodo = null;
        let selectedPatient = null;

        // Load initial data
        async function loadInitialData() {
            try {
                // Load ToDos
                const todoResp = await fetch('/api/todos');
                todos = await todoResp.json();

                // Load Patients
                const patientResp = await fetch('/api/patients');
                patients = await patientResp.json();

                // Populate dropdowns
                populateTodoSelect();
                populatePatientSelect();
                renderTodoList();

            } catch (error) {
                console.error('Error loading data:', error);
            }
        }

        function populateTodoSelect() {
            const select = document.getElementById('todoSelect');
            todos.forEach(todo => {
                const option = document.createElement('option');
                option.value = todo.id;
                option.textContent = `${todo.name} (${todo.priority})`;
                select.appendChild(option);
            });
        }

        function populatePatientSelect() {
            const select = document.getElementById('patientSelect');
            patients.forEach((patient, index) => {
                const option = document.createElement('option');
                option.value = index;
                option.textContent = patient.demographics.name;
                select.appendChild(option);
            });
        }

        function renderTodoList() {
            const container = document.getElementById('todoListContainer');
            container.innerHTML = '';

            // Show first 5 todos
            todos.slice(0, 5).forEach(todo => {
                const div = document.createElement('div');
                div.className = 'todo-item';
                div.innerHTML = `
                    <span class="todo-item-title">${todo.name}</span>
                    <span class="priority-badge priority-${todo.priority.toLowerCase()}">${todo.priority}</span>
                `;
                div.onclick = () => selectTodoFromList(todo);
                container.appendChild(div);
            });
        }

        function selectTodoFromList(todo) {
            // Update dropdown
            document.getElementById('todoSelect').value = todo.id;
            selectedTodo = todo;
            updateLoadButton();

            // Highlight in list
            document.querySelectorAll('.todo-item').forEach(item => {
                item.classList.remove('selected');
            });
            event.currentTarget.classList.add('selected');
        }

        // Event listeners
        document.getElementById('todoSelect').addEventListener('change', (e) => {
            const todoId = e.target.value;
            selectedTodo = todos.find(t => t.id === todoId);
            updateLoadButton();
        });

        document.getElementById('patientSelect').addEventListener('change', (e) => {
            const patientIndex = parseInt(e.target.value);
            selectedPatient = patients[patientIndex];
            updateLoadButton();
        });

        document.getElementById('loadDetailBtn').addEventListener('click', loadDetailView);

        function updateLoadButton() {
            const btn = document.getElementById('loadDetailBtn');
            btn.disabled = !(selectedTodo && selectedPatient);
        }

        async function loadDetailView() {
            if (!selectedTodo || !selectedPatient) return;

            // Show loading overlay
            document.getElementById('loadingOverlay').style.display = 'flex';

            try {
                const response = await fetch('/api/generate-detail', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        todo_id: selectedTodo.id,
                        patient_index: patients.indexOf(selectedPatient)
                    })
                });

                const data = await response.json();

                if (data.error) {
                    showError(data.error);
                } else {
                    renderDetailView(data);
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
                        <span class="priority-badge priority-${detail.priority.toLowerCase()}">${detail.priority}</span>
                    </div>

                    <!-- Verily Intelligence Section -->
                    <div class="section-card">
                        <div class="section-header">
                            <span class="section-icon">✨</span>
                            <span class="section-title">Verily Intelligence</span>
                            <span class="beta-badge">BETA</span>
                        </div>

                        <div style="font-size: 12px; color: #64748b; margin-bottom: 16px;">
                            <strong>Note:</strong> Verily Intelligence (VI) is not a substitute for your clinical judgement.
                            It cannot reference any information outside the Console. Do not use VI for diagnoses or medical decisions.
                        </div>

                        <div style="font-weight: 600; margin-bottom: 12px; color: #1e293b;">
                            Context for "${escapeHtml(detail.task_title)}"
                        </div>
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
                            <li class="overview-item">Clinic member: ${escapeHtml(detail.participant_overview.clinic_member)}</li>
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
                                <span class="section-icon">📊</span>
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

                    <!-- Suggested Messages -->
                    ${detail.suggested_messages && detail.suggested_messages.length > 0 ? `
                        <div class="section-card">
                            <div class="section-header">
                                <span class="section-icon">💬</span>
                                <span class="section-title">Suggested Messages</span>
                            </div>
                            ${detail.suggested_messages.map(msg => `
                                <div class="message-card">
                                    <div class="message-header">
                                        <span class="message-category">${escapeHtml(msg.category)}</span>
                                        <span class="message-type">${escapeHtml(msg.type.replace('_', ' '))}</span>
                                    </div>
                                    <div class="message-text">${escapeHtml(msg.message)}</div>
                                    <div class="message-rationale">Rationale: ${escapeHtml(msg.rationale)}</div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <!-- Protocol Steps -->
                    ${detail.protocol_steps && detail.protocol_steps.length > 0 ? `
                        <div class="section-card">
                            <div class="section-header">
                                <span class="section-icon">📋</span>
                                <span class="section-title">Protocol Steps</span>
                            </div>
                            ${detail.protocol_steps.map((step, idx) => `
                                <div class="protocol-step">
                                    <strong>Step ${idx + 1}:</strong> ${escapeHtml(step)}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `;

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

        // Load data on page load
        window.addEventListener('load', loadInitialData);
    </script>
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

        if todo_id is None or patient_index is None:
            return jsonify({'error': 'Missing todo_id or patient_index'}), 400

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

        # Prepare LLM prompt
        llm_prompt = f"""
{DETAIL_VIEW_PROMPT}

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

        return jsonify(detail_view)

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
    print("  ✓ 12 Clinical ToDos (Hyperglycemia, Hypoglycemia, Hypertension)")
    print(f"  ✓ {len(PATIENTS)} Synthetic Patients")
    print("  ✓ AI-Generated Detail Views (OpenAI GPT-4)")
    print("  ✓ Protocol RAG Search (Pinecone)")
    print()
    print("Press Ctrl+C to stop the server")
    print("="*80)
    print()

    # Open browser in background (only in main process, not in reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        threading.Thread(target=open_browser, daemon=True).start()

    # Start Flask server
    app.run(debug=True, host='0.0.0.0', port=5001)
