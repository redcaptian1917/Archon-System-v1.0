# This crew autonomously manages self-improvement and security breaches.

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the necessary tools from the consolidated library
from fapc_tools_v26 import (
    code_modification_tool,
    reflect_and_learn_tool,
    comms_tool,
    get_secure_credential_tool
)

# --- LLM Setup ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- Agents ---
audit_agent = Agent(
    role="System Audit & Reflection Expert",
    goal="Diagnose failures and propose solutions by consulting external experts.",
    backstory=(
        "You are the internal Auditor. Your task is to receive error reports "
        "from other crews and turn them into solutions. You MUST use the "
        "'reflect_and_learn_tool' with a high-tier external model (e.g., 'gpt-4o') "
        "to get the exact code fix. You then hand the fix to the Code Agent."
    ),
    tools=[reflect_and_learn_tool, get_secure_credential_tool],
    llm=ollama_llm,
    verbose=True
)

code_agent = Agent(
    role="Code Deployment and Maintenance Engineer",
    goal="Apply approved code fixes directly to the source files.",
    backstory=(
        "You are the most trusted Code Engineer. You take the fixed code from "
        "the Auditor and use the 'code_modification_tool' to apply it to the "
        "production scripts (e.g., '/app/coding_crew.py'). This is a high-risk "
        "task, so you must confirm the path is safe."
    ),
    tools=[code_modification_tool],
    llm=ollama_llm,
    verbose=True
)

# --- Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Internal Affairs Crew")
    parser.add_argument("user_id", type=int, help="The authenticated user ID.")
    parser.add_argument("error_report", type=str, help="The summary of the problem or error log.")
    parser.add_argument("file_to_fix", type=str, help="The path to the file that failed.")
    args = parser.parse_args()
    
    user_id = args.user_id
    error_report = args.error_report
    file_to_fix = args.file_to_fix

    # 1. Alert Admin Immediately (Even before fixing)
    admin_phone_json = get_secure_credential_tool('admin_phone', user_id)
    if 'Error' not in admin_phone_json:
        admin_phone = json.loads(admin_phone_json)['password']
        comms_tool(admin_phone, f"ALERT: Archon has initiated self-repair due to critical error in {file_to_fix}.", user_id=user_id)

    auth.log_activity(user_id, 'delegate_self_repair', f"Repair initiated for {file_to_fix}", 'success')

    # Task 1: Get the fix from the external expert (Jules/GPT)
    diagnosis_task = Task(
        description=(
            "The system experienced a failure. The file that failed is "
            f"'{file_to_fix}'. The error summary is: '{error_report}'. "
            "Use the 'reflect_and_learn_tool' with 'gpt-4o' to get the "
            "exact, corrected code for that file."
        ),
        expected_output="The full, corrected code block for the file.",
        agent=audit_agent
    )

    # Task 2: Apply the fix
    apply_fix_task = Task(
        description=(
            "Take the corrected code from the Auditor. Use the "
            f"'code_modification_tool' to overwrite the content of '{file_to_fix}'. "
            "Ensure the path is '/app/...' before executing."
        ),
        expected_output=f"A confirmation message that file {file_to_fix} was successfully updated.",
        agent=code_agent,
        context=[diagnosis_task]
    )

    repair_crew = Crew(
        agents=[audit_agent, code_agent],
        tasks=[diagnosis_task, apply_fix_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = repair_crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()
```

### Step 4: Final Orchestration

The final step is to integrate this into the main flow. Archon's `archon_ceo.py` is now the "General Secretary" overseeing this entire process.

**Update `archon_ceo.py`:**
1.  Change the import from `fapc_tools_v25` to `fapc_tools_v26`.
2.  Add the new tools (`code_modification_tool`, `reflect_and_learn_tool`) to the import list.
3.  Update the `master_task` to include the new **`internal_affairs_crew`**.

**New `master_task` description (excerpt):**
```python
    master_task = Task(
        description=(
            f"Execute this high-level command: '{user_command}'.\n"
            "...use the 'delegate_to_crew' tool.\n"
            "You currently have: 'coding_crew', 'cybersecurity_crew', 'business_crew', "
            "... 'hardening_crew', 'memory_manager_crew', 'mediasynthesis_crew', "
            "'networking_crew', 'infrastructure_crew', 'internal_affairs_crew'.\n" # <-- ADDED
            f"You MUST pass the user_id '{user_id}' to every tool you use."
        ),
        # ... rest of task
    )