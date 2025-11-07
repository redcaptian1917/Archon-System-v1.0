# ... (All previous imports from v26) ...

from crewai_tools import tool
from datetime import datetime, timedelta, timezone

# --- Import key tools from v26 ---
from fapc_tools_v26 import (
    # ... (all your tools) ...
    comms_tool
)
_ = (comms_tool,) # etc.

# --- NEW TOOL: Audit Logs Retriever ---
@tool("Retrieve Audit Logs Tool")
def retrieve_audit_logs_tool(status_filter: str, days_ago: int, user_id: int) -> str:
    """
    Retrieves entries from the activity_logs table based on criteria.
    - status_filter: The log status to search for ('failure', 'error', 'success').
    - days_ago: How many days back to search.
    - user_id: The user_id for logging.
    Returns a JSON list of log entries.
    """
    print(f"\n[Tool Call: retrieve_audit_logs_tool] FILTER: {status_filter}")
    
    try:
        conn = db_manager.db_connect()
        # Calculate the timestamp threshold
        threshold = datetime.now(timezone.utc) - timedelta(days=days_ago)
        
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT log_id, timestamp, action_type, details
                FROM activity_logs
                WHERE status = %s AND timestamp > %s
                ORDER BY timestamp DESC
                LIMIT 20;
                """,
                (status_filter, threshold)
            )
            results = cur.fetchall()
            
            logs = []
            for log_id, ts, action, details in results:
                logs.append({
                    'id': log_id,
                    'timestamp': str(ts),
                    'action': action,
                    'details': details
                })
        
        auth.log_activity(user_id, 'audit_log_retrieve', f"Retrieved {len(logs)} logs with status {status_filter}", 'success')
        return json.dumps(logs)
        
    except Exception as e:
        return f"Error retrieving logs: {e}"

# ... (Rest of fapc_tools_v26.py content) ...