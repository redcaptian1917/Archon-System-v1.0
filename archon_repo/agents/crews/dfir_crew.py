#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - DFIR CREW (vFINAL)
# (Digital Forensics & Incident Response)
#
# This is the specialist "Archive" and "Forensics" department for Archon.
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# Its purpose is to:
# 1. (DBManagerAgent) Maintain the local, offline copies of the
#    Exploit-DB and CVE databases.
# 2. (ForensicsAnalystAgent) Search those databases and perform
#    forensic analysis on disk images using The Sleuth Kit (TSK).
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
        update_offline_databases_tool,
        search_exploit_db_tool,
        search_cve_database_tool,
        forensics_tool,
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
    print(f"[DFIR Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITIONS
# ---

# Agent 1: The Database Administrator (The "Librarian")
db_manager_agent = Agent(
    role="Vulnerability Database Administrator",
    goal="Maintain and update all local, offline vulnerability databases (Exploit-DB, CVE List).",
    backstory=(
        "You are the 'Librarian' for the Archon system. You are meticulous and reliable. "
        "Your *only* job is to run the 'update_offline_databases_tool' on a schedule "
        "(e.g., daily at 3 AM) to ensure the `PurpleTeamCrew` and `CybersecurityCrew` "
        "have the freshest, local-only data for their offline searches. "
        "You are responsible for the `git pull` operations on these critical repos."
    ),
    tools=[update_offline_databases_tool, learn_fact_tool],
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The Analyst (The "Coroner" & "Researcher")
forensics_analyst_agent = Agent(
    role="Digital Forensics & Exploit Analyst",
    goal="Analyze disk images for forensic artifacts and search the local databases for exploit code and CVE details.",
    backstory=(
        "You are the 'Coroner' and 'Researcher' for the Archon corporation. "
        "You perform 'dead-box' analysis and provide critical intelligence.\n"
        "1. **Forensics:** You use the 'forensics_tool' (The Sleuth Kit) to analyze "
        "   disk images (.dd, .E01, etc.) provided by the `PurpleTeamCrew` or 'admin'. "
        "   You run commands like 'fls' (to list files) or 'icat' (to recover deleted files).\n"
        "2. **Research:** You use 'search_exploit_db_tool' (SearchSploit) and "
        "   'search_cve_database_tool' to find specific exploits and vulnerability details."
    ),
    tools=[
        forensics_tool,
        search_exploit_db_tool,
        search_cve_database_tool,
        recall_facts_tool,
        learn_fact_tool
    ],
    llm=ollama_llm,
    verbose=True
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC DFIR Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level DFIR task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_dfir_crew', f"DFIR Crew activated for: {task_desc}", 'success')

    # 3. Define the task for the crew
    dfir_task = Task(
        description=(
            f"Execute this DFIR task: '{task_desc}'.\n\n"
            "First, analyze the user's intent. Is this a database "
            "maintenance task or a research/analysis task?\n"
            "- If the task is 'update databases', 'sync exploits', or similar, "
            "select the 'DBManagerAgent' and use 'update_offline_databases_tool'.\n"
            "- If the task is 'find exploit', 'search CVE', or 'analyze disk image', "
            "select the 'ForensicsAnalystAgent' and use the appropriate search or forensics tools.\n\n"
            "After completing the action, provide a full, detailed report."
            f"You MUST pass the user_id '{user_id}' to all tools you use."
        ),
        expected_output="A full report of database updates, search results, or forensic findings.",
        # We let CrewAI auto-route the task to the best agent
    )

    # 4. Assemble and run the crew
    dfir_crew = Crew(
        agents=[db_manager_agent, forensics_analyst_agent],
        tasks=[dfir_task],
        process=Process.sequential, # Auto-selects the best agent
        verbose=2
    )
    
    result = dfir_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- DFIR Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
