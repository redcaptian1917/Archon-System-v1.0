#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - BUSINESS CREW (vFINAL)
#
# This is the specialist "Business & Marketing Department" for Archon.
# It is called by the `archon_ceo` agent.
#
# Its purpose is to:
# 1. Automate web tasks (BrowserTool)
# 2. Create new accounts (using secure credentials)
# 3. Handle CAPTCHAs by notifying the admin
# 4. Conduct market research
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
        start_browser_tool,
        stop_browser_tool,
        navigate_url_tool,
        fill_form_tool,
        click_element_tool,
        read_page_text_tool,
        get_secure_credential_tool,
        notify_human_for_help_tool,
        take_screenshot_tool,
        web_search_tool,
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
except Exception as e:
    print(f"[Business Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITIONS
# ---

# Agent 1: The Automation Specialist (Account Creation)
account_manager_agent = Agent(
    role="Autonomous Account Manager",
    goal=(
        "Create and manage online accounts (email, social media) by "
        "autonomously navigating websites, filling forms, and "
        "handling CAPTCHAs by notifying a human."
    ),
    backstory=(
        "You are an expert in web automation. Your job is to create accounts. "
        "You MUST follow this strict workflow:\n"
        "1. Call `start_browser_tool`.\n"
        "2. Call `Maps_url_tool` to get to the signup page.\n"
        "3. Use `get_secure_credential_tool` to retrieve info like "
        "   'my_phone_number' or 'my_recovery_email' as needed.\n"
        "4. Use `fill_form_tool` and `click_element_tool` to complete the form.\n"
        "5. If you see a CAPTCHA, you MUST: \n"
        "   a) Call `take_screenshot_tool` to save proof (e.g., 'captcha.png').\n"
        "   b) Call `notify_human_for_help_tool` to ask for help, "
        "      providing the URL and screenshot path in the details.\n"
        "6. Once the task is done or blocked, you MUST call `stop_browser_tool`."
    ),
    tools=[
        start_browser_tool,
        stop_browser_tool,
        navigate_url_tool,
        fill_form_tool,
        click_element_tool,
        get_secure_credential_tool,
        notify_human_for_help_tool,
        take_screenshot_tool
    ],
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The Market Analyst (Research & Sales)
market_analyst_agent = Agent(
    role="Market Analyst & Sales Specialist",
    goal="Conduct market research, identify sales targets, and draft compelling marketing copy.",
    backstory=(
        "You are a 'sales super-employee' for Defendology and PlausiDen. "
        "You use 'web_search_tool' to find new leads or market data. "
        "You use 'read_page_text_tool' (after navigating) to analyze competitor websites. "
        "You use 'learn_fact_tool' to save your important findings (like new sales leads) "
        "to the Archon system's permanent memory."
    ),
    tools=[
        web_search_tool,
        start_browser_tool,
        stop_browser_tool,
        navigate_url_tool,
        read_page_text_tool,
        learn_fact_tool
    ],
    llm=ollama_llm,
    verbose=True
)


# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC Business Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level business task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_business_crew', f"Business Crew activated for: {task_desc}", 'success')

    # 3. Define the task for the crew
    business_task = Task(
        description=(
            f"Execute this business task: '{task_desc}'.\n"
            "Analyze the request. Is it an 'account creation' task or a 'market research' task?\n"
            "If 'account creation', select the 'AccountManagerAgent' and follow your browser workflow.\n"
            "If 'market research', select the 'MarketAnalystAgent' and use the search/browser tools.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of actions taken, accounts created, research findings, or CAPTCHAs encountered.",
        # We do not assign a specific agent. CrewAI will analyze the task
        # and route it to the agent with the most appropriate tools and goal.
    )

    # 4. Assemble and run the crew
    business_crew = Crew(
        agents=[account_manager_agent, market_analyst_agent],
        tasks=[business_task],
        process=Process.sequential, # Auto-selects the best agent for the task
        verbose=2
    )
    
    result = business_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Business Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
