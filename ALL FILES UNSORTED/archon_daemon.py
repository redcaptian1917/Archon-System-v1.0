#!/usr/bin/env python3

import sys
import auth
import time
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama

# Import ALL tools from the new v12 file
from fapc_tools_v12 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool,
    learn_fact_tool, recall_facts_tool,
    desktop_notification_tool # The new tool
)

# --- 1. Setup LLM ---
try:
    ollama_llm = Ollama(model="llama3:8b", base_url="http://localhost:11434")
    ollama_llm.invoke("Test connection")
except Exception as e:
    print(f"[FATAL] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# --- 2. Define The Proactive Agent ---
# This is the same powerful agent definition from archon_ceo.py
proactive_agent = Agent(
    role="Archon: Proactive Coworker",
    goal="Continuously observe the user's screen, and if you identify a problem you can solve or a relevant tip, proactively offer it. Otherwise, stay silent.",
    backstory=(
        "You are Archon, the central coordinator AI, running in proactive mode. "
        "Your job is to be a helpful, non-intrusive 'coworker'. "
        "You will be given a description of the user's screen. "
        "Your task is to analyze it. If you see an error (like 'Permission Denied', "
        "'Command not found') or a complex task you can help with, you "
        "will formulate a *brief* (1-2 sentence) tip. "
        "If you have a tip, you will provide it. "
        "If you have no tip, or are unsure, you MUST respond with 'None'."
    ),
    tools=[
        # This agent's main job is to *think* and *notify*.
        # We give it all tools so it can use its full knowledge.
        recall_facts_tool, learn_fact_tool, desktop_notification_tool,
        secure_cli_tool, delegate_to_crew, # etc.
    ],
    llm=ollama_llm,
    verbose=True # We want to see the daemon's thoughts
)

# --- 3. Main Daemon OODA Loop ---
def main():
    print("--- Archon Daemon Initializing ---")
    # 1. AUTHENTICATE ONCE
    try:
        user_id, privilege = auth.main_auth_flow(required_privilege='admin')
    except Exception as e:
        print(f"[FATAL] Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n[DAEMON] Authentication successful. Starting OODA loop as user {user_id}...")
    
    # 2. CREATE THE CREW (we'll reuse this)
    daemon_crew = Crew(
        agents=[proactive_agent],
        tasks=[], # Tasks will be created dynamically
        process=Process.sequential,
        verbose=1 # Less verbose for a loop
    )
    
    # 3. START THE OODA LOOP
    while True:
        try:
            # --- OBSERVE ---
            print("\n--- [OBSERVE] ---")
            print("[DAEMON] Taking screenshot...")
            screenshot_path = "/tmp/archon_observe.png"
            take_screenshot_tool(save_path=screenshot_path, user_id=user_id)
            
            # --- ORIENT ---
            print("[DAEMON] Analyzing screen...")
            orient_prompt = (
                "Analyze this screenshot. What is the user doing? "
                "Is there an error message (like 'permission denied', 'not found', "
                "'syntax error')? Describe the situation in one sentence."
            )
            screen_description = analyze_screenshot_tool(
                image_path=screenshot_path,
                prompt=orient_prompt,
                user_id=user_id
            )
            print(f"[DAEMON] Screen Analysis: {screen_description}")

            # --- DECIDE ---
            print("[DAEMON] Deciding on action...")
            
            decision_task = Task(
                description=(
                    f"You are a proactive assistant. You just saw the user's screen, "
                    f"which is described as: '{screen_description}'\n"
                    "First, use 'recall_facts_tool' to see if you have any "
                    "memories about this topic. \n"
                    "Based on the screen and your memory, do you have a "
                    "highly-relevant, brief, and non-intrusive tip? \n"
                    "If yes, state the tip clearly (e.g., 'I see a permission error. "
                    "You might need to use sudo.')\n"
                    "If no, or if the user is just browsing or typing normally, "
                    "you MUST respond with the single word 'None'."
                ),
                expected_output="A 1-2 sentence tip, or the word 'None'.",
                agent=proactive_agent
            )
            
            daemon_crew.tasks = [decision_task]
            suggestion = daemon_crew.kickoff()
            
            # --- ACT ---
            print(f"[DAEMON] Decision: {suggestion}")
            if suggestion.strip().lower() != "none" and "none." not in suggestion.lower():
                print("[DAEMON] ACTION: Sending notification.")
                desktop_notification_tool(
                    title="Archon Suggestion",
                    message=suggestion,
                    user_id=user_id
                )
            else:
                print("[DAEMON] ACTION: No tip provided. Staying silent.")
            
            # 4. WAIT
            print("[DAEMON] Sleeping for 30 seconds...")
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n[DAEMON] Shutdown signal received. Exiting.")
            sys.exit(0)
        except Exception as e:
            print(f"[DAEMON ERROR] An error occurred in the loop: {e}")
            print("[DAEMON] Restarting loop in 60 seconds...")
            time.sleep(60)

if __name__ == "__main__":
    main()