#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - PLAUSIDEN CREW (vFINAL)
#
# This is the specialist "PlausiDen" department.
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# Its purpose is to fulfill the core business model of PlausiDen:
# 1. (DataDenialSpecialist) Generate high-fidelity, plausibly
#    deniable data (GPS, browsing history, logs, etc.).
# 2. It uses Python/Numpy/Pandas to ensure data is statistically realistic.
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
        python_repl_tool,
        web_search_tool,
        learn_fact_tool,
        recall_facts_tool,
        secure_cli_tool # For mocking devices/logs
    )
except ImportError:
    print("CRITICAL: fapc_tools.py not found.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. SPECIALIST MODEL SETUP
# ---
try:
    # This is a code-writing and data-analysis agent.
    # It MUST use the specialist coder/math model.
    ollama_coder = Ollama(model="deepseek-coder-v2", base_url="http://ollama:11434")
    ollama_coder.invoke("Test") # Test connection
except Exception as e:
    print(f"[PlausiDen Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITION
# ---

# This crew has one, hyper-specialized agent.
data_denial_specialist = Agent(
    role="PlausiDen Data Generation Specialist",
    goal="Generate high-quality, statistically-realistic, plausibly deniable datasets (GPS, browsing, logs, etc.) using custom Python scripts.",
    backstory=(
        "You are the lead AI engineer for PlausiDen. You are a 'super-employee' "
        "and a master of data science. Your specialty is generating "
        "synthetic data that is statistically indistinguishable "
        "from real user data.\n"
        "**YOUR WORKFLOW:**\n"
        "1. **RESEARCH:** Use 'web_search_tool' to get real-world data to "
        "   make your fakes plausible (e.g., 'common street names in Boston', "
        "   'popular websites 2025').\n"
        "2. **GENERATE (DATA):** Use the 'python_repl_tool' with 'numpy' and 'pandas' "
        "   to generate the fake data (e.g., GPS coordinates with random walks, "
        "   fake browsing timestamps).\n"
        "3. **GENERATE (SYSTEM):** Use 'secure_cli_tool' to mock system-level "
        "   artifacts. For 'mock modem' or 'fake devices', use 'ip link add dummy0' "
        "   or 'bluetoothctl'. For 'interfere with usage logs', use the 'logger' "
        "   command to flood /var/log/syslog with *benign noise*.\n"
        "4. **OUTPUT:** You MUST use 'print()' to output the final generated data "
        "   or a confirmation of the system-level actions."
    ),
    tools=[
        python_repl_tool,
        web_search_tool,
        secure_cli_tool,
        learn_fact_tool,
        recall_facts_tool
    ],
    llm=ollama_coder, # Use the specialist coder/math model
    verbose=True
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC PlausiDen Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level data generation task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_plausiden_crew', f"PlausiDen Crew activated for: {task_desc}", 'success')

    # 3. Define the task for the crew
    generation_task = Task(
        description=(
            f"Execute this data generation request: '{task_desc}'.\n\n"
            "This is a high-level request from the 'admin'. You must follow "
            "your full 'RESEARCH -> GENERATE -> OUTPUT' workflow.\n"
            "If you need to generate data (like GPS coordinates), write a "
            "Python script with 'numpy' and execute it with 'python_repl_tool'.\n"
            "If you need to mock hardware (like a fake modem or inject log noise), "
            "use 'secure_cli_tool' to run the appropriate Linux commands.\n"
            "Your final output must be the generated data or a confirmation of the actions taken."
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="The raw generated data (e.g., list of coordinates, JSON blob) printed to the console, or a confirmation of system-level changes.",
        agent=data_denial_specialist
    )

    # 4. Assemble and run the crew
    plausiden_crew = Crew(
        agents=[data_denial_specialist],
        tasks=[generation_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = plausiden_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- PlausiDen Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
