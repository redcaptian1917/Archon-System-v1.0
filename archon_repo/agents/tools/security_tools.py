#!/usr/bin/env python3
# Archon Agent - Security & Auditing Tools

import json
import os
import subprocess
from crewai_tools import tool
from gvm.connections import TLSConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from ..core import auth
from .credential_tools import get_secure_credential_tool
from .helpers import GVM_HOST, GVM_PORT, DB_PATH, EXPLOIT_DB_PATH, CVE_LIST_PATH, _gvm_connect
from .control_tools import secure_cli_tool

@tool("Start Vulnerability Scan Tool")
def start_vulnerability_scan_tool(target_ip: str, user_id: int) -> str:
    """Starts a new GVM/OpenVAS vulnerability scan on a target IP."""
    print(f"\n[Tool Call: start_vulnerability_scan_tool] TARGET: {target_ip}")
    try:
        with _gvm_connect(user_id) as gmp:
            scan_config_id = "daba56c8-73ec-11df-a475-002264764cea" # Full and fast
            target_xml = gmp.create_target(name=f"Target {target_ip}", hosts=[target_ip])
            target_id = target_xml.get("id")
            task_xml = gmp.create_task(name=f"Scan for {target_ip}", config_id=scan_config_id, target_id=target_id)
            task_id = task_xml.get("id")
            gmp.start_task(task_id)

            auth.log_activity(user_id, 'gvm_start_scan', f"Started scan on {target_ip}", 'success')
            return json.dumps({"task_id": task_id, "target_id": target_id})
    except Exception as e:
        return f"Error starting scan: {e}"

@tool("Check Scan Status Tool")
def check_scan_status_tool(task_id: str, user_id: int) -> str:
    """Checks the status of a running GVM/OpenVAS scan."""
    print(f"\n[Tool Call: check_scan_status_tool] TASK: {task_id}")
    try:
        with _gvm_connect(user_id) as gmp:
            task_xml = gmp.get_task(task_id)
            status = task_xml.find("status").text
            progress = task_xml.find("progress").text
            return json.dumps({"status": status, "progress": progress})
    except Exception as e:
        return f"Error checking status: {e}"

@tool("Get Scan Report Tool")
def get_scan_report_tool(task_id: str, user_id: int) -> str:
    """Gets the final report summary of a *completed* GVM/OpenVAS scan."""
    print(f"\n[Tool Call: get_scan_report_tool] TASK: {task_id}")
    try:
        with _gvm_connect(user_id) as gmp:
            task_xml = gmp.get_task(task_id)
            if task_xml.find("status").text != "Done":
                return "Error: Scan is not 'Done'. Check status first."

            report_id = task_xml.find("report").get("id")
            report_xml = gmp.get_report(report_id)

            results = []
            for result in report_xml.findall(".//results/result"):
                name = result.find("name").text
                host = result.find("host").text
                port = result.find("port").text
                severity = result.find("severity").text
                if float(severity) > 0:
                    results.append({"name": name, "host": host, "port": port, "severity": float(severity)})

            auth.log_activity(user_id, 'gvm_get_report', f"Got report for {task_id}", 'success')
            if not results: return "Scan complete. No high-severity vulnerabilities found."
            return f"Scan complete. Found {len(results)} vulnerabilities:\n{json.dumps(results, indent=2)}"
    except Exception as e:
        return f"Error getting report: {e}"

# --- DFIR Tools ---
@tool("Update Offline Databases Tool")
def update_offline_databases_tool(user_id: int) -> str:
    """Clones or updates the local Exploit-DB and CVE JSON database."""
    print(f"\n[Tool Call: update_offline_databases_tool]")
    os.makedirs(DB_PATH, exist_ok=True)
    results = {}

    # Run commands directly inside the container
    def run_cmd(cmd):
        return subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)

    try:
        if os.path.exists(EXPLOIT_DB_PATH): cmd = f"cd {EXPLOIT_DB_PATH} && git pull"
        else: cmd = f"git clone https://github.com/offensive-security/exploit-database.git {EXPLOIT_DB_PATH}"
        run_cmd(cmd)
        results['exploit_db'] = "Update/Clone successful."
    except Exception as e: results['exploit_db'] = f"Update/Clone failed: {e}"

    try:
        if os.path.exists(CVE_LIST_PATH): cmd = f"cd {CVE_LIST_PATH} && git pull"
        else: cmd = f"git clone https://github.com/CVEProject/cvelistV5.git {CVE_LIST_PATH}"
        run_cmd(cmd)
        results['cve_list'] = "Update/Clone successful."
    except Exception as e: results['cve_list'] = f"Update/Clone failed: {e}"

    auth.log_activity(user_id, 'db_update', json.dumps(results), 'success')
    return f"Database update complete: {json.dumps(results)}"

@tool("Search Exploit-DB Tool")
def search_exploit_db_tool(query: str, user_id: int) -> str:
    """Uses 'searchsploit' to search the offline Exploit-DB."""
    print(f"\n[Tool Call: search_exploit_db_tool] QUERY: {query}")
    cmd = f"cd {EXPLOIT_DB_PATH} && ./searchsploit --no-color -j {query}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    auth.log_activity(user_id, 'search_exploit_db', query, 'success')
    if not result.stdout: return "No exploits found."
    return f"Found exploits:\n{result.stdout}"

@tool("Search CVE Database Tool")
def search_cve_database_tool(cve_id: str, user_id: int) -> str:
    """Searches the offline cvelistV5 JSON database for a specific CVE ID."""
    print(f"\n[Tool Call: search_cve_database_tool] ID: {cve_id}")
    parts = cve_id.split('-')
    if len(parts) != 3 or not parts[1].isdigit(): return "Error: Invalid CVE format."

    year, number_dir = parts[1], f"{parts[2][:-3]}xxx"
    json_path = os.path.join(CVE_LIST_PATH, 'cves', year, number_dir, f"{cve_id}.json")

    cmd = f"jq '.containers.cna.descriptions[0].value' {json_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        return f"Error: Could not find or parse CVE: {cve_id}. {result.stderr}"
    auth.log_activity(user_id, 'search_cve', cve_id, 'success')
    return f"CVE details for {cve_id}:\n{result.stdout}"

@tool("Forensics Tool (tsk)")
def forensics_tool(tsk_command: str, disk_image_path: str, user_id: int) -> str:
    """Runs a command from 'The Sleuth Kit' (tsk) on a disk image."""
    print(f"\n[Tool Call: forensics_tool] CMD: {tsk_command}")
    cmd = f"{tsk_command} {disk_image_path}" # e.g., "fls -r /app/images/image.dd"
    # This must run on the worker, as the image is likely there
    result = secure_cli_tool(cmd, user_id)
    auth.log_activity(user_id, 'forensics_tool', cmd, 'success')
    return result

# --- Hardening Tools ---
@tool("Metadata Scrubber Tool")
def metadata_scrubber_tool(file_or_dir_path: str, user_id: int) -> str:
    """Removes all metadata from a specified file or directory using 'mat2'."""
    print(f"\n[Tool Call: metadata_scrubber_tool] PATH: {file_or_dir_path}")
    # This command must run on the worker where the files are
    cmd = f"mat2 {file_or_dir_path}"
    result = secure_cli_tool(cmd, user_id)
    if "STDERR:" in result:
        return f"Error scrubbing metadata: {result}"
    auth.log_activity(user_id, 'scrub_metadata_success', file_or_dir_path, 'success')
    return f"Metadata scrubbed successfully for: {file_or_dir_path}"

@tool("OS Hardening Tool")
def os_hardening_tool(profile: str, user_id: int) -> str:
    """Applies a pre-defined OS hardening profile on the worker."""
    print(f"\n[Tool Call: os_hardening_tool] PROFILE: {profile}")
    if profile == "network_privacy":
        cmd = "sysctl -w net.ipv4.icmp_echo_ignore_all=1 && sysctl -w net.ipv4.tcp_syncookies=1"
    elif profile == "kernel_lockdown":
        cmd = "sysctl -w kernel.dmesg_restrict=1"
    else: return "Error: Unknown hardening profile."
    result = secure_cli_tool(cmd, user_id)
    auth.log_activity(user_id, 'os_hardening', profile, 'success')
    return f"Profile '{profile}' applied: {result}"
