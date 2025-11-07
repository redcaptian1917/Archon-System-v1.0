#!/usr/bin/env python3

import chromadb
import argparse
import sys
from typing import Dict, Any, Optional

# --- Configuration ---
CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
CHROMA_COLLECTION = 'fapc_project_context'

def connect_to_chroma() -> Optional[chromadb.Collection]:
    """Connects to the running ChromaDB server and gets the collection."""
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        client.heartbeat() # Test connection
        collection = client.get_collection(name=CHROMA_COLLECTION)
        print(f"[INFO] Connected to ChromaDB and loaded collection '{CHROMA_COLLECTION}'.")
        return collection
    except Exception as e:
        print(f"[FATAL] Could not connect to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}.", file=sys.stderr)
        print(f"       Ensure ChromaDB is running and collection '{CHROMA_COLLECTION}' exists.", file=sys.stderr)
        print(f"       Error: {e}", file=sys.stderr)
        return None

def get_task(collection: chromadb.Collection, task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single task (document and metadata) by its ID."""
    print(f"[INFO] Fetching task '{task_id}'...")
    try:
        result = collection.get(
            ids=[task_id],
            include=["metadatas", "documents"] # Get all current data
        )
        
        if not result or not result.get('ids'):
            print(f"[ERROR] Task ID '{task_id}' not found in database.", file=sys.stderr)
            return None
        
        task_data = {
            "id": result['ids'][0],
            "document": result['documents'][0],
            "metadata": result['metadatas'][0]
        }
        print("[INFO] Task data retrieved successfully.")
        return task_data
        
    except Exception as e:
        print(f"[ERROR] Error fetching task '{task_id}': {e}", file=sys.stderr)
        return None

def update_task(collection: chromadb.Collection, task_data: Dict[str, Any], updates: Dict[str, Any]):
    """Updates the specified task in the ChromaDB collection."""
    
    # Get the current metadata and document
    task_id = task_data['id']
    current_metadata = task_data['metadata']
    current_document = task_data['document']
    
    # Create the new metadata object
    new_metadata = current_metadata.copy()
    update_log = []
    
    for key, value in updates.items():
        if value is not None: # Only update if a value was provided
            if key in new_metadata and new_metadata[key] != value:
                update_log.append(f"  - {key}: '{new_metadata[key]}' -> '{value}'")
            elif key not in new_metadata:
                update_log.append(f"  - {key}: (new) -> '{value}'")
            new_metadata[key] = value

    if not update_log:
        print("[INFO] No changes detected. Task is already up-to-date.")
        return

    print(f"[INFO] Updating task '{task_id}' with new metadata...")
    for log_entry in update_log:
        print(log_entry)

    try:
        # Use collection.update() to change *only* the metadata
        # for the existing document and embedding.
        collection.update(
            ids=[task_id],
            metadatas=[new_metadata],
            documents=[current_document] # We must re-supply the document
        )
        print(f"[SUCCESS] Task '{task_id}' has been updated.")
        
    except Exception as e:
        print(f"[ERROR] Failed to update task in database: {e}", file=sys.stderr)

def main():
    # 1. Setup command-line argument parsing
    parser = argparse.ArgumentParser(description="FAPC Task Management Agent")
    
    # Required argument: The ID of the task to modify
    parser.add_argument(
        "task_id",
        type=str,
        help="The unique ID of the task to update (e.g., 'task_...')."
    )
    
    # Optional arguments for metadata fields
    parser.add_argument(
        "--status",
        type=str,
        choices=['new', 'in_progress', 'completed', 'blocked'],
        help="Set a new status for the task."
    )
    parser.add_argument(
        "--priority",
        type=str,
        choices=['Low', 'Medium', 'High', 'Critical'],
        help="Set a new priority for the task."
    )
    parser.add_argument(
        "--project",
        type=str,
        choices=['PlausiDen', 'Defendology', 'PQC-Monero', 'FAPC-AI', 'General-Ops'],
        help="Re-assign the task to a different project."
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Update the title of the task."
    )
    
    args = parser.parse_args()
    
    # Collect all provided updates into a dictionary
    updates_to_make = {
        "status": args.status,
        "priority": args.priority,
        "project": args.project,
        "title": args.title
    }

    print(f"--- Task Management Agent Initialized ---")
    
    # 2. Connect to ChromaDB
    collection = connect_to_chroma()
    if not collection:
        sys.exit(1)
        
    # 3. Get the task to be updated
    task_data = get_task(collection, args.task_id)
    if not task_data:
        sys.exit(1)
        
    # 4. Apply the updates
    update_task(collection, task_data, updates_to_make)
    
    print("--- Task Management Agent Finished ---")

if __name__ == "__main__":
    main()