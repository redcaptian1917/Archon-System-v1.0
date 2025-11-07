#!/usr/bin/env python3
# Archon Agent - Credential Tools

import json
from crewai_tools import tool
from ..core import auth
from ..core import db_manager

@tool("Add Secure Credential Tool")
def add_secure_credential_tool(service_name: str, username: str, password: str, user_id: int) -> str:
    """
    Stores a new credential (like an email password or your phone number)
    securely in the encrypted database.
    """
    print(f"\n[Tool Call: add_secure_credential_tool] SERVICE: {service_name}")
    try:
        encrypted_data = db_manager.encrypt_credential(password)
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO credentials (owner_user_id, service_name, username, encrypted_password, encryption_nonce, encryption_tag) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, service_name, username, encrypted_data['encrypted_password'], encrypted_data['nonce'], encrypted_data['tag'])
            )
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'cred_add', f"Added credential for {service_name}", 'success')
        return f"Success: Credential for {service_name} stored securely."
    except Exception as e:
        conn.rollback()
        conn.close()
        return f"Error storing credential: {e}"

@tool("Get Secure Credential Tool")
def get_secure_credential_tool(service_name: str, user_id: int) -> str:
    """
    Retrieves a secure credential from the database.
    Returns a JSON string: {"username": "...", "password": "..."}
    """
    print(f"\n[Tool Call: get_secure_credential_tool] SERVICE: {service_name}")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, encrypted_password, encryption_nonce, encryption_tag FROM credentials WHERE service_name = %s AND owner_user_id = %s ORDER BY credential_id DESC LIMIT 1;",
                (service_name, user_id)
            )
            result = cur.fetchone()
        conn.close()
        if not result:
            return f"Error: No credential found for '{service_name}'."

        username, enc_pass, nonce, tag = result
        password = db_manager.decrypt_credential(nonce, tag, enc_pass)
        if password is None:
            return "Error: Decryption failed! Master key may be incorrect."

        auth.log_activity(user_id, 'cred_get', f"Retrieved credential for {service_name}", 'success')
        return json.dumps({"username": username, "password": password})
    except Exception as e:
        return f"Error retrieving credential: {e}"
