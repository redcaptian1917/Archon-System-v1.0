#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama

# Import the secure CLI tool and logging function
# We use fapc_tools_v4 because this crew only needs the CLI
from fapc_tools_v4 import secure_cli_tool
import auth

# --- 1. Setup Specialist Models ---
# The general-purpose model for planning
ollama_llm = Ollama(model="llama3:8b", base_url="http://localhost:11434")
# The specialist model for coding
# Make sure you have run 'ollama pull deepseek-coder-v2'
ollama_coder = Ollama(model="deepseek-coder-v2", base_url="http://localhost:11434")

# --- 2. Define Specialist Agents ---

# Agent 1: The Planner
code_planner = Agent(
    role="Senior Code Planner",
    goal="Analyze a coding task, break it down into a list of file paths and actionable, precise coding steps. Pass this plan to the engineer.",
    backstory=(
        "You are a 20-year veteran software architect. You are meticulous. "
        "You do not write code. Your job is to create a perfect, step-by-step "
        "plan for the engineer to follow, including what files to create or edit."
    ),
    tools=[], # This agent only thinks
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The Engineer
code_engineer = Agent(
    role="Expert Code Engineer",
    goal="Execute a coding plan provided by the planner. You write high-quality, efficient code and save it to the specified files.",
    backstory=(
        "You are a specialist engineer who uses 'deepseek-coder-v2'. You only follow "
        "plans. You use the 'secure_cli_tool' to write code to files. "
        "To write a file, you MUST use the command: "
        "echo '...your code...' | secure_cli_tool 'cat > /path/to/file.py'"
    ),
    tools=[secure_cli_tool],
    llm=ollama_coder, # Using the specialist model
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    # 1. Parse arguments from the "CEO"
    parser = argparse.ArgumentParser(description="FAPC Coding Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level coding task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description

    # 2. Log that this crew was activated
    auth.log_activity(user_id, 'delegate', f"Coding Crew activated for task: {task_desc}", 'success')

    # 3. Define the tasks
    task_1_plan = Task(
        description=f"Create a step-by-step coding plan for this request: '{task_desc}'",
        expected_output="A list of files to be created and a step-by-step plan of code to write.",
        agent=code_planner
    )

    task_2_code = Task(
        description=(
            "Execute the coding plan. Use the 'secure_cli_tool' to write all "
            "code to the correct files. "
            f"You MUST pass the user_id '{user_id}' to the secure_cli_tool for logging."
        ),
        expected_output="A final summary stating which files were created or modified.",
        agent=code_engineer,
        context=[task_1_plan]
    )

    # 4. Assemble and run the crew
    coding_crew = Crew(
        agents=[code_planner, code_engineer],
        tasks=[task_1_plan, task_2_code],
        process=Process.sequential,
        verbose=2
    )
    
    result = coding_crew.kickoff()
    
    # 5. Print the final result to stdout for the "CEO" to read
    print(result)

if __name__ == "__main__":
    main()