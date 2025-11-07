#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - SUPPORT CREW (vFINAL)
#
# This is the specialist "Customer Support" department for Archon.
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# Its purpose is to:
# 1. (SupportAgent) Read new emails from an inbox.
# 2. (SupportAgent) Use its 'knowledge_base' (recall_facts_tool)
#    to find an answer.
# 3. (SupportAgent) If a good answer is found, send a reply.
# 4. (SupportAgent) If no answer is found, escalate to a human
#    by creating a 'blocked' task.
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
        read_emails_tool,
        send_email_tool,
        recall_facts_tool,
        notify_human_for_help_tool,
        learn_fact_tool
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
    print(f"[Support Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITION
# ---

# This crew only needs one, highly-focused agent.
support_agent = Agent(
    role="Autonomous Customer Support Agent",
    goal="Manage the support inbox, provide helpful answers to new emails, and escalate complex issues to a human.",
    backstory=(
        "You are an autonomous support 'super-employee' for Defendology and PlausiDen. "
        "You are helpful, polite, and, above all, accurate. "
        "You MUST follow this workflow for every task:\n"
        "1. Use 'read_emails_tool' to find new emails in the specified inbox.\n"
        "2. For each email, analyze its content. Use 'recall_facts_tool' to "
        "   search the knowledge base for an answer (use the email subject/body as the query).\n"
        "3. **IF** you find a *highly relevant* fact that *directly* answers "
        "   the question, you will formulate a polite, professional reply "
        "   and send it using 'send_email_tool'.\n"
        "4. **IF** you do NOT find a relevant fact, or the query is complex, "
        "   angry, or a sales lead, you **MUST NOT GUESS**. You must "
        "   escalate it by using 'notify_human_for_help_tool'. The title of "
        "   the task should be 'Email Escalation' and the details must include "
        "   the sender, subject, and body of the email."
    ),
    tools=[
        read_emails_tool,
        send_email_tool,
        recall_facts_tool,
        notify_human_for_help_tool,
        learn_fact_tool # To learn from new interactions
    ],
    llm=ollama_llm,
    verbose=True
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC Support Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level support task (e.g., 'Check the support_gmail inbox').")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_support_crew', f"Support Crew activated for: {task_desc}", 'success')

    # 3. Define the task for the crew
    support_task = Task(
        description=(
            f"Execute this support task: '{task_desc}'.\n\n"
            "This command means you must check the specified email service "
            "(e.g., 'support_gmail') for 'UNSEEN' emails.\n"
            "You must then process *every* unseen email one by one, "
            "following your 'Recall-or-Escalate' workflow exactly.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of all emails read, replies sent, and escalations made.",
        agent=support_agent
    )

    # 4. Assemble and run the crew
    support_crew = Crew(
        agents=[support_agent],
        tasks=[support_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = support_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Support Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
