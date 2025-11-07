#!/usr/bin/env python3

import os
import argparse
import sys
import auth
import db_manager
import ollama
import psycopg2
from pgvector.psycopg2 import register_vector
import time

# --- Configuration ---
# These must match your v11+ tools and DB
EMBED_MODEL = 'nomic-embed-text'
OLLAMA_HOST = 'http://ollama:11434' # Docker service name
CHUNK_SIZE = 512 # Number of characters per "fact"
FILE_EXTENSIONS = ('.py', '.md', '.txt', '.c', '.cpp', '.h', '.sh', '.json')

# --- Embedding Function ---
# (Duplicated from fapc_tools for this standalone script)
def get_embedding(text_to_embed: str) -> list:
    """Generates an embedding vector for a string."""
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        response = client.embeddings(
            model=EMBED_MODEL,
            prompt=text_to_embed
        )
        return response["embedding"]
    except Exception as e:
        print(f"  [ERROR] Failed to get embedding: {e}", file=sys.stderr)
        return None

# --- Text Chunking Function ---
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list:
    """Splits a large text into smaller, overlapping chunks."""
    chunks = []
    for i in range(0, len(text), chunk_size - 50): # 50-char overlap
        chunks.append(text[i:i + chunk_size])
    return chunks

# --- Learning Function ---
def learn_fact(conn, fact: str, user_id: int, file_path: str):
    """
    Saves a new fact to the knowledge base.
    (This is a direct-to-db version of the tool)
    """
    # 1. Generate the embedding
    embedding = get_embedding(fact)
    if embedding is None:
        print(f"  [SKIP] Could not generate embedding for a chunk from {file_path}.")
        return False
    
    # 2. Store the fact and its embedding
    try:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_base (owner_user_id, fact_text, embedding)
                VALUES (%s, %s, %s)
                """,
                (user_id, fact, embedding)
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to insert fact: {e}", file=sys.stderr)
        conn.rollback()
        return False

# --- Main Priming Logic ---
def main():
    parser = argparse.ArgumentParser(description="Archon Knowledge Base Primer")
    parser.add_argument(
        "directory",
        type=str,
        help="The full path to the directory to scan for knowledge (e.g., '/app/my_projects')."
    )
    args = parser.parse_args()

    # 1. AUTHENTICATE
    print("--- Archon Knowledge Primer ---")
    try:
        user_id, privilege = auth.main_auth_flow(required_privilege='admin')
        if user_id is None:
            sys.exit(1)
    except Exception as e:
        print(f"[FATAL] Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[PRIMER] Starting scan of directory: {args.directory}")
    print(f"[PRIMER] Will import for user_id: {user_id}")
    
    conn = db_manager.db_connect()
    if not conn:
        sys.exit(1)
        
    total_files = 0
    total_chunks = 0

    try:
        # 2. WALK DIRECTORY
        for root, dirs, files in os.walk(args.directory):
            # Skip hidden directories like .git, .vscode, etc.
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            files = [f for f in files if not f.startswith('.')]
            
            for file in files:
                if file.endswith(FILE_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    print(f"\n[PRIMER] Processing: {file_path}")
                    total_files += 1
                    
                    try:
                        # 3. READ FILE
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        if not content:
                            print("  [SKIP] File is empty.")
                            continue
                            
                        # 4. CHUNK TEXT
                        chunks = chunk_text(content)
                        print(f"  [INFO] Split into {len(chunks)} chunks.")
                        
                        # 5. LEARN (INSERT) CHUNKS
                        chunks_added = 0
                        for chunk in chunks:
                            # Prepend file path as context
                            fact_with_context = f"File: '{file_path}'\n\nContent:\n{chunk}"
                            
                            if learn_fact(conn, fact_with_context, user_id, file_path):
                                chunks_added += 1
                                total_chunks += 1
                                
                            time.sleep(0.1) # Be nice to the Ollama server
                            
                        print(f"  [SUCCESS] Added {chunks_added} facts from this file.")

                    except Exception as e:
                        print(f"  [ERROR] Failed to process file {file_path}: {e}", file=sys.stderr)
                        
    except KeyboardInterrupt:
        print("\n[PRIMER] Manual interruption. Stopping.")
    finally:
        conn.close()
        
    print("\n--- Priming Complete ---")
    print(f"Processed: {total_files} files")
    print(f"Learned:   {total_chunks} new facts")
    auth.log_activity(user_id, 'kb_primer', f"Primed {total_chunks} facts from {total_files} files.", 'success')

if __name__ == "__main__":
    main()