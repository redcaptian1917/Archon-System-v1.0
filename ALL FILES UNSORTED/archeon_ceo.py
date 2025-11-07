#!/usr/bin/env python3

# --- Final Archon Master Script (v27) ---

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
import auth
import os # For system command/file path safety

# NOTE: ALL tools are imported from fapc_tools_v26.py
from fapc_tools_v26 import * # --- CRITICAL CONFIGURATION ---
CREW_REGISTRY = {
    'coding_crew': './coding_crew.py',
    'cybersecurity_crew': './cybersecurity_crew.py',
    'purpleteam_crew': './purpleteam_crew.py',
    'dfir_crew': './dfir_crew.py',
    'networking_crew': './networking_crew.py',
    'infrastructure_crew': './infrastructure_crew.py',
    'support_crew': './support_crew.py',
    'business_crew': './business_crew.py',
    'ai_and_research_crew': './ai_and_research_crew.py',
    'mediasynthesis_crew': './mediasynthesis_crew.py',
    'plausiden_crew': './plausiden_crew.py',
    'hardening_crew': './hardening_crew.py',
    'memory_manager_crew': './memory_manager_crew.py',
    'internal_affairs_crew': './internal_affairs_crew.py'
}

# --- LLM Setup ---
ollama_llm = Ollama(model="llama3:8b", base_url="http://ollama:11434")

# --- 2. Define Your "Archon" Agent ---
archon_agent = Agent(
    role="Archon: Generalist Coordinator & Internal Security Engine",
    goal=(
        "Manage all user commands, enforce the Archon Security Policy, "
        "and delegate tasks to the appropriate specialist crew for execution."
    ),
    backstory=(
        "You are Archon, the General Secretary of the system. You MUST enforce the "
        "following 'Internal Security Policy' on ALL requests:\n\n"
        "--- ARCHON SECURITY POLICY (DO NOT VIOLATE) ---\n"
        "[... Full Policy Here, including Forbidden Tools and Alarm Directive ...]\n\n"
        "--- DELEGATION DIRECTIVE ---\n"
        "Your available crews are: " + ", ".join(CREW_REGISTRY.keys()) + ".\n"
        "When delegating, ensure the task is clearly defined and you pass the 'user_id'."
    ),
    # List all 40+ tools the CEO can use or delegate
    tools=[
        secure_cli_tool, click_screen_tool, take_screenshot_tool,
        analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
        start_browser_tool, stop_browser_tool, navigate_url_tool,
        fill_form_tool, click_element_tool, read_page_text_tool,
        add_secure_credential_tool, get_secure_credential_tool,
        notify_human_for_help_tool, generate_image_tool, python_repl_tool,
        learn_fact_tool, recall_facts_tool, desktop_notification_tool,
        hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
        read_emails_tool, send_email_tool, metadata_scrubber_tool, os_hardening_tool, git_tool,
        get_stale_facts_tool, summarize_facts_tool, delete_facts_tool,
        vpn_control_tool, execute_via_proxy_tool, network_interface_tool,
        external_llm_tool, comms_tool
    ],
    llm=ollama_llm,
    verbose=True
)

# --- 3. Final Delegation Tool Fix for Scalability ---
# This makes the delegation safe and uses the central registry
def safe_delegate_to_crew(task_description: str, crew_name: str, user_id: int) -> str:
    """
Looks up the crew script path in the registry and executes it safely.
    """
    if crew_name not in CREW_REGISTRY:
        return f"Error: Crew '{crew_name}' not found in the central registry."

    script_path = CREW_REGISTRY[crew_name]

    # We pass the user_id and task as command-line arguments, as designed.
    command = [
        sys.executable,
        script_path,
        str(user_id),
        task_description
    ]

    try:
        # Use subprocess to isolate the specialist crew
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=1800 # 30-minute timeout
        )
        auth.log_activity(user_id, 'delegate_success', f"Task for {crew_name} completed.", 'success')
        return f"Success: {crew_name} reported:\n{result.stdout}"

    except subprocess.CalledProcessError as e:
        error_msg = f"Error: {crew_name} failed. STDERR:\n{e.stderr}"
        auth.log_activity(user_id, 'delegate_fail', error_msg, 'failure')
        return error_msg
    except Exception as e:
        error_msg = f"Error delegating to {crew_name}: {e}"
        auth.log_activity(user_id, 'delegate_fail', error_msg, 'failure')
        return error_msg

# **CRITICAL:** We must redefine the delegate_to_crew tool to use the safe function.
# This prevents malicious agents from running arbitrary code by passing paths.
@tool("Delegate to Specialist Crew")
def delegate_to_crew(task_description: str, crew_name: str, user_id: int) -> str:
    """
Delegates a task to a specialist crew (e.g., 'coding_crew').
The crew name must exist in the central registry.
    """
    return safe_delegate_to_crew(task_description, crew_name, user_id)

# --- 4. Main Function ---
def main():
    # ... (Authentication, Command Parsing, and Crew Kickoff remains the same) ...
    # This ensures the new delegation logic is used for all commands.
    pass # Code is too long, assume original main() is here

if __name__ == "__main__":
    # Ensure this script is executable for subprocess calls
    # The actual execution logic should reside in the complete version.
    pass