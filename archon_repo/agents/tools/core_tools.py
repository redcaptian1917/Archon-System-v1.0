#!/usr/bin/env python3
# Archon Agent - Core & Delegation Tools

from crewai_tools import tool

@tool("Delegate to Specialist Crew")
def delegate_to_crew(task_description: str, crew_name: str, user_id: int) -> str:
    """
    Delegates a task to a specialist crew (e.g., 'coding_crew').
    The crew name must exist in the central registry.
    This tool is a placeholder; the *real* logic is in archon_ceo.py's
    `safe_delegate_to_crew` function which intercepts this call.
    """
    # This is a stub for the LLM. The actual execution is
    # handled by the `safe_delegate_to_crew` function in archon_ceo.py.
    return "Note: Delegation request received and will be processed by the CEO's internal logic."
