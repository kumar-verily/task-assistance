# Firebase Migration - Complete Guide

This directory contains everything you need to deploy the Clinical ToDo Viewer to Firebase.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm installed
- Python 3.9+ installed
- Firebase account (free tier works!)
- Your Pinecone and OpenAI API keys

### Step 1: Install Firebase CLI

```bash
npm install -g firebase-tools
```

### Step 2: Login to Firebase

```bash
firebase login
```

### Step 3: Create Firebase Project

1. Go to https://console.firebase.google.com/
2. Click "Add project"
3. Name it (e.g., `clinical-todo-viewer`)
4. Disable Google Analytics (optional)
5. Click "Create project"

### Step 4: Initialize Firebase

```bash
cd firebase_migration
firebase init
```

**Select these services:**
- ✓ Firestore
- ✓ Functions
- ✓ Hosting
- ✓ Storage (optional, for future use)

**Configuration:**
- Project: Select the project you just created
- Firestore rules: Use default
- Functions language: **Python**
- Install dependencies: **Yes**
- Public directory: `public`
- Single-page app: **Yes**
- Overwrite index.html: **No** (we'll copy it later)

### Step 5: Copy Your HTML to Public Directory

```bash
# Extract HTML from your Python file
python3 << 'EOF'
import re
with open('../todo_viewer_enhanced.py', 'r') as f:
    content = f.read()

# Extract HTML_TEMPLATE
start = content.find('HTML_TEMPLATE = """') + len('HTML_TEMPLATE = """')
end = content.find('"""', start)
html = content[start:end]

# Update API endpoints to use Firebase Functions
# This will be done automatically below
with open('public/index.html', 'w') as f:
    f.write(html)
print("✓ HTML extracted to public/index.html")
EOF
```

Or manually copy the HTML section from `todo_viewer_enhanced.py` to `public/index.html`

### Step 6: Update Frontend API Calls

In `public/index.html`, find all `fetch('/api/...` and replace with:

```javascript
// Change this:
const response = await fetch('/api/todos');

// To this:
const response = await fetch('https://YOUR_REGION-YOUR_PROJECT_ID.cloudfunctions.net/get_todos');
```

**OR** configure rewrites in `firebase.json` (recommended):

```json
{
  "hosting": {
    "public": "public",
    "rewrites": [
      {
        "source": "/api/todos",
        "function": "get_todos"
      },
      {
        "source": "/api/patients",
        "function": "get_patients"
      },
      {
        "source": "/api/check-cached-tasks",
        "function": "check_cached_tasks"
      },
      {
        "source": "/api/get-protocol",
        "function": "get_protocol"
      },
      {
        "source": "/api/generate-detail",
        "function": "generate_detail"
      }
    ]
  },
  "functions": {
    "source": "functions"
  }
}
```

With rewrites, you keep the same `/api/...` URLs!

### Step 7: Set Environment Variables

```bash
firebase functions:config:set \
  pinecone.api_key="YOUR_PINECONE_API_KEY" \
  openai.api_key="YOUR_OPENAI_API_KEY"
```

### Step 8: Upload Patient Data to Firestore

First, download your service account key:
1. Go to Firebase Console > Project Settings
2. Service Accounts tab
3. Click "Generate new private key"
4. Save as `serviceAccountKey.json` in `scripts/`

Then run:

```bash
cd scripts
pip install firebase-admin
python upload_patients.py
```

### Step 9: Add Detail View Prompt

The prompt file is too large to embed in code. Upload to Firebase Storage:

```bash
firebase storage:upload ../detail_view_prompt.txt /prompts/detail_view_prompt.txt
```

Or embed it directly in `functions/main.py` (around line 270).

### Step 10: Deploy!

```bash
# Deploy everything
firebase deploy

# Or deploy step by step:
firebase deploy --only hosting
firebase deploy --only functions
firebase deploy --only firestore:rules
```

### Step 11: Access Your App

After deployment, Firebase will show your URL:
```
✔  Deploy complete!

Project Console: https://console.firebase.google.com/project/YOUR_PROJECT_ID
Hosting URL: https://YOUR_PROJECT_ID.web.app
```

Open that URL in your browser!

## 🔧 Development

### Local Testing

```bash
# Install Functions Framework
pip install functions-framework

# Set environment variables
export PINECONE_API_KEY="your_key"
export OPENAI_API_KEY="your_key"

# Run locally
firebase emulators:start
```

Access at http://localhost:5000

### Update Functions

After changing `functions/main.py`:

```bash
firebase deploy --only functions
```

### Update Frontend

After changing `public/index.html`:

```bash
firebase deploy --only hosting
```

## 📊 Monitoring

- **Firebase Console:** https://console.firebase.google.com/
- **Functions Logs:** Functions tab > Logs
- **Firestore Data:** Firestore Database tab
- **Usage & Billing:** Usage and billing tab

## 💰 Costs (Free Tier Limits)

Your app should easily stay in the free tier:

**Cloud Functions:**
- 2M invocations/month
- 400K GB-seconds, 200K GHz-seconds compute/month
- 5GB network egress/month

**Firestore:**
- 1 GiB storage
- 50K reads, 20K writes, 20K deletes per day

**Hosting:**
- 10 GB storage
- 360 MB/day transfer

## 🔒 Security

### Firestore Rules

Edit `firestore.rules`:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow authenticated users to read patients
    match /patients/{patientId} {
      allow read: if request.auth != null;
      allow write: if false; // Only functions can write
    }

    // Allow authenticated users to access task assistance
    match /task_assistance/{docId} {
      allow read: if request.auth != null;
      allow write: if false; // Only functions can write
    }

    // Allow reading todos (public data)
    match /todos/{todoId} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```

Deploy rules:
```bash
firebase deploy --only firestore:rules
```

### Adding Authentication (Optional)

Enable Firebase Authentication for secure access:

1. Firebase Console > Authentication
2. Enable "Email/Password" or "Google" sign-in
3. Update Firestore rules to require auth
4. Add Firebase Auth to your frontend

## 🐛 Troubleshooting

**Functions timeout:**
- Increase timeout in `functions/main.py`: `@https_fn.on_request(timeout_sec=540)`

**CORS errors:**
- Already configured in `functions/main.py`
- Check browser console for specific errors

**Firestore permission denied:**
- Update `firestore.rules`
- Check authentication status

**Environment variables not working:**
- Verify: `firebase functions:config:get`
- Re-set if needed: `firebase functions:config:set ...`

## 📝 Next Steps

1. ✅ Deploy to Firebase
2. 🔐 Add Firebase Authentication
3. 📊 Set up monitoring alerts
4. 🎨 Customize branding
5. 📱 Make it mobile-responsive
6. 🤖 Add more AI features

## 🆘 Need Help?

- Firebase Docs: https://firebase.google.com/docs
- Firebase Support: https://firebase.google.com/support
- Stack Overflow: Tag `firebase`

---

**You're all set! 🎉**

Your Clinical ToDo Viewer is now a production-ready web app with:
- ✅ Global CDN hosting
- ✅ Serverless backend
- ✅ Scalable database
- ✅ All running on Firebase's free tier!
