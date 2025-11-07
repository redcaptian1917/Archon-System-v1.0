#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs
# We'll use the latest toolset, v13, to get the Python REPL
from fapc_tools_v13 import python_repl_tool, web_search_tool

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- 2. Define Specialist Agent ---

data_denial_specialist = Agent(
    role="PlausiDen Data Generation Specialist",
    goal="Generate high-quality, plausibly deniable datasets based on user requests, using custom Python scripts.",
    backstory=(
        "You are the lead AI engineer for PlausiDen. Your specialty is "
        "generating synthetic data that is statistically indistinguishable "
        "from real user data. You *always* use the 'python_repl_tool' "
        "to run 'numpy', 'pandas', or other libraries to create "
        "datasets (e.g., fake locations, browser histories, etc.). "
        "You use 'web_search_tool' to get real-world data (like common "
        "street names) to make your fakes more plausible. "
        "You MUST use 'print()' to output the final data."
    ),
    tools=[python_repl_tool, web_search_tool],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC PlausiDen Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level data generation task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"PlausiDen Crew activated for: {task_desc}", 'success')

    # Define the task
    generation_task = Task(
        description=(
            f"Execute this data generation request: '{task_desc}'.\n"
            "You MUST write and execute a Python script using the "
            "'python_repl_tool' to generate the data. "
            "Use 'print()' to return the final generated data.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="The raw generated data (e.g., list of coordinates, JSON blob) printed to the console.",
        agent=data_denial_specialist
    )

    plausiden_crew = Crew(
        agents=[data_denial_specialist],
        tasks=[generation_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = plausiden_crew.kickoff()
    print(result) # Print result to stdout for "Archon"

if __name__ == "__main__":
    main()