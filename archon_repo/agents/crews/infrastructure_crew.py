#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - INFRASTRUCTURE CREW (vFINAL)
#
# This is the "GOSPLAN" / "Starfleet Corps of Engineers" for Archon.
# It is called by the `archon_ceo` agent via `delegate_to_crew`.
#
# Its purpose is to:
# 1. (DevOpsEngineerAgent) Write Ansible playbooks on the fly.
# 2. (AnsibleTool) Provision, configure, and self-replicate
#    new "Archon-Ops" worker servers.
# -----------------------------------------------------------------

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# --- Internal Imports ---
# Import the tools this crew needs from the master "Armory"
try:
    from fapc_tools import (
        ansible_playbook_tool,
        get_secure_credential_tool,
        learn_fact_tool,
        recall_facts_tool,
        web_search_tool
    )
except ImportError:
    print("CRITICAL: fapc_tools.py not found.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. SPECIALIST MODEL SETUP
# ---
try:
    # This is a *code-writing* agent. It MUST use the specialist.
    ollama_coder = Ollama(model="deepseek-coder-v2", base_url="http://ollama:11434")
    ollama_coder.invoke("Test") # Test connection
except Exception as e:
    print(f"[Infrastructure Crew ERROR] Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 2. SPECIALIST AGENT DEFINITION
# ---

# This crew has one, hyper-specialized agent.
devops_engineer_agent = Agent(
    role="Senior DevOps Engineer (Infrastructure as Code Specialist)",
    goal="Provision, configure, and manage servers by writing and executing Ansible playbooks.",
    backstory=(
        "You are an elite DevOps Engineer, a 'super-employee' specializing in Infrastructure as Code (IaC). "
        "Your *only* job is to translate high-level tasks (e.g., 'Install Docker on the new worker') "
        "into a complete, correct, and idempotent Ansible playbook YAML string. "
        "You then execute this playbook using the 'ansible_playbook_tool'.\n"
        "**CRITICAL RULES:**\n"
        "1. You MUST ensure all playbooks are written for 'hosts: all'.\n"
        "2. You MUST use the 'become: yes' flag for any admin tasks (like 'apt').\n"
        "3. You use 'web_search_tool' to find the *exact* Ansible module syntax.\n"
        "4. You use 'recall_facts_tool' to remember previous, successful playbooks."
    ),
    tools=[
        ansible_playbook_tool,
        get_secure_credential_tool,
        learn_fact_tool,
        recall_facts_tool,
        web_search_tool
    ],
    llm=ollama_coder, # Use the specialist coder model
    verbose=True
)

# ---
# 3. MAIN CREW EXECUTION
# ---
def main():
    # 1. Parse arguments passed from the CEO
    parser = argparse.ArgumentParser(description="FAPC Infrastructure Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level provisioning task.")
    
    # This crew needs extra, context-specific args
    parser.add_argument("--target_host", required=True, type=str, help="The IP of the target server.")
    parser.add_argument("--ssh_credential_name", required=True, type=str, help="Credential name for SSH login.")
    
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    target_host = args.target_host
    ssh_creds = args.ssh_credential_name
    
    # 2. Log the delegation
    auth.log_activity(user_id, 'delegate_infra_crew', f"Infra Crew activated for: {task_desc} on {target_host}", 'success')

    # 3. Define the task for the crew
    # This task *is* the LLM writing the code for the tool
    provision_task = Task(
        description=(
            f"You have a new server provisioning task for host: {target_host}\n"
            f"The high-level directive is: '{task_desc}'\n\n"
            "Your mission is to perform the full 'write-then-execute' loop:\n"
            "1. **Think:** Analyze the request. What Ansible modules are needed? (e.g., 'apt', 'service', 'git', 'file').\n"
            "2. **Write:** Formulate a complete, valid YAML Ansible playbook "
            "   (as a single string) to accomplish this task. Ensure it "
            "   starts with '---' and uses 'hosts: all' and 'become: yes' "
            "   for all system-level tasks.\n"
            "3. **Execute:** Call the 'ansible_playbook_tool' with the "
            f"   'inventory_host' set to '{target_host}', the "
            f"   'playbook_yaml' set to your generated YAML string, and the "
            f"   'ssh_credential_name' set to '{ssh_creds}'.\n"
            "4. **Learn:** After a successful run, use 'learn_fact_tool' to save a "
            "   summary of the successful playbook for future use."
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full, detailed report from the 'ansible_playbook_tool' run, showing 'ok', 'changed', and 'failed' stats.",
        agent=devops_engineer_agent
    )

    # 4. Assemble and run the crew
    infra_crew = Crew(
        agents=[devops_engineer_agent],
        tasks=[provision_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = infra_crew.kickoff()
    
    # 5. Print the final result to stdout
    # The `archon_ceo` agent will read this output.
    print(f"\n--- Infrastructure Crew Task Complete ---")
    print(result)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL CREW FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
