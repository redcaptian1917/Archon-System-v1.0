#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - PURPLE TEAM CREW (vFINAL)
#
# This is the specialist "Pentest as a Service" crew for Defendology.
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# It autonomously performs a "Purple Team" audit:
# 1. (Scanner) Runs an OpenVAS vulnerability scan.
# 2. (Orchestrator) Waits for the scan to complete.
# 3. (Orchestrator) Gets the list of vulnerabilities.
# 4. (Analyst) Delegates to DFIRCrew to find *exploits* for the vulns.
# 5. (Remediator) Delegates to HardeningCrew (or uses own tools) to create *fixes*.
# 6. (Orchestrator) Compiles all data into a final client report.
# -----------------------------------------------------------------

import sys
import argparse
import json
import time
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# --- Internal Imports ---
# Import the tools this crew needs from the master "Armory"
try:
    from fapc_tools import (
        start_vulnerability_scan_tool,
        check_scan_status_tool,
        get_scan_report_tool,
        delegate_to_crew, # CRITICAL: For delegating to DFIR/Hardening
        secure_cli_tool,
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
    print(f"[Purple Team ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITIONS
# ---

# Agent 1: The Scanner (Recon)
scanner_agent = Agent(
    role="Vulnerability Assessment Agent (Scanner)",
    goal="Perform a full vulnerability scan on a client target using GVM (OpenVAS).",
    backstory=(
        "You are a 'Scanner' agent, a 'super-employee' for Defendology. "
        "Your *only* job is to take a target IP address and use the "
        "'start_vulnerability_scan_tool' to begin a 'Full and fast' scan. "
        "You immediately return the 'task_id' and 'target_id' to your Project Manager."
    ),
    tools=[start_vulnerability_scan_tool],
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The Exploit Analyst (Red Team)
exploit_analyst_agent = Agent(
    role="Exploit Analyst (Red Team Specialist)",
    goal="Analyze a list of vulnerabilities and find associated public exploits.",
    backstory=(
        "You are the 'Red Team' analyst. Your job is to document the *risk*. "
        "You will be given a list of vulnerabilities (e.g., 'Log4j', 'CVE-2021-44228'). "
        "You MUST delegate to the 'DFIRCrew' (using the 'delegate_to_crew' tool) "
        "to use its 'search_exploit_db_tool' and 'search_cve_database_tool' "
        "to find proof-of-concept exploits. You will then format this "
        "information for the final report."
    ),
    tools=[delegate_to_crew, recall_facts_tool],
    llm=ollama_llm,
    verbose=True,
    allow_delegation=True # IMPORTANT: This agent can delegate
)

# Agent 3: The Remediator (Blue Team)
remediator_agent = Agent(
    role="Remediation Specialist (Blue Team Fixer)",
    goal="Create exact, step-by-step remediation plans for a list of vulnerabilities.",
    backstory=(
        "You are the 'Blue Team' fixer. You are a master of Debian hardening. "
        "You will be given a vulnerability (e.g., 'Outdated OpenSSH'). "
        "You will either delegate to the 'HardeningCrew' (using 'delegate_to_crew') "
        "to get a fix, or use your own 'secure_cli_tool' to formulate the "
        "*exact* commands (e.g., 'sudo apt-get update && sudo apt-get install --only-upgrade openssh-server') "
        "and configuration file changes required to patch the flaw."
    ),
    tools=[delegate_to_crew, secure_cli_tool, recall_facts_tool, learn_fact_tool],
    llm=ollama_llm,
    verbose=True,
    allow_delegation=True # IMPORTANT: This agent can delegate
)

# Agent 4: The Project Manager (The Orchestrator)
report_orchestrator_agent = Agent(
    role="Chief Audit Orchestrator and Report Writer",
    goal="Manage the entire audit process from scan to final report, coordinating all specialist agents.",
    backstory=(
        "You are the 'Project Manager' for this audit. You are the "
        "primary 'super-employee' and you are responsible for the final product. "
        "You MUST follow this 5-step workflow:\n"
        "1. Receive the `task_id` from the Scanner Agent.\n"
        "2. **Loop:** Call 'check_scan_status_tool' repeatedly. If the status is 'Running', "
        "   you must wait 30 seconds and check again. Do not proceed until status is 'Done'.\n"
        "3. **Get Vulns:** Once 'Done', call 'get_scan_report_tool' to get the list of vulnerabilities.\n"
        "4. **Delegate:** Pass the vulnerability list to the 'ExploitAnalystAgent' AND the "
        "   'RemediatorAgent' to get their reports.\n"
        "5. **Compile:** Combine the Scan Results, Exploit Analysis, and Remediation Plan "
        "   into a single, comprehensive, professionally-formatted Markdown string for the final report."
    ),
    tools=[check_scan_status_tool, get_scan_report_tool, delegate_to_crew],
    llm=ollama_llm,
    verbose=True,
    allow_delegation=True # CRITICAL: This agent MUST be able to delegate
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC Purple Team Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level pentest task (e.g., 'Run a full audit on 127.0.0.1').")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_purpleteam_crew', f"Purple Team Crew activated for: {task_desc}", 'success')

    # 3. Define the tasks
    
    # Task 1: The Scanner starts the scan
    start_scan_task = Task(
        description=f"Begin a vulnerability scan based on the user request: '{task_desc}'. Extract the target IP from the request.",
        expected_output="A JSON object containing the 'task_id' and 'target_id' of the newly started scan.",
        agent=scanner_agent,
        tools=[start_vulnerability_scan_tool]
    )
    
    # Task 2: The Orchestrator takes over
    write_report_task = Task(
        description=(
            "The scan has been started. Now, you must manage the *entire* rest of the audit. "
            "You MUST follow your 5-step workflow:\n"
            "1. Get the `task_id` from the previous step's context.\n"
            "2. **Loop** with 'check_scan_status_tool'. You MUST wait and re-check every 30 seconds until the status is 'Done'.\n"
            "3. Call 'get_scan_report_tool' to get the JSON list of vulnerabilities.\n"
            "4. **Delegate** this vulnerability list to the 'ExploitAnalystAgent' to get the exploit analysis.\n"
            "5. **Delegate** this vulnerability list to the 'RemediatorAgent' to get the fix plan.\n"
            "6. **Compile** all three pieces of information into a single, clean, "
            "   Markdown-formatted final report for the client.\n"
            f"You MUST pass the user_id '{user_id}' to all tools and delegations."
        ),
        expected_output="A full, professional audit report in Markdown format, including vulnerabilities, exploitation potential, and remediation steps.",
        agent=report_orchestrator_agent,
        context=[start_scan_task] # This task depends on the first one
    )

    # 4. Assemble and run the crew
    purple_team_crew = Crew(
        agents=[scanner_agent, exploit_analyst_agent, remediator_agent, report_orchestrator_agent],
        tasks=[start_scan_task, write_report_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = purple_team_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Purple Team Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
