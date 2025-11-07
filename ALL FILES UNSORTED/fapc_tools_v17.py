#!/usr/bin/env python3

import json
import auth
from crewai_tools import tool
from gvm.connections import UnixSocketConnection, TLSConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from gvm.xml import write_xml
import xml.etree.ElementTree as ET

# --- Import all v16 tools ---
from fapc_tools_v16 import (
    # ... (all your v16 tools) ...
    webcam_tool, listen_tool, transcribe_audio_tool
)
_ = (webcam_tool, listen_tool, transcribe_audio_tool) # etc.
# ---

# --- GVM/OpenVAS Toolset ---
GVM_HOST = "openvas"  # The Docker service name
GVM_PORT = 9390
GVM_CREDENTIAL_NAME = "gvm_admin"

def _gvm_connect(user_id):
    """Helper: Connects to GVM and returns the Gmp protocol object."""
    # 1. Get credentials
    creds_json = get_secure_credential_tool(GVM_CREDENTIAL_NAME, user_id)
    if 'Error' in creds_json:
        raise Exception(f"GVM credentials '{GVM_CREDENTIAL_NAME}' not found.")
    creds = json.loads(creds_json)
    
    # 2. Connect
    # Note: This Docker image uses TLS
    connection = TLSConnection(hostname=GVM_HOST, port=GVM_PORT)
    transform = EtreeTransform()
    gmp = Gmp(connection=connection, transform=transform)
    gmp.connect(creds['username'], creds['password'])
    return gmp

# --- TOOL 1: Start Scan ---
@tool("Start Vulnerability Scan Tool")
def start_vulnerability_scan_tool(target_ip: str, user_id: int) -> str:
    """
    Starts a new vulnerability scan on a target IP.
    Uses the 'Full and fast' scan configuration.
    - target_ip: The IP address of the target.
    - user_id: The user_id for logging.
    Returns a JSON string: {"task_id": "...", "target_id": "..."}
    """
    print(f"\n[Tool Call: start_vulnerability_scan_tool] TARGET: {target_ip}")
    try:
        with _gvm_connect(user_id) as gmp:
            # 1. Find the "Full and fast" scan config
            scan_config_id = "daba56c8-73ec-11df-a475-002264764cea" # Static ID
            
            # 2. Create the target
            target_xml = gmp.create_target(
                name=f"Target {target_ip}",
                hosts=[target_ip]
            )
            target_id = target_xml.get("id")

            # 3. Create and start the task
            task_xml = gmp.create_task(
                name=f"Scan for {target_ip}",
                config_id=scan_config_id,
                target_id=target_id
            )
            task_id = task_xml.get("id")
            
            gmp.start_task(task_id)
            
            auth.log_activity(user_id, 'gvm_start_scan', f"Started scan on {target_ip}", 'success')
            return json.dumps({"task_id": task_id, "target_id": target_id})
            
    except Exception as e:
        auth.log_activity(user_id, 'gvm_start_scan', f"Failed scan on {target_ip}", str(e))
        return f"Error starting scan: {e}"

# --- TOOL 2: Check Scan Status ---
@tool("Check Scan Status Tool")
def check_scan_status_tool(task_id: str, user_id: int) -> str:
    """
    Checks the status of a running scan.
    - task_id: The ID of the task to check.
    - user_id: The user_id for logging.
    Returns a JSON string: {"status": "Running", "progress": "50"}
    """
    print(f"\n[Tool Call: check_scan_status_tool] TASK: {task_id}")
    try:
        with _gvm_connect(user_id) as gmp:
            task_xml = gmp.get_task(task_id)
            status = task_xml.find("status").text
            progress = task_xml.find("progress").text
            
            return json.dumps({"status": status, "progress": progress})
            
    except Exception as e:
        return f"Error checking status: {e}"

# --- TOOL 3: Get Scan Report ---
@tool("Get Scan Report Tool")
def get_scan_report_tool(task_id: str, user_id: int) -> str:
    """
    Gets the final report of a *completed* scan.
    - task_id: The ID of the task (must have status 'Done').
    - user_id: The user_id for logging.
    Returns a simplified summary of the results.
    """
    print(f"\n[Tool Call: get_scan_report_tool] TASK: {task_id}")
    try:
        with _gvm_connect(user_id) as gmp:
            # 1. Get the task's report ID
            task_xml = gmp.get_task(task_id)
            if task_xml.find("status").text != "Done":
                return "Error: Scan is not 'Done'. Check status first."
            
            report_id = task_xml.find("report").get("id")
            
            # 2. Get the full report
            report_xml = gmp.get_report(report_id)
            
            # 3. Parse the report into a simple summary
            results = []
            for result in report_xml.findall(".//results/result"):
                name = result.find("name").text
                host = result.find("host").text
                port = result.find("port").text
                severity = result.find("severity").text
                
                # Only include results with a severity > 0
                if float(severity) > 0:
                    results.append({
                        "name": name,
                        "host": host,
                        "port": port,
                        "severity": float(severity)
                    })
            
            auth.log_activity(user_id, 'gvm_get_report', f"Got report for {task_id}", 'success')
            if not results:
                return "Scan complete. No high-severity vulnerabilities found."
            
            return f"Scan complete. Found {len(results)} vulnerabilities:\n{json.dumps(results, indent=2)}"

    except Exception as e:
        auth.log_activity(user_id, 'gvm_get_report', f"Failed report for {task_id}", str(e))
        return f"Error getting report: {e}"