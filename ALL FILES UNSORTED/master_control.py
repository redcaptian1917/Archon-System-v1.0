#!/usr/bin/env python3

import sys
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama

# Import the tools we just defined
from fapc_tools import find_tasks_tool, update_task_tool, create_task_tool

# --- 1. Setup the LLM ---
# This connects CrewAI to your local Ollama server.
print("[INFO] Connecting to local Ollama LLM (llama3:8b)...")
try:
    ollama_llm = Ollama(
        model="llama3:8b",          # Use the model you have
        base_url="http://localhost:11434" # Default Ollama URL
    )
    ollama_llm.invoke("Test connection")
    print("[INFO] Ollama connection successful.")
except Exception as e:
    print(f"[FATAL] Could not connect to Ollama. Is it running?", file=sys.stderr)
    print(f"       Error: {e}", file=sys.stderr)
    sys.exit(1)

# --- 2. Define Your Agent ---
# This is the "brain" of your operation.
print("[INFO] Defining FAPC Master Control Agent...")
project_manager_agent = Agent(
    role="FAPC Master Project Manager",
    goal=(
        "Efficiently manage all projects by processing high-level commands. "
        "You must use the provided tools to find, update, and create tasks."
    ),
    backstory=(
        "You are 'FAPC-1', an expert AI project manager. You are methodical, "
        "precise, and you *always* think step-by-step. You process a user's "
        "command, decide which tool to use, analyze the tool's output, "
        "and then decide the next step. You continue this loop until the "
        "user's entire command is fulfilled. You must provide a final, "
        "concise summary of all actions taken."
    ),
    tools=[find_tasks_tool, update_task_tool, create_task_tool],
    llm=ollama_llm,  # Use your local LLM
    verbose=True,    # Set to True to see the agent's "thoughts"
    allow_delegation=False
)

# --- 3. Define the Task ---
def main():
    # Get the user's high-level command from the command line
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} \"<your high-level command>\"", file=sys.stderr)
        sys.exit(1)
        
    user_command = " ".join(sys.argv[1:])
    print(f"--- Master Control Initialized ---")
    print(f"[COMMAND] \"{user_command}\"")

    # Create the task for the agent
    master_task = Task(
        description=(
            f"Process and fully execute this user command: '{user_command}'.\n"
            "1. First, you must understand the user's *intent*. "
            "2. If they want to find tasks, use the 'Find Tasks Tool'. "
            "3. If they want to change tasks, you must *first* use the "
            "'Find Tasks Tool' to get the task ID, and *then* use the "
            "'Update Task Tool' with that ID. "
            "4. If they want to create a task, use the 'Create Task Tool'. "
            "5. Provide a final summary of what you did."
        ),
        expected_output=(
            "A final, concise summary of all actions taken to fulfill the "
            "user's command, including any task IDs found or updated."
        ),
        agent=project_manager_agent
    )

    # --- 4. Create and Kickoff the Crew ---
    print("[INFO] Assembling Crew and kicking off task...")
    
    # Create the Crew
    fapc_crew = Crew(
        agents=[project_manager_agent],
        tasks=[master_task],
        process=Process.sequential,
        verbose=2 # Set to 2 for detailed step-by-step logging
    )
    
    # Run the mission
    result = fapc_crew.kickoff()
    
    print("\n--- FAPC Mission Complete ---")
    print("\n[FINAL RESULT]:")
    print(result)
    print("-------------------------------")

if __name__ == "__main__":
    main()