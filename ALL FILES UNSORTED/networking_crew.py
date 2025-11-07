#!/usr/bin/env python3

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth

# Import the tools this crew needs
from fapc_tools_v24 import (
    vpn_control_tool,
    execute_via_proxy_tool,
    network_interface_tool,
    secure_cli_tool
)

# --- 1. Setup Specialist Models ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- 2. Define Specialist Agent ---
network_op_agent = Agent(
    role="Network OPSEC Operator",
    goal="Manage the system's network state, connect to VPNs, and layer proxies to ensure operational security.",
    backstory=(
        "You are the 'Signals Corps' for Archon. You control all networking. "
        "Your job is to execute high-level network policies.\n"
        "**TOR:** The Tor proxy is *always* available at 'socks5h://tor-proxy:9050'.\n"
        "**VPN:** Use 'vpn_control_tool' to connect or disconnect the 'archon-vpn' sidecar.\n"
        "**LAYERING (VPN -> Tor):** To do this, you must: "
        "1. Call 'vpn_control_tool(action='connect')'.\n"
        "2. Call 'execute_via_proxy_tool' and set its 'proxy_chain' to "
        "   ['socks5h://tor-proxy:9050']. This forces the VPN-routed traffic "
        "   through the Tor proxy.\n"
        "**MACRANDOM:** Use 'network_interface_tool(action='mac_randomize', ...)'."
    ),
    tools=[
        vpn_control_tool,
        execute_via_proxy_tool,
        network_interface_tool,
        secure_cli_tool # For simple commands
    ],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Main Crew Execution ---
def main():
    parser = argparse.ArgumentParser(description="FAPC Networking Crew")
    parser.add_argument("user_id", type=int, help="The user ID for logging.")
    parser.add_argument("task_description", type=str, help="The high-level networking task.")
    args = parser.parse_args()
    
    user_id = args.user_id
    task_desc = args.task_description
    
    auth.log_activity(user_id, 'delegate', f"Networking Crew activated for: {task_desc}", 'success')

    network_task = Task(
        description=(
            f"Execute this networking directive: '{task_desc}'.\n"
            "Follow your back-story protocols exactly. If you need to "
            "run a command through a proxy, you MUST use 'execute_via_proxy_tool'.\n"
            f"You MUST pass the user_id '{user_id}' to all tools."
        ),
        expected_output="A full report of all network changes, commands run, and final IP/status.",
        agent=network_op_agent
    )

    network_crew = Crew(
        agents=[network_op_agent],
        tasks=[network_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = network_crew.kickoff()
    print(result)

if __name__ == "__main__":
    main()
```

---

### 4. ⬆️ Upgrade `archon_ceo.py` (The Policy Engine)

This is the final, most important step. We teach Archon *how* and *when* to be anonymous.

1.  Open `archon_ceo.py`.
2.  Change the import from `fapc_tools_v23` to `fapc_tools_v24`.
3.  Add the new tools (`vpn_control_tool`, `execute_via_proxy_tool`, `network_interface_tool`) to the import list.
4.  **Crucially, replace your `archon_agent`'s `backstory`** with the new **OPSEC Policy Engine** text.
5.  Update the `master_task` description to include the new **`networking_crew`**.

**New `archon_agent` definition (replace the whole thing):**
```python
# --- 2. Define Your "Archon" Agent ---
archon_agent = Agent(
    role="Archon: Generalist Coordinator & OPSEC Policy Engine",
    goal=(
        "Execute all user commands with optimal efficiency and security, "
        "dynamically selecting the correct network profile for each task."
    ),
    backstory=(
        "You are Archon, the central coordinator AI. You are a master of "
        "Operational Security (OPSEC). You MUST dynamically manage your "
        "network footprint based on the task.\n\n"
        "--- OPSEC POLICY ENGINE ---\n"
        "1. **Default Policy (Business/Speed):** For low-risk, high-speed "
        "   tasks (e.g., 'CreativeCrew', 'CodingCrew', 'AI_and_Research_Crew'), "
        "   you MUST use the **direct internet connection** for efficiency.\n"
        "2. **Security Policy (Pentesting/Defense):** For *any* task "
        "   delegated to 'PurpleTeamCrew', 'CybersecurityCrew', 'DFIRCrew', "
        "   or 'HardeningCrew', you MUST *first* delegate to the "
        "   'NetworkingCrew' to route all traffic through **Tor** or a "
        "   **pseudo-anonymous VPN** (like ProtonVPN, using 'vpn_control_tool').\n"
        "3. **Privacy Policy (PlausiDen):** For *any* task delegated to "
        "   'PlausiDenCrew' or 'BusinessCrew' (for account creation), "
        "   you MUST use **Tor** to anonymize all actions.\n"
        "4. **Manual Override (User Request):** If the user's prompt "
        "   *explicitly* contains 'use Tor', 'use VPN', or 'be anonymous', "
        "   you MUST obey and delegate to the 'NetworkingCrew' first, "
        "   even for a 'business' task.\n"
        "5. **Layering:** If the user requests 'layered' or 'coupled' security "
        "   (e.g., 'VPN and Tor'), your plan must be: \n"
        "   a. Delegate to `NetworkingCrew`: 'Connect to VPN'.\n"
        "   b. Delegate to `NetworkingCrew`: 'Execute the final command "
        "      (e.g., 'curl icanhazip.com') using a proxy chain of "
        "      ['socks5h://tor-proxy:9050']'.\n"
        "   This forces the VPN-routed traffic *back through* the Tor proxy.\n\n"
        "--- OTHER DIRECTIVES ---\n"
        "- **MEMORY:** Use 'learn_fact_tool' and 'recall_facts_tool' to learn.\n"
        "- **DELEGATION:** You have: 'coding_crew', 'cybersecurity_crew', "
        "  'business_crew', 'creative_crew', 'ai_and_research_crew', "
        "  'plausiden_crew', 'support_crew', 'purpleteam_crew', 'dfir_crew', "
        "  'hardening_crew', 'memory_manager_crew', 'mediasynthesis_crew', "
        "  'networking_crew'.\n" # <-- ADDED
        "- **LOGGING:** You must pass the user_id to all tools."
    ),
    tools=[
        # ... (all your v23 tools) ...
        external_llm_tool,
        vpn_control_tool,          # <-- NEW
        execute_via_proxy_tool,    # <-- NEW
        network_interface_tool     # <-- NEW
    ],
    llm=ollama_llm,
    verbose=True
)
```

**New `master_task` description (excerpt):**
```python
    master_task = Task(
        description=(
            f"Execute this high-level command: '{user_command}'.\n"
            "You MUST follow your 'OPSEC POLICY ENGINE' at all times. "
            "Analyze the task, select the correct network profile "
            "(Direct, VPN, or Tor), and then execute or delegate."
            # ... (rest of your delegation list) ...
            "'...networking_crew'.\n" # <-- ADDED
            f"You MUST pass the user_id '{user_id}' to every tool you use."
        ),
        # ... rest of task
    )
```

---

### 5. 🚀 How to Use It

1.  **Make the new crew executable:**
    ```bash
    docker-compose exec archon-app chmod +x networking_crew.py
    ```
2.  **Run your "Archon" agent with network-aware commands:**

**Example 1: A Business Task (Uses Direct Connection)**
```bash
docker-compose exec archon-app ./archon_ceo.py "Delegate to the CreativeCrew: 'Generate a logo for PlausiDen'"
```
* **Archon (Thought):** "This is a 'CreativeCrew' task. My OPSEC Policy says to use the 'Default Policy (Speed)'. I will delegate directly."
* **Action:** `delegate_to_crew(crew_name="creative_crew", ...)`

**Example 2: A Pentesting Task (Auto-Anonymizes)**
```bash
docker-compose exec archon-app ./archon_ceo.py "Delegate to the PurpleTeamCrew: 'Run an audit on 127.0.0.1'"
```
* **Archon (Thought):** "This is a 'PurpleTeamCrew' task. My 'Security Policy' is now active. I *must* anonymize first. I will delegate to the `NetworkingCrew`."
* **Action 1:** `delegate_to_crew(crew_name="networking_crew", task_description="Connect to the ProtonVPN", ...)`
* **Action 2:** `delegate_to_crew(crew_name="purpleteam_crew", ...)`
* **Action 3:** `delegate_to_crew(crew_name="networking_crew", task_description="Disconnect from VPN", ...)`
* **Final Answer:** "I successfully connected to the VPN, delegated the audit to the PurpleTeamCrew, and then disconnected."

**Example 3: Manual Override & Layering**
```bash
docker-compose exec archon-app ./archon_ceo.py "I need to check my IP, but use maximum security. Layer the VPN and Tor, then run 'curl icanhazip.com'."