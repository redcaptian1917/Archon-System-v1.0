#!/usr/bin/env python3

import ollama
import chromadb
import sys

# --- Configuration ---
# NOTE: If running this script on a DIFFERENT machine from the
# server, change 'localhost' to the server's IP address.
OLLAMA_HOST = 'http://localhost:11434'
CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
EMBED_MODEL = 'nomic-embed-text' # The model we downloaded

print(f"--- FAPC Core Verification Script ---")

try:
    # --- 1. Connect to ChromaDB (The Memory) ---
    print(f"[1/4] Connecting to ChromaDB server at {CHROMA_HOST}:{CHROMA_PORT}...")
    # This connects to the server we just started
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    
    # Create or get a "collection" (like a table)
    collection = client.get_or_create_collection(name="fapc_project_context")
    print("     ... ChromaDB connection SUCCESSFUL.")

    # --- 2. Connect to Ollama (The Brain) ---
    print(f"[2/4] Connecting to Ollama server at {OLLAMA_HOST}...")
    # This uses the official Ollama Python client
    ollama_client = ollama.Client(host=OLLAMA_HOST)
    # Check if the embedding model is available
    ollama_client.show(EMBED_MODEL)
    print("     ... Ollama connection SUCCESSFUL.")

    # --- 3. Create and Store a "Memory" (RAG Ingestion) ---
    print(f"[3/4] Storing test memory...")
    test_document = "The PQC Monero Fork is the highest priority project to secure funding for PlausiDen and Defendology."
    test_id = "project-priority-001"

    # Generate the embedding (vector) using Ollama
    print(f"     ... Generating embedding with '{EMBED_MODEL}'...")
    response = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=test_document
    )
    embedding_vector = response["embedding"]

    # Store the document, its ID, and the vector in ChromaDB
    collection.add(
        embeddings=[embedding_vector],
        documents=[test_document],
        metadatas=[{"source": "startup_directive"}],
        ids=[test_id]
    )
    print("     ... Test memory STORED.")

    # --- 4. Retrieve the "Memory" (RAG Retrieval) ---
    print(f"[4/4] Retrieving test memory...")
    query_text = "What is the highest priority project?"
    
    # Generate an embedding for the QUERY
    query_embedding = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=query_text
    )["embedding"]

    # Search ChromaDB for the most similar vectors
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=1
    )

    retrieved_doc = results['documents'][0][0]
    print(f"     ... Query: '{query_text}'")
    print(f"     ... Retrieved: '{retrieved_doc}'")

    if test_document in retrieved_doc:
        print("\n--- VERIFICATION SUCCESSFUL ---")
        print("The FAPC core (Brain and Memory) is operational.")
    else:
        print("\n--- VERIFICATION FAILED ---")
        print("Retrieved document does not match test document.")

except Exception as e:
    print(f"\n--- SCRIPT FAILED ---", file=sys.stderr)
    print(f"Error: {e}", file=sys.stderr)
    print("Please check all services are running and accessible.", file=sys.stderr)
    sys.exit(1)