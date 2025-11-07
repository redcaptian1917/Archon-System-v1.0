#!/usr/bin/env python3

import json
import auth
import os
import subprocess
from crewai_tools import tool
import docker # New import

# --- Import all v23 tools ---
from fapc_tools_v23 import (
    # ... (all your v23 tools) ...
    external_llm_tool
)
_ = (external_llm_tool,) # etc.
# ---

# --- Import key tools from v23 ---
from fapc_tools_v23 import secure_cli_tool, get_secure_credential_tool

# --- NEW TOOL 1: VPN Control ---
@tool("VPN Control Tool")
def vpn_control_tool(action: str, user_id: int) -> str:
    """
    Controls the VPN sidecar container.
    - action: The command to send ('connect', 'disconnect', 'status').
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: vpn_control_tool] ACTION: {action}")
    
    try:
        # Connect to the Docker socket
        client = docker.from_env()
        vpn_container = client.containers.get('archon-vpn')
        
        if action == 'connect':
            # Uses "Fastest" connect. Can be changed to a specific country
            cmd = "protonvpn-cli connect -f"
        elif action == 'disconnect':
            cmd = "protonvpn-cli disconnect"
        elif action == 'status':
            cmd = "protonvpn-cli status"
        else:
            return "Error: Unknown VPN action. Use 'connect', 'disconnect', or 'status'."
            
        # Execute the command *inside the vpn container*
        exit_code, output = vpn_container.exec_run(cmd)
        
        result = output.decode('utf-8')
        auth.log_activity(user_id, 'vpn_control', f"Action: {action}", 'success')
        return f"VPN {action} command executed. Result:\n{result}"
        
    except Exception as e:
        auth.log_activity(user_id, 'vpn_control', f"Action: {action}", str(e))
        return f"Error controlling VPN container: {e}"

# --- NEW TOOL 2: ProxyChains & Layering Tool ---
@tool("Execute via Proxy Tool")
def execute_via_proxy_tool(
    command_to_run: str,
    proxy_chain: list,
    user_id: int
) -> str:
    """
    Executes a shell command *through* a specified proxy chain.
    This is the "Layering" tool.
    - command_to_run: The full command to execute (e.g., 'curl icanhazip.com').
    - proxy_chain: A list of proxy types and IPs (e.g., ['socks5 127.0.0.1 9050', 'http 192.168.1.1 8080']).
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: execute_via_proxy_tool] CMD: {command_to_run}")
    
    # 1. Create a temporary proxychains config file
    config_path = f"/tmp/proxy_{uuid.uuid4()}.conf"
    config_content = "[ProxyList]\n" + "\n".join(proxy_chain)
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # 2. Construct the full proxychains command
        # 'proxychains4 -f [config_file] [command]'
        full_cmd = f"proxychains4 -f {config_path} {command_to_run}"
        
        # 3. Execute using the standard secure_cli_tool
        result = secure_cli_tool(full_cmd, user_id)
        
        auth.log_activity(user_id, 'proxy_exec', f"Chain: {proxy_chain} Cmd: {command_to_run}", 'success')
        return f"Command executed via proxy. Result:\n{result}"
        
    except Exception as e:
        auth.log_activity(user_id, 'proxy_exec', f"Cmd: {command_to_run}", str(e))
        return f"Error executing via proxy: {e}"
    finally:
        if os.path.exists(config_path):
            os.remove(config_path) # Clean up

# --- NEW TOOL 3: Network Interface Tool ---
@tool("Network Interface Tool")
def network_interface_tool(action: str, interface: str = None, user_id: int = None) -> str:
    """
    Manages network interfaces on the host.
    - action: 'list' (shows all interfaces), 'mac_randomize' (sets a new MAC).
    - interface: (Required for mac_randomize) The interface (e.g., 'wlan0').
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: network_interface_tool] ACTION: {action}")
    
    if action == 'list':
        cmd = "nmcli device status"
    elif action == 'mac_randomize':
        if not interface:
            return "Error: 'mac_randomize' action requires an 'interface'."
        # This requires 'macchanger' to be installed on the host
        cmd = f"macchanger -r {interface}"
    else:
        return "Error: Unknown action. Use 'list' or 'mac_randomize'."

    result = secure_cli_tool(cmd, user_id)
    auth.log_activity(user_id, 'net_interface_tool', f"Action: {action}", 'success')
    return f"Interface command '{action}' successful:\n{result}"