#!/usr/bin/env python3

import ollama
import chromadb
import argparse
import json
import sys
from typing import Dict, Any, List

# --- Configuration ---
# Connects to the services you already have running.
OLLAMA_HOST = 'http://localhost:11434'
OLLAMA_REASONING_MODEL = 'llama3:8b'     # The "brain" for parsing queries
OLLAMA_EMBED_MODEL = 'nomic-embed-text'  # The model for vectorizing

CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
CHROMA_COLLECTION = 'fapc_project_context'

# This prompt forces the LLM to act as a query parser,
# converting natural language into a structured database query.
QUERY_PARSING_PROMPT_TEMPLATE = """
You are a 'Query Parsing Agent' for a project management system.
Your sole purpose is to analyze a raw user query and convert it into a
structured JSON object for searching a vector database.

You MUST respond with *only* the JSON object and no other text,
preamble, or explanation.

The JSON object MUST have the following schema:
{
  "query_text": "The core semantic meaning of the query. What is the user looking for? (e.g., 'cryptography research', 'website design'). If no specific subject is mentioned, use 'all tasks'.",
  "where_filter": {
    "key_1": "value_1",
    "key_2": "value_2"
  }
}

The 'where_filter' object is for metadata filtering.
- It should be an EMPTY object ({}) if no filters are mentioned.
- Valid filter keys are: "project", "priority", "status".

- Valid values for "project": ["PlausiDen", "Defendology", "PQC-Monero", "FAPC-AI", "General-Ops"]
- Valid values for "priority": ["Low", "Medium", "High", "Critical"]
- Valid values for "status": ["new", "in_progress", "completed"]

If a user mentions a filter, use the exact value from the valid values list.
If a user mentions multiple filters (e.g., "critical plausiden tasks"),
include both in the filter object (e.g., {"priority": "Critical", "project": "PlausiDen"}).

Here is the raw query from the user:
"{raw_query_text}"
"""

def connect_clients() -> (ollama.Client, chromadb.Collection):
    """Connects to Ollama and ChromaDB servers."""
    try:
        ollama_client = ollama.Client(host=OLLAMA_HOST)
        ollama_client.show(OLLAMA_REASONING_MODEL)
        ollama_client.show(OLLAMA_EMBED_MODEL)
        print("[INFO] Connected to Ollama server.")
    except Exception as e:
        print(f"[FATAL] Could not connect to Ollama at {OLLAMA_HOST}.", file=sys.stderr)
        print(f"       Ensure Ollama is running.", file=sys.stderr)
        sys.exit(1)

    try:
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = chroma_client.get_collection(name=CHROMA_COLLECTION)
        print(f"[INFO] Connected to ChromaDB and loaded collection '{CHROMA_COLLECTION}'.")
    except Exception as e:
        print(f"[FATAL] Could not connect to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}.", file=sys.stderr)
        print(f"       Ensure ChromaDB is running and collection '{CHROMA_COLLECTION}' exists.", file=sys.stderr)
        sys.exit(1)
        
    return ollama_client, collection

def parse_query_with_llm(client: ollama.Client, raw_query: str) -> (str, Dict[str, Any]):
    """Uses the LLM to parse the raw query into semantic text and a metadata filter."""
    print(f"[INFO] Parsing query with '{OLLAMA_REASONING_MODEL}'...")
    
    prompt = QUERY_PARSING_PROMPT_TEMPLATE.format(raw_query_text=raw_query)
    
    try:
        response = client.chat(
            model=OLLAMA_REASONING_MODEL,
            messages=[{'role': 'system', 'content': prompt}],
            options={'temperature': 0.0} # Deterministic output
        )
        
        json_response_str = response['message']['content'].strip().replace('```json', '').replace('```', '')
        
        parsed_data = json.loads(json_response_str)
        
        query_text = parsed_data.get('query_text', 'all tasks')
        where_filter = parsed_data.get('where_filter', {})
        
        print(f"[INFO] Query parsed successfully.")
        print(f"       - Semantic Query: '{query_text}'")
        print(f"       - Metadata Filter: {where_filter}")
        
        return query_text, where_filter

    except Exception as e:
        print(f"[ERROR] Failed to parse query with LLM: {e}", file=sys.stderr)
        print(f"       LLM Response: {json_response_str}", file=sys.stderr)
        # Fallback to a simple search if parsing fails
        print("[WARN] LLM parsing failed. Falling back to simple semantic search.")
        return raw_query, {}

def query_vector_memory(
    ollama_client: ollama.Client,
    collection: chromadb.Collection,
    query_text: str,
    where_filter: Dict[str, Any],
    n_results: int = 5
) -> List[Dict[str, Any]]:
    """Searches the vector database using both semantic text and metadata filters."""
    
    print(f"[INFO] Generating embedding for query with '{OLLAMA_EMBED_MODEL}'...")
    
    try:
        # 1. Generate the embedding for the semantic query text
        query_embedding = ollama.embeddings(
            model=OLLAMA_EMBED_MODEL,
            prompt=query_text
        )["embedding"]
        
        # 2. Query ChromaDB
        # This is the core of the search. It uses BOTH the vector AND the filter.
        if where_filter:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter # Apply the metadata filter
            )
        else:
            # If no filter, just do a pure semantic search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
        
        print(f"[INFO] Vector search complete. Found {len(results.get('ids', [[]])[0])} results.")
        
        # 3. Format the results into a clean list of dictionaries
        formatted_results = []
        if not results.get('ids', [[]])[0]:
            return []
            
        for i in range(len(results['ids'][0])):
            task = {
                "id": results['ids'][0][i],
                "summary": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] # How "similar" it is
            }
            formatted_results.append(task)
            
        return formatted_results

    except Exception as e:
        print(f"[ERROR] Failed to query vector memory: {e}", file=sys.stderr)
        return []

def print_results(results: List[Dict[str, Any]]):
    """Prints the retrieved tasks in a readable format."""
    
    if not results:
        print("\n--- No tasks found matching your query. ---")
        return

    print(f"\n--- FAPC Project Status Report ---")
    print(f"Found {len(results)} matching task(s):\n")
    
    for task in results:
        meta = task['metadata']
        print(f"----------------------------------------")
        print(f"  TASK:     {meta.get('title', 'N/A')}")
        print(f"  PROJECT:  {meta.get('project', 'N/A')}")
        print(f"  PRIORITY: {meta.get('priority', 'N/A')}")
        print(f"  STATUS:   {meta.get('status', 'N/A')}")
        print(f"  ID:       {task['id']}")
        print(f"  SUMMARY:  {task['summary']}")
        # print(f"  (Similarity: {task['distance']:.4f})") # Uncomment for debugging
    
    print(f"----------------------------------------")
    print("--- End of Report ---")

def main():
    parser = argparse.ArgumentParser(description="FAPC Project Status Agent")
    parser.add_argument(
        "query_text",
        type=str,
        nargs='+',
        help="The natural language query about your projects."
    )
    parser.add_argument(
        "-n", "--num_results",
        type=int,
        default=5,
        help="The maximum number of results to return."
    )
    args = parser.parse_args()
    
    raw_query_text = " ".join(args.query_text)
    print(f"--- Project Status Agent Initialized ---")
    print(f"[INPUT] Raw Query: \"{raw_query_text}\"")
    
    # 1. Connect to services
    ollama_client, collection = connect_clients()
    
    # 2. Parse the raw query using the LLM
    query_text, where_filter = parse_query_with_llm(ollama_client, raw_query_text)
    
    # 3. Retrieve tasks from vector memory
    results = query_vector_memory(
        ollama_client,
        collection,
        query_text,
        where_filter,
        args.num_results
    )
    
    # 4. Display the results
    print_results(results)
    
    print("--- Project Status Agent Finished ---")

if __name__ == "__main__":
    main()