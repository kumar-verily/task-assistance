#!/usr/bin/env python3
"""
Common Pinecone Operations
Examples of frequent operations you'll use in real applications
"""

from pinecone import Pinecone
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agentic-quickstart-test")

def view_index_stats():
    """Check index statistics and namespaces"""
    print("\n" + "="*80)
    print("INDEX STATISTICS")
    print("="*80)

    stats = index.describe_index_stats()
    print(f"\nTotal vectors: {stats.total_vector_count}")
    print(f"\nNamespaces:")
    for ns, ns_stats in stats.namespaces.items():
        print(f"  - {ns}: {ns_stats.vector_count} vectors")

def fetch_specific_records():
    """Retrieve specific records by ID"""
    print("\n" + "="*80)
    print("FETCH RECORDS BY ID")
    print("="*80)

    # Fetch a few specific records
    record_ids = ["rec1", "rec7", "rec15"]
    result = index.fetch(namespace="example-namespace", ids=record_ids)

    print(f"\nFetched {len(result.vectors)} records:\n")
    for record_id, record in result.vectors.items():
        print(f"ID: {record_id}")
        print(f"  Content: {record.metadata['content']}")
        print(f"  Category: {record.metadata['category']}")
        print()

def list_all_record_ids():
    """List all record IDs in a namespace"""
    print("\n" + "="*80)
    print("LIST ALL RECORD IDs")
    print("="*80)

    all_ids = []

    # list() returns a generator that yields pages of IDs
    for page in index.list(namespace="example-namespace", limit=100):
        all_ids.extend(page)

    print(f"\nFound {len(all_ids)} records:")
    for record_id in sorted(all_ids):
        print(f"  - {record_id}")

def search_with_filter():
    """Search with metadata filtering"""
    print("\n" + "="*80)
    print("SEARCH WITH METADATA FILTER")
    print("="*80)

    # Search only within the "history" category
    query = "ancient civilizations and landmarks"
    print(f"\nQuery: '{query}'")
    print("Filter: category = 'history'\n")

    results = index.search(
        namespace="example-namespace",
        query={
            "top_k": 5,
            "inputs": {"text": query},
            "filter": {"category": {"$eq": "history"}}
        },
        rerank={
            "model": "bge-reranker-v2-m3",
            "top_n": 5,
            "rank_fields": ["content"]
        }
    )

    print("Results (history only):")
    for i, hit in enumerate(results['result']['hits'], 1):
        print(f"{i}. {hit['fields']['content']}")
        print(f"   Category: {hit['fields']['category']}, Score: {round(hit['_score'], 3)}")
        print()

def search_by_category():
    """Show results grouped by category"""
    print("\n" + "="*80)
    print("SEARCH ACROSS ALL CATEGORIES")
    print("="*80)

    query = "creative works and masterpieces"
    print(f"\nQuery: '{query}'\n")

    results = index.search(
        namespace="example-namespace",
        query={
            "top_k": 10,
            "inputs": {"text": query}
        },
        rerank={
            "model": "bge-reranker-v2-m3",
            "top_n": 10,
            "rank_fields": ["content"]
        }
    )

    # Group by category
    by_category = {}
    for hit in results['result']['hits']:
        category = hit['fields']['category']
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(hit)

    print("Results grouped by category:\n")
    for category, hits in sorted(by_category.items()):
        print(f"{category.upper()}:")
        for hit in hits[:3]:  # Top 3 per category
            print(f"  - {hit['fields']['content']}")
            print(f"    Score: {round(hit['_score'], 3)}")
        print()

def upsert_new_records():
    """Add new records to the index"""
    print("\n" + "="*80)
    print("UPSERT NEW RECORDS")
    print("="*80)

    new_records = [
        {
            "_id": "rec_new1",
            "content": "The Golden Gate Bridge spans the San Francisco Bay.",
            "category": "engineering"
        },
        {
            "_id": "rec_new2",
            "content": "Mount Everest is the highest peak in the world.",
            "category": "geography"
        }
    ]

    print(f"\nAdding {len(new_records)} new records...\n")
    for record in new_records:
        print(f"  - {record['_id']}: {record['content']}")

    index.upsert_records("example-namespace", new_records)
    print("\n✓ Records added successfully!")
    print("  Note: Wait ~10 seconds before searching for these records")

def update_existing_records():
    """Update metadata for existing records"""
    print("\n" + "="*80)
    print("UPDATE EXISTING RECORDS")
    print("="*80)

    # Update an existing record (same ID, new/updated fields)
    updated_records = [
        {
            "_id": "rec1",
            "content": "The Eiffel Tower was completed in 1889 and stands in Paris, France.",
            "category": "history",
            "year": 1889,
            "location": "Paris"
        }
    ]

    print("\nUpdating record 'rec1' with new metadata fields (year, location)...")
    index.upsert_records("example-namespace", updated_records)
    print("✓ Record updated successfully!")

def delete_records():
    """Delete specific records"""
    print("\n" + "="*80)
    print("DELETE RECORDS")
    print("="*80)

    # Note: Uncomment to actually delete
    print("\nExample (commented out to preserve quickstart data):")
    print("  index.delete(namespace='example-namespace', ids=['rec_new1', 'rec_new2'])")
    print("\nTo delete all records in a namespace:")
    print("  index.delete(namespace='example-namespace', delete_all=True)")

def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("PINECONE COMMON OPERATIONS EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates common operations you'll use frequently.")

    # Read operations
    view_index_stats()
    list_all_record_ids()
    fetch_specific_records()

    # Search operations
    search_with_filter()
    search_by_category()

    # Write operations
    print("\n" + "="*80)
    print("WRITE OPERATIONS (Uncomment in code to run)")
    print("="*80)
    print("\nThe following operations are available but commented out")
    print("to preserve the quickstart data:")
    print("  1. upsert_new_records() - Add new documents")
    print("  2. update_existing_records() - Update metadata")
    print("  3. delete_records() - Remove documents")

    # Uncomment these to try write operations:
    # upsert_new_records()
    # update_existing_records()
    # delete_records()

    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print("\nModify this script to experiment with different operations.")

if __name__ == "__main__":
    main()
