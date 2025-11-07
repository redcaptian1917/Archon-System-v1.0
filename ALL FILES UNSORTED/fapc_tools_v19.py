#!/usr/bin/env python3

import json
import auth
from crewai_tools import tool
import os

# --- Import all v18 tools ---
from fapc_tools_v18 import (
    # ... (all your v18 tools) ...
    comms_tool
)
_ = (comms_tool,) # etc.
# ---

# --- Import secure_cli_tool ---
# This crew relies heavily on the secure_cli_tool
from fapc_tools_v18 import secure_cli_tool

# --- Database Paths ---
DB_PATH = "/app/offline_dbs"
EXPLOIT_DB_PATH = os.path.join(DB_PATH, "exploit-database")
CVE_LIST_PATH = os.path.join(DB_PATH, "cvelistV5")

# --- NEW TOOL 1: Update Offline DBs ---
@tool("Update Offline Databases Tool")
def update_offline_databases_tool(user_id: int) -> str:
    """
    Clones or updates the local Exploit-DB (for searchsploit) and
    the official CVE JSON database (cvelistV5).
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: update_offline_databases_tool]")
    os.makedirs(DB_PATH, exist_ok=True)
    
    results = {}
    
    # 1. Update Exploit-DB
    try:
        if os.path.exists(EXPLOIT_DB_PATH):
            print("[DB TOOL] Updating Exploit-DB...")
            cmd = f"cd {EXPLOIT_DB_PATH} && git pull"
        else:
            print("[DB TOOL] Cloning Exploit-DB...")
            cmd = f"git clone https://github.com/offensive-security/exploit-database.git {EXPLOIT_DB_PATH}"
        
        result = secure_cli_tool(cmd, user_id)
        results['exploit_db'] = "Update/Clone successful."
        auth.log_activity(user_id, 'db_update', 'Exploit-DB updated', 'success')
    except Exception as e:
        results['exploit_db'] = f"Update/Clone failed: {e}"

    # 2. Update CVE List (cvelistV5)
    try:
        if os.path.exists(CVE_LIST_PATH):
            print("[DB TOOL] Updating CVE List...")
            cmd = f"cd {CVE_LIST_PATH} && git pull"
        else:
            print("[DB TOOL] Cloning CVE List...")
            cmd = f"git clone https://github.com/CVEProject/cvelistV5.git {CVE_LIST_PATH}"
        
        result = secure_cli_tool(cmd, user_id)
        results['cve_list'] = "Update/Clone successful."
        auth.log_activity(user_id, 'db_update', 'CVE List updated', 'success')
    except Exception as e:
        results['cve_list'] = f"Update/Clone failed: {e}"

    return f"Database update complete: {json.dumps(results)}"

# --- NEW TOOL 2: Search Exploit-DB (SearchSploit) ---
@tool("Search Exploit-DB Tool")
def search_exploit_db_tool(query: str, user_id: int) -> str:
    """
    Uses 'searchsploit' to search the offline Exploit-DB.
    - query: The search query (e.g., 'WordPress 5.0 RCE', 'CVE-2021-44228').
    - user_id: The user_id for logging.
    Returns the search results.
    """
    print(f"\n[Tool Call: search_exploit_db_tool] QUERY: {query}")
    # Use '--no-color -j' for clean, parsable JSON output
    cmd = f"cd {EXPLOIT_DB_PATH} && ./searchsploit --no-color -j {query}"
    
    result = secure_cli_tool(cmd, user_id)
    auth.log_activity(user_id, 'search_exploit_db', query, 'success')
    
    # Check if STDOUT is empty
    if "STDOUT:\n\n" in result or "STDOUT:\n" == result:
         return "No exploits found."
         
    return result.replace("STDOUT:\n", "Found exploits:\n")

# --- NEW TOOL 3: Search CVE Database ---
@tool("Search CVE Database Tool")
def search_cve_database_tool(cve_id: str, user_id: int) -> str:
    """
    Searches the offline cvelistV5 JSON database for a specific CVE ID.
    - cve_id: The CVE ID (e.g., 'CVE-2021-44228').
    - user_id: The user_id for logging.
    Returns the CVE's JSON details.
    """
    print(f"\n[Tool Call: search_cve_database_tool] ID: {cve_id}")
    
    # Format: CVE-YYYY-NNNN...
    parts = cve_id.split('-')
    if len(parts) != 3 or not parts[1].isdigit():
        return "Error: Invalid CVE format. Must be 'CVE-YYYY-NNNN'."
    
    year = parts[1]
    
    # The cvelistV5 repo is sharded by year and number
    # e.g., /cvelistV5/cves/2021/44xxx/CVE-2021-44228.json
    number_dir = f"{parts[2][:-3]}xxx"
    
    json_path = os.path.join(CVE_LIST_PATH, 'cves', year, number_dir, f"{cve_id}.json")
    
    # Use 'jq' to extract the description
    cmd = f"jq '.containers.cna.descriptions[0].value' {json_path}"
    
    result = secure_cli_tool(cmd, user_id)
    
    if "STDERR:" in result:
        auth.log_activity(user_id, 'search_cve', cve_id, 'failure')
        return f"Error: Could not find or parse CVE: {cve_id}. {result}"
        
    auth.log_activity(user_id, 'search_cve', cve_id, 'success')
    return f"CVE details for {cve_id}:\n{result.replace('STDOUT:', '')}"

# --- NEW TOOL 4: Forensics Tool ---
@tool("Forensics Tool (tsk)")
def forensics_tool(tsk_command: str, disk_image_path: str, user_id: int) -> str:
    """
    Runs a command from 'The Sleuth Kit' (tsk) on a disk image.
    (e.g., 'fls', 'icat').
    - tsk_command: The TSK command to run (e.g., 'fls -r').
    - disk_image_path: Path to the .dd or .E01 disk image.
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: forensics_tool] CMD: {tsk_command}")
    
    # We'd need to add 'sleuthkit' to the Dockerfile
    cmd = f"{tsk_command} {disk_image_path}"
    
    result = secure_cli_tool(cmd, user_id)
    auth.log_activity(user_id, 'forensics_tool', cmd, 'success')
    return result