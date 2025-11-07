#!/usr/bin/env python3

import requests
import json
from crewai_tools import tool
import os
import base64
import ollama # New Import

# --- AGENT-SPECIFIC CONFIGURATION ---
# !! CRITICAL: Replace with your .onion address !!
AGENT_ONION_URL = "loremipsum123456789abcdefgvizx.onion"
# ------------------------------------

# --- VPS-SIDE LLM CONFIGURATION ---
VISION_MODEL = 'llava:7b'
OLLAMA_HOST = 'http://localhost:11434'
# ------------------------------------

TOR_SOCKS_PROXY = 'socks5h://127.0.0.1:9050'
proxies = {'http': TOR_SOCKS_PROXY, 'https': TOR_SOCKS_PROXY}

# --- Tool 1: CLI (No Change) ---
def _send_agent_request(endpoint: str, payload: dict) -> dict:
    """Helper function to send a request over Tor."""
    target_url = f"http://{AGENT_ONION_URL}/{endpoint}"
    try:
        response = requests.post(target_url, json=payload, proxies=proxies, timeout=60)
        response.raise_for_status(); return response.json()
    except Exception as e: return {'error': f'Request Failed: {e}'}

@tool("Secure CLI Tool")
def secure_cli_tool(command: str) -> str:
    """Executes a Bash/CLI command on the remote agent."""
    print(f"\n[Tool Call: secure_cli_tool] CMD: \"{command}\"")
    result = _send_agent_request('cli', {'command': command})
    if 'error' in result: return f"Error: {result['error']}"
    if result.get('returncode') == 0: return f"STDOUT:\n{result.get('stdout', '(No stdout)')}"
    return f"STDERR:\n{result.get('stderr', '(No stderr)')}"

# --- Tool 2: Click (No Change) ---
@tool("Click Screen Tool")
def click_screen_tool(x: int, y: int) -> str:
    """Clicks the mouse at the specified (x, y) coordinate."""
    print(f"\n[Tool Call: click_screen_tool] COORDS: ({x}, {y})")
    result = _send_agent_request('click', {'x': x, 'y': y})
    if 'error' in result: return f"Error: {result['error']}"
    return json.dumps(result)

# --- Tool 3: Screenshot (No Change) ---
@tool("Take Screenshot Tool")
def take_screenshot_tool(save_path: str) -> str:
    """Takes a screenshot of the remote agent and saves it locally."""
    print(f"\n[Tool Call: take_screenshot_tool] SAVE_TO: \"{save_path}\"")
    result = _send_agent_request('screenshot', {})
    if 'error' in result: return f"Error: {result['error']}"
    try:
        image_bytes = base64.b64decode(result['image_base64'])
        with open(save_path, 'wb') as f: f.write(image_bytes)
        return f"Success: Screenshot saved to {save_path}"
    except Exception as e: return f"Error saving screenshot: {e}"

# --- Tool 4: Vision (NEW) ---
@tool("Analyze Screenshot Tool")
def analyze_screenshot_tool(image_path: str, prompt: str) -> str:
    """
    Analyzes a local screenshot using a multimodal AI (LLaVA).
    Use this to 'see' the screen, find icons, or get coordinates.
    - image_path: The local path to the screenshot (e.g., 'current_screen.png').
    - prompt: The question to ask the AI. To get coordinates, ask:
      "Find the [item]. Respond ONLY with a JSON object: {\"x\": <x>, \"y\": <y>}"
    """
    print(f"\n[Tool Call: analyze_screenshot_tool] IMG: \"{image_path}\"")
    print(f"  - PROMPT: \"{prompt}\"")
    
    try:
        # 1. Initialize Ollama client
        client = ollama.Client(host=OLLAMA_HOST)
        
        # 2. Read the image and convert to Base64 (Ollama API needs this)
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # 3. Call the LLaVA model
        response = client.chat(
            model=VISION_MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                    'images': [image_base64]
                }
            ],
            options={'temperature': 0.0} # For precise JSON output
        )
        
        result_text = response['message']['content']
        print(f"  - VISION RESULT: {result_text}")
        return result_text
        
    except FileNotFoundError:
        return f"Error: Image file not found at {image_path}"
    except Exception as e:
        return f"Error during vision analysis: {e}"