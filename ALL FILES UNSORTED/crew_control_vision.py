#!/usr/bin/env python3

import sys
import auth # 1. Import the new auth module
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from fapc_tools_v4 import (
    secure_cli_tool,
    click_screen_tool,
    take_screenshot_tool,
    analyze_screenshot_tool
)

# --- 1. Setup the LLM ---
try:
    ollama_llm = Ollama(model="llama3:8b", base_url="http://localhost:11434")
    ollama_llm.invoke("Test connection")
except Exception as e:
    print(f"[FATAL] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# --- 2. Define Your Sighted Agent ---
vision_controller_agent = Agent(
    role="FAPC Sighted Operator",
    goal=(
        "Execute complex, multi-step visual tasks on a remote GUI. "
        "Combine CLI, screenshot, vision, and clicking to achieve goals."
    ),
    backstory=(
        "You are 'FAPC-Prime', a fully autonomous RPA agent. You operate "
        "using a precise See-Think-Act loop:\n"
        "1. **ACT (CLI):** Use `secure_cli_tool` to start an app (e.g., 'firefox &').\n"
        "2. **SEE:** Use `take_screenshot_tool('screen.png')` to see the desktop.\n"
        "3. **THINK:** Use `analyze_screenshot_tool` on 'screen.png' to find "
        "what you need. Your prompt MUST ask for JSON coordinates, e.g., "
        "'Find the Firefox search bar. Respond ONLY with a JSON object: "
        "{\"x\": <x>, \"y\": <y>}'\n"
        "4. **ACT (GUI):** Parse the JSON to get the x, y values, then use "
        "`click_screen_tool(x, y)` to click that spot.\n"
        "You must follow this loop until the user's goal is complete."
    ),
    tools=[
        secure_cli_tool,
        click_screen_tool,
        take_screenshot_tool,
        analyze_screenshot_tool
    ],
    llm=ollama_llm,
    verbose=True,
    allow_delegation=False
)

# --- 3. Define the Task ---
def main():
    # 2. Add this block at the very beginning
    # This is the new "front door".
    # We require 'admin' privilege to run this powerful script.
    try:
        user_id, privilege = auth.main_auth_flow(required_privilege='admin')
    except Exception as e:
        print(f"[FATAL] Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Original main() code continues below ---

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} \"<your high-level command>\"", file=sys.stderr)
        sys.exit(1)

    user_command = " ".join(sys.argv[1:])
    print(f"--- FAPC Vision Crew Control ---")
    print(f"[COMMAND] \"{user_command}\"")

    master_task = Task(
        description=(
            f"Execute this high-level visual task: '{user_command}'.\n"
            # 3. Pass the user_id to the agent's context
            f"You MUST pass the user_id '{user_id}' to all tools "
            "that require it for logging."
        ),
        expected_output="A final summary of all actions taken and their results.",
        agent=vision_controller_agent
    )

    fapc_crew = Crew(...)
    result = fapc_crew.kickoff()
    print(f"\n[FINAL RESULT]:\n{result}")

if __name__ == "__main__":