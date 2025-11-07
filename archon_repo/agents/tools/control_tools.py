#!/usr/bin/env python3
# Archon Agent - C2 & Control Tools

import json
import base64
from crewai_tools import tool
from ..core import auth
from .helpers import _send_agent_request

@tool("Secure CLI Tool")
def secure_cli_tool(command: str, user_id: int) -> str:
    """Executes a Bash/CLI command on the remote device agent (Kali/Debian)."""
    print(f"\n[Tool Call: secure_cli_tool] CMD: \"{command}\"")
    result = _send_agent_request('cli', {'command': command})

    if 'error' in result:
        auth.log_activity(user_id, 'cli_command', f"Command: {command}", f"failure: {result['error']}")
        return f"Error: {result['error']}"

    if result.get('returncode') == 0:
        auth.log_activity(user_id, 'cli_command', f"Command: {command}", 'success')
        return f"STDOUT:\n{result.get('stdout', '(No stdout)')}"

    error_detail = result.get('stderr', '(No stderr)')
    auth.log_activity(user_id, 'cli_command', f"Command: {command}", f"failure: {error_detail}")
    return f"STDERR:\n{error_detail}"

@tool("Click Screen Tool")
def click_screen_tool(x: int, y: int, user_id: int) -> str:
    """Clicks the mouse at the specified (x, y) coordinate on the remote agent's screen."""
    print(f"\n[Tool Call: click_screen_tool] COORDS: ({x}, {y})")
    result = _send_agent_request('click', {'x': x, 'y': y})
    auth.log_activity(user_id, 'click_tool', f"Clicked at ({x},{y})", 'success' if 'error' not in result else 'failure')
    return json.dumps(result)

@tool("Take Screenshot Tool")
def take_screenshot_tool(save_path: str, user_id: int) -> str:
    """Takes a screenshot of the remote agent's entire screen and saves it locally."""
    print(f"\n[Tool Call: take_screenshot_tool] SAVE_TO: \"{save_path}\"")
    result = _send_agent_request('screenshot', {})

    if 'error' in result:
        auth.log_activity(user_id, 'screenshot_fail', result['error'], 'failure')
        return f"Error: {result['error']}"

    try:
        image_bytes = base64.b64decode(result['image_base64'])
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        auth.log_activity(user_id, 'screenshot_success', f"Saved to {save_path}", 'success')
        return f"Success: Screenshot saved to {save_path}"
    except Exception as e:
        auth.log_activity(user_id, 'screenshot_fail', str(e), 'failure')
        return f"Error saving screenshot: {e}"

@tool("Hardware Type Tool")
def hardware_type_tool(text: str, user_id: int) -> str:
    """Types a string of text using the physical hardware (HID) agent."""
    print(f"\n[Tool Call: hardware_type_tool] TEXT: {text[:20]}...")
    result = _send_agent_request('type', {'text': text}, is_hardware=True)
    if 'error' in result:
        auth.log_activity(user_id, 'hw_type_fail', str(result['error']), 'failure')
        return f"Error: {result['error']}"
    auth.log_activity(user_id, 'hw_type', text, 'success')
    return "Hardware type command sent successfully."

@tool("Hardware Key Tool")
def hardware_key_tool(key: str, modifier: str = "", user_id: int = None) -> str:
    """Presses a special key (e.g., 'ENTER') or a combo using the physical hardware (HID) agent."""
    print(f"\n[Tool Call: hardware_key_tool] KEY: {modifier} + {key}")
    payload = {'key': key, 'modifier': modifier}
    result = _send_agent_request('key', payload, is_hardware=True)
    if 'error' in result:
        auth.log_activity(user_id, 'hw_key_fail', str(result['error']), 'failure')
        return f"Error: {result['error']}"
    auth.log_activity(user_id, 'hw_key', f"{modifier} + {key}", 'success')
    return "Hardware key command sent successfully."

@tool("Hardware Mouse Move Tool")
def hardware_mouse_move_tool(x: int, y: int, user_id: int) -> str:
    """Moves the mouse *relatively* using the physical hardware (HID) agent."""
    print(f"\n[Tool Call: hardware_mouse_move_tool] MOVE: ({x}, {y})")
    payload = {'x': x, 'y': y}
    result = _send_agent_request('mouse_move', payload, is_hardware=True)
    if 'error' in result:
        auth.log_activity(user_id, 'hw_mouse_fail', str(result['error']), 'failure')
        return f"Error: {result['error']}"
    auth.log_activity(user_id, 'hw_mouse', f"({x}, {y})", 'success')
    return "Hardware mouse move command sent."
