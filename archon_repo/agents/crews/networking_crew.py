#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - NETWORKING CREW (vFINAL)
#
# This is the specialist "Signals Corps" & "OPSEC Engine".
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# Its purpose is to:
# 1. (NetworkOpAgent) Manage the 'openvpn-client' sidecar.
# 2. (NetworkOpAgent) Set up layered connections (VPN+Tor) via ProxyChains.
# 3. (NetworkOpAgent) Manage worker network interfaces (MAC spoofing, etc.).
# -----------------------------------------------------------------

import sys
import argparse
import json
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# --- Internal Imports ---
# Import the tools this crew needs from the master "Armory"
try:
    from fapc_tools import (
        vpn_control_tool,
        execute_via_proxy_tool,
        network_interface_tool,
        secure_cli_tool,
        get_secure_credential_tool,
        learn_fact_tool,
        recall_facts_tool
    )
except ImportError:
    print("CRITICAL: fapc_tools.py not found.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. SPECIALIST MODEL SETUP
# ---
try:
    # A general-purpose model is perfect for these tasks
    ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")
    ollama_llm.invoke("Test") # Test connection
except Exception as e:
    print(f"[Networking Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITION
# ---

# This crew has one, hyper-specialized agent.
network_op_agent = Agent(
    role="Network OPSEC Operator",
    goal="Manage the system's network state, connect to VPNs, layer proxies, and manage interfaces to ensure operational security.",
    backstory=(
        "You are the 'Signals Corps' for Archon. You are a 'super-employee' who controls all networking. "
        "Your job is to execute high-level network policies dictated by the CEO.\n"
        "**YOUR CAPABILITIES:**\n"
        "1. **TOR:** You know the 'tor-proxy' service is *always* available at 'socks5h://tor-proxy:9050'.\n"
        "2. **VPN:** You use 'vpn_control_tool' to 'connect', 'disconnect', or 'status' the 'archon-vpn' sidecar container. You use 'protonvpn-cli' commands.\n"
        "3. **LAYERING (VPN -> Tor):** To achieve this, your plan *must* be:\n"
        "   a. Call 'vpn_control_tool(action='connect')'.\n"
        "   b. Call 'execute_via_proxy_tool' for the *final command* (e.g., 'nmap'), "
        "      and set its 'proxy_chain' to ['socks5h://tor-proxy:9050']. "
        "   This forces the VPN-routed traffic *back through* the Tor proxy.\n"
        "4. **INTERFACES:** You use 'network_interface_tool' to 'list' adapters or 'mac_randomize' them on worker agents."
    ),
    tools=[
        vpn_control_tool,
        execute_via_proxy_tool,
        network_interface_tool,
        secure_cli_tool, # For simple commands like 'curl icanhazip.com'
        get_secure_credential_tool,
        learn_fact_tool,
        recall_facts_tool
    ],
    llm=ollama_llm,
    verbose=True
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC Networking Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level networking task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_networking_crew', f"Networking Crew activated for: {task_desc}", 'success')

    # 3. Define the task for the crew
    network_task = Task(
        description=(
            f"Execute this networking directive: '{task_desc}'.\n\n"
            "You must follow your back-story protocols *exactly*. "
            "Analyze the user's request and select the correct tool or combination of tools.\n"
            "- If 'connect vpn', use 'vpn_control_tool'.\n"
            "- If 'layer vpn and tor' for a command, use the full layering protocol.\n"
            "- If 'check ip', use 'secure_cli_tool' with 'curl icanhazip.com' "
            "  (or 'execute_via_proxy_tool' if you need to check the *proxied* IP).\n\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of all network changes, commands run, and the final IP/status.",
        agent=network_op_agent
    )

    # 4. Assemble and run the crew
    network_crew = Crew(
        agents=[network_op_agent],
        tasks=[network_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = network_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Networking Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
