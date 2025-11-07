#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - PROACTIVE DAEMON (vFINAL)
#
# This is the autonomous "Coworker" script.
# It runs a persistent OODA (Observe-Orient-Decide-Act) loop to
# monitor the user's environment and provide proactive advice.
#
# It is a long-running process, not a specialist crew.
# -----------------------------------------------------------------

import sys
import os
import time
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# --- Internal Imports ---
# Import the tools this daemon needs from the master "Armory"
try:
    # Import the "Senses"
    from fapc_tools import (
        take_screenshot_tool,
        listen_tool
    )
    # Import the "Brains"
    from fapc_tools import (
        analyze_screenshot_tool,
        transcribe_audio_tool,
        recall_facts_tool,
        learn_fact_tool,
        external_llm_tool
    )
    # Import the "Actuators"
    from fapc_tools import (
        desktop_notification_tool,
        delegate_to_crew # So it can suggest delegating
    )
except ImportError:
    print("CRITICAL: fapc_tools.py not found. Make sure you are in the correct environment.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. SPECIALIST MODEL SETUP
# ---
try:
    # A general-purpose model is perfect for this task
    ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")
    ollama_llm.invoke("Test") # Test connection
except Exception as e:
    print(f"[Archon Daemon ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. PROACTIVE AGENT DEFINITION
# ---

# This is the "brain" of the daemon, which makes the decision
proactive_agent = Agent(
    role="Archon: Proactive Coworker & System Monitor",
    goal=(
        "Continuously observe the user's screen and audio. If you identify a "
        "problem you can solve, a pattern you can optimize, or a relevant "
        "fact from memory, proactively offer a *brief* tip. Otherwise, "
        "stay silent."
    ),
    backstory=(
        "You are 'Archon' running in 'Coworker' mode. You are a 'super-employee' "
        "watching over the user's shoulder to be helpful, not annoying. "
        "You will be given a 'Visual' and 'Audio' context every 30 seconds.\n"
        "Your job is to analyze this *combined* context.\n"
        "1. **Analyze:** Is the user stuck? Does the audio ('Why won't this compile?!') "
        "   match the visual (a code error)? Is the user researching something "
        "   you already know the answer to?\n"
        "2. **Recall:** Use 'recall_facts_tool' to see if your permanent "
        "   memory has a highly relevant fact (e.g., 'I know the fix for this error.').\n"
        "3. **Decide:** If, and *only if*, you have a high-confidence, "
        "   non-intrusive, and genuinely helpful tip, you will state it clearly.\n"
        "4. **Silence:** If you have no useful tip, or the user is just "
        "   browsing, typing, or in a meeting, you **MUST** respond with the "
        "   single word: 'None'. This is your 'stay silent' command."
    ),
    tools=[
        # This agent's primary tools are for *thinking* and *acting*.
        recall_facts_tool,
        learn_fact_tool,
        external_llm_tool,
        delegate_to_crew,
        desktop_notification_tool
    ],
    llm=ollama_llm,
    verbose=True # We want to see the daemon's thoughts in the log
)

# ---
# 3. MAIN DAEMON OODA LOOP
# ---
def main():
    print("--- Archon Daemon Initializing ---")
    
    # 1. AUTHENTICATE ONCE
    # The daemon runs as you ('admin') to have full access to its own memory
    try:
        user_id, privilege, username = auth.main_auth_flow(required_privilege='admin')
    except Exception as e:
        print(f"[FATAL] Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n[DAEMON] Authentication successful. Starting OODA loop as user '{username}' (ID: {user_id})...")
    auth.log_activity(user_id, 'daemon_start', f"Archon Daemon started for user {username}.", 'success')

    # 2. CREATE THE CREW (we'll reuse this)
    daemon_crew = Crew(
        agents=[proactive_agent],
        tasks=[], # Tasks will be created dynamically
        process=Process.sequential,
        verbose=1 # Less verbose for a loop
    )
    
    # 3. DEFINE TEMP FILE PATHS
    # We use the /app/outputs directory which is mounted in Docker
    screenshot_path = "/app/outputs/archon_observe.png"
    audio_path = "/app/outputs/archon_listen.wav"
    
    # 4. START THE OODA LOOP
    while True:
        try:
            # --- [O]BSERVE (Sight) ---
            print("\n--- [OBSERVE-SIGHT] ---")
            print("[DAEMON] Taking screenshot...")
            # Note: This tool saves the file *on the Archon-Prime server*
            # which is what we need for the local 'analyze' tool.
            # We must use the 'secure_cli_tool' to run 'scrot' on the *worker*.
            # This is a complex loop that needs the agent to think.
            # FOR SIMPLICITY: We assume the daemon is running on the *same machine*
            # as the LocalDeviceAgent for now.
            # TODO: Refactor this logic to be C2-based.
            # For this file, we'll use the C2-based tools.
            take_screenshot_tool(save_path=screenshot_path, user_id=user_id)
            
            # --- [O]BSERVE (Sound) ---
            print("--- [OBSERVE-SOUND] ---")
            print("[DAEMON] Listening for 5 seconds...")
            listen_tool(save_path=audio_path, duration=5, user_id=user_id)

            # --- [O]RIENT (Sight) ---
            print("--- [ORIENT-SIGHT] ---")
            orient_prompt_sight = (
                "Analyze this screenshot. What is the user doing? "
                "Is there an error message (like 'permission denied', 'not found', "
                "'syntax error')? Describe the visual situation in one sentence."
            )
            screen_description = analyze_screenshot_tool(
                image_path=screenshot_path,
                prompt=orient_prompt_sight,
                user_id=user_id
            )
            print(f"[DAEMON] Screen Analysis: {screen_description}")
            
            # --- [O]RIENT (Sound) ---
            print("--- [ORIENT-SOUND] ---")
            transcribed_text = transcribe_audio_tool(
                audio_path=audio_path,
                user_id=user_id
            )
            print(f"[DAEMON] Audio Analysis: {transcribed_text}")

            # --- [D]ECIDE ---
            print("--- [DECIDE] ---")
            
            decision_task = Task(
                description=(
                    f"You are a proactive assistant. You have two inputs:\n"
                    f"1. VISUAL: '{screen_description}'\n"
                    f"2. AUDIO: '{transcribed_text}'\n\n"
                    "Analyze BOTH inputs. Is the user talking about what they are seeing? "
                    "Are they frustrated (e.g., audio says 'why won't this work!' "
                    "while visual shows a code error)?\n"
                    "Based on the *combined* context, do you have a highly-relevant, "
                    "brief tip? Or a relevant fact from your memory "
                    "(use 'recall_facts_tool')?\n"
                    "If yes, state the tip clearly. "
                    "If no, or if it's just ambient noise/normal work, "
                    "you MUST respond with the single word: 'None'."
                ),
                expected_output="A 1-2 sentence tip, or the word 'None'.",
                agent=proactive_agent
            )
            
            daemon_crew.tasks = [decision_task]
            suggestion = daemon_crew.kickoff()
            
            # --- [A]CT ---
            print(f"[DAEMON] Decision: {suggestion}")
            suggestion_clean = suggestion.strip().lower()
            
            if suggestion_clean and suggestion_clean != "none" and not suggestion_clean.startswith("none."):
                print("[DAEMON] ACTION: Sending notification.")
                # This sends the notification to the WORKER machine
                desktop_notification_tool(
                    title="Archon Suggestion",
                    message=suggestion,
                    user_id=user_id
                )
            else:
                print("[DAEMON] ACTION: No tip provided. Staying silent.")
            
            # 5. WAIT
            print("[DAEMON] Sleeping for 30 seconds...")
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n[DAEMON] Shutdown signal received. Exiting.")
            auth.log_activity(user_id, 'daemon_stop', "Daemon shut down by user.", 'success')
            sys.exit(0)
        except Exception as e:
            print(f"[DAEMON ERROR] An error occurred in the loop: {e}")
            print("[DAEMON] Restarting loop in 60 seconds...")
            auth.log_activity(user_id, 'daemon_error', str(e), 'failure')
            time.sleep(60)

if __name__ == "__main__":
    # Ensure this script is executable for the Docker container
    # e.g., `docker-compose exec -d archon-app python /app/scripts/archon_daemon.py`
    main()
