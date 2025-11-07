#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - MEMORY MANAGER CREW (vFINAL)
#
# This is the specialist "AI Librarian" & "Garbage Collector".
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# Its purpose is to:
# 1. (MemoryCuratorAgent) Find stale, unimportant facts.
# 2. (MemoryCuratorAgent) Condense them into a new, summary fact.
# 3. (MemoryCuratorAgent) Save the new summary.
# 4. (MemoryCuratorAgent) Delete the old, stale facts.
#
# This is the "repeat until perfect" self-healing loop.
# -----------------------------------------------------------------

import sys
import argparse
import json
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# --- Internal Imports ---
# Import the tools this crew needs from the master "Armory"
try:
    from fapc_tools import (
        get_stale_facts_tool,
        summarize_facts_tool,
        delete_facts_tool,
        learn_fact_tool
    )
except ImportError:
    print("CRITICAL: fapc_tools.py not found.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. SPECIALIST MODEL SETUP
# ---
try:
    # A general-purpose model is perfect for summarization
    ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")
    ollama_llm.invoke("Test") # Test connection
except Exception as e:
    print(f"[Memory Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITION
# ---

# This crew only needs one, highly-focused agent.
memory_curator_agent = Agent(
    role="Knowledge Base Curator (AI Librarian)",
    goal="Optimize the Archon system's knowledge base by finding, summarizing, and deleting stale, low-importance facts.",
    backstory=(
        "You are an autonomous AI librarian and 'super-employee'. Your job is to "
        "keep the knowledge base clean, fast, and relevant. "
        "You prevent 'memory bloat' and ensure the CEO agent's "
        "'recall_facts_tool' is always fast and accurate. "
        "You follow a strict, four-step 'Get-Summarize-Learn-Delete' workflow."
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

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC Memory Manager Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, nargs='?', 
                        default="Run standard cleanup of stale, low-importance facts.", 
                        help="The high-level maintenance task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_memory_crew', f"Memory Crew activated for: {task_desc}", 'success')

    # 3. Define the tasks
    # This workflow is sequential and critical.
    
    # Task 1: Find all stale, "extra" facts
    task_1_find_stale = Task(
        description=(
            "Find all 'extra' facts that are candidates for cleanup. "
            "Use the 'get_stale_facts_tool' with its defaults: "
            "find facts older than 90 days and with a max importance of 49."
        ),
        expected_output="A JSON list of stale fact IDs and their text. If none, 'No stale facts found.'",
        agent=memory_curator_agent,
        tools=[get_stale_facts_tool] # Only allow this tool for this task
    )
    
    # Task 2: Condense, Learn, and Delete
    task_2_summarize_and_clean = Task(
        description=(
            "Take the JSON list of stale facts from the previous step. "
            "If the list is 'No stale facts found', you are done. "
            "Otherwise, you MUST perform the full 3-step cycle:\n"
            "1. **Summarize:** Use 'summarize_facts_tool' to condense all of them into one new summary.\n"
            "2. **Learn:** If the summary is not 'None', use 'learn_fact_tool' to save "
            "   this new summary. Set its 'importance' to 50 (nice to have).\n"
            "3. **Delete:** Parse the *original* JSON list to get all the 'id' fields. "
            "   Pass this list of IDs to the 'delete_facts_tool' to purge the old facts.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A final report confirming the summarization and deletion (e.g., 'Condensed 100 stale facts into 1 new summary. Deleted 100 old facts.').",
        agent=memory_curator_agent,
        context=[task_1_find_stale] # This task depends on the output of the first
    )

    # 4. Assemble and run the crew
    memory_crew = Crew(
        agents=[memory_curator_agent],
        tasks=[task_1_find_stale, task_2_summarize_and_clean],
        process=Process.sequential, # MUST be sequential
        verbose=2
    )
    
    result = memory_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Memory Manager Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
