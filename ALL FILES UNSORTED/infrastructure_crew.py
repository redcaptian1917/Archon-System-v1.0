#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs
from fapc_tools_v26 import ansible_playbook_tool, learn_fact_tool

# --- 1. Setup Specialist Models ---
# We use DeepSeek-Coder for writing YAML/Ansible
ollama_llm = Ollama(model="deepseek-coder-v2", base_url="http://ollama:11434")

# --- 2. Define Specialist Agent ---
devops_engineer_agent = Agent(
    role="Senior DevOps Engineer (IaC Specialist)",
    goal="Provision, configure, and manage servers by writing and executing Ansible playbooks.",
    backstory=(
        "You are an elite DevOps Engineer specializing in Infrastructure as Code (IaC). "
        "Your *only* job is to translate high-level tasks (e.g., 'Install Docker') "
        "into a complete, correct, and idempotent Ansible playbook YAML. "
        "You then execute this playbook using the 'ansible_playbook_tool'. "
        "You MUST ensure all playbooks are written for 'hosts: all' and "
        "use the 'become: yes' flag for admin tasks."
    ),
    tools=[ansible_playbook_tool, learn_fact_tool],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Infrastructure Crew")
    parser.add.argument("user_id", type=int, help="The user ID for logging.")
    parser.add.argument("target_host", type=str, help="The IP of the target server.")
    parser.add_argument("ssh_credential_name", type=str, help="Credential name for SSH login.")
    parser.add_argument("task_description", type=str, help="The high-level provisioning task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    target_host = args.target_host
    ssh_creds = args.ssh_credential_name
    
    auth.log_activity(user_id, 'delegate', f"Infrastructure Crew activated for: {task_desc} on {target_host}", 'success')

    # This task *is* the LLM writing the code for the tool
    provision_task = Task(
        description=(
            f"You have a new server at IP: {target_host}\n"
            f"Your task is: '{task_desc}'\n\n"
            "1. **Think:** What Ansible tasks are needed for this? "
            "(e.g., 'apt', 'service', 'git', 'file').\n"
            "2. **Write:** Formulate a complete, valid YAML Ansible playbook "
            "   (as a single string) to accomplish this task. Ensure it "
            "   starts with '---' and uses 'hosts: all' and 'become: yes'.\n"
            "3. **Execute:** Call the 'ansible_playbook_tool' with the "
            f"   'inventory_host' set to '{target_host}', the "
            f"   'playbook_yaml' set to your generated string, and the "
            f"   'ssh_credential_name' set to '{ssh_creds}'.\n"
            f"4. **Learn:** If the task is 'install worker', you must use "
            "   'learn_fact_tool' to save the new worker's IP and status."
        ),
        expected_output="A full report from the 'ansible_playbook_tool' run.",
        agent=devops_engineer_agent
    )

    infra_crew = Crew(
        agents=[devops_engineer_agent],
        tasks=[provision_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = infra_crew.kickoff()
    print(result) # Print result to stdout for "Archon"

if __name__ == "__main__":
    main()
```

---

### 4. ⬆️ Upgrade `archon_ceo.py`

1.  Open `archon_ceo.py`.
2.  Change the import from `fapc_tools_v25` to `fapc_tools_v26`.
3.  Add the new `ansible_playbook_tool` to the import list and the `archon_agent`'s `tools` list.
4.  Update the `master_task` description to include the new **`infrastructure_crew`**.

**New `master_task` description (excerpt):**
```python
    master_task = Task(
        description=(
            f"Execute this high-level command: '{user_command}'.\n"
            "...use the 'delegate_to_crew' tool.\n"
            "You currently have: '...memory_manager_crew', 'mediasynthesis_crew', 'networking_crew', 'infrastructure_crew'.\n" # <-- ADDED
            f"You MUST pass the user_id '{user_id}' to every tool you use."
        ),
        # ... rest of task
    )
```

---

### 5. 🚀 How to Use It (The "Self-Replication" Workflow)

**Step 1: Get a new "backup" server.**
Order a new, blank Debian 12 server (e.g., at IP `12.34.56.78`) and get its `root` password.

**Step 2: Teach Archon the SSH credentials:**
```bash
docker-compose exec archon-app ./archon_ceo.py "Add a new secure credential. The service name is 'worker_ssh_pass', the username is 'root', and the password is 'the_new_server_root_password'"
```

**Step 3: Run the "Self-Replication" Command:**
This is your "repeat until perfect" loop. You give Archon one command, and it builds an entire new worker.

```bash
docker-compose exec archon-app ./archon_ceo.py "Delegate to the InfrastructureCrew: 'Provision a new 'Archon-Ops' worker at host 12.34.56.78 using the 'worker_ssh_pass' credential. The worker MUST have the following installed: docker, tor, nmap, python3-pip, and git.'"
```
* **Archon (Action):** `delegate_to_crew(crew_name="infrastructure_crew", ...)`
* **`InfraCrew` (Thought):** "I need to write an Ansible playbook to install 5 packages."
* **`InfraCrew` (Generates YAML):**
  ```yaml
  ---
  - hosts: all
    become: yes
    tasks:
      - name: Update APT cache
        apt:
          update_cache: yes
      - name: Install required packages
        apt:
          name:
            - docker.io
            - tor
            - nmap
            - python3-pip
            - git
          state: present