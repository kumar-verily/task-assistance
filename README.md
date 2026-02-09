# Pinecone Python Quickstart

This project demonstrates how to use Pinecone for semantic search with integrated embeddings and reranking.

## What You've Accomplished

✅ **Index Creation**: Created a Pinecone serverless index with integrated `llama-text-embed-v2` embeddings
✅ **Data Ingestion**: Upserted 12 sample documents with metadata across multiple categories
✅ **Semantic Search**: Performed searches based on meaning, not just keyword matching
✅ **Reranking**: Used the `bge-reranker-v2-m3` model to improve result relevance

## Files

- **`.env`** - Contains your Pinecone API key (never commit this!)
- **`quickstart.py`** - Main quickstart script demonstrating search functionality
- **`setup.sh`** - Automated setup script
- **`venv/`** - Python virtual environment with dependencies

## Quick Start

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Run the quickstart:**
   ```bash
   python quickstart.py
   ```

## Try Different Queries

Edit `quickstart.py` and change the query on line 67:

```python
# Try these queries:
query = "Famous historical structures and monuments"
query = "Art and paintings"
query = "Scientific processes and energy"
query = "Music and instruments"
```

## Key Concepts Learned

### 1. Integrated Embeddings
The index automatically converts text to vectors using the `llama-text-embed-v2` model:
```python
index.upsert_records("namespace", records)
# No need to generate embeddings manually!
```

### 2. Namespaces
Namespaces provide data isolation (useful for multi-tenant applications):
```python
index.upsert_records("example-namespace", records)
index.search(namespace="example-namespace", ...)
```

### 3. Semantic Search
Searches based on meaning, not just keywords:
```python
query = "Famous historical structures"
# Returns: Eiffel Tower, Taj Mahal, Great Wall, etc.
```

### 4. Reranking
Improves relevance by re-scoring initial results:
```python
rerank={
    "model": "bge-reranker-v2-m3",
    "top_n": 10,
    "rank_fields": ["content"]
}
```

## Index Details

- **Name**: `agentic-quickstart-test`
- **Model**: `llama-text-embed-v2` (1024 dimensions)
- **Metric**: Cosine similarity
- **Cloud**: AWS, us-east-1 (serverless)
- **Field Mapping**: `text` → `content` (embeds the "content" field from your records)

## Next Steps

### Explore More Quickstarts

The `.agents/` directory contains guides for:
- **Semantic Search System** - Build production search with filtering
- **Multi-Tenant RAG System** - Retrieval-augmented generation with LLMs
- **Recommendation Engine** - Suggest similar items using semantic similarity

### View Your Data

Visit the Pinecone console to explore your index:
https://app.pinecone.io/

### Clean Up

When you're done experimenting, delete the test index:
```bash
export PATH="$HOME/.local/bin:$PATH"
pc index delete --name agentic-quickstart-test
```

## Resources

- **Pinecone Documentation**: https://docs.pinecone.io/
- **Python SDK Reference**: See `.agents/PINECONE-python.md`
- **CLI Reference**: See `.agents/PINECONE-cli.md`
- **Troubleshooting**: See `.agents/PINECONE-troubleshooting.md`

## Important Best Practices

1. **Always use namespaces** - Every operation should specify a namespace
2. **Wait after upserting** - Wait 10+ seconds before searching newly upserted data
3. **Use reranking** - Improves result quality significantly
4. **Match field names** - Record fields must match the `field-map` used during index creation
5. **Keep API keys secure** - Never commit `.env` files to version control

## Architecture

```
quickstart.py
    ↓
Pinecone SDK (pinecone==8.0.0)
    ↓
Index: agentic-quickstart-test
    ↓
llama-text-embed-v2 (embeddings)
    ↓
Vector Search + Reranking
    ↓
Results
```
