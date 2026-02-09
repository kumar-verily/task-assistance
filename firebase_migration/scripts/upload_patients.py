#!/usr/bin/env python3
"""
Upload synthetic patients data to Firestore
"""

import json
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path

# Initialize Firebase Admin SDK
# Download your service account key from Firebase Console
# Project Settings > Service Accounts > Generate New Private Key
cred = credentials.Certificate('path/to/serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

def upload_patients():
    """Upload patients from synthetic_patients.json to Firestore"""

    # Load patients data
    patients_file = Path(__file__).parent.parent.parent / 'synthetic_patients.json'

    with open(patients_file, 'r') as f:
        patients = json.load(f)

    print(f"Found {len(patients)} patients to upload")

    # Upload each patient
    patients_ref = db.collection('patients')

    for i, patient in enumerate(patients):
        # Use patient name as document ID (or generate unique ID)
        doc_id = f"patient_{i:03d}"

        # Upload to Firestore
        patients_ref.document(doc_id).set(patient)

        print(f"Uploaded patient {i+1}/{len(patients)}: {patient['demographics']['name']}")

    print(f"\\n✓ Successfully uploaded {len(patients)} patients to Firestore!")

def upload_cached_assistance():
    """Upload existing cached task assistance to Firestore"""

    assistance_dir = Path(__file__).parent.parent.parent / 'task_assistance_outputs'

    if not assistance_dir.exists():
        print("No cached task assistance found")
        return

    assistance_ref = db.collection('task_assistance')
    count = 0

    for file_path in assistance_dir.glob('*.json'):
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Extract patient index and todo_id from filename
        # Format: {todo_id}_patient{index}.json
        filename = file_path.stem
        parts = filename.split('_patient')
        if len(parts) == 2:
            todo_id = parts[0]
            patient_index = parts[1]

            # Create document ID
            doc_id = f"patient_{int(patient_index):03d}_{todo_id}"

            # Upload to Firestore
            assistance_ref.document(doc_id).set({
                'patient_id': f"patient_{int(patient_index):03d}",
                'todo_id': todo_id,
                'patient_name': data.get('patient_name', ''),
                'timestamp': data.get('timestamp', ''),
                'detail_view': data.get('detail_view', {})
            })

            count += 1
            print(f"Uploaded cached assistance: {doc_id}")

    print(f"\\n✓ Successfully uploaded {count} cached task assistance records!")

if __name__ == '__main__':
    print("=== Uploading Data to Firestore ===\\n")

    # Upload patients
    upload_patients()

    # Upload cached task assistance
    print("\\n=== Uploading Cached Task Assistance ===\\n")
    upload_cached_assistance()

    print("\\n=== Done! ===")
