#!/usr/bin/env python3

import subprocess
import json
import auth
from fapc_tools_v4 import (
    secure_cli_tool,
    click_screen_tool,
    take_screenshot_tool,
    analyze_screenshot_tool
)
from crewai_tools import tool

# This file imports all v4 tools and adds the new delegation tool.
# We just need to re-state the imports so they are all in one place.
_ = secure_cli_tool
_ = click_screen_tool
_ = take_screenshot_tool
_ = analyze_screenshot_tool

@tool("Delegate to Specialist Crew")
def delegate_to_crew(task_description: str, crew_name: str, user_id: int) -> str:
    """
Use this to delegate a complex, specialized task to a specialist crew.
- task_description: The high-level task for them to accomplish.
- crew_name: The crew to run (e.g., 'coding_crew').
- user_id: The user_id for logging.
Returns the final report from that crew.
    """
    print(f"\n[Tool Call: delegate_to_crew] TO: {crew_name}")
    print(f"  - TASK: \"{task_description}\"")

    try:
        # Construct the command to run the other script
        # We pass the user_id and task as command-line arguments
        script_path = f"./{crew_name}.py"
        command = [
            sys.executable,  # Use the current python interpreter
            script_path,
            str(user_id),
            task_description
        ]

        # Run the subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=900 # 15-minute timeout for complex crew tasks
        )

        # Log the delegation success
        auth.log_activity(user_id, 'delegate_success', f"Task for {crew_name} completed.", 'success')
        return f"Success: {crew_name} reported:\n{result.stdout}"

    except subprocess.CalledProcessError as e:
        error_msg = f"Error: {crew_name} failed:\n{e.stderr}"
        auth.log_activity(user_id, 'delegate_fail', error_msg, 'failure')
        return error_msg
    except Exception as e:
        error_msg = f"Error delegating to {crew_name}: {e}"
        auth.log_activity(user_id, 'delegate_fail', error_msg, 'failure')
        return error_msg