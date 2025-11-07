#!/usr/bin/env python3

import sys
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama

# Import the new secure tool
from fapc_tools_v2 import secure_cli_tool

# --- 1. Setup the LLM ---
print("[INFO] Connecting to local Ollama LLM (llama3:8b)...")
try:
    ollama_llm = Ollama(
        model="llama3:8b",
        base_url="http://localhost:11434"
    )
    ollama_llm.invoke("Test connection")
    print("[INFO] Ollama connection successful.")
except Exception as e:
    print(f"[FATAL] Could not connect to Ollama. Is it running?", file=sys.stderr)
    sys.exit(1)

# --- 2. Define Your Agent ---
print("[INFO] Defining FAPC Master Control Agent...")
system_controller_agent = Agent(
    role="FAPC System Controller",
    goal=(
        "Execute the user's high-level command by translating it into "
        "one or more precise Bash/CLI commands and running them with "
        "the 'Secure CLI Tool'."
    ),
    backstory=(
        "You are 'FAPC-Prime', the central controller for a remote device. "
        "You take high-level requests from the user and decide what "
        "Bash commands are needed to accomplish the goal. You must be "
        "precise. You *only* have one tool: 'secure_cli_tool'. You must "
        "use this tool for all actions. Think step-by-step. If a "
        "command fails, analyze the error and try to fix it."
    ),
    tools=[secure_cli_tool], # This is its ONLY tool
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
    print(f"--- FAPC Crew Control Initialized ---")
    print(f"[COMMAND] \"{user_command}\"")

    master_task = Task(
        description=(
            f"Execute this high-level user command: '{user_command}'.\n"
            "1. Analyze the command. What is the user's *intent*?\n"
            "2. Formulate the *exact* Bash command needed to achieve this.\n"
            "3. Execute that command using the 'secure_cli_tool'.\n"
            "4. Analyze the output from the tool.\n"
            "5. If successful, provide the output. If it failed, "
            "provide the error and a summary."
        ),
        expected_output=(
            "The final result (stdout or stderr) from the "
            "'secure_cli_tool', along with a brief summary of "
            "whether the command succeeded."
        ),
        agent=system_controller_agent
    )

    # --- 4. Create and Kickoff the Crew ---
    print("[INFO] Assembling Crew and kicking off task...")
    
    fapc_crew = Crew(
        agents=[system_controller_agent],
        tasks=[master_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = fapc_crew.kickoff()
    
    print("\n--- FAPC Mission Complete ---")
    print("\n[FINAL RESULT]:")
    print(result)
    print("-------------------------------")

if __name__ == "__main__":
    main()