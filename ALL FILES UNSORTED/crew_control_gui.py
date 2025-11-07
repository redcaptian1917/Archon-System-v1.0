#!/usr/bin/env python3

import sys
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from fapc_tools_v3 import secure_cli_tool, click_screen_tool, take_screenshot_tool

# --- 1. Setup the LLM ---
try:
    ollama_llm = Ollama(model="llama3:8b", base_url="http://localhost:11434")
    ollama_llm.invoke("Test connection")
except Exception as e:
    print(f"[FATAL] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# --- 2. Define Your Agent ---
gui_controller_agent = Agent(
    role="FAPC GUI/CLI Operator",
    goal=(
        "Execute complex, multi-step user tasks by combining CLI commands, "
        "mouse clicks, and taking screenshots."
    ),
    backstory=(
        "You are 'FAPC-Prime'. You can see and act. You take high-level "
        "requests and break them down. For example, to 'open Firefox', "
        "you first use 'secure_cli_tool' to run 'firefox &'. Then you "
        "might use 'click_screen_tool' to click on a link, and "
        "'take_screenshot_tool' to verify the result."
    ),
    tools=[secure_cli_tool, click_screen_tool, take_screenshot_tool],
    llm=ollama_llm,
    verbose=True,
    allow_delegation=False
)

# --- 3. Define the Task ---
def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} \"<your high-level command>\"", file=sys.stderr)
        sys.exit(1)
        
    user_command = " ".join(sys.argv[1:])
    print(f"--- FAPC GUI Crew Control ---")
    print(f"[COMMAND] \"{user_command}\"")

    master_task = Task(
        description=(
            f"Execute this high-level user command: '{user_command}'.\n"
            "Think step-by-step. You must combine your tools. "
            "For example, to check a project's status, you might first "
            "use 'secure_cli_tool' to 'ls /path/to/project', then "
            "use 'take_screenshot_tool' to see the whole desktop, "
            "saving the image as 'debug_screenshot.png'. "
            "Provide a final summary of your actions."
        ),
        expected_output="A final summary of all actions taken and their results.",
        agent=gui_controller_agent
    )
    
    fapc_crew = Crew(
        agents=[gui_controller_agent],
        tasks=[master_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = fapc_crew.kickoff()
    print("\n--- FAPC Mission Complete ---")
    print(f"\n[FINAL RESULT]:\n{result}")

if __name__ == "__main__":
    main()