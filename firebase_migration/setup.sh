#!/bin/bash

echo "=========================================="
echo "Firebase Migration Setup Script"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js is not installed. Please install from https://nodejs.org/${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js found${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

if ! command -v firebase &> /dev/null; then
    echo -e "${YELLOW}Installing Firebase CLI...${NC}"
    npm install -g firebase-tools
fi
echo -e "${GREEN}✓ Firebase CLI ready${NC}"

echo ""

# Step 2: Login to Firebase
echo -e "${YELLOW}Step 2: Firebase Login${NC}"
echo "Please login to Firebase when the browser opens..."
firebase login
echo ""

# Step 3: Extract HTML from Python file
echo -e "${YELLOW}Step 3: Extracting frontend HTML...${NC}"

mkdir -p public

python3 << 'EOF'
import re
import sys

try:
    with open('../todo_viewer_enhanced.py', 'r') as f:
        content = f.read()

    # Extract HTML_TEMPLATE
    start = content.find('HTML_TEMPLATE = """')
    if start == -1:
        print("ERROR: Could not find HTML_TEMPLATE in todo_viewer_enhanced.py")
        sys.exit(1)

    start += len('HTML_TEMPLATE = """')
    end = content.find('"""', start)

    if end == -1:
        print("ERROR: Could not find end of HTML_TEMPLATE")
        sys.exit(1)

    html = content[start:end]

    # Write to public/index.html
    with open('public/index.html', 'w') as f:
        f.write(html)

    print("✓ HTML extracted to public/index.html")
    sys.exit(0)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to extract HTML${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Frontend HTML ready${NC}"
echo ""

# Step 4: Copy Firebase Functions
echo -e "${YELLOW}Step 4: Setting up Firebase Functions...${NC}"

if [ ! -f "functions/main.py" ]; then
    echo -e "${RED}✗ functions/main.py not found!${NC}"
    echo "Please ensure you're in the firebase_migration directory"
    exit 1
fi

echo -e "${GREEN}✓ Functions ready${NC}"
echo ""

# Step 5: Initialize Firebase Project
echo -e "${YELLOW}Step 5: Initialize Firebase${NC}"
echo "When prompted:"
echo "  - Select: Firestore, Functions, Hosting"
echo "  - Functions language: Python"
echo "  - Public directory: public"
echo "  - Single-page app: Yes"
echo ""
read -p "Press Enter to continue..."

firebase init

echo ""

# Step 6: Set environment variables
echo -e "${YELLOW}Step 6: Configure API Keys${NC}"
echo ""

read -p "Enter your Pinecone API key: " PINECONE_KEY
read -p "Enter your OpenAI API key: " OPENAI_KEY

firebase functions:config:set \
  pinecone.api_key="$PINECONE_KEY" \
  openai.api_key="$OPENAI_KEY"

echo -e "${GREEN}✓ Environment variables configured${NC}"
echo ""

# Step 7: Instructions for data upload
echo -e "${YELLOW}Step 7: Upload Patient Data${NC}"
echo ""
echo "To upload patient data to Firestore:"
echo "1. Go to Firebase Console: https://console.firebase.google.com/"
echo "2. Select your project"
echo "3. Go to Project Settings > Service Accounts"
echo "4. Click 'Generate new private key'"
echo "5. Save the file as 'scripts/serviceAccountKey.json'"
echo "6. Run: cd scripts && python3 upload_patients.py"
echo ""

# Step 8: Deploy
echo -e "${YELLOW}Step 8: Ready to Deploy!${NC}"
echo ""
read -p "Deploy now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Deploying to Firebase..."
    firebase deploy

    echo ""
    echo -e "${GREEN}=========================================="
    echo -e "✓ Deployment Complete!"
    echo -e "==========================================${NC}"
    echo ""
    echo "Your app is now live!"
    echo ""
    firebase open hosting:site
else
    echo ""
    echo "To deploy later, run:"
    echo "  firebase deploy"
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
