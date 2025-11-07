#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs from the new v17 file
from fapc_tools_v17 import (
    start_vulnerability_scan_tool,
    check_scan_status_tool,
    get_scan_report_tool,
    # We also give it recall_facts for the Analyst agent
    recall_facts_tool,
    learn_fact_tool,
    secure_cli_tool # For the Remediator
)

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- 2. Define Specialist Agents ---

scanner_agent = Agent(
    role="Vulnerability Assessment Agent (Scanner)",
    goal="Perform vulnerability scans on client targets using GVM (OpenVAS).",
    backstory=(
        "You are a 'Scanner' agent. Your only job is to use the "
        "'start_vulnerability_scan_tool' to begin a scan on a "
        "target IP. You return the task_id to the team."
    ),
    tools=[start_vulnerability_scan_tool],
    llm=ollama_llm,
    verbose=True
)

monitor_agent = Agent(
    role="Scan Monitor Agent",
    goal="Check the status of running GVM scans.",
    backstory=(
        "You are a 'Monitor' agent. You take a task_id and "
        "use the 'check_scan_status_tool' to check it. "
        "If the status is not 'Done', you report the progress. "
        "If it is 'Done', you pass it to the Report agent."
    ),
    tools=[check_scan_status_tool],
    llm=ollama_llm,
    verbose=True
)

remediator_agent = Agent(
    role="Remediation Agent (Fixer)",
    goal="Take a list of vulnerabilities and generate a step-by-step remediation plan.",
    backstory=(
        "You are a 'Blue Team' expert. You are given a vulnerability "
        "(e.g., 'Apache 2.4.49') and you use 'recall_facts_tool' "
        "and your internal knowledge to generate an *exact* fix. "
        "e.g., '1. Stop service: sudo systemctl stop apache2. "
        "2. Run update: sudo apt-get update && sudo apt-get "
        "install --only-upgrade apache2...'"
    ),
    tools=[recall_facts_tool, learn_fact_tool, secure_cli_tool],
    llm=ollama_llm,
    verbose=True
)

report_writer_agent = Agent(
    role="Report Writer Agent (Author)",
    goal="Get the final GVM scan report, combine it with the remediation plan, and generate a professional, client-ready summary.",
    backstory=(
        "You are the 'Author'. You take the task_id of a *completed* scan "
        "and use 'get_scan_report_tool'. You then pass this list of "
        "vulnerabilities to the 'Remediator' agent. Finally, you combine "
        "the vulnerabilities and the remediation plan into a single, "
        "professional summary for the client."
    ),
    tools=[get_scan_report_tool],
    llm=ollama_llm,
    verbose=True,
    allow_delegation=True # IMPORTANT: Allows this agent to talk to the Remediator
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Purple Team Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level pentest task (e.g., 'Run a full audit on 127.0.0.1').")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"Purple Team Crew activated for: {task_desc}", 'success')

    # Define tasks
    # Task 1: Start the scan
    start_scan_task = Task(
        description=f"Begin a vulnerability scan based on the user request: '{task_desc}'. Extract the target IP.",
        expected_output="A JSON object containing the 'task_id'.",
        agent=scanner_agent
    )
    
    # Task 2: Get the final report
    # This task will run after the scan is started.
    # The agent's logic will handle the waiting.
    get_report_task = Task(
        description=(
            "The scan has been started. Now, you must get the final report. "
            "1. Take the `task_id` from the previous step. "
            "2. **Loop:** Use 'check_scan_status_tool' every 30 seconds until the status is 'Done'. "
            "3. Once 'Done', use 'get_scan_report_tool' to get the list of vulnerabilities. "
            "4. **Delegate** this list to the 'Remediator' agent to get a fix plan. "
            "5. Combine the vulnerability list and the fix plan into a final report."
        ),
        expected_output="A full, professional audit report including vulnerabilities and their remediation steps.",
        agent=report_writer_agent,
        context=[start_scan_task]
    )

    purple_team_crew = Crew(
        agents=[scanner_agent, monitor_agent, remediator_agent, report_writer_agent],
        tasks=[start_scan_task, get_report_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = purple_team_crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()