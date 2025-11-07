#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - KNOWLEDGE BASE PRIMER (vFINAL)
#
# This is a one-time-use, 'admin-only' utility script.
#
# Its purpose is to perform a "brain dump" by recursively scanning
# a directory (e.g., your projects folder) and "teaching" all
# text-based files to the Archon agent's permanent memory.
#
# This script is "standalone" and duplicates the 'learn_fact_tool'
# logic to avoid circular dependencies.
# -----------------------------------------------------------------

import os
import argparse
import sys
import time
from datetime import datetime, timedelta, timezone

# --- External Libraries ---
import ollama
import psycopg2
from pgvector.psycopg2 import register_vector

# --- Internal Imports ---
try:
    import auth
    import db_manager
except ImportError:
    print("CRITICAL: auth.py or db_manager.py not found.", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
# Must match your Docker environment
EMBED_MODEL = 'nomic-embed-text'
OLLAMA_HOST = 'http://ollama:11434' # Docker service name

# How large each "fact" should be
CHUNK_SIZE = 512 # characters
CHUNK_OVERLAP = 50 # characters

# What files to read
FILE_EXTENSIONS = (
    '.py', '.md', '.txt', '.json', '.yml', '.yaml', '.sh', '.c', '.cpp', '.h',
    '.js', '.ts', '.html', '.css', '.dockerfile', '.conf'
)

# What directories to skip
SKIP_DIRS = (
    '.git', '.vscode', '__pycache__', 'node_modules',
    '.venv', 'venv', 'dist', 'build'
)

# ---
# 1. HELPER FUNCTIONS (Duplicated from fapc_tools.py)
# ---

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

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list:
    """Splits a large text into smaller, overlapping chunks."""
    chunks = []
    for i in range(0, len(text), chunk_size - CHUNK_OVERLAP):
        chunks.append(text[i:i + chunk_size])
    return chunks

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
    # We set importance to 50 ('nice to have') by default
    try:
        register_vector(conn) # Enable pgvector for this connection
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_base (owner_user_id, fact_text, embedding, 
                                            importance_score, do_not_delete)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, fact, embedding, 50, False)
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to insert fact: {e}", file=sys.stderr)
        conn.rollback()
        return False

# ---
# 2. MAIN PRIMING LOGIC
# ---
def main():
    parser = argparse.ArgumentParser(
        description="Archon Knowledge Base Primer",
        epilog="Example: ./knowledge_primer.py /app/agents"
    )
    parser.add_argument(
        "directory",
        type=str,
        help="The full path to the directory to scan for knowledge (e.g., '/app/agents')."
    )
    args = parser.parse_args()

    # 1. AUTHENTICATE (Admin Only)
    print("--- Archon Knowledge Primer ---")
    try:
        # This script modifies the AI's core brain, it MUST be admin-only.
        user_id, privilege, username = auth.main_auth_flow(required_privilege='admin')
    except Exception as e:
        print(f"[FATAL] Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[PRIMER] Starting scan of directory: {args.directory}")
    print(f"[PRIMER] Will import for user_id: {user_id} ({username})")
    
    conn = db_manager.db_connect()
    if not conn:
        sys.exit(1)
        
    total_files = 0
    total_chunks = 0
    start_time = time.time()

    try:
        # 2. WALK DIRECTORY
        for root, dirs, files in os.walk(args.directory, topdown=True):
            # Skip hidden/junk directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
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
                        
                        if not content.strip():
                            print("  [SKIP] File is empty.")
                            continue
                            
                        # 4. CHUNK TEXT
                        chunks = chunk_text(content)
                        print(f"  [INFO] Split into {len(chunks)} chunks.")
                        
                        # 5. LEARN (INSERT) CHUNKS
                        chunks_added = 0
                        for chunk in chunks:
                            # Prepend file path as context for the AI
                            fact_with_context = f"File: '{file_path}'\n\nContent:\n{chunk}"
                            
                            if learn_fact(conn, fact_with_context, user_id, file_path):
                                chunks_added += 1
                                total_chunks += 1
                                
                            # Rate limit to be nice to the Ollama server
                            time.sleep(0.1) 
                            
                        print(f"  [SUCCESS] Added {chunks_added} facts from this file.")

                    except Exception as e:
                        print(f"  [ERROR] Failed to process file {file_path}: {e}", file=sys.stderr)
                        
    except KeyboardInterrupt:
        print("\n[PRIMER] Manual interruption. Stopping.")
    finally:
        conn.close()
        
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n--- Priming Complete ---")
    print(f"Processed:     {total_files} files")
    print(f"Learned:       {total_chunks} new facts")
    print(f"Total Time:    {total_time:.2f} seconds")
    
    auth.log_activity(user_id, 'kb_primer', f"Primed {total_chunks} facts from {total_files} files.", 'success')

if __name__ == "__main__":
    main()
