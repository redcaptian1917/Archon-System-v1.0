#!/usr/bin/env python3

import json
import auth
import db_manager
import ollama
from crewai_tools import tool
from pgvector.psycopg2 import register_vector
import psycopg2

# --- Import all v10 tools ---
from fapc_tools_v10 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool,
     add_secure_credential_tool, get_secure_credential_tool,
     notify_human_for_help_tool, generate_image_tool, python_repl_tool)
# ---

# --- Configuration for Embeddings ---
EMBED_MODEL = 'nomic-embed-text'
OLLAMA_HOST = 'http://localhost:11434'

def get_embedding(text_to_embed: str) -> list:
    """Generates an embedding vector for a string."""
    client = ollama.Client(host=OLLAMA_HOST)
    response = client.embeddings(
        model=EMBED_MODEL,
        prompt=text_to_embed
    )
    return response["embedding"]

# --- NEW TOOL 1: Learn Fact (Write to Memory) ---

@tool("Learn Fact Tool")
def learn_fact_tool(fact: str, user_id: int) -> str:
    """
    Saves a new fact, user preference, or successful procedure
    to your permanent knowledge base.
    Use this to remember things you've learned.
    - fact: The piece of information to remember (e.g., "I learned that
      'nmap -sV' is the best command for auditing ports.")
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: learn_fact_tool] FACT: \"{fact}\"")
    try:
        # 1. Generate the embedding for the fact
        embedding = get_embedding(fact)
        
        # 2. Store the fact and its embedding
        conn = db_manager.db_connect()
        register_vector(conn) # Enable pgvector
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_base (owner_user_id, fact_text, embedding)
                VALUES (%s, %s, %s)
                """,
                (user_id, fact, embedding)
            )
            conn.commit()
        
        auth.log_activity(user_id, 'kb_learn', fact, 'success')
        return "Success: The fact has been learned and stored in the knowledge base."
        
    except Exception as e:
        error_msg = f"Error learning fact: {e}"
        auth.log_activity(user_id, 'kb_learn', fact, str(e))
        return error_msg

# --- NEW TOOL 2: Recall Facts (Read from Memory) ---

@tool("Recall Facts Tool")
def recall_facts_tool(query: str, user_id: int) -> str:
    """
    Searches your permanent knowledge base for the most relevant facts
    related to a query. Use this to remember things you've learned in the past.
    - query: The topic to search for (e.g., "What is the user's preferred
      method for auditing ports?").
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: recall_facts_tool] QUERY: \"{query}\"")
    try:
        # 1. Generate the embedding for the query
        query_embedding = get_embedding(query)
        
        # 2. Search the knowledge base for the 3 most similar facts
        conn = db_manager.db_connect()
        register_vector(conn)
        with conn.cursor() as cur:
            # We use '<->' (L2 distance) to find the nearest neighbors
            cur.execute(
                """
                SELECT fact_text, embedding <-> %s AS distance
                FROM knowledge_base
                WHERE owner_user_id = %s
                ORDER BY distance ASC
                LIMIT 3;
                """,
                (query_embedding, user_id)
            )
            results = cur.fetchall()
            
            if not results:
                return "No relevant facts found in memory."
            
            # Format the results
            formatted_results = "\n".join(
                [f"- (Relevance: {dist:.4f}): {fact}" for fact, dist in results]
            )
            auth.log_activity(user_id, 'kb_recall', query, 'success')
            return f"Success: Retrieved {len(results)} relevant facts:\n{formatted_results}"

    except Exception as e:
        error_msg = f"Error recalling facts: {e}"
        auth.log_activity(user_id, 'kb_recall', query, str(e))
        return error_msg