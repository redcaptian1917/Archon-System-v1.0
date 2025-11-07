#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs from the new v8 file
from fapc_tools_v8 import (
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    get_secure_credential_tool, notify_human_for_help_tool,
    take_screenshot_tool
)

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://localhost:11434")

# --- 2. Define Specialist Agent ---
account_manager_agent = Agent(
    role="Autonomous Account Manager",
    goal=(
        "Create and manage online accounts (email, social media) by "
        "autonomously navigating websites, filling forms, and "
        "handling CAPTCHAs by notifying a human."
    ),
    backstory=(
        "You are an expert in web automation. Your job is to create accounts. "
        "You follow a strict workflow:\n"
        "1. Start the browser.\n"
        "2. Navigate to the signup page.\n"
        "3. Use 'get_secure_credential_tool' to retrieve info like "
        "'my_phone_number' or 'my_recovery_email' as needed.\n"
        "4. Fill forms with 'fill_form_tool' and click with 'click_element_tool'.\n"
        "5. If you see a CAPTCHA, use 'take_screenshot_tool' to save "
        "proof, then use 'notify_human_for_help_tool' to ask for help.\n"
        "6. Once the task is done, stop the browser."
    ),
    tools=[
        start_browser_tool, stop_browser_tool, navigate_url_tool,
        fill_form_tool, click_element_tool, read_page_text_tool,
        get_secure_credential_tool, notify_human_for_help_tool,
        take_screenshot_tool
    ],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Business Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level business task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"Business Crew activated for: {task_desc}", 'success')

    business_task = Task(
        description=(
            f"Execute this business task: '{task_desc}'.\n"
            "You MUST follow your workflow (start browser, navigate, fill, "
            "handle CAPTCHAs, stop browser).\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of actions taken, accounts created, or CAPTCHAs encountered.",
        agent=account_manager_agent
    )

    business_crew = Crew(
        agents=[account_manager_agent],
        tasks=[business_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = business_crew.kickoff()
    print(result) # Print result to stdout for "Archon"

if __name__ == "__main__":
    main()