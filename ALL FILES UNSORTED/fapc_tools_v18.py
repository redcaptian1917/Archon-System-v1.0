#!/usr/bin/env python3

import json
import auth
from crewai_tools import tool
from twilio.rest import Client

# --- Import all v17 tools ---
from fapc_tools_v17 import (
    # ... (all your v17 tools) ...
    start_vulnerability_scan_tool, check_scan_status_tool, get_scan_report_tool
)
_ = (start_vulnerability_scan_tool, check_scan_status_tool, get_scan_report_tool) # etc.
# ---

# --- NEW TOOL: Twilio Comms ---

def _get_twilio_client(user_id: int) -> Client:
    """Helper: Gets Twilio credentials and returns an authenticated client."""
    # 1. Get API keys
    creds_json = get_secure_credential_tool('twilio_api', user_id)
    if 'Error' in creds_json:
        raise Exception("Twilio API credentials ('twilio_api') not found.")
    creds = json.loads(creds_json)
    account_sid = creds['username']
    auth_token = creds['password']
    
    return Client(account_sid, auth_token)

def _get_twilio_number(user_id: int) -> str:
    """Helper: Gets the 'from' number."""
    num_json = get_secure_credential_tool('twilio_phone_number', user_id)
    if 'Error' in num_json:
        raise Exception("Twilio phone number ('twilio_phone_number') not found.")
    return json.loads(num_json)['password']


@tool("Comms Tool (Send SMS/Call)")
def comms_tool(to_number: str, message: str, is_call: bool = False, user_id: int = None) -> str:
    """
    Sends an SMS message or makes a voice call to a phone number.
    - to_number: The destination phone number (e.g., '+19876543210').
    - message: The text message to send, or the text to be spoken in a call.
    - is_call: (Optional) Set to True to make a voice call instead of an SMS (default False).
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: comms_tool] TO: {to_number} CALL: {is_call}")
    try:
        client = _get_twilio_client(user_id)
        from_number = _get_twilio_number(user_id)
        
        if is_call:
            # This creates a TwiML "say" command for the call
            twiml_message = f'<Response><Say>{message}</Say></Response>'
            
            client.calls.create(
                twiml=twiml_message,
                to=to_number,
                from_=from_number
            )
            action = "call_placed"
            log_message = f"Placed call to {to_number}"
        else:
            client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            action = "sms_sent"
            log_message = f"Sent SMS to {to_number}"
        
        auth.log_activity(user_id, action, log_message, 'success')
        return f"Success: {log_message}."
        
    except Exception as e:
        auth.log_activity(user_id, 'comms_fail', str(e), 'failure')
        return f"Error sending communication: {e}"