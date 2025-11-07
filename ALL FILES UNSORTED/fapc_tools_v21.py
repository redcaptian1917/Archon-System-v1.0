#!/usr/bin/env python3

import json
import auth
import db_manager
import ollama
from crewai_tools import tool
from pgvector.psycopg2 import register_vector
import psycopg2

# --- Import all v20 tools ---
from fapc_tools_v20 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool,
    learn_fact_tool, recall_facts_tool, desktop_notification_tool,
    hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
    read_emails_tool, send_email_tool,
    metadata_scrubber_tool, os_hardening_tool, git_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool,
     add_secure_credential_tool, get_secure_credential_tool,
     notify_human_for_help_tool, generate_image_tool, python_repl_tool,
     learn_fact_tool, recall_facts_tool, desktop_notification_tool,
     hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
     read_emails_tool, send_email_tool, metadata_scrubber_tool, os_hardening_tool, git_tool)
# ---

# --- Config and Helper ---
EMBED_MODEL = 'nomic-embed-text'
OLLAMA_HOST = 'http://ollama:11434'

def get_embedding(text_to_embed: str) -> list:
    client = ollama.Client(host=OLLAMA_HOST)
    response = client.embeddings(model=EMBED_MODEL, prompt=text_to_embed)
    return response["embedding"]

# --- UPGRADED TOOL 1: Learn Fact (Write to Memory) ---
@tool("Learn Fact Tool")
def learn_fact_tool(fact: str, importance: int = 50, do_not_delete: bool = False, user_id: int = None) -> str:
    """
    Saves a new fact to the permanent knowledge base.
    - fact: The piece of information to remember.
    - importance: (Optional) A score 1-100. (1=extra, 50=nice to have, 100=critical).
    - do_not_delete: (Optional) Set to True for critical facts like "Mission Directives".
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: learn_fact_tool] FACT: \"{fact[:50]}...\"")
    try:
        embedding = get_embedding(fact)
        conn = db_manager.db_connect()
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO knowledge_base (owner_user_id, fact_text, embedding, 
                                            importance_score, do_not_delete)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, fact, embedding, importance, do_not_delete)
            )
            conn.commit()
        auth.log_activity(user_id, 'kb_learn', fact, 'success')
        return "Success: The fact has been learned and stored."
    except Exception as e:
        return f"Error learning fact: {e}"

# --- UPGRADED TOOL 2: Recall Facts (Read from Memory) ---
@tool("Recall Facts Tool")
def recall_facts_tool(query: str, user_id: int) -> str:
    """
    Searches the knowledge base for relevant facts.
    This tool also *refreshes* the 'last_accessed_at' timestamp of recalled facts.
    - query: The topic to search for.
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: recall_facts_tool] QUERY: \"{query}\"")
    try:
        query_embedding = get_embedding(query)
        conn = db_manager.db_connect()
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT fact_id, fact_text, embedding <-> %s AS distance
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
            
            fact_ids = [res[0] for res in results]
            formatted_results = "\n".join([f"- (ID: {fid}): {fact}" for fid, fact, dist in results])
            
            # ** THE CRITICAL UPGRADE **
            # Update last_accessed_at for the facts we just recalled
            cur.execute(
                "UPDATE knowledge_base SET last_accessed_at = CURRENT_TIMESTAMP WHERE fact_id = ANY(%s)",
                (fact_ids,)
            )
            conn.commit()
            
            auth.log_activity(user_id, 'kb_recall', query, 'success')
            return f"Success: Retrieved {len(results)} relevant facts:\n{formatted_results}"
    except Exception as e:
        return f"Error recalling facts: {e}"

# --- NEW TOOL 3: Get Stale Facts (for GC) ---
@tool("Get Stale Facts Tool")
def get_stale_facts_tool(older_than_days: int = 90, max_importance: int = 49, user_id: int = None) -> str:
    """
    Finds "stale" facts that are candidates for summarization and deletion.
    - older_than_days: (Optional) How old a fact must be (default 90).
    - max_importance: (Optional) The max importance score (default 49, 'extra').
    - user_id: The user_id for logging.
    Returns a JSON list of fact IDs and text.
    """
    print(f"\n[Tool Call: get_stale_facts_tool]")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT fact_id, fact_text FROM knowledge_base
                WHERE owner_user_id = %s
                  AND do_not_delete = FALSE
                  AND importance_score <= %s
                  AND last_accessed_at < (CURRENT_TIMESTAMP - INTERVAL '%s days')
                LIMIT 100;
                """,
                (user_id, max_importance, older_than_days)
            )
            results = cur.fetchall()
        if not results:
            return "No stale facts found."
        
        facts = [{"id": fid, "text": ftext} for fid, ftext in results]
        return json.dumps(facts)
    except Exception as e:
        return f"Error getting stale facts: {e}"

# --- NEW TOOL 4: Summarize Facts (for GC) ---
@tool("Summarize Facts Tool")
def summarize_facts_tool(facts_to_summarize: str, user_id: int) -> str:
    """
    Takes a JSON list of facts and condenses them into a single, high-density summary.
    - facts_to_summarize: A string (from 'Get Stale Facts Tool') of facts.
    - user_id: The user_id for logging.
    Returns the new summary.
    """
    print(f"\n[Tool Call: summarize_facts_tool]")
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        prompt = (
            "You are a memory summarization AI. The following is a list of "
            "old, stale facts from a knowledge base. Condense them into a "
            "single, high-density paragraph that retains all unique information. "
            "If the facts are just noise, respond with 'None'.\n\n"
            f"FACTS:\n{facts_to_summarize}"
        )
        response = client.chat(
            model="llama3:8b",
            messages=[{'role': 'user', 'content': prompt}]
        )
        summary = response['message']['content']
        auth.log_activity(user_id, 'kb_summarize', f'Summarized {len(facts_to_summarize)} facts.', 'success')
        return summary
    except Exception as e:
        return f"Error summarizing facts: {e}"

# --- NEW TOOL 5: Delete Facts (for GC) ---
@tool("Delete Facts Tool")
def delete_facts_tool(fact_ids: list, user_id: int) -> str:
    """
    Permanently deletes a list of fact IDs from the knowledge base.
    This CANNOT be undone. Only deletes facts where 'do_not_delete' is False.
    - fact_ids: A list of integers (e.g., [1, 5, 22]).
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: delete_facts_tool] DELETING {len(fact_ids)} IDs")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM knowledge_base
                WHERE fact_id = ANY(%s) AND do_not_delete = FALSE
                RETURNING fact_id;
                """,
                (fact_ids,)
            )
            deleted_count = cur.rowcount
            conn.commit()
        
        auth.log_activity(user_id, 'kb_delete', f'Deleted {deleted_count} facts.', 'success')
        return f"Success: Permanently deleted {deleted_count} stale facts."
    except Exception as e:
        return f"Error deleting facts: {e}"