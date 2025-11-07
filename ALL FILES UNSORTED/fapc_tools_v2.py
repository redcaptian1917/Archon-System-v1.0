#!/usr/bin/env python3

import requests
import json
from crewai_tools import tool

# --- AGENT-SPECIFIC CONFIGURATION ---
# !! CRITICAL: Replace this with your agent's .onion address !!
# (You get this from 'sudo cat /var/lib/tor/fapc_agent/hostname')
AGENT_ONION_URL = "loremipsum123456789abcdefgvizx.onion"
# ------------------------------------

# Tor's default SOCKS proxy port on localhost
TOR_SOCKS_PROXY = 'socks5h://127.0.0.1:9050'

# Configure the proxies dictionary for 'requests'
# 'socks5h://' means "resolve the hostname through the SOCKS proxy"
proxies = {
    'http': TOR_SOCKS_PROXY,
    'https': TOR_SOCKS_PROXY
}

@tool("Secure CLI Tool")
def secure_cli_tool(command: str) -> str:
    """
    Use this tool to execute any Bash/CLI command securely on a remote
    device agent. The input 'command' is the full command string.
    The tool will return the 'stdout' or 'stderr' from the agent.
    Example: secure_cli_tool("ls -l /home/william/projects")
    """
    print(f"\n[Tool Call: secure_cli_tool]")
    print(f"  - Command: \"{command}\"")
    
    # The agent's hidden service URL (it listens on port 80)
    target_url = f"http://{AGENT_ONION_URL}/"
    payload = {'command': command}
    
    try:
        response = requests.post(
            target_url,
            json=payload,
            proxies=proxies, # This routes the request through Tor
            timeout=60       # Tor can be slow, so a long timeout is needed
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('returncode') == 0:
            print(f"  - Result: Success (code 0)")
            return f"STDOUT:\n{result.get('stdout', '(No stdout)')}"
        else:
            print(f"  - Result: Failed (code {result.get('returncode')})")
            return f"STDERR:\n{result.get('stderr', '(No stderr)')}"

    except requests.exceptions.ConnectionError as e:
        error_msg = f"Error: Connection failed. Is the agent at {AGENT_ONION_URL} online and Tor running?"
        print(f"  - {error_msg}")
        return error_msg
    except requests.exceptions.Timeout:
        error_msg = "Error: Request timed out. The agent or Tor network is too slow."
        print(f"  - {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        print(f"  - {error_msg}")
        return error_msg