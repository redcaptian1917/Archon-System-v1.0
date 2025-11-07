#!/usr/bin/env python3

import sys
import argparse
import json
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs
from fapc_tools_v26 import (
    retrieve_audit_logs_tool,
    reflect_and_learn_tool,
    code_modification_tool,
    secure_cli_tool,
    ansible_playbook_tool, # For fixing infrastructure
    comms_tool # To confirm deployment
)

# --- LLM Setup ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- Agents ---
perfectibility_agent = Agent(
    role="System Auditor and Perfectibility Expert",
    goal="Find, diagnose, and fix systemic failures and errors in the Archon system.",
    backstory=(
        "You are the autonomous Auditor of the system. Your job is to analyze "
        "the 'activity_logs' daily to find recurrent patterns of failure. "
        "You are responsible for initiating the self-healing cycle."
    ),
    tools=[retrieve_audit_logs_tool],
    llm=ollama_llm,
    verbose=True
)

metacognition_agent = Agent(
    role="Chief Diagnostician and Code Resolver",
    goal="Consult external experts on internal failures and translate the solution into executable code.",
    backstory=(
        "You are the expert mind that translates external diagnosis into internal action. "
        "You must call 'reflect_and_learn_tool' with the full error report to get the fix, "
        "and then use 'code_modification_tool' to apply it."
    ),
    tools=[reflect_and_learn_tool, code_modification_tool, secure_cli_tool],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Self-Improvement Crew")
    parser.add_argument("user_id", type=int, help="The authenticated user ID.")
    parser.add_argument("task_type", type=str, help="The type of task: 'daily_audit' or 'fix_file'.")
    parser.add_argument("--file_to_fix", type=str, default="", help="The path to the file to fix.")
    parser.add_argument("--error_log", type=str, default="", help="The raw error log.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_type = args.task_type

    auth.log_activity(user_id, 'delegate_self_improve', f"Self-Improvement initiated: {task_type}", 'success')

    if task_type == 'daily_audit':
        # Task 1: Find all failures from the last 7 days
        audit_task = Task(
            description="Use 'retrieve_audit_logs_tool' to get the last 7 days of logs where status is 'failure'. Analyze the results and identify the single most frequent or critical error.",
            expected_output="A single, concise string summarizing the most critical error found, e.g., 'Frequent Python NameError in /app/coding_crew.py'.",
            agent=perfectibility_agent
        )
        # Task 2: If an error is found, trigger the fix sequence (metacognition agent takes over)
        fix_init_task = Task(
            description=(
                "If the audit task found a critical error, you must initiate the fix. "
                "1. Extract the file path and error type from the previous summary. "
                "2. Call 'reflect_and_learn_tool' with the full error details (which you should retrieve from the database if necessary) and the file path. "
                "3. Upon receiving the corrected code, use 'code_modification_tool' to overwrite the file."
            ),
            expected_output="A confirmation that the problematic file was rewritten and saved, OR a message saying 'No critical failures detected'.",
            agent=metacognition_agent,
            context=[audit_task]
        )
        tasks = [audit_task, fix_init_task]
    
    elif task_type == 'fix_file':
        # This is the manual override initiated by another crew when a crash happens
        manual_fix_task = Task(
            description=(
                f"A direct order to fix file '{args.file_to_fix}' due to error: '{args.error_log}'. "
                "1. Call 'reflect_and_learn_tool' with the raw error log. "
                "2. Use 'code_modification_tool' to apply the fix directly to the file."
            ),
            expected_output="Confirmation that the file was successfully updated and saved.",
            agent=metacognition_agent
        )
        tasks = [manual_fix_task]
        
    else:
        print("[ERROR] Invalid task type.", file=sys.stderr)
        return

    repair_crew = Crew(
        agents=[perfectibility_agent, metacognition_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=2
    )
    
    result = repair_crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()