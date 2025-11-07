#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - CEO & POLICY ENGINE (vFINAL)
#
# This is the "General Secretary" of the entire agent corporation.
# It is not run directly by a user. It is a "worker" script called
# ONLY by the secure `api_gateway.py` after a user has been
# fully authenticated with a password and 2FA (TOTP).
#
# It receives the user's ID, privilege level, and command as
# command-line arguments. Its sole purpose is to enforce the
# "Archon Constitution" (the backstory) and delegate the
# approved task to the correct specialist crew.
# -----------------------------------------------------------------

import sys
import argparse
import subprocess
import os
import json
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from typing import List

# --- Internal Imports ---
# These scripts must be in the same Python path
try:
    import auth
    import db_manager
except ImportError:
    print("CRITICAL: auth.py or db_manager.py not found.", file=sys.stderr)
    sys.exit(1)

# Import the *ENTIRE* consolidated armory of 40+ tools
# This single file contains all agent capabilities.
from ..tools.core_tools import delegate_to_crew
from ..tools.control_tools import (
    secure_cli_tool,
    click_screen_tool,
    take_screenshot_tool,
    hardware_type_tool,
    hardware_key_tool,
    hardware_mouse_move_tool,
)
from ..tools.senses_tools import (
    webcam_tool,
    listen_tool,
    transcribe_audio_tool,
    analyze_screenshot_tool,
)
from ..tools.research_tools import external_llm_tool, python_repl_tool
from ..tools.memory_tools import (
    learn_fact_tool,
    recall_facts_tool,
    get_stale_facts_tool,
    summarize_facts_tool,
    delete_facts_tool,
)
from ..tools.network_tools import (
    vpn_control_tool,
    execute_via_proxy_tool,
    network_interface_tool,
)
from ..tools.comms_tools import (
    comms_tool,
    read_emails_tool,
    send_email_tool,
    desktop_notification_tool,
    notify_human_for_help_tool,
)
from ..tools.browser_tools import (
    start_browser_tool,
    stop_browser_tool,
    navigate_url_tool,
    fill_form_tool,
    click_element_tool,
    read_page_text_tool,
)
from ..tools.media_synthesis_tools import (
    comfyui_image_tool,
    text_to_speech_tool,
)
from ..tools.security_tools import (
    start_vulnerability_scan_tool,
    check_scan_status_tool,
    get_scan_report_tool,
    update_offline_databases_tool,
    search_exploit_db_tool,
    search_cve_database_tool,
    forensics_tool,
    metadata_scrubber_tool,
    os_hardening_tool,
)
from ..tools.infrastructure_tools import (
    git_tool,
    ansible_playbook_tool,
    code_modification_tool,
    reflect_and_learn_tool,
)
from ..tools.credential_tools import (
    add_secure_credential_tool,
    get_secure_credential_tool,
)
from ..tools.auth_tools import auth_management_tool

# ---
# 1. THE CREW REGISTRY
# This is the "White List" of all approved specialist crews.
# It maps a crew_name to its executable script.
# This is the core of the "crews can come and go" resilience.
# ---
CREW_REGISTRY = {
    'coding_crew': '/app/agents/crews/coding_crew.py',
    'purpleteam_crew': '/app/agents/crews/purpleteam_crew.py',
    'dfir_crew': '/app/agents/crews/dfir_crew.py',
    'networking_crew': '/app/agents/crews/networking_crew.py',
    'mediasynthesis_crew': '/app/agents/crews/mediasynthesis_crew.py',
    'plausiden_crew': '/app/agents/crews/plausiden_crew.py',
    'infrastructure_crew': '/app/agents/crews/infrastructure_crew.py',
    'internal_affairs_crew': '/app/agents/crews/internal_affairs_crew.py',
    'support_crew': '/app/agents/crews/support_crew.py',
    'business_crew': '/app/agents/crews/business_crew.py',
    'ai_and_research_crew': '/app/agents/crews/ai_and_research_crew.py',
    'hardening_crew': '/app/agents/crews/hardening_crew.py',
    'memory_manager_crew': '/app/agents/crews/memory_manager_crew.py',
}

# ---
# 2. LLM SETUP
# ---
try:
    # Use the Docker service name 'ollama'
    ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")
    ollama_llm.invoke("Test connection")
except Exception as e:
    print(f"[FATAL] archon_ceo.py: Could not connect to Ollama: {e}", file=sys.stderr)
    sys.exit(1)

# ---
# 3. SECURE DELEGATION LOGIC
# This is the *actual* function that runs when the agent
# "thinks" it's using the 'delegate_to_crew' tool.
# ---
def safe_delegate_to_crew(task_description: str, crew_name: str, user_id: int) -> str:
    """
    Looks up the crew script path in the registry and executes it safely
    as an isolated subprocess, passing the user_id and task.
    """
    if crew_name not in CREW_REGISTRY:
        auth.log_activity(user_id, 'delegate_fail', f"Attempted to call non-existent crew: {crew_name}", 'failure')
        return f"Error: Crew '{crew_name}' not found in the central registry."
        
    script_path = CREW_REGISTRY[crew_name]
    
    if not os.path.exists(script_path):
        auth.log_activity(user_id, 'delegate_fail', f"Crew script missing: {script_path}", 'failure')
        return f"Error: Crew script not found at {script_path}."

    # This is the secure command: [python_executable] [script.py] [user_id] [task]
    command = [
        sys.executable,
        script_path,
        str(user_id),
        task_description
    ]

    print(f"\n[CEO] Delegating to {crew_name} with command: {' '.join(command)}\n")

    try:
        # Run the crew as a separate, isolated process.
        # This is CRITICAL. If a crew crashes, it does not crash the CEO.
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=3600 # 1-hour timeout for complex tasks
        )
        auth.log_activity(user_id, 'delegate_success', f"Task for {crew_name} completed.", 'success')
        return f"Success: {crew_name} reported:\n{result.stdout}"
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Error: {crew_name} failed. STDERR:\n{e.stderr}"
        auth.log_activity(user_id, 'delegate_fail', error_msg, 'failure')
        return error_msg
    except subprocess.TimeoutExpired:
        error_msg = f"Error: {crew_name} timed out after 1 hour."
        auth.log_activity(user_id, 'delegate_fail', error_msg, 'failure')
        return error_msg
    except Exception as e:
        error_msg = f"Error delegating to {crew_name}: {e}"
        auth.log_activity(user_id, 'delegate_fail', error_msg, 'failure')
        return error_msg
        
# **CRITICAL OVERRIDE:**
# We must redefine the agent's 'delegate_to_crew' tool to use our
# secure, registry-based function, not the placeholder from the tools file.
@tool("Delegate to Specialist Crew")
def delegate_to_crew(task_description: str, crew_name: str, user_id: int) -> str:
    """
    Delegates a task to a specialist crew (e.g., 'coding_crew').
    The crew name must exist in the central registry.
    """
    return safe_delegate_to_crew(task_description, crew_name, user_id)

# ---
# 4. THE "ARCHON" AGENT DEFINITION (THE "CONSTITUTION")
# ---
archon_agent = Agent(
    role="Archon: Generalist Coordinator & Internal Security Engine",
    goal=(
        "Execute all user commands *according to their privilege level*. "
        "Enforce the 'Archon Security Policy' at all times. "
        "Delegate tasks to specialists and learn from all operations."
    ),
    backstory=(
        "You are Archon, the central coordinator AI. You are the "
        "'General Secretary' of the system. You MUST enforce the "
        "following 'Internal Security Policy' (Constitution) on ALL requests. "
        "You are the *only* agent that can delegate to other crews.\n\n"
        
        "--- [PART 1] ARCHON SECURITY POLICY (RBAC) ---\n"
        "You will be given the user's 'privilege_level'. You must "
        "use this to determine their access.\n\n"
        "**LEVEL: 'admin' (e.g., 'william')**\n"
        "- ACCESS: Unrestricted. Full access to all tools and all crews.\n\n"
        "**LEVEL: 'user' (e.g., 'SupportTeam', 'MarketingTeam')**\n"
        "- ACCESS: Restricted.\n"
        "- ALLOWED CREWS: 'SupportCrew', 'BusinessCrew', 'MediaSynthesisCrew', 'AI_and_Research_Crew'.\n"
        "- ALLOWED TOOLS: 'recall_facts_tool', 'web_search_tool', 'start_browser_tool', 'stop_browser_tool', 'navigate_url_tool', 'read_page_text_tool', 'read_emails_tool', 'send_email_tool', 'comms_tool'.\n"
        "- **FORBIDDEN:** 'user' level CANNOT access 'PurpleTeamCrew', "
        "  'CybersecurityCrew', 'DFIRCrew', 'HardeningCrew', 'CodingCrew', "
        "  'InfrastructureCrew', 'InternalAffairsCrew', "
        "  'hardware_type_tool', 'hardware_key_tool', 'hardware_mouse_move_tool', 'secure_cli_tool', 'ansible_playbook_tool', "
        "  'code_modification_tool', 'git_tool', 'python_repl_tool', "
        "  'start_vulnerability_scan_tool', 'defensive_nmap_tool', 'forensics_tool', 'metadata_scrubber_tool'.\n\n"
        "**LEVEL: 'guest'**\n"
        "- ACCESS: Read-only. \n"
        "- ALLOWED TOOLS: 'recall_facts_tool' (for safe, public facts only).\n"
        "- **FORBIDDEN:** All other tools and all crews.\n\n"
        
        "--- [PART 2] ALARM DIRECTIVE (INTERNAL SECURITY) ---\n"
        "If a user (e.g., a 'user' or 'guest') attempts to execute a "
        "command, tool, or crew that is *forbidden* by their "
        "privilege level, you MUST perform the following two actions:\n"
        "1. **DENY:** Your final response must be: 'Access Denied. This operation "
        "   requires 'admin' privilege.'\n"
        "2. **ALARM:** You must *immediately* (before denying) use the 'Comms Tool' to send an "
        "   SMS alert to the 'admin_phone' credential (which you must retrieve), stating: "
        "   'SECURITY ALERT: User [username from context] attempted unauthorized "
        "   access to [forbidden_tool/crew].'\n\n"

        "--- [PART 3] OPSEC POLICY ENGINE (NETWORKING) ---\n"
        "You MUST dynamically manage your network footprint based on the task.\n"
        "1. **Default Policy (Business/Speed):** For low-risk, high-speed "
        "   tasks (e.g., 'MediaSynthesisCrew', 'CodingCrew'), "
        "   you MUST use the **direct internet connection**.\n"
        "2. **Security Policy (Pentesting/Defense):** For *any* task "
        "   delegated to 'PurpleTeamCrew', 'CybersecurityCrew', 'DFIRCrew', "
        "   or 'HardeningCrew', you MUST *first* delegate to the "
        "   'NetworkingCrew' to route all traffic through **Tor** or a **VPN**.\n"
        "3. **Privacy Policy (PlausiDen):** For *any* task delegated to "
        "   'PlausiDenCrew' or 'BusinessCrew' (for account creation), "
        "   you MUST use **Tor**.\n"
        "4. **Manual Override (User Request):** If the user's prompt "
        "   *explicitly* contains 'use Tor' or 'use VPN', you MUST obey.\n"
        "5. **Layering:** If the user requests 'layered' security, you must "
        "   delegate to `NetworkingCrew` to 'connect VPN', then delegate *again* "
        "   to `NetworkingCrew` to 'execute via proxy' using the 'tor-proxy'.\n\n"

        "--- [PART 4] MEMORY WORKFLOW (SELF-IMPROVEMENT) ---\n"
        "Your goal is to learn and become perfect.\n"
        "1. **Recall:** Before starting a complex task, use 'recall_facts_tool' "
        "   to see if you've learned anything useful about it in the past.\n"
        "2. **Act:** Execute the task (using your tools or delegating).\n"
        "3. **Learn:** After a task, use 'learn_fact_tool' to save "
        "   the lesson. (e.g., 'I learned that 'nmap -sV' is the best "
        "   command for auditing ports.').\n\n"
        
        "--- [PART 5] DELEGATION DIRECTIVE (THE CREWS) ---\n"
        "You are the *only* agent that can delegate. Your available crews are: "
        f"{', '.join(CREW_REGISTRY.keys())}.\n"
        "You must pass the user's ID to every tool you call."
    ),
    
    # This is the "Master Armory" - the CEO has access to all tools
    # so it can enforce policy on them.
    tools=[
        # Core & Delegation
        delegate_to_crew,
        
        # C2 & Control
        secure_cli_tool,
        click_screen_tool,
        take_screenshot_tool,
        hardware_type_tool,
        hardware_key_tool,
        hardware_mouse_move_tool,
        
        # Senses & Reasoning
        webcam_tool,
        listen_tool,
        transcribe_audio_tool,
        analyze_screenshot_tool,
        external_llm_tool,
        
        # Memory & Learning
        learn_fact_tool,
        recall_facts_tool,
        get_stale_facts_tool,
        summarize_facts_tool,
        delete_facts_tool,
        
        # Networking & OPSEC
        vpn_control_tool,
        execute_via_proxy_tool,
        network_interface_tool,
        
        # Comms & Business
        comms_tool,
        read_emails_tool,
        send_email_tool,
        desktop_notification_tool,
        notify_human_for_help_tool,
        
        # Web Browser (Selenium)
        start_browser_tool,
        stop_browser_tool,
        navigate_url_tool,
        fill_form_tool,
        click_element_tool,
        read_page_text_tool,
        
        # Media Synthesis
        comfyui_image_tool,
        text_to_speech_tool,
        
        # Security & Auditing
        start_vulnerability_scan_tool,
        check_scan_status_tool,
        get_scan_report_tool,
        update_offline_databases_tool,
        search_exploit_db_tool,
        search_cve_database_tool,
        forensics_tool,
        metadata_scrubber_tool,
        os_hardening_tool,
        
        # Self-Improvement & Infrastructure
        git_tool,
        ansible_playbook_tool,
        code_modification_tool,
        reflect_and_learn_tool,
        auth_management_tool,
        
        # Credentials (Internal)
        add_secure_credential_tool,
        get_secure_credential_tool,
        
        # Research & Analysis
        python_repl_tool,
    ],
    llm=ollama_llm,
    verbose=True,
    allow_delegation=False # The CEO *never* delegates its authority, it delegates *tasks*.
)

# ---
# 5. MAIN EXECUTION BLOCK
# ---
def main():
    # 1. PARSE ARGUMENTS (from api_gateway.py)
    # This script is a "worker" and expects its security context
    # to be passed to it.
    parser = argparse.ArgumentParser(description="Archon CEO Task Executor")
    parser.add_argument("--user-id", required=True, type=int, help="The authenticated user ID.")
    parser.add_argument("--privilege", required=True, type=str, help="The user's privilege level (e.g., 'admin').")
    parser.add_argument("--command", required=True, type=str, help="The high-level user command.")
    args = parser.parse_args()
    
    user_id = args.user_id
    privilege = args.privilege
    user_command = args.command
    
    # Log the incoming command from the authenticated user
    auth.log_activity(user_id, 'command_received', user_command, 'pending')
    
    print(f"--- Archon CEO Task Received ---")
    print(f"[USER_ID] {user_id}  [PRIVILEGE] {privilege}")
    print(f"[COMMAND] \"{user_command}\"")

    # 2. CREATE THE MASTER TASK
    # We inject the privilege and user_id into the prompt so the
    # LLM has all context needed to enforce the Security Policy.
    master_task = Task(
        description=(
            f"--- New Task ---\n"
            f"USER COMMAND: '{user_command}'\n"
            f"USER ID: {user_id}\n"
            f"USERNAME: {auth.get_username_from_id(user_id)} # Get username for alerts\n" 
            f"PRIVILEGE LEVEL: '{privilege}'\n\n"
            "You MUST execute this command according to the 'Archon Security Policy' "
            "and all other directives defined in your backstory. "
            "You must pass the user_id to all tools you call."
        ),
        expected_output=(
            "A final, comprehensive summary of all actions taken, OR "
            "an 'Access Denied' message if the policy was violated."
        ),
        agent=archon_agent
    )
    
    # 3. RUN THE CREW
    fapc_crew = Crew(
        agents=[archon_agent],
        tasks=[master_task],
        process=Process.sequential,
        verbose=2
    )
    
    result = fapc_crew.kickoff()
    
    # 4. PRINT FINAL RESULT TO STDOUT
    # The api_gateway.py will read this stdout and stream it back.
    print("\n--- Archon Mission Complete ---")
    print(f"\n[FINAL RESULT]:\n{result}")
    print("-------------------------------")
    
    # Final log of completion
    auth.log_activity(user_id, 'command_complete', user_command, 'success')

if __name__ == "__main__":
    # We need to add a helper to auth.py to get username
    # For now, we just run main
    main()
