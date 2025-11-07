#!/usr/bin/env python3

import json
import auth
from crewai_tools import tool
import os
import git # New import for GitTool

# --- Import all v19 tools ---
from fapc_tools_v19 import (
    # ... (all your v19 tools) ...
    search_exploit_db_tool, search_cve_database_tool, forensics_tool
)
_ = (search_exploit_db_tool, search_cve_database_tool, forensics_tool) # etc.
# ---

# --- Import secure_cli_tool ---
from fapc_tools_v19 import secure_cli_tool

# --- NEW TOOL 1: Metadata Scrubber Tool ---
@tool("Metadata Scrubber Tool")
def metadata_scrubber_tool(file_or_dir_path: str, user_id: int) -> str:
    """
    Removes all metadata from a specified file or all files in a directory.
    - file_or_dir_path: The absolute path to the file or directory (e.g., '/app/outputs/logo.png').
    - user_id: The user_id for logging.
    Returns a log of actions.
    """
    print(f"\n[Tool Call: metadata_scrubber_tool] PATH: {file_or_dir_path}")
    
    # mat2 scrubs files and places them in a new dir, 
    # we'll move them back to overwrite the originals for simplicity.
    cmd = f"mat2 {file_or_dir_path}"
    
    result = secure_cli_tool(cmd, user_id)
    
    if "STDERR:" in result:
        auth.log_activity(user_id, 'scrub_metadata_fail', file_or_dir_path, result)
        return f"Error scrubbing metadata: {result}"
    
    auth.log_activity(user_id, 'scrub_metadata_success', file_or_dir_path, 'success')
    return f"Metadata scrubbed successfully for: {file_or_dir_path}"

# --- NEW TOOL 2: OS Hardening Tool ---
@tool("OS Hardening Tool")
def os_hardening_tool(profile: str, user_id: int) -> str:
    """
    Applies a pre-defined OS hardening profile.
    - profile: The name of the profile (e.g., 'network_privacy', 'kernel_lockdown').
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: os_hardening_tool] PROFILE: {profile}")
    
    cmd = ""
    if profile == "network_privacy":
        # Disables pings, hardens TCP/IP stack
        cmd = "sysctl -w net.ipv4.icmp_echo_ignore_all=1 && sysctl -w net.ipv4.tcp_syncookies=1"
    elif profile == "kernel_lockdown":
        # Restricts kernel dmesg to admin
        cmd = "sysctl -w kernel.dmesg_restrict=1"
    else:
        return "Error: Unknown hardening profile."

    result = secure_cli_tool(cmd, user_id)
    auth.log_activity(user_id, 'os_hardening', profile, 'success')
    return f"Profile '{profile}' applied: {result}"

# --- NEW TOOL 3: Git Tool (for Self-Improvement) ---
@tool("Git Repository Tool")
def git_tool(repo_path: str, action: str, branch: str = 'main', user_id: int = None) -> str:
    """
    Performs Git actions on a local repository.
    - repo_path: The local path to the git repo (e.g., '/app').
    - action: The git command to perform ('pull', 'status').
    - branch: (Optional) The branch to act on (default 'main').
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: git_tool] REPO: {repo_path} ACTION: {action}")
    try:
        repo = git.Repo(repo_path)
        
        if action == "pull":
            origin = repo.remotes.origin
            pull_result = origin.pull(branch)
            result_str = f"Pull successful. Flags: {pull_result[0].flags}"
            
        elif action == "status":
            result_str = repo.git.status()
            
        else:
            return "Error: Unsupported Git action."
            
        auth.log_activity(user_id, 'git_tool', f"{action} on {repo_path}", 'success')
        return result_str
        
    except Exception as e:
        auth.log_activity(user_id, 'git_tool_fail', str(e), 'failure')
        return f"Error with Git operation: {e}"