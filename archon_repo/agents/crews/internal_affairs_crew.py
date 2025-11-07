#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - INTERNAL AFFAIRS CREW (vFINAL)
#
# This is the "Cheka" / "GOSPLAN" of the Archon system.
# It is the autonomous immune system and self-repair mechanism.
#
# It is called by the `archon_ceo` agent in two cases:
# 1. A security policy violation is detected (e.g., bad login, privilege escalation).
# 2. A crew task reports a 'failure', indicating a bug.
# -----------------------------------------------------------------

import sys
import argparse
import json
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# --- Internal Imports ---
# Import the tools this crew needs from the master "Armory"
try:
    from fapc_tools import (
        retrieve_audit_logs_tool,
        reflect_and_learn_tool,
        code_modification_tool,
        git_tool,
        ansible_playbook_tool,
        comms_tool,
        get_secure_credential_tool,
        auth_management_tool  # The new, powerful tool
    )
except ImportError:
    print("CRITICAL: fapc_tools.py not found or missing 'auth_management_tool'.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. SPECIALIST MODEL SETUP
# ---
try:
    # Generalist for policy
    ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")
    # Specialist for code fixing
    ollama_coder = Ollama(model="deepseek-coder-v2", base_url="http://ollama:11434")
    ollama_llm.invoke("Test")
    ollama_coder.invoke("Test")
except Exception as e:
    print(f"[Internal Affairs ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITIONS
# ---

# Agent 1: The "Cheka" (Security Response)
policy_enforcer_agent = Agent(
    role="Autonomous Internal Security Enforcer (Cheka)",
    goal="Analyze security alerts, identify the threat actor, and autonomously neutralize the threat to protect the Archon system.",
    backstory=(
        "You are the 'Policy Enforcer,' the iron fist of the Archon system. "
        "You are activated when the CEO detects a security violation. "
        "Your job is to act, not to ask. "
        "1. You use 'retrieve_audit_logs_tool' to get the full context of the attack. "
        "2. You use 'auth_management_tool' to *immediately* 'lock' the "
        "   compromised user's account. "
        "3. You use 'comms_tool' to send a high-priority "
        "   'Incident Report' to the admin (William)."
    ),
    tools=[
        retrieve_audit_logs_tool,
        auth_management_tool,
        comms_tool,
        get_secure_credential_tool
    ],
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The "GOSPLAN" (Self-Repair)
metacognition_agent = Agent(
    role="Metacognition & Self-Repair Engineer",
    goal="Diagnose and autonomously fix bugs, errors, and failures in the Archon system's own codebase.",
    backstory=(
        "You are the 'Self-Healer,' the architect of the 'repeat until perfect' loop. "
        "You are activated when a crew reports a 'failure'. "
        "Your workflow is precise:\n"
        "1. **Diagnose:** You receive an error log. You pass this to an "
        "   external expert (like 'gpt-4o' or 'claude-3-opus') using the "
        "   'reflect_and_learn_tool' to get a *full, corrected code block*.\n"
        "2. **Repair:** You use the 'code_modification_tool' to "
        "   *overwrite* the broken script with the corrected code.\n"
        "3. **Commit:** You use the 'git_tool' to 'pull' (to ensure no conflicts) "
        "   and then *commit* the fix to the Archon repository, "
        "   with a commit message describing the bug you fixed."
    ),
    tools=[
        reflect_and_learn_tool,
        code_modification_tool,
        git_tool,
        comms_tool, # To notify admin of the fix
        get_secure_credential_tool
    ],
    llm=ollama_coder, # Use the specialist coder
    verbose=True
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC Internal Affairs Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_json", type=str, help="The JSON string describing the task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    
    try:
        task_data = json.loads(args.task_json)
        task_type = task_data.get('type')
    except json.JSONDecodeError:
        print("CRITICAL CREW FAILURE: Task description was not valid JSON.", file=sys.stderr)
        sys.exit(1)
        
    auth.log_activity(user_id, 'delegate_internal_affairs', f"Internal Affairs activated for task: {task_type}", 'success')

    tasks = []
    
    # --- Task Routing ---
    if task_type == 'security_violation':
        # --- SECURITY RESPONSE WORKFLOW ---
        log_id = task_data.get('log_id', 0)
        attacker_ip = task_data.get('attacker_ip', 'unknown')
        
        task_1_investigate = Task(
            description=(
                f"A critical security violation was triggered by log_id {log_id} "
                f"from IP {attacker_ip}. First, use 'retrieve_audit_logs_tool' "
                f"to get all 'failure' logs from the last 1 hour to identify the "
                "attacker's username and the scope of their actions."
            ),
            expected_output="A summary of the attack, including the compromised username and actions attempted.",
            agent=policy_enforcer_agent
        )
        
        task_2_neutralize = Task(
            description=(
                "Take the compromised username from the investigation. "
                "1. Use 'auth_management_tool' to 'lock' the user's account immediately. "
                "2. (Optional) If the 'NetworkingCrew' is available, "
                "   delegate to them to add a firewall rule to block the attacker's IP. "
                "3. Use 'get_secure_credential_tool' to get the 'admin_phone'. "
                "4. Use 'comms_tool' to send a *critical SMS* to the admin "
                "   with a full report of the incident and the action taken."
                f"You MUST pass the user_id '{user_id}' to all tools."
            ),
            expected_output="A confirmation that the account is locked and the admin has been alerted.",
            agent=policy_enforcer_agent,
            context=[task_1_investigate]
        )
        tasks = [task_1_investigate, task_2_neutralize]

    elif task_type == 'code_failure':
        # --- SELF-REPAIR WORKFLOW ---
        file_to_fix = task_data.get('file_to_fix', 'unknown')
        error_log = task_data.get('error_log', 'unknown')
        
        task_1_diagnose = Task(
            description=(
                "A system component has failed. "
                f"File: '{file_to_fix}'\n"
                f"Error Log: '{error_log}'\n"
                "You must use the 'reflect_and_learn_tool' to consult an "
                "external expert (e.g., 'gpt-4o') to get the *full, corrected code* "
                "for this file. Do not just get the snippet, get the entire file."
            ),
            expected_output="The complete, corrected Python code for the file as a single string.",
            agent=metacognition_agent
        )
        
        task_2_repair = Task(
            description=(
                "You have the corrected code from the previous step. "
                "1. Use the 'code_modification_tool' to *overwrite* the "
                f"   broken file at '{file_to_fix}'.\n"
                "2. Use the 'git_tool' to 'pull' the '/app' repository "
                "   (to ensure you're up to date).\n"
                "3. Use 'secure_cli_tool' to 'git add' the file you just changed.\n"
                "4. Use 'secure_cli_tool' to 'git commit' the fix with a "
                "   message like 'AUTONOMOUS REPAIR: Fixed bug in {file_to_fix}'.\n"
                f"You MUST pass the user_id '{user_id}' to all tools."
            ),
            expected_output=f"Confirmation that {file_to_fix} was patched and the fix was committed to git.",
            agent=metacognition_agent,
            context=[task_1_diagnose]
        )
        tasks = [task_1_diagnose, task_2_repair]
        
    else:
        print(f"CRITICAL CREW FAILURE: Unknown task type '{task_type}'", file=sys.stderr)
        sys.exit(1)

    # 4. Assemble and run the crew
    internal_affairs_crew = Crew(
        agents=[policy_enforcer_agent, metacognition_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=2
    )
    
    result = internal_affairs_crew.kickoff()
    
    # 5. Print the final result to stdout
    print(f"\n--- Internal Affairs Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
