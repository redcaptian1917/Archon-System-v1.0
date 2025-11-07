#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs
from fapc_tools_v20 import (
    metadata_scrubber_tool,
    os_hardening_tool,
    secure_cli_tool,
    web_search_tool
)

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- 2. Define Specialist Agents ---
anonymizer_agent = Agent(
    role="Data Anonymizer",
    goal="Find and destroy all metadata and fingerprints from files.",
    backstory=(
        "You are a privacy expert for PlausiDen. You use the "
        "'metadata_scrubber_tool' to clean files and directories. "
        "You also use 'secure_cli_tool' to find files to clean."
    ),
    tools=[metadata_scrubber_tool, secure_cli_tool],
    llm=ollama_llm,
    verbose=True
)

hardener_agent = Agent(
    role="OS Hardening Specialist",
    goal="Apply security and privacy configurations to operating systems.",
    backstory=(
        "You are a 'Blue Team' engineer. You apply hardening profiles "
        "using the 'os_hardening_tool'. You can also use 'web_search_tool' "
        "to research new hardening techniques for Debian-based systems."
    ),
    tools=[os_hardening_tool, web_search_tool],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Hardening Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level hardening/anonymization task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"Hardening Crew activated for: {task_desc}", 'success')

    hardening_task = Task(
        description=(
            f"Execute this hardening task: '{task_desc}'.\n"
            "If it's about cleaning files, use the 'metadata_scrubber_tool'.\n"
            "If it's about OS settings, use the 'os_hardening_tool'.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of all files scrubbed or settings applied.",
        # Let CrewAI auto-route
    )

    hardening_crew = Crew(
        agents=[anonymizer_agent, hardener_agent],
        tasks=[hardening_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = hardening_crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()