#!/bin/bash

# Pinecone Quick Test Setup Script
# This script helps you set up and run the Pinecone quick test

set -e

echo "=========================================="
echo "Pinecone Quick Test Setup"
echo "=========================================="
echo ""

# Add CLI to PATH
export PATH="$HOME/.local/bin:$PATH"

# Check if API key is set in .env
if ! grep -q "PINECONE_API_KEY=pcsk-" .env 2>/dev/null; then
    echo "⚠️  STEP 1: Set your Pinecone API key"
    echo ""
    echo "Please edit the .env file and replace 'your-api-key-here' with your actual API key."
    echo "You can get your API key from: https://app.pinecone.io/"
    echo ""
    echo "After updating .env, run this script again."
    exit 1
fi

echo "✓ API key found in .env"
echo ""

# Load API key into environment
source .env
export PINECONE_API_KEY

# Check if index already exists
if pc index list | grep -q "agentic-quickstart-test"; then
    echo "✓ Index 'agentic-quickstart-test' already exists"
else
    echo "Creating index 'agentic-quickstart-test'..."
    pc index create -n agentic-quickstart-test -m cosine -c aws -r us-east-1 --model llama-text-embed-v2 --field-map text=content

    echo ""
    echo "Waiting 5 seconds for index to be ready..."
    sleep 5
    echo "✓ Index created successfully"
fi

echo ""
echo "=========================================="
echo "Running Quick Test"
echo "=========================================="
echo ""

# Activate virtual environment and run the script
source venv/bin/activate
python quickstart.py

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "You can now:"
echo "  1. View your index in the Pinecone console: https://app.pinecone.io/"
echo "  2. Modify quickstart.py to try different queries"
echo "  3. Explore other quickstart examples:"
echo "     - Semantic Search System"
echo "     - Multi-Tenant RAG System"
echo "     - Recommendation Engine"
echo ""
echo "To delete the test index when done:"
echo "  pc index delete --name agentic-quickstart-test"
echo ""
