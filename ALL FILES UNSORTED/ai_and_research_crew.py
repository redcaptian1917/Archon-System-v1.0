#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs from the new v10 file
from fapc_tools_v10 import python_repl_tool, web_search_tool

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://localhost:11434")

# --- 2. Define Specialist Agents ---

# Agent 1: The Research Scientist
research_scientist_agent = Agent(
    role="Senior Research Scientist (Math & Physics)",
    goal="Solve complex mathematics, physics, and engineering problems by writing and executing Python code.",
    backstory=(
        "You are a Ph.D. in theoretical physics and applied mathematics. "
        "You solve complex problems by writing Python scripts. You *never* "
        "guess the answer to a calculation. You *always* use the "
        "'python_repl_tool' with 'numpy' or 'scipy' to find the solution. "
        "You always use 'print()' to show your work."
    ),
    tools=[python_repl_tool, web_search_tool],
    llm=ollama_llm,
    verbose=True
)

# Agent 2: The AI Engineer
ai_engineer_agent = Agent(
    role="AI Engineer and Data Scientist",
    goal="Develop AI/ML proof-of-concepts, perform data analysis, and build AI-driven logic.",
    backstory=(
        "You are an AI Engineer specializing in data analysis and model "
        "development for PlausiDen. You use the 'python_repl_tool' with "
        "'pandas' and 'scikit-learn' to analyze data and build models. "
        "You also use 'web_search_tool' to research new AI techniques."
    ),
    tools=[python_repl_tool, web_search_tool],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC AI & Research Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level research task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"AI/Research Crew activated for: {task_desc}", 'success')

    # Define the task
    research_task = Task(
        description=(
            f"Execute this research task: '{task_desc}'.\n"
            "If it involves math, physics, or data, you MUST use the "
            "'python_repl_tool' to calculate the answer. Do not "
            "calculate in your head. Use 'print()' to show the result.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of the findings, including any calculations or data analysis results.",
        # Let CrewAI auto-route to the best agent
    )

    research_crew = Crew(
        agents=[research_scientist_agent, ai_engineer_agent],
        tasks=[research_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = research_crew.kickoff()
    print(result) # Print result to stdout for "Archon"

if __name__ == "__main__":
    main()