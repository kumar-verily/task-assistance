# Clinical Task Assistance — Pinecone RAG for Clinical Protocols

A clinical decision support system that uses **Pinecone vector search** and **OpenAI GPT-4** to provide AI-powered task assistance for healthcare providers. Clinical protocols are stored in Pinecone with integrated embeddings, searched via semantic + filtered queries, reranked for relevance, and fed to an LLM alongside patient chart data to generate actionable clinical guidance.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Flask Web Application                      │
│              todo_viewer_enhanced.py (port 5001)              │
└──────────┬────────────────────────────┬──────────────────────┘
           │                            │
     ┌─────▼──────────┐         ┌──────▼──────────┐
     │   Pinecone      │         │   OpenAI GPT-4   │
     │   Vector DB     │         │   (LLM Engine)   │
     └─────┬──────────┘         └──────┬──────────┘
           │                            │
           │  Protocol retrieved        │  Protocol + Patient data
           │  via semantic search       │  → AI-generated guidance
           │                            │
     ┌─────▼──────────────────────────▼───────────────────────┐
     │              AI Task Assistance Response                │
     │  • Clinical summary        • Suggested messages         │
     │  • Patient timeline        • Protocol step guidance     │
     │  • Risk assessment         • Role-specific actions      │
     └────────────────────────────────────────────────────────┘
```

## How Pinecone Is Used

### Index Configuration

| Parameter         | Value                        |
|-------------------|------------------------------|
| **Index Name**    | `clinical-protocols-rag`     |
| **Namespace**     | `protocols`                  |
| **Embedding Model** | `llama-text-embed-v2` (1024 dimensions) |
| **Reranker Model** | `bge-reranker-v2-m3`        |
| **Cloud**         | AWS, us-east-1 (serverless)  |
| **Field Mapping** | `text` → `content`           |
| **Total Records** | ~74 clinical protocol chunks |

The index uses **Pinecone Integrated Inference** — no external embedding pipeline needed. Pinecone automatically converts the `content` field to vectors using `llama-text-embed-v2` on upsert and query.

### Record Schema

Each protocol record stored in Pinecone has this schema:

```python
record = {
    "_id": "lightpath_BGM-104_0",          # Unique chunk ID
    "content": "Task: HYPERGLYCEMIA...",    # Embedded field (searchable text)
    "task_code": "BGM-104",                 # Filterable metadata
    "task_name": "HYPERGLYCEMIA: BG > 400", # Human-readable name
    "priority": "P0",                       # P0, P1, P2, P3
    "program": "lightpath",                 # Program identifier
    "full_text": "| BGM-104 | ...",         # Complete protocol markdown
    "roles": "HC,RN,RD,PharmD",            # Applicable provider roles
}
```

The `content` field is constructed from multiple protocol fields to create a rich, searchable text representation:

```python
content_parts = [
    f"Task: {protocol['task_name']}",
    f"Code: {protocol['task_code']}",
    f"Priority: {protocol['priority']}",
    f"Program: {protocol['program']}",
    f"Trigger: {protocol['trigger']}",
    f"Criteria: {protocol['triggering_criteria']}",
    f"Steps ({step_type}): {step_content}",   # clinic / non-clinic / general
    f"Roles: {', '.join(protocol['roles'])}"
]
content = "\n".join(content_parts)
```

### Data Ingestion

Protocols are loaded from `clinical_protocols.jsonl` into Pinecone using `load_protocols.py`:

```python
from pinecone import Pinecone

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("clinical-protocols-rag")

# Records are upserted in batches of 96
# Pinecone handles embedding via integrated inference
index.upsert_records("protocols", batch)
```

The source data flows through this pipeline:

```
All Protocol.md (markdown tables)
        ↓  protocol_parser_complete.py
clinical_protocols.json (structured JSON)
        ↓  converted to JSONL
clinical_protocols.jsonl (one record per line)
        ↓  load_protocols.py
Pinecone index: clinical-protocols-rag / namespace: protocols
```

---

## Search Patterns

### Pattern 1: Exact Protocol Lookup by Task Code

Used by the **Task Assistance** feature to retrieve a specific protocol when a clinician selects a task (e.g., BGM-104):

```python
# Primary: filtered search by exact task code
protocol_results = protocol_index.search(
    namespace="protocols",
    query={
        "top_k": 1,
        "inputs": {"text": f"task code {todo_id}"},
        "filter": {"task_code": {"$eq": todo_id}}
    }
)

# Extract the protocol fields
protocol = protocol_results['result']['hits'][0]['fields']
# → {'task_code': 'BGM-104', 'task_name': '...', 'content': '...', ...}
```

If the filtered search returns no hits, a **fallback semantic search** runs without the filter:

```python
# Fallback: pure semantic search
protocol_results = protocol_index.search(
    namespace="protocols",
    query={
        "top_k": 1,
        "inputs": {"text": todo_id}
    }
)
```

### Pattern 2: Semantic Search with Reranking

Used by the **Protocol Search** interface for free-text clinical queries (e.g., "patient blood glucose above 400"):

```python
# Build optional metadata filters
filters = {}
if priority_filter:
    filters['priority'] = {'$eq': priority_filter}   # e.g., "P0"
if program_filter:
    filters['program'] = {'$eq': program_filter}      # e.g., "lightpath"

# Search with 2x top_k, then rerank down to top_k
results = pinecone_index.search(
    namespace="protocols",
    query={
        "top_k": top_k * 2,
        "inputs": {"text": query_text},
        "filter": filters
    },
    rerank={
        "model": "bge-reranker-v2-m3",
        "top_n": top_k,
        "rank_fields": ["content"]
    }
)
```

**Why 2x top_k?** The initial vector search retrieves a broader set of candidates. The reranker then re-scores them using cross-attention (more accurate than vector similarity alone), keeping only the top N most relevant results.

### Processing Search Results

```python
for hit in results['result']['hits']:
    fields = hit['fields']
    result = {
        'task_code':  fields.get('task_code', ''),
        'task_name':  fields.get('task_name', ''),
        'priority':   fields.get('priority', ''),
        'program':    fields.get('program', ''),
        'content':    fields.get('content', ''),
        'roles':      fields.get('roles', ''),
        'score':      hit.get('_score', 0)          # Relevance score 0-1
    }
```

### Filter Operators

Pinecone supports MongoDB-style filter syntax on metadata fields:

```python
# Exact match
{"task_code": {"$eq": "BGM-104"}}

# Priority range
{"priority": {"$in": ["P0", "P1"]}}

# Combined filters
{"$and": [
    {"priority": {"$eq": "P0"}},
    {"program": {"$eq": "lightpath"}}
]}
```

Supported operators: `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`, `$exists`, `$and`, `$or`

---

## RAG Pipeline: Protocol → LLM → Clinical Guidance

After retrieving a protocol from Pinecone, the system combines it with patient chart data and sends it to GPT-4:

```python
# 1. Fetch protocol from Pinecone (Pattern 1 above)
protocol = protocol_results['result']['hits'][0]['fields']

# 2. Determine clinic context from patient data
clinic_member = patient.get('participant_overview', {}).get('clinic_member', 'Unknown')
clinic_context = "Clinic" if clinic_member == "Yes" else "Non-Clinic"

# 3. Construct LLM prompt with protocol + patient
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

# 4. Call OpenAI GPT-4
response = openai_client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": llm_prompt}
    ],
    temperature=0.7,
    max_tokens=4000,
    response_format={"type": "json_object"}
)

# 5. Parse structured response
detail_view = json.loads(response.choices[0].message.content)
```

### Role-Based Context

The protocol steps have variants that are selected based on the patient's status:

| Patient Status | Protocol Steps Used |
|----------------|-------------------|
| Clinic member = "Yes" | `Steps (clinic)` |
| Clinic member = "No"  | `Steps (non_clinic)` |
| Only general available | `Steps (general)` |

The LLM also tailors its response based on provider role:

| Role | Focus Area |
|------|-----------|
| **HC** (Health Coach) | Lifestyle, education, behavior change |
| **RN** (Registered Nurse) | Clinical assessment, medication adherence, care coordination |
| **RD** (Registered Dietitian) | Nutrition, meal planning, diet factors |
| **PharmD** (Pharmacist) | Medications, side effects, drug interactions |

### Caching

AI-generated task assistance is cached to `task_assistance_outputs/` to avoid redundant LLM calls:

```
task_assistance_outputs/
├── BGM-104_patient0.json     # Cached hyperglycemia analysis for patient 0
├── ENG-100_patient0.json     # Cached engagement task for patient 0
├── PHQ-101_patient0.json     # Cached mental health task for patient 0
└── ...
```

---

## Clinical Protocol Coverage

### 38 Clinical Tasks Across 11 Categories

| Category | Count | Task Codes |
|----------|-------|------------|
| Hyperglycemia | 6 | BGM-102, BGM-103, BGM-104, BGM-105, BGM-106, BGM-107 |
| Hypoglycemia | 2 | BGM-100, BGM-101 |
| A1C Management | 1 | A1c-101 |
| Hypertension | 5 | BP-101, BP-102, BP-103, BP-104, BP-105 |
| Hypotension | 1 | BP-106 |
| BP Monitoring | 1 | BP-100 |
| Patient Engagement | 3 | ENG-100, ENG-101, ENG-110 |
| Mental Health | 3 | PHQ-9, PHQ-100, PHQ-101 |
| Health Assessment | 4 | PRM-101, PRM-102, PRM-103, PRM-104 |
| Surveys | 4 | SRV-100, SRV-101, SRV-102, SRV-103 |
| Custom Tasks | 1 | TODO-100 |

### Protocol Data Structure

Each protocol in `clinical_protocols.json`:

```json
{
  "task_code": "BGM-104",
  "task_name": "HYPERGLYCEMIA: BG > 400",
  "program": "lightpath",
  "priority": "P0",
  "trigger": "Blood glucose reading above 400 mg/dL",
  "triggering_criteria": "BGM > 400",
  "steps": {
    "general": "1. Call patient immediately...",
    "clinic": "1. Contact clinic provider...",
    "non_clinic": "1. Assess symptoms remotely..."
  },
  "message_templates": [
    {
      "language": "en",
      "template": "We noticed your blood sugar reading was very high...",
      "placeholders": ["(patient_name)", "(reading_value)"]
    }
  ],
  "links": [{"title": "EHR Portal", "url": "https://..."}],
  "roles": ["HC", "RN", "RD", "PharmD"],
  "full_text": "| BGM-104 | HYPERGLYCEMIA: BG > 400 | ...",
  "chunk_id": "lightpath_BGM-104_0"
}
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/api/todos` | List all 38 clinical tasks |
| `GET` | `/api/patients` | List synthetic patients |
| `GET` | `/api/patient/<index>` | Get full patient chart |
| `GET` | `/api/task-assistance/<todo_id>/<patient_index>/<role>` | Generate AI task assistance (Pinecone + GPT-4) |
| `POST` | `/api/get-protocol` | Retrieve protocol from Pinecone only |
| `POST` | `/api/generate-detail` | Generate AI detail view |
| `POST` | `/api/check-cached-tasks` | Check which tasks have cached results |
| `POST` | `/api/save-patient` | Save edited patient data |
| `GET` | `/api/health` | Health check (includes Pinecone stats) |

---

## Running Locally

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables in .env
PINECONE_API_KEY="your-key"
OPENAI_API_KEY="your-key"

# 4. Start the app
python todo_viewer_enhanced.py
# Opens at http://localhost:5001
```

## Deploying to Railway

The app is configured for Railway deployment with:
- `Procfile` — runs with gunicorn
- `runtime.txt` — pins Python 3.11
- `requirements.txt` — all dependencies

Set these environment variables in Railway:
- `PINECONE_API_KEY`
- `OPENAI_API_KEY`
- `RAILWAY_ENVIRONMENT=production`

---

## Key Files

| File | Purpose |
|------|---------|
| `todo_viewer_enhanced.py` | Main Flask app (2600+ lines, includes embedded frontend) |
| `protocol_search.py` | Standalone protocol search UI (port 5000) |
| `load_protocols.py` | Loads protocols from JSONL into Pinecone |
| `protocol_parser_complete.py` | Parses protocol markdown tables into structured JSON |
| `clinical_protocols.json` | 74 structured clinical protocols |
| `clinical_protocols.jsonl` | Protocols formatted for Pinecone ingestion |
| `synthetic_patients.json` | 20 synthetic patient records with full chart data |
| `detail_view_prompt.txt` | System prompt for GPT-4 clinical analysis |
| `requirements.txt` | Python dependencies |
| `Procfile` | Railway deployment entrypoint |

## Tech Stack

- **Backend**: Flask + gunicorn
- **Vector DB**: Pinecone (serverless, integrated inference)
- **Embedding**: `llama-text-embed-v2` (1024 dimensions, via Pinecone)
- **Reranking**: `bge-reranker-v2-m3` (via Pinecone)
- **LLM**: OpenAI GPT-4 Turbo
- **Deployment**: Railway
- **Python SDK**: `pinecone==8.0.0`
