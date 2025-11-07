#!/usr/bin/env python3

import requests
import argparse
import json
import sys

# --- Configuration ---
# This is the address of your LocalDeviceAgent.py
# For testing on the same machine, 'localhost' is correct.
AGENT_URL = 'http://localhost:8080'

def main():
    # 1. Setup argument parsing
    parser = argparse.ArgumentParser(description="FAPC Master Control v2")
    parser.add_argument(
        "command",
        type=str,
        nargs='+',
        help="The full command string to execute on the agent."
    )
    parser.add_argument(
        "--host",
        type=str,
        default='localhost',
        help="The hostname or IP of the device agent."
    )
    args = parser.parse_args()
    
    # Join all arguments into a single command string
    command_to_run = " ".join(args.command)
    target_url = f"http://{args.host}:{PORT}" # (PORT is 8080 from agent)
    
    print(f"--- FAPC Master Control ---")
    print(f"[MASTER] Sending command to {target_url}: \"{command_to_run}\"")

    # 2. Prepare the JSON payload
    payload = {'command': command_to_run}
    
    try:
        # 3. Send the POST request
        response = requests.post(target_url, json=payload, timeout=40)
        response.raise_for_status() # Raise an error for bad responses
        
        # 4. Parse and display the response
        result = response.json()
        
        print(f"[MASTER] Received response (Status: {result.get('returncode')})")
        print("\n--- AGENT STDOUT ---")
        if result.get('stdout'):
            print(result['stdout'])
        else:
            print("(No stdout)")
        
        if result.get('stderr'):
            print("\n--- AGENT STDERR ---")
            print(result['stderr'])
            
    except requests.exceptions.ConnectionError:
        print(f"\n[MASTER] FATAL: Connection refused.", file=sys.stderr)
        print(f"       Is the LocalDeviceAgent.py running on {target_url}?", file=sys.stderr)
    except requests.exceptions.Timeout:
        print(f"\n[MASTER] FATAL: Request timed out. Agent is unresponsive.", file=sys.stderr)
    except requests.exceptions.RequestException as e:
        print(f"\n[MASTER] FATAL: An error occurred: {e}", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"\n[MASTER] FATAL: Agent returned invalid JSON.", file=sys.stderr)

if __name__ == "__main__":
    # We need to define PORT here for the client script too
    PORT = 8080 
    main()