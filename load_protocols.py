#!/usr/bin/env python3
"""
Load clinical protocols into Pinecone RAG index
"""

import json
import time
from pinecone import Pinecone
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("clinical-protocols-rag")

def load_protocols():
    """Load protocols from JSONL file into Pinecone"""

    print("Loading protocols from clinical_protocols.jsonl...")

    protocols = []
    with open('clinical_protocols.jsonl', 'r') as f:
        for line in f:
            protocol = json.loads(line.strip())
            protocols.append(protocol)

    print(f"Loaded {len(protocols)} protocols from file")

    # Prepare records for Pinecone
    # We'll create searchable content from multiple fields
    records = []
    for protocol in protocols:
        # Create rich searchable content
        content_parts = [
            f"Task: {protocol['task_name']}",
            f"Code: {protocol['task_code']}",
            f"Priority: {protocol['priority']}",
            f"Program: {protocol['program']}",
        ]

        if protocol.get('trigger'):
            content_parts.append(f"Trigger: {protocol['trigger']}")

        if protocol.get('triggering_criteria'):
            content_parts.append(f"Criteria: {protocol['triggering_criteria']}")

        # Add steps
        if protocol.get('steps'):
            if isinstance(protocol['steps'], dict):
                for step_type, step_content in protocol['steps'].items():
                    content_parts.append(f"Steps ({step_type}): {step_content}")
            else:
                content_parts.append(f"Steps: {protocol['steps']}")

        # Add roles
        if protocol.get('roles'):
            content_parts.append(f"Roles: {', '.join(protocol['roles'])}")

        # Combine all parts
        content = "\n".join(content_parts)

        record = {
            "_id": protocol['chunk_id'],
            "content": content,
            "task_code": protocol['task_code'],
            "task_name": protocol['task_name'],
            "priority": protocol['priority'],
            "program": protocol['program'],
            "full_text": protocol.get('full_text', ''),
            "roles": ','.join(protocol.get('roles', [])),
        }

        records.append(record)

    print(f"\nPrepared {len(records)} records for upload")

    # Upload in batches (max 96 for text records)
    batch_size = 96
    total_batches = (len(records) + batch_size - 1) // batch_size

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        print(f"Uploading batch {batch_num}/{total_batches} ({len(batch)} records)...")
        index.upsert_records("protocols", batch)
        time.sleep(0.5)  # Small delay between batches

    print("\n✓ All protocols uploaded successfully!")

    # Wait for indexing
    print("\nWaiting 10 seconds for indexing to complete...")
    time.sleep(10)

    # Show stats
    stats = index.describe_index_stats()
    print(f"\nIndex Statistics:")
    print(f"  Total vectors: {stats.total_vector_count}")
    print(f"  Namespaces: {list(stats.namespaces.keys())}")
    if stats.namespaces:
        for ns, ns_stats in stats.namespaces.items():
            print(f"    - {ns}: {ns_stats.vector_count} vectors")

if __name__ == "__main__":
    print("="*80)
    print("CLINICAL PROTOCOLS RAG SYSTEM - DATA LOADER")
    print("="*80)
    print()

    # Wait for index to be ready
    print("Checking if index is ready...")
    time.sleep(5)

    try:
        load_protocols()
        print("\n" + "="*80)
        print("SUCCESS! Protocols are now searchable in Pinecone")
        print("="*80)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
