#!/usr/bin/env python3
# Archon Agent - Comms & Business Tools

import json
import smtplib
from email.message import EmailMessage
from crewai_tools import tool
from twilio.rest import Client
from imapclient import IMAPClient
from ..core import auth
from ..core import db_manager
from .credential_tools import get_secure_credential_tool
from .helpers import _get_twilio_client, _get_twilio_number, _get_email_servers
from .helpers import _send_agent_request

@tool("Comms Tool (Send SMS/Call)")
def comms_tool(to_number: str, message: str, is_call: bool = False, user_id: int = None) -> str:
    """Sends an SMS message or makes a voice call to a phone number."""
    print(f"\n[Tool Call: comms_tool] TO: {to_number} CALL: {is_call}")
    try:
        client = _get_twilio_client(user_id)
        from_number = _get_twilio_number(user_id)
        if is_call:
            twiml_message = f'<Response><Say>{message}</Say></Response>'
            client.calls.create(twiml=twiml_message, to=to_number, from_=from_number)
            action = "call_placed"
        else:
            client.messages.create(body=message, from_=from_number, to=to_number)
            action = "sms_sent"
        auth.log_activity(user_id, action, f"To: {to_number}", 'success')
        return f"Success: {action}."
    except Exception as e:
        return f"Error sending communication: {e}"

@tool("Read Emails Tool")
def read_emails_tool(email_service_name: str, folder: str = 'INBOX', criteria: str = 'UNSEEN', user_id: int = None) -> str:
    """Reads emails from a specified inbox."""
    print(f"\n[Tool Call: read_emails_tool] SERVICE: {email_service_name}")
    try:
        creds_json = get_secure_credential_tool(email_service_name, user_id)
        if 'Error' in creds_json: return creds_json
        creds = json.loads(creds_json)
        imap_server, _, _ = _get_email_servers(creds['username'])

        with IMAPClient(imap_server) as client:
            client.login(creds['username'], creds['password'])
            client.select_folder(folder, readonly=False)
            message_uids = client.search(criteria)
            if not message_uids: return "No new emails found."

            fetched_emails = []
            for uid, data in client.fetch(message_uids[-5:], ['ENVELOPE', 'BODY[TEXT]']).items():
                envelope = data[b'ENVELOPE']
                fetched_emails.append({
                    'uid': uid,
                    'from': f"{envelope.from_[0].name.decode('utf-8', 'ignore')} <{envelope.from_[0].mailbox.decode('utf-8', 'ignore')}@{envelope.from_[0].host.decode('utf-8', 'ignore')}>",
                    'subject': envelope.subject.decode('utf-8', 'ignore'),
                    'body': data[b'BODY[TEXT]'].decode('utf-8', 'ignore')[:500]
                })
        auth.log_activity(user_id, 'email_read', f"Read {len(fetched_emails)} emails", 'success')
        return json.dumps(fetched_emails)
    except Exception as e:
        return f"Error reading email: {e}"

@tool("Send Email Tool")
def send_email_tool(email_service_name: str, to_email: str, subject: str, body: str, user_id: int = None) -> str:
    """Sends an email."""
    print(f"\n[Tool Call: send_email_tool] TO: {to_email}")
    try:
        creds_json = get_secure_credential_tool(email_service_name, user_id)
        if 'Error' in creds_json: return creds_json
        creds = json.loads(creds_json)
        from_email, password = creds['username'], creds['password']
        _, smtp_server, smtp_port = _get_email_servers(creds['username'])

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg.set_content(body)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)

        auth.log_activity(user_id, 'email_send', f"Sent to {to_email}", 'success')
        return "Email sent successfully."
    except Exception as e:
        return f"Error sending email: {e}"

@tool("Desktop Notification Tool")
def desktop_notification_tool(title: str, message: str, user_id: int) -> str:
    """Sends a non-intrusive desktop notification to the user's GUI."""
    print(f"\n[Tool Call: desktop_notification_tool] TITLE: {title}")
    safe_title = title.replace("'", "\\'")
    safe_message = message.replace("'", "\\'")
    command = f"notify-send -a 'Archon' -i 'emblem-system' '{safe_title}' '{safe_message}'"
    result = _send_agent_request('cli', {'command': command})
    if 'error' in result or result.get('returncode') != 0:
        return f"Error sending notification: {result.get('stderr', 'Unknown')}"
    return "Notification sent successfully."

@tool("Notify Human for Help Tool")
def notify_human_for_help_tool(title: str, details: str, user_id: int) -> str:
    """Creates a 'Critical' priority task for a human user (e.g., for CAPTCHA)."""
    print(f"\n[Tool Call: notify_human_for_help_tool] TITLE: {title}")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (created_by_user_id, status, priority, title, details) VALUES (%s, %s, %s, %s, %s)",
                (user_id, 'blocked', 'Critical', title, details)
            )
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'notify_human', title, 'success')
        return "Success: Human user has been notified with a 'Critical' task."
    except Exception as e:
        return f"Error notifying human: {e}"
