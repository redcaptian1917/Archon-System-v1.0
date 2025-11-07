#!/usr/bin/env python3

import requests
import json
from crewai_tools import tool
import os
import base64

# --- AGENT-SPECIFIC CONFIGURATION ---
# !! CRITICAL: Replace with your .onion address !!
AGENT_ONION_URL = "loremipsum123456789abcdefgvizx.onion"
# ------------------------------------

TOR_SOCKS_PROXY = 'socks5h://127.0.0.1:9050'
proxies = {'http': TOR_SOCKS_PROXY, 'https': TOR_SOCKS_PROXY}

def _send_agent_request(endpoint: str, payload: dict) -> dict:
    """Helper function to send a request over Tor."""
    target_url = f"http://{AGENT_ONION_URL}/{endpoint}"
    
    try:
        response = requests.post(
            target_url,
            json=payload,
            proxies=proxies,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {'error': f'Failed to send request: {e}'}

@tool("Secure CLI Tool")
def secure_cli_tool(command: str) -> str:
    """
    Executes a Bash/CLI command on the remote agent.
    Returns the stdout or stderr.
    """
    print(f"\n[Tool Call: secure_cli_tool] CMD: \"{command}\"")
    result = _send_agent_request('cli', {'command': command})
    
    if 'error' in result:
        return f"Error: {result['error']}"
    if result.get('returncode') == 0:
        return f"STDOUT:\n{result.get('stdout', '(No stdout)')}"
    return f"STDERR:\n{result.get('stderr', '(No stderr)')}"

@tool("Click Screen Tool")
def click_screen_tool(x: int, y: int) -> str:
    """
    Clicks the mouse at the specified (x, y) coordinate
    on the remote agent's screen.
    """
    print(f"\n[Tool Call: click_screen_tool] COORDS: ({x}, {y})")
    result = _send_agent_request('click', {'x': x, 'y': y})
    
    if 'error' in result:
        return f"Error: {result['error']}"
    return json.dumps(result)

@tool("Take Screenshot Tool")
def take_screenshot_tool(save_path: str) -> str:
    """
    Takes a screenshot of the remote agent's entire screen.
    Saves it locally to the 'save_path' and returns a
    description (or an error).
    """
    print(f"\n[Tool Call: take_screenshot_tool] SAVE_TO: \"{save_path}\"")
    result = _send_agent_request('screenshot', {})
    
    if 'error' in result:
        return f"Error: {result['error']}"
    
    try:
        # Decode the Base64 string back into bytes
        image_bytes = base64.b64decode(result['image_base64'])
        
        # Save the bytes to the local file
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        
        return f"Success: Screenshot saved to {save_path}"
    except Exception as e:
        return f"Error saving screenshot: {e}"