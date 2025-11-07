#!/usr/bin/env python3

import psycopg2
import bcrypt
import sys
from getpass import getpass

# --- Configuration ---
# Must match your db_manager.py settings
DB_NAME = "fapc_db"
DB_USER = "archon_admin"
DB_PASS = "YOUR_DB_PASSWORD" # The password you set
DB_HOST = "localhost"

def db_connect():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST
        )
        return conn
    except Exception as e:
        print(f"[AUTH FATAL] Could not connect to database: {e}", file=sys.stderr)
        sys.exit(1)

def authenticate_user(username, password):
    """
    Checks a username and password against the database.
    Returns (user_id, privilege_name) if successful, else (None, None).
    """
    conn = db_connect()
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
                return None, None # User not found
            
            user_id, password_hash, privilege_name = result
            
            # Check the password
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                return user_id, privilege_name
            else:
                return None, None # Password incorrect
            
    except Exception as e:
        print(f"[AUTH ERROR] Error during authentication: {e}", file=sys.stderr)
        return None, None
    finally:
        conn.close()

def log_activity(user_id, action_type, details, status):
    """
    Logs an action to the 'activity_logs' table.
    This provides the "observable and transparent" logging you wanted.
    """
    conn = db_connect()
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
        conn.close()

def main_auth_flow(required_privilege='admin'):
    """
    The main "front door" for all scripts.
    Prompts for login, authenticates, logs the attempt, and checks privilege.
    """
    print("--- Archon System Authentication ---")
    username = input("Username: ")
    password = getpass("Password: ")
    
    user_id, privilege = authenticate_user(username, password)
    
    if user_id and privilege:
        # Check if the user has the required privilege level
        if privilege != required_privilege:
            log_activity(user_id, 'login_fail', f"User {username} attempted login but lacked '{required_privilege}' privilege.", 'failure')
            print(f"Access Denied: '{required_privilege}' privilege is required. You have '{privilege}'.")
            sys.exit(1)
            
        # Successful login and privilege check
        log_activity(user_id, 'login', f"User {username} authenticated successfully with '{privilege}' privilege.", 'success')
        print(f"Authentication successful. Welcome, {username} ({privilege}).")
        return user_id, privilege
    else:
        # Failed login
        log_activity(None, 'login_fail', f"Failed login attempt for username '{username}'.", 'failure')
        print("Access Denied: Invalid username or password.")
        sys.exit(1)