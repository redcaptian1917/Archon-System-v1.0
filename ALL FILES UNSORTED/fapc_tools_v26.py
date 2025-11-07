# ... (All previous tools imported) ...
from crewai_tools import tool
import simplejson as json

# --- Tool for Code Modification (CRITICAL SECURITY TOOL) ---
@tool("Code Modification Tool")
def code_modification_tool(file_path: str, new_content: str, user_id: int) -> str:
    """
    Writes or overwrites a file with new content. Use with EXTREME CAUTION.
    This is how the agent modifies its own scripts or creates new ones.
    - file_path: Absolute path to the file to modify (e.g., '/app/coding_crew.py').
    - new_content: The full, revised content (Python code, YAML, etc.).
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: code_modification_tool] PATH: {file_path}")
    
    # Restrict modification to the 'app' directory for safety
    if not file_path.startswith('/app'):
        auth.log_activity(user_id, 'code_mod_fail', f"Attempt to modify path outside /app: {file_path}", 'failure')
        return "Access Denied: Code modification is restricted to the /app directory."

    try:
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        auth.log_activity(user_id, 'code_mod_success', f"Overwrote file {file_path} with new code.", 'success')
        return f"Success: File {file_path} updated. Code must be reloaded/re-executed."
        
    except Exception as e:
        auth.log_activity(user_id, 'code_mod_fail', str(e), 'failure')
        return f"Error writing file: {e}"

# --- Tool for External Reflection (Collaboration with Jules) ---
@tool("Reflect and Learn Tool")
def reflect_and_learn_tool(problem_summary: str, external_model: str, user_id: int) -> str:
    """
    Submits a complex problem (error message, reasoning failure) to a superior external LLM for diagnostic advice.
    - problem_summary: A concise summary of the failure or error logs.
    - external_model: The external service to consult (e.g., 'gpt-4o', 'claude-3-opus').
    - user_id: The user_id for logging.
    Returns the diagnostic response from the external model.
    """
    print(f"\n[Tool Call: reflect_and_learn_tool] PROBLEM: {problem_summary[:50]}...")
    
    # The external_llm_tool already handles fetching the API key and routing through Tor.
    # We craft a special prompt to guide the expert.
    
    diagnostic_prompt = (
        "DIAGNOSTIC REQUEST: You are analyzing code written by an agent. "
        "The agent failed with the following problem or error log: "
        f"'{problem_summary}'. "
        "Your task is to provide the **EXACT, CORRECTED CODE BLOCK** "
        "and a brief (one-sentence) explanation of the fix. "
        "If a full code rewrite is needed, provide the full file content."
    )

    # Use the existing External LLM Tool (from fapc_tools_v23)
    return external_llm_tool(service_name=external_model, prompt=diagnostic_prompt, user_id=user_id)