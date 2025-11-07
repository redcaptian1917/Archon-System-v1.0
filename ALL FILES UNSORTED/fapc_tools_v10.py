#!/usr/bin/env python3

import json
import subprocess
import auth
from crewai_tools import tool

# --- Import all v9 tools ---
# (This assumes v9 is in a file named fapc_tools_v9.py)
from fapc_tools_v9 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool,
     add_secure_credential_tool, get_secure_credential_tool,
     notify_human_for_help_tool, generate_image_tool)
# ---

# --- NEW TOOL: Python REPL (Code Interpreter) ---

@tool("Python REPL Tool")
def python_repl_tool(code: str, user_id: int) -> str:
    """
    Executes a block of Python code in a sandboxed REPL.
    You MUST use this for all math, physics, data analysis,
    and complex calculations.
    You can use libraries like 'numpy', 'pandas', 'scipy'.
    You MUST use a 'print()' statement to see the result.
    The code should be a single string.
    
    Example:
    'import numpy as np; x = np.array([1, 2, 3]); print(np.mean(x))'
    
    - code: The Python code to execute.
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: python_repl_tool]")
    print(f"  - CODE: \"{code}\"")

    try:
        # Use 'sys.executable' to run python in the same venv
        # '-c' flag executes the code string
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
            timeout=60 # 60-second timeout
        )
        
        output = result.stdout
        auth.log_activity(user_id, 'python_repl', f"Code executed: {code}", 'success')
        return f"Execution successful. Output:\n{output}"
        
    except subprocess.CalledProcessError as e:
        # This catches errors *from the Python code itself*
        error_msg = f"Python Error:\n{e.stderr}"
        auth.log_activity(user_id, 'python_repl', f"Code failed: {code}", error_msg)
        return error_msg
    except Exception as e:
        # This catches errors *in the tool itself*
        error_msg = f"Tool Error: {e}"
        auth.log_activity(user_id, 'python_repl', f"Code failed: {code}", error_msg)
        return error_msg