#!/usr/bin/env python3

import json
import auth
import smtplib
from email.message import EmailMessage
from imapclient import IMAPClient
from crewai_tools import tool

# --- Import all v13 tools ---
from fapc_tools_v13 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool,
    learn_fact_tool, recall_facts_tool, desktop_notification_tool,
    hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool,
     add_secure_credential_tool, get_secure_credential_tool,
     notify_human_for_help_tool, generate_image_tool, python_repl_tool,
     learn_fact_tool, recall_facts_tool, desktop_notification_tool,
    hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool)
# ---

# --- Email Server Helper ---
def _get_email_servers(service_name: str):
    """Helper to get IMAP/SMTP servers based on the service name."""
    service_name = service_name.lower()
    if 'gmail' in service_name:
        return 'imap.gmail.com', 'smtp.gmail.com', 587
    elif 'outlook' in service_name or 'hotmail' in service_name:
        return 'outlook.office365.com', 'smtp.office365.com', 587
    # Add more providers as needed
    else:
        # Default, but likely to fail without specific domain
        return f'imap.{service_name}', f'smtp.{service_name}', 587

# --- NEW TOOL 1: Read Emails ---
@tool("Read Emails Tool")
def read_emails_tool(email_service_name: str, folder: str = 'INBOX', criteria: str = 'UNSEEN', user_id: int = None) -> str:
    """
    Reads emails from a specified inbox.
    - email_service_name: The name of the credential in the database (e.g., 'support_gmail').
    - folder: The mailbox folder to check (default 'INBOX').
    - criteria: The IMAP search criteria (default 'UNSEEN').
    - user_id: The user_id for logging.
    Returns a JSON list of emails: [{'uid': uid, 'from': sender, 'subject': subject, 'body': body_snippet}]
    """
    print(f"\n[Tool Call: read_emails_tool] SERVICE: {email_service_name}")
    try:
        # 1. Get credentials and server info
        creds_json = get_secure_credential_tool(email_service_name, user_id)
        if 'Error' in creds_json:
            return creds_json
        creds = json.loads(creds_json)
        username = creds['username']
        password = creds['password']
        imap_server, _, _ = _get_email_servers(email_service_name)
        
        # 2. Connect and read emails
        with IMAPClient(imap_server) as client:
            client.login(username, password)
            client.select_folder(folder, readonly=False)
            message_uids = client.search(criteria)
            
            if not message_uids:
                return "No new emails found."
            
            # Fetch the 5 most recent
            fetched_emails = []
            for uid, data in client.fetch(message_uids[-5:], ['ENVELOPE', 'BODY[TEXT]']).items():
                envelope = data[b'ENVELOPE']
                subject = envelope.subject.decode()
                sender = f"{envelope.from_[0].name.decode()} <{envelope.from_[0].mailbox.decode()}@{envelope.from_[0].host.decode()}>"
                body = data[b'BODY[TEXT]'].decode('utf-8', 'ignore')
                
                fetched_emails.append({
                    'uid': uid,
                    'from': sender,
                    'subject': subject,
                    'body': body[:500] # Return a 500-char snippet
                })
        
        auth.log_activity(user_id, 'email_read', f"Read {len(fetched_emails)} emails", 'success')
        return json.dumps(fetched_emails)
        
    except Exception as e:
        auth.log_activity(user_id, 'email_read', 'Failed to read email', str(e))
        return f"Error reading email: {e}"

# --- NEW TOOL 2: Send Email ---
@tool("Send Email Tool")
def send_email_tool(email_service_name: str, to_email: str, subject: str, body: str, user_id: int = None) -> str:
    """
    Sends an email.
    - email_service_name: The name of the credential in the database (e.g., 'support_gmail').
    - to_email: The recipient's email address.
    - subject: The subject line of the email.
    - body: The plain text content of the email.
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: send_email_tool] TO: {to_email} SUBJECT: {subject}")
    try:
        # 1. Get credentials and server info
        creds_json = get_secure_credential_tool(email_service_name, user_id)
        if 'Error' in creds_json:
            return creds_json
        creds = json.loads(creds_json)
        from_email = creds['username']
        password = creds['password']
        _, smtp_server, smtp_port = _get_email_servers(email_service_name)

        # 2. Construct the email
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg.set_content(body)

        # 3. Connect and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)
            
        auth.log_activity(user_id, 'email_send', f"Sent email to {to_email}", 'success')
        return "Email sent successfully."
        
    except Exception as e:
        auth.log_activity(user_id, 'email_send', f"Failed to send to {to_email}", str(e))
        return f"Error sending email: {e}"