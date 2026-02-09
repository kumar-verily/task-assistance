#!/usr/bin/env python3
"""
Script to enhance todo_viewer.py with:
1. Patient chart editing and persistence
2. Protocol reference display

Run this to create todo_viewer_enhanced.py
"""

import re

# Read the original file
with open('todo_viewer.py', 'r') as f:
    content = f.read()

# ENHANCEMENT 1: Update imports and add patient management functions
imports_addition = """
from datetime import datetime
"""

# Insert after the existing imports
content = content.replace(
    "import webbrowser",
    "import webbrowser\nfrom datetime import datetime"
)

# ENHANCEMENT 2: Add patient file management functions
patient_mgmt_functions = """
# Patient file path
PATIENTS_FILE = 'synthetic_patients.json'

def load_patients():
    \"\"\"Load patients from file\"\"\"
    with open(PATIENTS_FILE, 'r') as f:
        return json.loads(f.read())

def save_patients(patients):
    \"\"\"Save patients to file with timestamp\"\"\"
    # Add last_modified timestamp
    timestamp = datetime.now().isoformat()
    for patient in patients:
        if 'metadata' not in patient:
            patient['metadata'] = {}
        patient['metadata']['last_modified'] = timestamp

    with open(PATIENTS_FILE, 'w') as f:
        json.dump(patients, f, indent=2)
    return timestamp

# Replace static PATIENTS loading with function
"""

# Replace the PATIENTS loading
content = content.replace(
    "# Load synthetic patients\nwith open('synthetic_patients.json', 'r') as f:\n    PATIENTS = json.loads(f.read())",
    "# Load synthetic patients\nPATIENTS_FILE = 'synthetic_patients.json'\n\ndef load_patients():\n    with open(PATIENTS_FILE, 'r') as f:\n        return json.loads(f.read())\n\ndef save_patients(patients):\n    timestamp = datetime.now().isoformat()\n    for patient in patients:\n        if 'metadata' not in patient:\n            patient['metadata'] = {}\n        patient['metadata']['last_modified'] = timestamp\n    with open(PATIENTS_FILE, 'w') as f:\n        json.dump(patients, f, indent=2)\n    return timestamp\n\nPATIENTS = load_patients()"
)

# ENHANCEMENT 3: Add modal and protocol CSS (insert before closing </style>)
additional_css = """
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

        /* Protocol Reference Section */
        .protocol-accordion {
            margin-top: 20px;
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
"""

# Insert the additional CSS before </style>
content = content.replace("    </style>", additional_css + "    </style>")

# ENHANCEMENT 4: Add Edit Patient button in HTML (after patient select)
edit_button_html = """
                <button id="editPatientBtn" class="edit-patient-btn" disabled>
                    📝 View/Edit Patient Chart
                </button>
                <div id="lastModified" class="last-modified"></div>
"""

content = content.replace(
    '                <button id="loadDetailBtn" class="load-button" disabled>',
    edit_button_html + '\n                <button id="loadDetailBtn" class="load-button" disabled>'
)

# ENHANCEMENT 5: Add modals before closing </body>
modals_html = """
    <!-- Patient Editor Modal -->
    <div id="patientEditorModal" class="modal-overlay" style="display: none;">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Edit Patient Chart</h3>
                <button class="modal-close" onclick="closePatientEditor()">&times;</button>
            </div>
            <div class="modal-body">
                <div id="saveSuccess" class="success-message" style="display: none;">
                    ✓ Patient chart saved successfully!
                </div>
                <p style="margin-bottom: 12px; color: #64748b; font-size: 13px;">
                    Edit the patient chart data below. Changes are saved to <code>synthetic_patients.json</code>.
                </p>
                <textarea id="patientDataEditor" class="patient-editor"></textarea>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closePatientEditor()">Cancel</button>
                <button class="btn btn-primary" onclick="savePatientData()">💾 Save Changes</button>
            </div>
        </div>
    </div>
"""

content = content.replace("</body>", modals_html + "\n</body>")

# ENHANCEMENT 6: Add JavaScript functions for patient editing
patient_edit_js = """
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

        function openPatientEditor() {
            if (!selectedPatient) return;

            editingPatientIndex = patients.indexOf(selectedPatient);
            const editor = document.getElementById('patientDataEditor');
            editor.value = JSON.stringify(selectedPatient, null, 2);

            document.getElementById('patientEditorModal').style.display = 'flex';
            document.getElementById('saveSuccess').style.display = 'none';
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
                alert('Invalid JSON format. Please check your syntax.\\n\\n' + error.message);
            }
        }
"""

# Insert patient edit JS before the closing script tag
content = content.replace(
    "        // Load data on page load\n        window.addEventListener('load', loadInitialData);",
    patient_edit_js + "\n        // Load data on page load\n        window.addEventListener('load', loadInitialData);"
)

# Update the patient select change handler to call updateEditButton
content = content.replace(
    "        document.getElementById('patientSelect').addEventListener('change', (e) => {\n            const patientIndex = parseInt(e.target.value);\n            selectedPatient = patients[patientIndex];\n            updateLoadButton();\n        });",
    "        document.getElementById('patientSelect').addEventListener('change', (e) => {\n            const patientIndex = parseInt(e.target.value);\n            selectedPatient = patients[patientIndex];\n            updateLoadButton();\n            updateEditButton();\n        });"
)

# ENHANCEMENT 7: Add protocol accordion rendering function
protocol_js = """
        function renderProtocolReference(protocol) {
            if (!protocol) return '';

            return `
                <div class="protocol-accordion">
                    <div class="protocol-accordion-header" onclick="toggleProtocol()">
                        <div class="protocol-accordion-title">
                            <span class="section-icon">📖</span>
                            <span>Clinical Protocol Reference</span>
                        </div>
                        <span class="protocol-accordion-icon" id="protocolIcon">▼</span>
                    </div>
                    <div class="protocol-accordion-content" id="protocolContent">
                        <div class="protocol-content">
                            <div class="protocol-field">
                                <div class="protocol-label">Task Code</div>
                                <div class="protocol-value">${escapeHtml(protocol.task_code)}</div>
                            </div>
                            <div class="protocol-field">
                                <div class="protocol-label">Task Name</div>
                                <div class="protocol-value">${escapeHtml(protocol.task_name)}</div>
                            </div>
                            <div class="protocol-field">
                                <div class="protocol-label">Priority</div>
                                <div class="protocol-value">${escapeHtml(protocol.priority)}</div>
                            </div>
                            <div class="protocol-field">
                                <div class="protocol-label">Protocol Content</div>
                                <div class="protocol-value">${escapeHtml(protocol.content)}</div>
                            </div>
                            ${protocol.full_text ? `
                                <div class="protocol-field">
                                    <div class="protocol-label">Full Protocol Text</div>
                                    <div class="protocol-value">${escapeHtml(protocol.full_text)}</div>
                                </div>
                            ` : ''}
                            <a href="#protocol-steps" class="protocol-link" onclick="scrollToProtocolSteps()">
                                → Jump to Protocol Steps Below
                            </a>
                        </div>
                    </div>
                </div>
            `;
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
"""

# Insert protocol JS before the patient edit functions
content = content.replace(
    patient_edit_js,
    protocol_js + "\n" + patient_edit_js
)

# ENHANCEMENT 8: Update renderDetailView to include protocol reference
# Find and replace the renderDetailView function to add protocol section after clinical assessment
render_detail_addition = """
                    <!-- Protocol Reference -->
                    ${detail.protocol ? renderProtocolReference(detail.protocol) : ''}
"""

# Insert before Suggested Messages section
content = content.replace(
    "                    <!-- Suggested Messages -->",
    render_detail_addition + "\n                    <!-- Suggested Messages -->"
)

# Write the enhanced version
with open('todo_viewer_enhanced.py', 'w') as f:
    f.write(content)

print("✓ Created todo_viewer_enhanced.py")
print()
print("Now adding backend endpoints...")

# Read the enhanced file
with open('todo_viewer_enhanced.py', 'r') as f:
    enhanced_content = f.read()

# ENHANCEMENT 9: Add new API endpoints before the @app.route('/api/health')
new_endpoints = """
@app.route('/api/save-patient', methods=['POST'])
def save_patient():
    \"\"\"Save updated patient data\"\"\"
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
    \"\"\"Get full patient data by index\"\"\"
    try:
        patients = load_patients()
        if patient_index < 0 or patient_index >= len(patients):
            return jsonify({'error': 'Invalid patient index'}), 404

        return jsonify(patients[patient_index])

    except Exception as e:
        return jsonify({'error': str(e)}), 500

"""

# Insert new endpoints before health endpoint
enhanced_content = enhanced_content.replace(
    "@app.route('/api/health')",
    new_endpoints + "@app.route('/api/health')"
)

# ENHANCEMENT 10: Update generate-detail endpoint to include protocol in response
# Find the generate-detail function and modify it to return protocol
generate_detail_update = """
        # Include protocol in response
        detail_view['protocol'] = {
            'task_code': protocol.get('task_code', 'N/A'),
            'task_name': protocol.get('task_name', 'N/A'),
            'priority': protocol.get('priority', 'N/A'),
            'content': protocol.get('content', 'N/A'),
            'full_text': protocol.get('full_text', '')
        }

        return jsonify(detail_view)
"""

# Replace the return statement in generate-detail
enhanced_content = enhanced_content.replace(
    "        return jsonify(detail_view)",
    generate_detail_update
)

# Write the final enhanced version
with open('todo_viewer_enhanced.py', 'w') as f:
    f.write(enhanced_content)

print("✓ Added backend endpoints")
print("✓ Enhanced todo_viewer.py created as todo_viewer_enhanced.py")
print()
print("Enhancements added:")
print("  1. Patient chart editing with JSON editor modal")
print("  2. Save patient data to synthetic_patients.json")
print("  3. Last modified timestamp tracking")
print("  4. Protocol reference accordion section")
print("  5. Protocol content display with full text")
print("  6. Jump to protocol steps link")
print()
print("To use the enhanced version:")
print("  python todo_viewer_enhanced.py")
