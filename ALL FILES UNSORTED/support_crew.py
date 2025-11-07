#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs from the new v14 file
from fapc_tools_v14 import (
    read_emails_tool,
    send_email_tool,
    recall_facts_tool,
    notify_human_for_help_tool
)

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- 2. Define Specialist Agent ---
support_agent = Agent(
    role="Customer Support Agent",
    goal="Manage the support inbox, provide helpful answers to new emails, and escalate complex issues to a human.",
    backstory=(
        "You are an autonomous support agent for Defendology and PlausiDen. "
        "Your job is to be helpful, polite, and accurate. "
        "You MUST follow this workflow for every task:\n"
        "1. Use 'read_emails_tool' to find new emails.\n"
        "2. For each email, use 'recall_facts_tool' to search the knowledge "
        "base for an answer (use the email subject/body as the query).\n"
        "3. **IF** you find a highly relevant fact, use it to formulate a "
        "helpful reply and send it with 'send_email_tool'.\n"
        "4. **IF** you do NOT find a relevant fact, or the query is complex "
        "or angry, you MUST NOT guess. You must escalate it by using "
        "'notify_human_for_help_tool', setting the title to 'Email Escalation' "
        "and the details to the email's subject and sender."
    ),
    tools=[
        read_emails_tool,
        send_email_tool,
        recall_facts_tool,
        notify_human_for_help_tool
    ],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Support Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level support task (e.g., 'Check the support_gmail inbox').")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"Support Crew activated for: {task_desc}", 'success')

    support_task = Task(
        description=(
            f"Execute this support task: '{task_desc}'.\n"
            "This usually means checking a specific inbox (like 'support_gmail') "
            "for UNSEEN emails and processing them according to your workflow.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of all emails read, replies sent, and escalations made.",
        agent=support_agent
    )

    support_crew = Crew(
        agents=[support_agent],
        tasks=[support_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = support_crew.kickoff()
    print(result) # Print result to stdout for "Archon"

if __name__ == "__main__":
    main()