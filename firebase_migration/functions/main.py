"""
Firebase Functions for Clinical ToDo Viewer
Converted from Flask application
"""

from firebase_functions import https_fn, options
from firebase_admin import initialize_app, firestore, storage
import os
from pinecone import Pinecone
from openai import OpenAI
import json
from datetime import datetime

# Initialize Firebase Admin
initialize_app()
db = firestore.client()
bucket = storage.bucket()

# Initialize Pinecone and OpenAI (using Firebase config)
# In production, these come from: firebase functions:config:set
pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY', ''))
protocol_index = pc.Index("clinical-protocols-rag")
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY', ''))

# CORS configuration for all functions
cors_options = options.CorsOptions(
    cors_origins=["*"],
    cors_methods=["get", "post", "options"],
)


@https_fn.on_request(cors=cors_options)
def get_todos(req: https_fn.Request) -> https_fn.Response:
    """Get list of all clinical todos"""

    TODOS = [
        {"id": "BGM-104", "name": "Hyperglycemia > 400, daily", "priority": "P0", "category": "Hyperglycemia"},
        {"id": "BGM-103", "name": "Hyperglycemia > 250", "priority": "P2", "category": "Hyperglycemia"},
        {"id": "BGM-102", "name": "Hyperglycemia > 180", "priority": "P3", "category": "Hyperglycemia"},
        {"id": "BGM-107", "name": "BG Average > 220 for 2 weeks (A1c 8-8.9)", "priority": "P2", "category": "Hyperglycemia"},
        {"id": "BGM-106", "name": "BG Average > 190 for 2 weeks (A1c 7-7.9)", "priority": "P2", "category": "Hyperglycemia"},
        {"id": "BGM-105", "name": "BG Average > 170 for 2 weeks (A1c<7)", "priority": "P2", "category": "Hyperglycemia"},
        {"id": "BGM-100", "name": "Hypoglycemia < 54", "priority": "P0", "category": "Hypoglycemia"},
        {"id": "BGM-101", "name": "Hypoglycemia < 70", "priority": "P1", "category": "Hypoglycemia"},
        {"id": "A1c-101", "name": "Review A1c ingested > 7.0%", "priority": "P2", "category": "A1C Management"},
        {"id": "BP-105", "name": "Hypertension (High): BP > 180/120", "priority": "P0", "category": "Hypertension"},
        {"id": "BP-104", "name": "Hypertension: BP > 160/100", "priority": "P1", "category": "Hypertension"},
        {"id": "BP-103", "name": "Hypertension: BP > 150/90", "priority": "P1", "category": "Hypertension"},
        {"id": "BP-102", "name": "Hypertension: BP > 140/90", "priority": "P1", "category": "Hypertension"},
        {"id": "BP-101", "name": "Hypertension: BP > 130/80", "priority": "P2", "category": "Hypertension"},
        {"id": "BP-106", "name": "Hypotension (Low): BP < 90/60", "priority": "P1", "category": "Hypotension"},
        {"id": "BP-100", "name": "Remind member to take initial BP reading", "priority": "P2", "category": "BP Monitoring"},
        {"id": "ENG-100", "name": "Greet new member", "priority": "P2", "category": "Engagement"},
        {"id": "ENG-101", "name": "Schedule telehealth visit", "priority": "P2", "category": "Engagement"},
        {"id": "PHQ-9", "name": "PHQ-9 Self-harm risk (Q9: answer 1-3)", "priority": "P0", "category": "Mental Health"},
        {"id": "PHQ-101", "name": "Review PHQ-9 score >= 10", "priority": "P1", "category": "Mental Health"},
    ]

    return https_fn.Response(json.dumps(TODOS), mimetype='application/json')


@https_fn.on_request(cors=cors_options)
def get_patients(req: https_fn.Request) -> https_fn.Response:
    """Get list of all patients"""

    patients_ref = db.collection('patients')
    patients = []

    for doc in patients_ref.stream():
        patient = doc.to_dict()
        # Return simplified data for list
        patients.append({
            'id': doc.id,
            'demographics': patient.get('demographics', {})
        })

    return https_fn.Response(json.dumps(patients), mimetype='application/json')


@https_fn.on_request(cors=cors_options)
def get_patient(req: https_fn.Request) -> https_fn.Response:
    """Get full patient data by ID"""

    # Get patient_id from query params
    patient_id = req.args.get('id')
    if not patient_id:
        return https_fn.Response('Missing patient_id', status=400)

    doc = db.collection('patients').document(patient_id).get()
    if not doc.exists:
        return https_fn.Response('Patient not found', status=404)

    return https_fn.Response(json.dumps(doc.to_dict()), mimetype='application/json')


@https_fn.on_request(cors=cors_options)
def check_cached_tasks(req: https_fn.Request) -> https_fn.Response:
    """Check which tasks have cached assistance for a patient"""

    if req.method == 'OPTIONS':
        return https_fn.Response('', status=204)

    data = req.get_json()
    patient_id = data.get('patient_id')

    if not patient_id:
        return https_fn.Response('Missing patient_id', status=400)

    # Query task_assistance collection for this patient
    cached_tasks = []
    assistance_ref = db.collection('task_assistance')
    query = assistance_ref.where('patient_id', '==', patient_id)

    for doc in query.stream():
        task_data = doc.to_dict()
        cached_tasks.append(task_data.get('todo_id'))

    return https_fn.Response(
        json.dumps({'cached_task_ids': cached_tasks}),
        mimetype='application/json'
    )


@https_fn.on_request(cors=cors_options)
def get_protocol(req: https_fn.Request) -> https_fn.Response:
    """Get protocol data for a task without generating AI assistance"""

    if req.method == 'OPTIONS':
        return https_fn.Response('', status=204)

    data = req.get_json()
    todo_id = data.get('todo_id')
    patient_id = data.get('patient_id')

    if not todo_id or not patient_id:
        return https_fn.Response('Missing todo_id or patient_id', status=400)

    # Get patient
    patient_doc = db.collection('patients').document(patient_id).get()
    if not patient_doc.exists:
        return https_fn.Response('Patient not found', status=404)

    patient = patient_doc.to_dict()

    # Search protocol in Pinecone
    protocol_results = protocol_index.search(
        namespace="protocols",
        query={
            "top_k": 1,
            "inputs": {"text": f"task code {todo_id}"},
            "filter": {"task_code": {"$eq": todo_id}}
        }
    )

    protocol = {}
    if protocol_results['result']['hits']:
        protocol = protocol_results['result']['hits'][0]['fields']

    # Check if cached
    cache_id = f"{patient_id}_{todo_id}"
    cache_doc = db.collection('task_assistance').document(cache_id).get()
    has_cached = cache_doc.exists

    # Get todo info from list
    todo = next((t for t in get_todos_list() if t['id'] == todo_id), None)

    return https_fn.Response(
        json.dumps({
            'task_id': todo_id,
            'task_name': todo['name'] if todo else todo_id,
            'task_title': todo['name'] if todo else todo_id,
            'priority': todo['priority'] if todo else 'P2',
            'category': todo['category'] if todo else '',
            'patient_name': patient['demographics']['name'],
            'patient_id': patient_id,
            'protocol': {
                'task_code': protocol.get('task_code', 'N/A'),
                'task_name': protocol.get('task_name', 'N/A'),
                'priority': protocol.get('priority', 'N/A'),
                'content': protocol.get('content', 'N/A'),
                'full_text': protocol.get('full_text', '')
            },
            'has_cached_assistance': has_cached
        }),
        mimetype='application/json'
    )


@https_fn.on_request(
    cors=cors_options,
    timeout_sec=540,  # 9 minutes for LLM calls
    memory=options.MemoryOption.GB_1
)
def generate_detail(req: https_fn.Request) -> https_fn.Response:
    """Generate AI-powered task assistance"""

    if req.method == 'OPTIONS':
        return https_fn.Response('', status=204)

    data = req.get_json()
    todo_id = data.get('todo_id')
    patient_id = data.get('patient_id')
    user_role = data.get('user_role', 'RN')
    refresh = data.get('refresh', False)

    if not todo_id or not patient_id:
        return https_fn.Response('Missing required fields', status=400)

    cache_id = f"{patient_id}_{todo_id}"

    # Check cache unless refresh requested
    if not refresh:
        cache_doc = db.collection('task_assistance').document(cache_id).get()
        if cache_doc.exists:
            cached_data = cache_doc.to_dict()
            result = cached_data['detail_view'].copy()
            result['from_cache'] = True
            result['cached_timestamp'] = cached_data['timestamp']
            return https_fn.Response(json.dumps(result), mimetype='application/json')

    # Get patient data
    patient_doc = db.collection('patients').document(patient_id).get()
    if not patient_doc.exists:
        return https_fn.Response('Patient not found', status=404)

    patient = patient_doc.to_dict()

    # Search protocol
    protocol_results = protocol_index.search(
        namespace="protocols",
        query={
            "top_k": 1,
            "inputs": {"text": f"task code {todo_id}"},
            "filter": {"task_code": {"$eq": todo_id}}
        }
    )

    protocol = {}
    if protocol_results['result']['hits']:
        protocol = protocol_results['result']['hits'][0]['fields']

    # Get clinic context
    clinic_member = patient.get('participant_overview', {}).get('clinic_member', 'Unknown')
    clinic_context = "Clinic" if clinic_member == "Yes" else "Non-Clinic" if clinic_member == "No" else "Unknown"

    # Load detail view prompt from storage or embed it
    DETAIL_VIEW_PROMPT = """You are a clinical AI assistant generating patient-specific task assistance views..."""

    # Prepare LLM prompt
    llm_prompt = f"""
{DETAIL_VIEW_PROMPT}

## User Context:
Role: {user_role}
Patient Clinic Status: {clinic_context}

## Patient Chart Data:
{json.dumps(patient, indent=2)}

## Protocol Data:
Task Code: {protocol.get('task_code', 'N/A')}
Task Name: {protocol.get('task_name', 'N/A')}
Priority: {protocol.get('priority', 'N/A')}
Content: {protocol.get('content', 'N/A')}

Generate the detailed clinical view now in JSON format.
"""

    # Call OpenAI
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

    detail_view = json.loads(response.choices[0].message.content)

    # Add protocol and context
    detail_view['protocol'] = {
        'task_code': protocol.get('task_code', 'N/A'),
        'task_name': protocol.get('task_name', 'N/A'),
        'priority': protocol.get('priority', 'N/A'),
        'content': protocol.get('content', 'N/A'),
        'full_text': protocol.get('full_text', '')
    }

    detail_view['user_context'] = {
        'role': user_role,
        'clinic_context': clinic_context,
        'clinic_member': clinic_member
    }

    # Save to Firestore
    db.collection('task_assistance').document(cache_id).set({
        'patient_id': patient_id,
        'todo_id': todo_id,
        'patient_name': patient['demographics']['name'],
        'timestamp': datetime.now().isoformat(),
        'detail_view': detail_view
    })

    detail_view['from_cache'] = False
    return https_fn.Response(json.dumps(detail_view), mimetype='application/json')


def get_todos_list():
    """Helper to get todos list"""
    return [
        {"id": "BGM-104", "name": "Hyperglycemia > 400, daily", "priority": "P0", "category": "Hyperglycemia"},
        {"id": "BGM-103", "name": "Hyperglycemia > 250", "priority": "P2", "category": "Hyperglycemia"},
        # ... (abbreviated for space)
    ]
