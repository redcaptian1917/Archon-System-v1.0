#!/usr/bin/env python3
# Archon Agent - Networking & OPSEC Tools

import os
import uuid
import subprocess
import docker
from crewai_tools import tool
from ..core import auth
from .control_tools import secure_cli_tool

@tool("VPN Control Tool")
def vpn_control_tool(action: str, user_id: int) -> str:
    """Controls the VPN sidecar container ('connect', 'disconnect', 'status')."""
    print(f"\n[Tool Call: vpn_control_tool] ACTION: {action}")
    try:
        client = docker.from_env()
        vpn_container = client.containers.get('archon-vpn')
        if action == 'connect': cmd = "protonvpn-cli connect -f"
        elif action == 'disconnect': cmd = "protonvpn-cli disconnect"
        elif action == 'status': cmd = "protonvpn-cli status"
        else: return "Error: Unknown VPN action."

        exit_code, output = vpn_container.exec_run(cmd)
        result = output.decode('utf-8')
        auth.log_activity(user_id, 'vpn_control', f"Action: {action}", 'success')
        return f"VPN {action} command executed. Result:\n{result}"
    except Exception as e:
        return f"Error controlling VPN container: {e}"

@tool("Execute via Proxy Tool")
def execute_via_proxy_tool(command_to_run: str, proxy_chain: list, user_id: int) -> str:
    """Executes a shell command *through* a specified proxy chain (Layering Tool)."""
    print(f"\n[Tool Call: execute_via_proxy_tool] CMD: {command_to_run}")
    config_path = f"/tmp/proxy_{uuid.uuid4()}.conf"
    config_content = "[ProxyList]\n" + "\n".join(proxy_chain)
    try:
        # We must write this *inside* the container, so /tmp is fine.
        with open(config_path, 'w') as f: f.write(config_content)
        full_cmd = f"proxychains4 -f {config_path} {command_to_run}"

        # We must use subprocess directly here, *not* secure_cli_tool,
        # as this command *is* the secure shell.
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            output = result.stdout
            status = 'success'
        else:
            output = result.stderr
            status = 'failure'

        auth.log_activity(user_id, 'proxy_exec', f"Chain: {proxy_chain} Cmd: {command_to_run}", status)
        return f"Command executed via proxy. Result:\n{output}"
    except Exception as e:
        return f"Error executing via proxy: {e}"
    finally:
        if os.path.exists(config_path): os.remove(config_path)

@tool("Network Interface Tool")
def network_interface_tool(action: str, interface: str = None, user_id: int = None) -> str:
    """Manages network interfaces on the host ('list', 'mac_randomize')."""
    print(f"\n[Tool Call: network_interface_tool] ACTION: {action}")
    # This tool calls the *worker* agent, as the host interfaces are there.
    if action == 'list': cmd = "nmcli device status"
    elif action == 'mac_randomize':
        if not interface: return "Error: 'mac_randomize' action requires an 'interface'."
        cmd = f"macchanger -r {interface}"
    else: return "Error: Unknown action."

    # We use secure_cli_tool to run this on the *worker*
    result = secure_cli_tool(cmd, user_id)
    auth.log_activity(user_id, 'net_interface_tool', f"Action: {action}", 'success')
    return f"Interface command '{action}' successful:\n{result}"
