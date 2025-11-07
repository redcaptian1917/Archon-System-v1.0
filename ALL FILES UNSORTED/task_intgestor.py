#!/usr/bin/env python3

import ollama
import chromadb
import argparse
import json
import sys
import uuid
from typing import Dict, Any

# --- Configuration ---
# These settings connect to the services you already have running.
OLLAMA_HOST = 'http://localhost:11434'
OLLAMA_REASONING_MODEL = 'llama3:8b'     # The "brain" for processing tasks
OLLAMA_EMBED_MODEL = 'nomic-embed-text'  # The model for vectorizing

CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
CHROMA_COLLECTION = 'fapc_project_context' # The same collection from verify.py

# This is the "system prompt" that forces the LLM to be a good task parser.
# It commands the LLM to return *only* a JSON object.
TASK_PROCESSING_PROMPT_TEMPLATE = """
You are a 'Task Ingestor Agent' for a project management system.
Your sole purpose is to analyze a raw task description from the user
and convert it into a structured JSON object.

The user's raw text will be provided.

You MUST respond with *only* the JSON object and no other text,
preamble, or explanation.

The JSON object MUST have the following schema:
{
  "title": "A concise, descriptive title for the task (max 10 words)",
  "summary": "A detailed, one-paragraph summary of the task and its objective",
  "priority": "One of: 'Low', 'Medium', 'High', 'Critical'",
  "project": "The most relevant project. One of: 'PlausiDen', 'Defendology', 'PQC-Monero', 'FAPC-AI', 'General-Ops'"
}

Here is the raw task from the user:
"{raw_task_text}"
"""

def connect_clients() -> (ollama.Client, chromadb.Collection):
    """Connects to Ollama and ChromaDB servers."""
    try:
        # Connect to Ollama (The Brain)
        ollama_client = ollama.Client(host=OLLAMA_HOST)
        ollama_client.show(OLLAMA_REASONING_MODEL) # Check if model exists
        ollama_client.show(OLLAMA_EMBED_MODEL)     # Check if model exists
        print("[INFO] Connected to Ollama server.")
    except Exception as e:
        print(f"[FATAL] Could not connect to Ollama at {OLLAMA_HOST}.", file=sys.stderr)
        print(f"       Ensure Ollama is running: 'sudo systemctl status ollama'", file=sys.stderr)
        print(f"       Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Connect to ChromaDB (The Memory)
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION)
        print(f"[INFO] Connected to ChromaDB and loaded collection '{CHROMA_COLLECTION}'.")
    except Exception as e:
        print(f"[FATAL] Could not connect to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}.", file=sys.stderr)
        print(f"       Ensure ChromaDB is running: 'chroma run --host 0.0.0.0 --port 8000 ...'", file=sys.stderr)
        print(f"       Error: {e}", file=sys.stderr)
        sys.exit(1)
        
    return ollama_client, collection

def process_task_with_llm(client: ollama.Client, raw_task: str) -> Dict[str, Any]:
    """Uses the LLM to parse the raw task into structured JSON."""
    print(f"[INFO] Processing task with '{OLLAMA_REASONING_MODEL}'...")
    
    # Format the full prompt with the user's raw task
    prompt = TASK_PROCESSING_PROMPT_TEMPLATE.format(raw_task_text=raw_task)
    
    try:
        response = client.chat(
            model=OLLAMA_REASONING_MODEL,
            messages=[{'role': 'system', 'content': prompt}],
            options={'temperature': 0.0} # Low temp for deterministic JSON
        )
        
        # The LLM's response content
        json_response_str = response['message']['content']
        
        # Clean up the response, as LLMs sometimes add markdown fencing
        json_response_str = json_response_str.strip().replace('```json', '').replace('```', '')
        
        # Parse the JSON string into a Python dictionary
        processed_data = json.loads(json_response_str)
        
        print("[INFO] LLM processing successful. Structured data extracted.")
        return processed_data

    except json.JSONDecodeError:
        print(f"[ERROR] LLM returned invalid JSON:\n{json_response_str}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] Error during LLM processing: {e}", file=sys.stderr)
        return None

def embed_and_store_task(
    ollama_client: ollama.Client,
    collection: chromadb.Collection,
    processed_task: Dict[str, Any]
) -> str:
    """Generates an embedding and stores the task in ChromaDB."""
    
    print(f"[INFO] Generating embedding with '{OLLAMA_EMBED_MODEL}'...")
    
    # We embed the "summary" as it's the most descriptive part
    document_to_embed = processed_task['summary']
    
    try:
        # 1. Generate the embedding vector
        response = ollama.embeddings(
            model=OLLAMA_EMBED_MODEL,
            prompt=document_to_embed
        )
        embedding_vector = response["embedding"]
        
        # 2. Generate a unique ID for this task
        task_id = f"task_{uuid.uuid4()}"
        
        # 3. Create the metadata object
        # This is CRITICAL for filtering later
        metadata = {
            "title": processed_task['title'],
            "priority": processed_task['priority'],
            "project": processed_task['project'],
            "status": "new" # We can add a status field
        }
        
        # 4. Store in ChromaDB
        collection.add(
            ids=[task_id],
            embeddings=[embedding_vector],
            documents=[document_to_embed], # The main text content
            metadatas=[metadata]           # The filterable structured data
        )
        
        print(f"[SUCCESS] Task '{task_id}' stored in vector memory.")
        print(f"  - Title: {metadata['title']}")
        print(f"  - Project: {metadata['project']}")
        print(f"  - Priority: {metadata['priority']}")
        return task_id

    except Exception as e:
        print(f"[ERROR] Failed to embed or store task: {e}", file=sys.stderr)
        return None

def main():
    # 1. Setup command-line argument parsing
    parser = argparse.ArgumentParser(description="FAPC Task Ingestor Agent")
    parser.add_argument(
        "task_text",
        type=str,
        nargs='+', # This captures all following text as a list of strings
        help="The raw text description of the task."
    )
    args = parser.parse_args()
    
    # Join the list of strings into a single sentence
    raw_task_text = " ".join(args.task_text)
    print(f"--- Task Ingestor Agent Initialized ---")
    print(f"[INPUT] Raw Task: \"{raw_task_text}\"")
    
    # 2. Connect to services
    ollama_client, collection = connect_clients()
    
    # 3. Process the task with the LLM
    processed_task = process_task_with_llm(ollama_client, raw_task_text)
    
    if not processed_task:
        print("[FATAL] Could not process task. Aborting.", file=sys.stderr)
        sys.exit(1)
        
    # 4. Embed and store the task
    task_id = embed_and_store_task(ollama_client, collection, processed_task)
    
    if not task_id:
        print("[FATAL] Could not store task. Aborting.", file=sys.stderr)
        sys.exit(1)
        
    print("--- Task Ingestor Agent Finished ---")

if __name__ == "__main__":
    main()