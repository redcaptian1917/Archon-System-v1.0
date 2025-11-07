#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs
from fapc_tools_v19 import (
    update_offline_databases_tool,
    search_exploit_db_tool,
    search_cve_database_tool,
    forensics_tool
)

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- 2. Define Specialist Agents ---

db_manager_agent = Agent(
    role="Database Manager",
    goal="Keep all offline vulnerability databases (Exploit-DB, CVE List) up-to-date.",
    backstory=(
        "You are a meticulous database administrator. Your only job is to "
        "run the 'update_offline_databases_tool' to ensure all "
        "local databases are synced with their git repositories."
    ),
    tools=[update_offline_databases_tool],
    llm=ollama_llm,
    verbose=True
)

analyst_agent = Agent(
    role="Vulnerability Analyst",
    goal="Search the offline databases to find exploits and CVE details.",
    backstory=(
        "You are a 'Purple Team' analyst. You use 'search_exploit_db_tool' "
        "and 'search_cve_database_tool' to cross-reference vulnerabilities "
        "and find potential exploits. You provide this data to other crews."
    ),
    tools=[search_exploit_db_tool, search_cve_database_tool],
    llm=ollama_llm,
    verbose=True
)

forensics_agent = Agent(
    role="Digital Forensics Investigator",
    goal="Perform data recovery and file system analysis on disk images.",
    backstory=(
        "You are a forensics expert. You use the 'forensics_tool' (The "
        "Sleuth Kit) to list files ('fls'), recover deleted files ('icat'), "
        "and analyze disk images provided to you."
    ),
    tools=[forensics_tool],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC DFIR Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level DFIR task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"DFIR Crew activated for: {task_desc}", 'success')

    dfir_task = Task(
        description=(
            f"Execute this DFIR task: '{task_desc}'.\n"
            "If the task is 'update databases', use the 'update_offline_databases_tool'.\n"
            "If the task is 'find exploit' or 'search CVE', use the 'analyst_agent' tools.\n"
            "If the task is 'analyze disk image', use the 'forensics_tool'.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of database updates, search results, or forensic findings.",
        # Let CrewAI auto-route to the best agent
    )

    dfir_crew = Crew(
        agents=[db_manager_agent, analyst_agent, forensics_agent],
        tasks=[dfir_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = dfir_crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()