#!/usr/bin/env python3

import json
import auth
import requests
import base64
import os
from crewai_tools import tool

# --- Import all v14 tools ---
from fapc_tools_v14 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool,
    learn_fact_tool, recall_facts_tool, desktop_notification_tool,
    hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
    read_emails_tool, send_email_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool,
     add_secure_credential_tool, get_secure_credential_tool,
     notify_human_for_help_tool, generate_image_tool, python_repl_tool,
     learn_fact_tool, recall_facts_tool, desktop_notification_tool,
     hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
     read_emails_tool, send_email_tool)
# ---

# --- Tor Proxy & Helper Function Config ---
AGENT_ONION_URL = "your_kali_agent.onion" # !! Your Kali agent's .onion URL !!
TOR_SOCKS_PROXY = 'socks5h://tor-proxy:9050' # Docker service name
proxies = {'http': TOR_SOCKS_PROXY, 'https': TOR_SOCKS_PROXY}

def _send_agent_request(endpoint: str, payload: dict) -> dict:
    """Helper function to send a request to the local device agent over Tor."""
    target_url = f"http://{AGENT_ONION_URL}/{endpoint}"
    try:
        response = requests.post(target_url, json=payload, proxies=proxies, timeout=60)
        response.raise_for_status(); return response.json()
    except Exception as e: return {'error': f'Request Failed: {e}'}
# ---

# --- NEW TOOL 1: Webcam Tool ---
@tool("Webcam Tool")
def webcam_tool(save_path: str, user_id: int) -> str:
    """
    Captures a single image from the agent's default webcam and saves it.
    - save_path: The local path to save the image (e.g., 'webcam_capture.jpg').
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: webcam_tool] SAVE_TO: {save_path}")
    result = _send_agent_request('webcam', {})
    
    if 'error' in result:
        auth.log_activity(user_id, 'webcam_fail', result['error'], 'failure')
        return f"Error: {result['error']}"
    
    try:
        image_bytes = base64.b64decode(result['image_base64'])
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        
        auth.log_activity(user_id, 'webcam_success', f"Saved to {save_path}", 'success')
        return f"Success: Webcam image saved to {save_path}"
    except Exception as e:
        auth.log_activity(user_id, 'webcam_fail', str(e), 'failure')
        return f"Error saving image: {e}"

# --- NEW TOOL 2: Listen Tool ---
@tool("Listen Tool")
def listen_tool(save_path: str, duration: int = 5, user_id: int = None) -> str:
    """
    Records audio from the agent's default microphone and saves it as a WAV file.
    - save_path: The local path to save the audio (e.g., 'recording.wav').
    - duration: (Optional) The length of the recording in seconds (default 5).
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: listen_tool] SAVE_TO: {save_path}")
    result = _send_agent_request('listen', {'duration': duration})
    
    if 'error' in result:
        auth.log_activity(user_id, 'listen_fail', result['error'], 'failure')
        return f"Error: {result['error']}"
        
    try:
        audio_bytes = base64.b64decode(result['audio_base64'])
        with open(save_path, 'wb') as f:
            f.write(audio_bytes)
        
        auth.log_activity(user_id, 'listen_success', f"Saved to {save_path}", 'success')
        return f"Success: Audio recording saved to {save_path}"
    except Exception as e:
        auth.log_activity(user_id, 'listen_fail', str(e), 'failure')
        return f"Error saving audio: {e}"