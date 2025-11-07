#!/usr/bin/env python3
# Archon Agent - Memory & Learning Tools

import json
import ollama
from crewai_tools import tool
from pgvector.psycopg2 import register_vector
from ..core import auth
from ..core import db_manager
from .helpers import get_embedding

@tool("Learn Fact Tool")
def learn_fact_tool(fact: str, importance: int = 50, do_not_delete: bool = False, user_id: int = None) -> str:
    """Saves a new fact to the permanent knowledge base."""
    print(f"\n[Tool Call: learn_fact_tool] FACT: \"{fact[:50]}...\"")
    try:
        embedding = get_embedding(fact)
        if embedding is None: return "Error: Could not generate embedding."
        conn = db_manager.db_connect()
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO knowledge_base (owner_user_id, fact_text, embedding, importance_score, do_not_delete) VALUES (%s, %s, %s, %s, %s)",
                (user_id, fact, embedding, importance, do_not_delete)
            )
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'kb_learn', fact, 'success')
        return "Success: The fact has been learned and stored."
    except Exception as e:
        return f"Error learning fact: {e}"

@tool("Recall Facts Tool")
def recall_facts_tool(query: str, user_id: int) -> str:
    """Searches the knowledge base for relevant facts and refreshes them."""
    print(f"\n[Tool Call: recall_facts_tool] QUERY: \"{query}\"")
    try:
        query_embedding = get_embedding(query)
        if query_embedding is None: return "Error: Could not generate query embedding."
        conn = db_manager.db_connect()
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fact_id, fact_text, embedding <-> %s AS distance FROM knowledge_base WHERE owner_user_id = %s ORDER BY distance ASC LIMIT 3;",
                (query_embedding, user_id)
            )
            results = cur.fetchall()
            if not results:
                conn.close()
                return "No relevant facts found in memory."

            fact_ids = [res[0] for res in results]
            formatted_results = "\n".join([f"- (ID: {fid}): {fact}" for fid, fact, dist in results])

            # Refresh 'last_accessed_at'
            cur.execute(
                "UPDATE knowledge_base SET last_accessed_at = CURRENT_TIMESTAMP WHERE fact_id = ANY(%s)",
                (fact_ids,)
            )
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'kb_recall', query, 'success')
        return f"Success: Retrieved {len(results)} relevant facts:\n{formatted_results}"
    except Exception as e:
        return f"Error recalling facts: {e}"

@tool("Get Stale Facts Tool")
def get_stale_facts_tool(older_than_days: int = 90, max_importance: int = 49, user_id: int = None) -> str:
    """Finds 'stale' facts that are candidates for summarization and deletion."""
    print(f"\n[Tool Call: get_stale_facts_tool]")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fact_id, fact_text FROM knowledge_base WHERE owner_user_id = %s AND do_not_delete = FALSE AND importance_score <= %s AND last_accessed_at < (CURRENT_TIMESTAMP - INTERVAL '%s days') LIMIT 100;",
                (user_id, max_importance, older_than_days)
            )
            results = cur.fetchall()
        conn.close()
        if not results: return "No stale facts found."
        facts = [{"id": fid, "text": ftext} for fid, ftext in results]
        return json.dumps(facts)
    except Exception as e:
        return f"Error getting stale facts: {e}"

@tool("Summarize Facts Tool")
def summarize_facts_tool(facts_to_summarize: str, user_id: int) -> str:
    """Takes a JSON list of facts and condenses them into a single, high-density summary."""
    print(f"\n[Tool Call: summarize_facts_tool]")
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        prompt = (f"You are a memory summarization AI. Condense the following old facts into a single, high-density paragraph. If the facts are noise, respond with 'None'.\n\nFACTS:\n{facts_to_summarize}")
        response = client.chat(model="llama3:8b", messages=[{'role': 'user', 'content': prompt}])
        summary = response['message']['content']
        auth.log_activity(user_id, 'kb_summarize', f'Summarized {len(facts_to_summarize)} facts.', 'success')
        return summary
    except Exception as e:
        return f"Error summarizing facts: {e}"

@tool("Delete Facts Tool")
def delete_facts_tool(fact_ids: list, user_id: int) -> str:
    """Permanently deletes a list of fact IDs from the knowledge base."""
    print(f"\n[Tool Call: delete_facts_tool] DELETING {len(fact_ids)} IDs")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM knowledge_base WHERE fact_id = ANY(%s) AND do_not_delete = FALSE RETURNING fact_id;",
                (fact_ids,)
            )
            deleted_count = cur.rowcount
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'kb_delete', f'Deleted {deleted_count} facts.', 'success')
        return f"Success: Permanently deleted {deleted_count} stale facts."
    except Exception as e:
        return f"Error deleting facts: {e}"
