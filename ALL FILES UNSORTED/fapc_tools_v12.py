#!/usr/bin/env python3

import json
import auth
from crewai_tools import tool

# --- Import all v11 tools ---
from fapc_tools_v11 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool,
    learn_fact_tool, recall_facts_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool,
     add_secure_credential_tool, get_secure_credential_tool,
     notify_human_for_help_tool, generate_image_tool, python_repl_tool,
     learn_fact_tool, recall_facts_tool)
# ---

# --- Import the helper function from v11 tools ---
# This is the function that sends the request over Tor.
# (If v11 is in another file, you'd import it, e.g., from fapc_tools_v11 import _send_agent_request)
# For this example, let's assume the _send_agent_request function is in this file.
import requests
TOR_SOCKS_PROXY = 'socks5h://127.0.0.1:9050'
proxies = {'http': TOR_SOCKS_PROXY, 'https': TOR_SOCKS_PROXY}
AGENT_ONION_URL = "loremipsum123456789abcdefgvizx.onion" # !! Your .onion URL !!

def _send_agent_request(endpoint: str, payload: dict) -> dict:
    """Helper function to send a request over Tor."""
    target_url = f"http://{AGENT_ONION_URL}/{endpoint}"
    try:
        response = requests.post(target_url, json=payload, proxies=proxies, timeout=60)
        response.raise_for_status(); return response.json()
    except Exception as e: return {'error': f'Request Failed: {e}'}
# ---

# --- NEW TOOL: Desktop Notification ---

@tool("Desktop Notification Tool")
def desktop_notification_tool(title: str, message: str, user_id: int) -> str:
    """
    Sends a non-intrusive desktop notification to the user's GUI.
    - title: The title of the notification (e.g., 'Archon Suggestion').
    - message: The body of the message (e.g., 'I see you're getting a permission error.').
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: desktop_notification_tool] TITLE: {title}")
    
    # Escape single quotes for the shell command
    safe_title = title.replace("'", "\\'")
    safe_message = message.replace("'", "\\'")
    
    # -a 'Archon' sets the app name
    # -i 'emblem-system' uses a standard system icon
    command = f"notify-send -a 'Archon' -i 'emblem-system' '{safe_title}' '{safe_message}'"
    
    # We use the same secure /cli endpoint as the secure_cli_tool
    result = _send_agent_request('cli', {'command': command})
    
    if 'error' in result or result.get('returncode') != 0:
        error_msg = f"Error sending notification: {result.get('stderr', 'Unknown')}"
        auth.log_activity(user_id, 'notify_fail', title, error_msg)
        return error_msg
    
    auth.log_activity(user_id, 'notify_sent', title, 'success')
    return "Notification sent successfully."