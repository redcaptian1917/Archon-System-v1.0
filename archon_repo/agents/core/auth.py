#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - CENTRAL AUTH & LOGGING SERVICE (vFINAL)
#
# This is the "Cheka" (Internal Security) of the Archon system.
# It is a critical library, not an executable script.
# It is imported by:
# 1. api_gateway.py (to authenticate users at the "front door")
# 2. archon_ceo.py (to log commands and enforce policy)
# 3. fapc_tools.py (to log all 40+ tool-level actions)
# 4. All specialist crews (for logging)
# -----------------------------------------------------------------

import sys
import bcrypt
from getpass import getpass
from datetime import datetime, timedelta, timezone

# --- Internal Imports ---
# This creates a clean dependency. db_manager handles *how*
# to connect, and this auth.py file handles *what* to do
# with that connection.
try:
    import db_manager
except ImportError:
    print("CRITICAL: auth.py cannot find db_manager.py.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. USER AUTHENTICATION
# ---

def authenticate_user(username, password):
    """
    Checks a username and password against the database.
    This is the core "lock" for the entire system.
    It uses bcrypt to securely compare the hashed password.
    
    Returns: (user_id, privilege_name) on success
             (None, None) on failure
    """
    conn = db_manager.db_connect()
    if not conn:
        return None, None
        
    try:
        with conn.cursor() as cur:
            # Join users and privileges tables to get the role name
            cur.execute(
                """
                SELECT u.user_id, u.password_hash, p.privilege_name
                FROM users u
                JOIN privileges p ON u.privilege_id = p.privilege_id
                WHERE u.username = %s;
                """,
                (username,)
            )
            result = cur.fetchone()
            
            if not result:
                # User not found
                return None, None
            
            user_id, password_hash, privilege_name = result
            
            # Check the provided password against the stored hash
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                # Password is correct
                return user_id, privilege_name
            else:
                # Password incorrect
                return None, None
            
    except Exception as e:
        print(f"[AUTH ERROR] Error during authentication: {e}", file=sys.stderr)
        return None, None
    finally:
        if conn:
            conn.close()


def get_privilege_by_id(user_id: int) -> str | None:
    """
    Helper function to get a user's privilege level from a user ID.
    """
    conn = db_manager.db_connect()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.privilege_name
                FROM users u
                JOIN privileges p ON u.privilege_id = p.privilege_id
                WHERE u.user_id = %s;
                """,
                (user_id,)
            )
            result = cur.fetchone()
            if result:
                return result[0]
            else:
                return None
    except Exception as e:
        print(f"[AUTH ERROR] Failed to get privilege: {e}", file=sys.stderr)
        return None
    finally:
        if conn:
            conn.close()

# ---
# 2. ACTIVITY LOGGING (The "Ledger")
# ---

def log_activity(user_id, action_type, details, status):
    """
    Logs an action to the 'activity_logs' table.
    This provides the "observable and transparent" logging you wanted.
    This function is called by all 40+ tools and all 14+ crews.
    
    - user_id: The ID of the user performing the action. Can be None for system failures.
    - action_type: A category (e.g., 'cli_command', 'delegate_fail', 'kb_learn').
    - details: The specific content (e.g., the command run, the fact learned).
    - status: 'success', 'failure', or 'pending'.
    """
    conn = db_manager.db_connect()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO activity_logs (user_id, action_type, details, status)
                VALUES (%s, %s, %s, %s);
                """,
                (user_id, action_type, details, status)
            )
            conn.commit()
    except Exception as e:
        print(f"[AUTH ERROR] Failed to log activity: {e}", file=sys.stderr)
        conn.rollback()
    finally:
        if conn:
            conn.close()

# ---
# 3. IDENTITY MANAGEMENT (The "Passport")
# ---

def get_username_from_id(user_id: int) -> str | None:
    """
    Helper function to get a username from a user ID.
    Used by archon_ceo.py for logging and alerts.
    """
    conn = db_manager.db_connect()
    if not conn:
        return None
        
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            if result:
                return result[0]
            else:
                return None
    except Exception as e:
        print(f"[AUTH ERROR] Failed to get username: {e}", file=sys.stderr)
        return None
    finally:
        if conn:
            conn.close()

# ---
# 4. CLI AUTHENTICATION FLOW
# ---

def main_auth_flow(required_privilege: str = 'admin'):
    """
    The main "front door" for all *manual* CLI scripts
    (e.g., enable_2fa.py, knowledge_primer.py).
    
    Prompts for login, authenticates, logs the attempt,
    and checks if the user meets the required privilege level.
    """
    print("--- Archon System Authentication (CLI) ---")
    username = input("Username: ")
    password = getpass("Password: ")
    
    user_id, privilege = authenticate_user(username, password)
    
    if user_id and privilege:
        # User is valid. Now check their privilege.
        # We create a simple privilege hierarchy
        privileges = {
            'guest': 1,
            'user': 2,
            'admin': 3
        }
        
        user_level = privileges.get(privilege, 0)
        required_level = privileges.get(required_privilege, 3) # Default to admin
        
        if user_level < required_level:
            # User is valid, but does not have high enough privilege
            log_activity(user_id, 'login_fail_privilege', f"User {username} attempted CLI login but lacked '{required_privilege}' privilege.", 'failure')
            print(f"Access Denied: This script requires '{required_privilege}' privilege. You have '{privilege}'.")
            sys.exit(1)
            
        # Successful login and privilege check
        log_activity(user_id, 'login_cli', f"User {username} authenticated successfully with '{privilege}' privilege.", 'success')
        print(f"Authentication successful. Welcome, {username} ({privilege}).")
        return user_id, privilege, username
    else:
        # Failed login
        log_activity(None, 'login_fail_pass', f"Failed CLI login attempt for username '{username}'.", 'failure')
        print("Access Denied: Invalid username or password.")
        sys.exit(1)
