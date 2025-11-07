#!/usr/bin/env python3

import json
from crewai_tools import tool
import auth
import db_manager  # We will use our DB manager as a library
import psycopg2

# --- Import all v7 tools ---
# (This assumes v7 is in a file named fapc_tools_v7.py)
from fapc_tools_v7 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool)
# ---

# --- NEW TOOL 1: Credential Manager ---

@tool("Add Secure Credential Tool")
def add_secure_credential_tool(service_name: str, username: str, password: str, user_id: int) -> str:
    """
    Stores a new credential (like an email password or your phone number)
    securely in the encrypted database.
    - service_name: The name of the service (e.g., 'my_phone_number', 'gmail').
    - username: The username for the service (can be blank, e.g., for a phone number).
    - password: The secret value to store (the password, or the phone number itself).
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: add_secure_credential_tool] SERVICE: {service_name}")
    try:
        # Encrypt the secret
        encrypted_data = db_manager.encrypt_credential(password)
        
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO credentials (owner_user_id, service_name, username, 
                                         encrypted_password, encryption_nonce, encryption_tag)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, service_name, username, 
                 encrypted_data['encrypted_password'], 
                 encrypted_data['nonce'], 
                 encrypted_data['tag'])
            )
            conn.commit()
        auth.log_activity(user_id, 'cred_add', f"Added credential for {service_name}", 'success')
        return f"Success: Credential for {service_name} stored securely."
    except Exception as e:
        auth.log_activity(user_id, 'cred_add', f"Failed to add {service_name}", str(e))
        return f"Error storing credential: {e}"

@tool("Get Secure Credential Tool")
def get_secure_credential_tool(service_name: str, user_id: int) -> str:
    """
    Retrieves a secure credential from the database.
    - service_name: The name of the service (e.g., 'my_phone_number', 'gmail').
    - user_id: The user_id for logging.
    Returns a JSON string: {"username": "...", "password": "..."}
    """
    print(f"\n[Tool Call: get_secure_credential_tool] SERVICE: {service_name}")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT username, encrypted_password, encryption_nonce, encryption_tag
                FROM credentials
                WHERE service_name = %s AND owner_user_id = %s
                ORDER BY credential_id DESC LIMIT 1;
                """,
                (service_name, user_id)
            )
            result = cur.fetchone()
            
            if not result:
                return f"Error: No credential found for '{service_name}'."
            
            username, enc_pass, nonce, tag = result
            
            # Decrypt the secret
            password = db_manager.decrypt_credential(nonce, tag, enc_pass)
            
            if password is None:
                return "Error: Decryption failed! Master key may be incorrect."
            
            auth.log_activity(user_id, 'cred_get', f"Retrieved credential for {service_name}", 'success')
            return json.dumps({"username": username, "password": password})
            
    except Exception as e:
        auth.log_activity(user_id, 'cred_get', f"Failed to get {service_name}", str(e))
        return f"Error retrieving credential: {e}"

# --- NEW TOOL 2: CAPTCHA / Task Notifier ---

@tool("Notify Human for Help Tool")
def notify_human_for_help_tool(title: str, details: str, user_id: int) -> str:
    """
    Creates a 'Critical' priority task for a human user.
    Use this when you are blocked by a CAPTCHA or need human intervention.
    - title: A short title for the task (e.g., 'CAPTCHA Block').
    - details: Full details, e.g., 'Blocked by CAPTCHA on 'https://google.com'.
      Screenshot saved to 'captcha.png'. Please solve and tell me to continue.'
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: notify_human_for_help_tool] TITLE: {title}")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tasks (created_by_user_id, status, priority, title, details)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, 'blocked', 'Critical', title, details)
            )
            conn.commit()
        auth.log_activity(user_id, 'notify_human', title, 'success')
        return "Success: Human user has been notified with a 'Critical' task."
    except Exception as e:
        auth.log_activity(user_id, 'notify_human', title, str(e))
        return f"Error notifying human: {e}"