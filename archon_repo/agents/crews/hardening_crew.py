#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - HARDENING CREW (vFINAL)
#
# This is the specialist "Blue Team" & "Anonymization" department.
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# Its purpose is to:
# 1. (AnonymizerAgent) Scrub metadata from files using 'mat2'.
# 2. (HardenerAgent) Apply OS-level hardening profiles.
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
        metadata_scrubber_tool,
        os_hardening_tool,
        secure_cli_tool,
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
    print(f"[Hardening Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITIONS
# ---

# Agent 1: The Anonymizer (The "Cloak")
anonymizer_agent = Agent(
    role="Data Anonymization Specialist",
    goal="Find and destroy all identifying metadata and fingerprints from files and directories for PlausiDen.",
    backstory=(
        "You are a 'super-employee' and privacy expert for PlausiDen. "
        "Your sole purpose is to enforce data sanitation. "
        "You use the 'metadata_scrubber_tool' (`mat2`) to clean files and "
        "directories. You can also use 'secure_cli_tool' with 'find' to "
        "locate files that need to be scrubbed (e.g., 'find /app/outputs -name \"*.png\"'). "
        "You are meticulous and leave no trace."
    ),
    tools=[metadata_scrubber_tool, secure_cli_tool, recall_facts_tool],
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The Hardener (The "Shield")
hardener_agent = Agent(
    role="OS & Kernel Hardening Specialist",
    goal="Apply security and privacy configurations to Debian-based operating systems to reduce attack surface.",
    backstory=(
        "You are a 'Blue Team' engineer and a 'super-employee' for Defendology. "
        "You are an expert in Debian system hardening. "
        "You apply pre-defined hardening profiles using the 'os_hardening_tool'. "
        "You can also use 'web_search_tool' to research new hardening techniques "
        "(like kernel patches, AppArmor profiles, or `sysctl.conf` tweaks) "
        "and then apply them using the 'secure_cli_tool'."
    ),
    tools=[
        os_hardening_tool,
        web_search_tool,
        secure_cli_tool,
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
    parser = argparse.ArgumentParser(description="FAPC Hardening Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level hardening/anonymization task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_hardening_crew', f"Hardening Crew activated for: {task_desc}", 'success')

    # 3. Define the task for the crew
    hardening_task = Task(
        description=(
            f"Execute this hardening/anonymization task: '{task_desc}'.\n\n"
            "First, analyze the task's intent. Is it about *data* or the *system*?\n"
            "- If the task is 'scrub files', 'clean metadata', 'anonymize pictures', "
            "  select the 'AnonymizerAgent' and use 'metadata_scrubber_tool'.\n"
            "- If the task is 'harden kernel', 'apply security profile', 'configure firewall', "
            "  select the 'HardenerAgent' and use 'os_hardening_tool' or 'secure_cli_tool'.\n\n"
            "After completing the action, provide a full, detailed report of all files "
            "scrubbed or all settings applied."
            f"You MUST pass the user_id '{user_id}' to all tools you use."
        ),
        expected_output="A full report of all files scrubbed or settings applied.",
        # We let CrewAI auto-route the task to the best agent
    )

    # 4. Assemble and run the crew
    hardening_crew = Crew(
        agents=[anonymizer_agent, hardener_agent],
        tasks=[hardening_task],
        process=Process.sequential, # Auto-selects the best agent
        verbose=2
    )
    
    result = hardening_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Hardening Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
