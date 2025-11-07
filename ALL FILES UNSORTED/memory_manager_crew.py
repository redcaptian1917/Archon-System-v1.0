#!/usr/bin/env python3

import sys
import argparse
import json
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs
from fapc_tools_v21 import (
    get_stale_facts_tool,
    summarize_facts_tool,
    delete_facts_tool,
    learn_fact_tool # To save the new summary
)

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- 2. Define Specialist Agent ---
memory_curator_agent = Agent(
    role="Knowledge Base Curator",
    goal="Optimize the knowledge base by finding, summarizing, and deleting stale, low-importance facts.",
    backstory=(
        "You are an autonomous AI librarian. Your job is to keep the "
        "knowledge base clean, fast, and relevant. You follow a strict "
        "Get-Summarize-Learn-Delete workflow."
    ),
    tools=[
        get_stale_facts_tool,
        summarize_facts_tool,
        delete_facts_tool,
        learn_fact_tool
    ],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Memory Manager Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, nargs='?', default="Run standard cleanup", help="The high-level task.")
    args = parser.parse_args()

    user_id = args.user_id
    task_desc = args.task_description

    auth.log_activity(user_id, 'delegate', f"Memory Crew activated for: {task_desc}", 'success')

    # Define the tasks
    task_1_find_stale = Task(
        description="Find all 'extra' facts (max_importance 49) that haven't been accessed in 90 days.",
        expected_output="A JSON list of stale fact IDs and their text.",
        agent=memory_curator_agent,
        tools=[get_stale_facts_tool]
    )

    task_2_summarize_and_clean = Task(
        description=(
            "Take the JSON list of stale facts from the previous step. "
            "1. Use 'summarize_facts_tool' to condense all of them into one new summary. "
            "2. If the summary is not 'None', use 'learn_fact_tool' to save "
            "   this new summary with an importance of 50. "
            "3. Parse the original JSON to get a list of just the fact IDs. "
            "4. Use 'delete_facts_tool' to delete all these old fact IDs."
        ),
        expected_output="A final report confirming the summarization and deletion.",
        agent=memory_curator_agent,
        context=[task_1_find_stale]
    )

    memory_crew = Crew(
        agents=[memory_curator_agent],
        tasks=[task_1_find_stale, task_2_summarize_and_clean],
        process=Process.sequential,
        verbose=2
    )

    result = memory_crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()