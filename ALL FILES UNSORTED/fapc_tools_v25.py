#!/usr/bin/env python3

import json
import auth
import db_manager
import ollama
import psycopg2
import os
import requests
import uuid
import websocket
import time
from crewai_tools import tool
from pgvector.psycopg2 import register_vector
import git
from openai import OpenAI
from anthropic import Anthropic
from twilio.rest import Client # New import

# --- Import all v24 tools ---
from fapc_tools_v24 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool,
    learn_fact_tool, recall_facts_tool, desktop_notification_tool,
    hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
    read_emails_tool, send_email_tool,
    metadata_scrubber_tool, os_hardening_tool, git_tool,
    get_stale_facts_tool, summarize_facts_tool, delete_facts_tool,
    vpn_control_tool, execute_via_proxy_tool, network_interface_tool,
    external_llm_tool
)
# (This is just to show all tools are included)
_ = (secure_cli_tool, external_llm_tool, vpn_control_tool) 
# ---

# --- NEW TOOL: Twilio Comms ---

def _get_twilio_client(user_id: int) -> Client:
    """Helper: Gets Twilio credentials and returns an authenticated client."""
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