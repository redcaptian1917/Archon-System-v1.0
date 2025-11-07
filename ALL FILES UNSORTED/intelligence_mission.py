#!/usr/bin/env python3

import sys
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama

# Import the specific tools this crew will need
from fapc_tools import scrape_website_tool, create_task_tool

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

# --- 2. Define Your Agents ---

print("[INFO] Defining Intelligence Crew Agents...")

# Agent 1: The Researcher
# This agent's only job is to use the scrape tool.
researcher_agent = Agent(
    role="PQC Vulnerability Researcher",
    goal="Scrape specified websites for new information on Post-Quantum Cryptography (PQC) vulnerabilities, attacks, or breakthroughs.",
    backstory=(
        "You are a specialized research agent. You are given a URL and your "
        "sole purpose is to execute the 'scrape_website_tool' on that URL "
        "and return its full text content for analysis. You do not analyze "
        "the content yourself."
    ),
    tools=[scrape_website_tool],
    llm=ollama_llm,
    verbose=True,
    allow_delegation=False
)

# Agent 2: The Analyst
# This agent's job is to *think* and *act* using the create_task tool.
analyst_agent = Agent(
    role="Senior Security Task Analyst",
    goal=(
        "Analyze research findings and create new, high-priority tasks in the "
        "FAPC if a credible new threat is found."
    ),
    backstory=(
        "You are a senior analyst for Defendology and the PQC-Monero project. "
        "You will be given a block of text from a researcher. Your job is to "
        "read it and decide if it contains a *new, specific, and actionable* "
        "vulnerability or threat. If it does, you MUST use the "
        "'create_task_tool' to log a new 'Critical' priority task. The new "
        "task description must be detailed and reference the threat. "
        "If the information is old, vague, or not a threat, you must "
        "state that no action is needed."
    ),
    tools=[create_task_tool],
    llm=ollama_llm,
    verbose=True,
    allow_delegation=False
)

# --- 3. Define the Mission and Tasks ---
def main():
    # Get the target URL from the command line
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <URL_to_scrape>", file=sys.stderr)
        print("Example: ./intelligence_mission.py https://nist.gov/pqc", file=sys.stderr)
        sys.exit(1)
        
    target_url = sys.argv[1]
    
    print(f"--- Intelligence Mission Initialized ---")
    print(f"[TARGET] \"{target_url}\"")

    # Task 1: Scrape the website
    task_1_research = Task(
        description=f"Scrape the website at the following URL: '{target_url}'",
        expected_output="The full text content of the webpage, truncated to 4000 characters.",
        agent=researcher_agent
    )

    # Task 2: Analyze the findings and create tasks
    task_2_analyze_and_act = Task(
        description=(
            "Analyze the text provided by the researcher (from the context). "
            "Your analysis must be rigorous. Look for keywords like 'vulnerability', "
            "'broken', 'attack', 'CVE', or new 'NIST standard' announcements. "
            "If a new, credible threat is identified, use the 'create_task_tool' "
            "to create one new task for the 'PQC-Monero' or 'Defendology' project. "
            "The task MUST be 'Critical' priority and its description must summarize "
            "the threat and include the source URL: '{target_url}'. "
            "If no threat is found, your final answer must be: "
            "'No new actionable intelligence found.'"
        ),
        expected_output=(
            "A confirmation of the new task created (including its details) "
            "OR the statement 'No new actionable intelligence found.'"
        ),
        agent=analyst_agent,
        context=[task_1_research] # This is CRITICAL. It passes the output
                                 # of Task 1 to Task 2.
    )

    # --- 4. Create and Kickoff the Crew ---
    print("[INFO] Assembling Intelligence Crew and kicking off mission...")
    
    intelligence_crew = Crew(
        agents=[researcher_agent, analyst_agent],
        tasks=[task_1_research, task_2_analyze_and_act],
        process=Process.sequential,
        verbose=2 # Full logging
    )
    
    result = intelligence_crew.kickoff()
    
    print("\n--- FAPC Intelligence Mission Complete ---")
    print("\n[FINAL RESULT]:")
    print(result)
    print("------------------------------------------")

if __name__ == "__main__":
    main()