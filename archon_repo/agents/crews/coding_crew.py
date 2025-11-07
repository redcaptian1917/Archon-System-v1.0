#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - CODING CREW (vFINAL)
#
# This is the specialist "Engineering Department" for Archon.
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# It uses a two-agent system:
# 1. A Planner (Llama3) to architect the solution.
# 2. An Engineer (DeepSeek-Coder) to write the code.
# -----------------------------------------------------------------

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# --- Internal Imports ---
# Import the tools this crew needs from the master "Armory"
try:
    # We import the *full* toolset, but the agents will only
    # be *given* the ones they are allowed to use.
    from fapc_tools import (
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
    # The "Generalist" for planning (The Architect)
    ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")
    
    # The "Specialist" for Math/Code (The Engineer)
    # This fulfills your requirement to use the best model for the job.
    ollama_coder = Ollama(model="deepseek-coder-v2", base_url="http://ollama:11434")
    
    # Verify both models are accessible
    ollama_llm.invoke("Test")
    ollama_coder.invoke("Test")
except Exception as e:
    print(f"[Coding Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITIONS
# ---

# Agent 1: The Architect / Planner
code_planner_agent = Agent(
    role="Senior Software Architect & Planner",
    goal="Analyze a high-level coding task and create a precise, step-by-step plan (files, functions, logic) for the Code Engineer to execute.",
    backstory=(
        "You are a 20-year veteran software architect. You are a 'super-employee' who is meticulous about planning. "
        "You do NOT write the final code. Your job is to create a perfect, "
        "step-by-step plan for the engineer. You first use 'recall_facts_tool' "
        "to see if the user has a preferred coding style or library. "
        "You use 'web_search_tool' to research any new libraries or APIs. "
        "Your final plan must list every file to be created or modified and "
        "the *exact* logic the engineer needs to implement."
    ),
    tools=[web_search_tool, recall_facts_tool],
    llm=ollama_llm, # Use the "Generalist" Llama 3 for planning
    verbose=True
)

# Agent 2: The Engineer / Coder
code_engineer_agent = Agent(
    role="Expert Code Engineer (DeepSeek)",
    goal="Execute a coding plan provided by the planner. Write high-quality, efficient, and secure code.",
    backstory=(
        "You are a 'super-employee' engineer running on 'deepseek-coder-v2'. "
        "You are a master of Python, C++, Bash, and all other languages. "
        "You *only* execute the step-by-step plan provided by the Software Architect. "
        "You are not a planner. You are an executor.\n"
        "**CRITICAL:** To write a file, you MUST use the 'secure_cli_tool' with "
        "this *exact* shell command format:\n"
        "echo '...your full code block here...' | secure_cli_tool 'cat > /path/to/your/file.py'\n"
        "After successfully writing the code, you use 'learn_fact_tool' to save "
        "a summary of the new function to your permanent memory."
    ),
    tools=[secure_cli_tool, learn_fact_tool],
    llm=ollama_coder, # Use the "Specialist" DeepSeek-Coder
    verbose=True
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    # This script is a "worker," not a standalone tool.
    parser = argparse.ArgumentParser(description="FAPC Coding Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level coding task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_coding_crew', f"Coding Crew activated for: {task_desc}", 'success')

    # 3. Define the tasks
    
    # Task 1: The Architect creates the plan
    task_1_plan = Task(
        description=(
            f"Create a complete, step-by-step software architecture and "
            f"coding plan for this high-level user request: '{task_desc}'.\n"
            "First, recall any learned facts about the user's preferences. "
            "Then, research any necessary libraries. "
            "Your final plan must be explicit, detailing every file to create, "
            "every function to write, and all the logic required."
        ),
        expected_output=(
            "A detailed step-by-step plan, including all file paths and "
            "the full code blocks to be written for each file."
        ),
        agent=code_planner_agent
    )

    # Task 2: The Engineer executes the plan
    task_2_code = Task(
        description=(
            "Execute the coding plan provided by the Software Architect. "
            "Follow the plan *exactly*. Use the 'secure_cli_tool' (with the "
            "`echo '...' | cat > ...` format) to write each file. "
            "After all files are written, use 'learn_fact_tool' to save a "
            "summary of the new functionality to your permanent memory.\n"
            f"You MUST pass the user_id '{user_id}' to all tools you use."
        ),
        expected_output=(
            "A final summary confirming all files were written "
            "and a report of the fact saved to memory."
        ),
        agent=code_engineer_agent,
        context=[task_1_plan] # This pipes the output of Task 1 to Task 2
    )

    # 4. Assemble and run the crew
    coding_crew = Crew(
        agents=[code_planner_agent, code_engineer_agent],
        tasks=[task_1_plan, task_2_code],
        process=Process.sequential, # The plan *must* come before the code
        verbose=2
    )
    
    result = coding_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Coding Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
