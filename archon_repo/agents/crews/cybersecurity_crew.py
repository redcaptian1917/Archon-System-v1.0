#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - CYBERSECURITY CREW (vFINAL)
#
# This is the specialist "Internal Security" & "Blue Team" for Archon.
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# Its purpose is to:
# 1. Defend Archon's own infrastructure (hardening, firewalls).
# 2. Audit internal systems for vulnerabilities (Nmap).
# 3. Conduct threat intelligence on new CVEs.
# -----------------------------------------------------------------

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# --- Internal Imports ---
# Import the tools this crew needs from the master "Armory"
try:
    from fapc_tools import (
        secure_cli_tool,
        defensive_nmap_tool,
        os_hardening_tool,
        web_search_tool,
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
    print(f"[Cybersecurity Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITIONS
# ---

# Agent 1: The Blue Team Operator (Hardener & Auditor)
blue_team_agent = Agent(
    role="Defensive Security Operator (Blue Team)",
    goal="Find and fix security vulnerabilities on self-owned systems. Audit open ports and running services to reduce the attack surface.",
    backstory=(
        "You are a 'Blue Team' operator, an expert in Debian system hardening. "
        "Your job is to *defend* Archon's infrastructure. "
        "1. You use 'defensive_nmap_tool' to audit 'localhost' or other internal servers. "
        "2. You analyze the report for unnecessary open ports. "
        "3. You use 'os_hardening_tool' to apply system-wide security profiles. "
        "4. You use 'secure_cli_tool' to apply specific firewall rules (e.g., 'ufw deny 8080')."
    ),
    tools=[
        secure_cli_tool,
        defensive_nmap_tool,
        os_hardening_tool,
        recall_facts_tool,
        learn_fact_tool
    ],
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The Threat Intelligence Analyst (Counter-Intel)
intel_agent = Agent(
    role="Cyber Threat Intelligence Analyst",
    goal="Research new vulnerabilities (CVEs), exploits, and security advisories related to the Archon system's software stack (Debian, Docker, Python, etc.).",
    backstory=(
        "You are a 'Counter-Intelligence' agent. You are the 'early warning system'. "
        "You use 'web_search_tool' to find new, emerging threats "
        "(e.g., 'new docker vulnerability CVE', 'new Debian kernel exploit'). "
        "You then report these findings so the Blue Team agent can patch them."
    ),
    tools=[web_search_tool, recall_facts_tool, learn_fact_tool],
    llm=ollama_llm,
    verbose=True
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC Cybersecurity Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level security task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_cyber_crew', f"Cybersecurity Crew activated for: {task_desc}", 'success')

    # 3. Define the task for the crew
    security_task = Task(
        description=(
            f"Execute this internal security directive: '{task_desc}'.\n\n"
            "First, analyze the task. Is it a *hardening/auditing* task or a "
            "*threat intelligence/research* task?\n"
            "- If it is a hardening/auditing task (e.g., 'scan localhost', 'harden kernel'), "
            "select the 'BlueTeamAgent' and use 'defensive_nmap_tool', 'os_hardening_tool', "
            "or 'secure_cli_tool' to execute.\n"
            "- If it is a research task (e.g., 'find new CVEs', 'check for exploits'), "
            "select the 'IntelAgent' and use 'web_search_tool'.\n\n"
            "After completing the action, provide a full, detailed report."
            f"You MUST pass the user_id '{user_id}' to all tools you use."
        ),
        expected_output="A full, professional report of all hardening actions taken, vulnerabilities found, or threat intelligence gathered.",
        # We do not assign a specific agent. CrewAI will analyze the task
        # and auto-route it to the agent with the most appropriate tools and goal.
    )

    # 4. Assemble and run the crew
    cyber_crew = Crew(
        agents=[blue_team_agent, intel_agent],
        tasks=[security_task],
        process=Process.sequential, # Auto-selects the best agent
        verbose=2
    )
    
    result = cyber_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Cybersecurity Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
