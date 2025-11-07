# ... (all your other tools like git_tool, ansible_playbook_tool, etc.) ...

# --- NEW TOOL: User Account Management (for InternalAffairsCrew ONLY) ---
@tool("Auth Management Tool")
def auth_management_tool(action: str, username: str, user_id: int) -> str:
    """
    Manages user accounts. HIGHLY RESTRICTED.
    - action: The action to perform ('lock', 'unlock', 'delete').
    - username: The target username.
    - user_id: The *admin* user_id authorizing this.
    """
    print(f"\n[Tool Call: auth_management_tool] ACTION: {action} on USER: {username}")
    
    # This is a dangerous tool. Double-check the user is an admin.
    if auth.get_username_from_id(user_id) != 'william': # Or check privilege
        auth.log_activity(user_id, 'auth_tool_fail', f"Non-admin attempted to {action} {username}", 'failure')
        return "Error: This tool can only be run by the primary admin."

    conn = db_manager.db_connect()
    try:
        with conn.cursor() as cur:
            if action == 'lock':
                # Lock by setting password to an impossible hash
                impossible_hash = '$2b$12$THIS_IS_AN_IMPOSSIBLE_HASH_TO_PREVENT_LOGIN'
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE username = %s",
                    (impossible_hash, username)
                )
                msg = f"Account '{username}' has been successfully locked."
            elif action == 'unlock':
                # Unlock is complex; requires a password reset.
                # We will just log it and notify admin for now.
                auth.log_activity(user_id, 'auth_tool_unlock', f"Unlock requested for {username}", 'pending')
                return f"Unlock for '{username}' requires manual password reset. Admin notified."
            elif action == 'delete':
                cur.execute("DELETE FROM users WHERE username = %s", (username,))
                msg = f"Account '{username}' has been permanently deleted."
            else:
                return "Error: Unknown action. Use 'lock', 'unlock', or 'delete'."
            
            conn.commit()
        auth.log_activity(user_id, 'auth_tool_success', msg, 'success')
        return f"Success: {msg}"
        
    except Exception as e:
        conn.rollback()
        auth.log_activity(user_id, 'auth_tool_fail', str(e), 'failure')
        return f"Error managing account: {e}"
    finally:
        conn.close()
