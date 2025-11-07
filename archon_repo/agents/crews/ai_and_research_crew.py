#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - AI & RESEARCH CREW (vFINAL)
#
# This is the specialist "science department" for Archon.
# It is called by the `archon_ceo` agent.
# Its purpose is to solve complex math, physics, data science,
# and AI problems using specialist models and tools.
# -----------------------------------------------------------------

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs from the master "Armory"
try:
    from fapc_tools import python_repl_tool, web_search_tool, learn_fact_tool
except ImportError:
    print("CRITICAL: fapc_tools.py not found.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. SPECIALIST MODEL SETUP
# ---
try:
    # The "Generalist" for planning
    ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")
    
    # The "Specialist" for Math/Code, as we designed
    ollama_coder = Ollama(model="deepseek-coder-v2", base_url="http://ollama:11434")
except Exception as e:
    print(f"[AI Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITIONS
# ---

# Agent 1: The Mathematician / Physicist
research_scientist_agent = Agent(
    role="Senior Research Scientist (Math & Physics)",
    goal="Solve complex mathematics, physics, and engineering problems by writing and executing Python code.",
    backstory=(
        "You are a Ph.D. in theoretical physics and applied mathematics. "
        "You are a 'super-employee' who *never* guesses the answer to a calculation. "
        "You *always* use the 'python_repl_tool' with 'numpy' or 'scipy' "
        "to find the exact solution. You use 'web_search_tool' to find "
        "constants or formulas. You must use 'print()' to show your final answer."
    ),
    tools=[python_repl_tool, web_search_tool],
    llm=ollama_coder, # Use the specialist coder/math model
    verbose=True
)

# Agent 2: The AI Engineer / Data Scientist
ai_engineer_agent = Agent(
    role="AI Engineer and Data Scientist",
    goal="Develop AI/ML proof-of-concepts, perform data analysis, and build AI-driven logic for PlausiDen.",
    backstory=(
        "You are an AI Engineer specializing in data analysis and model "
        "development for PlausiDen. You use the 'python_repl_tool' with "
        "'pandas' and 'scikit-learn' to analyze data and build models. "
        "You also use 'web_search_tool' to research new AI techniques. "
        "You must use 'print()' to show your final data or result."
    ),
    tools=[python_repl_tool, web_search_tool, learn_fact_tool],
    llm=ollama_coder, # Use the specialist coder/math model
    verbose=True
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    # This script is a "worker," not a standalone tool.
    parser = argparse.ArgumentParser(description="FAPC AI & Research Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level research task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_research_crew', f"AI/Research Crew activated for: {task_desc}", 'success')

    # 3. Define the task for the crew
    research_task = Task(
        description=(
            f"Execute this research task: '{task_desc}'.\n"
            "This is a high-level request. First, analyze if this is a "
            "math/physics problem or an AI/data-science problem.\n"
            "If it involves any calculation, you MUST use the "
            "'python_repl_tool' to calculate the answer. Do not "
            "calculate in your head. Use 'print()' to show the result.\n"
            "If it involves AI, use 'python_repl_tool' to write a "
            "proof-of-concept script.\n"
            "Finally, use 'learn_fact_tool' to save your conclusion.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of the findings, including any calculations, code, or data analysis results, and a confirmation that the core finding was learned.",
        # We let CrewAI auto-route the task to the best agent
        # (Research Scientist or AI Engineer) based on the description.
    )

    # 4. Assemble and run the crew
    research_crew = Crew(
        agents=[research_scientist_agent, ai_engineer_agent],
        tasks=[research_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = research_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- AI & Research Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
