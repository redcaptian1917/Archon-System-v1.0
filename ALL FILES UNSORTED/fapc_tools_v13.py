#!/usr/bin/env python3

import json
import auth
import requests
from crewai_tools import tool

# --- Configuration for Hardware Agent ---
# !! CRITICAL: Replace with your Pi's .onion address from the previous step !!
HARDWARE_AGENT_ONION_URL = "your_pi_hardware_agent.onion"
# ----------------------------------------

# --- Tor Proxy Config ---
TOR_SOCKS_PROXY = 'socks5h://127.0.0.1:9050'
proxies = {'http': TOR_SOCKS_PROXY, 'https': TOR_SOCKS_PROXY}

# --- Import all v12 tools ---
from fapc_tools_v12 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool,
    learn_fact_tool, recall_facts_tool, desktop_notification_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool,
     add_secure_credential_tool, get_secure_credential_tool,
     notify_human_for_help_tool, generate_image_tool, python_repl_tool,
     learn_fact_tool, recall_facts_tool, desktop_notification_tool)
# ---

# --- Hardware Agent Helper Function ---
def _send_hardware_request(endpoint: str, payload: dict, user_id: int) -> dict:
    """Helper function to send a request to the hardware agent over Tor."""
    # Note: The Pi agent listens on port 80 of its hidden service
    target_url = f"http://{HARDWARE_AGENT_ONION_URL}/{endpoint}"
    
    try:
        response = requests.post(
            target_url,
            json=payload,
            proxies=proxies,
            timeout=60 # Tor can be slow
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        error_msg = f"Hardware agent request failed: {e}"
        auth.log_activity(user_id, 'hardware_fail', endpoint, error_msg)
        return {'error': error_msg}

# --- NEW TOOL 1: Hardware Type Tool ---
@tool("Hardware Type Tool")
def hardware_type_tool(text: str, user_id: int) -> str:
    """
    Types a string of text using the physical hardware (HID) agent.
    Use this to bypass lock screens or when software input fails.
    - text: The string to type.
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: hardware_type_tool] TEXT: {text[:20]}...")
    result = _send_hardware_request('type', {'text': text}, user_id)
    if 'error' in result:
        return f"Error: {result['error']}"
    auth.log_activity(user_id, 'hw_type', text, 'success')
    return "Hardware type command sent successfully."

# --- NEW TOOL 2: Hardware Key Tool ---
@tool("Hardware Key Tool")
def hardware_key_tool(key: str, modifier: str = "", user_id: int) -> str:
    """
    Presses a special key (like 'ENTER' or 'F1') or a combo
    (like 'LGUI' + 'r') using the physical hardware (HID) agent.
    - key: The key to press (e.g., 'ENTER', 'F5', 'a', 'TAB').
    - modifier: (Optional) The modifier key (e.g., 'LCTRL', 'LSHIFT', 'LGUI').
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: hardware_key_tool] KEY: {modifier} + {key}")
    payload = {'key': key, 'modifier': modifier}
    result = _send_hardware_request('key', payload, user_id)
    if 'error' in result:
        return f"Error: {result['error']}"
    auth.log_activity(user_id, 'hw_key', f"{modifier} + {key}", 'success')
    return "Hardware key command sent successfully."

# --- NEW TOOL 3: Hardware Mouse Move Tool ---
@tool("Hardware Mouse Move Tool")
def hardware_mouse_move_tool(x: int, y: int, user_id: int) -> str:
    """
    Moves the mouse *relatively* using the physical hardware (HID) agent.
    - x: Pixels to move horizontally (e.g., -10 or 20). Max +/- 127.
    - y: Pixels to move vertically (e.g., -10 or 20). Max +/- 127.
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: hardware_mouse_move_tool] MOVE: ({x}, {y})")
    payload = {'x': x, 'y': y}
    result = _send_hardware_request('mouse_move', payload, user_id)
    if 'error' in result:
        return f"Error: {result['error']}"
    auth.log_activity(user_id, 'hw_mouse', f"({x}, {y})", 'success')
    return "Hardware mouse move command sent."