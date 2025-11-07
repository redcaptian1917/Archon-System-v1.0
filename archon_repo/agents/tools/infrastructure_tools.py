#!/usr/bin/env python3
# Archon Agent - Self-Improvement & Infrastructure Tools

import json
import os
import tempfile
import git
import ansible_runner
from crewai_tools import tool
from ..core import auth
from .credential_tools import get_secure_credential_tool
from .research_tools import external_llm_tool

@tool("Git Repository Tool")
def git_tool(repo_path: str, action: str, branch: str = 'main', user_id: int = None) -> str:
    """Performs Git actions ('pull', 'status') on a local repository."""
    print(f"\n[Tool Call: git_tool] REPO: {repo_path} ACTION: {action}")
    try:
        repo = git.Repo(repo_path)
        if action == "pull":
            result_str = str(repo.remotes.origin.pull(branch)[0].flags)
        elif action == "status":
            result_str = repo.git.status()
        else: return "Error: Unsupported Git action."
        auth.log_activity(user_id, 'git_tool', f"{action} on {repo_path}", 'success')
        return result_str
    except Exception as e:
        return f"Error with Git operation: {e}"

@tool("Ansible Playbook Tool")
def ansible_playbook_tool(inventory_host: str, playbook_yaml: str, ssh_credential_name: str, user_id: int) -> str:
    """Executes an Ansible playbook on a remote host to provision it."""
    print(f"\n[Tool Call: ansible_playbook_tool] HOST: {inventory_host}")
    creds_json = get_secure_credential_tool(ssh_credential_name, user_id)
    if 'Error' in creds_json: return creds_json
    creds = json.loads(creds_json)

    with tempfile.TemporaryDirectory() as temp_dir:
        inventory_data = {'all': {'hosts': {inventory_host: {
            'ansible_user': creds.get('username'), 'ansible_ssh_pass': creds.get('password'),
            'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        }}}}
        with open(os.path.join(temp_dir, 'inventory.json'), 'w') as f: json.dump(inventory_data, f)
        with open(os.path.join(temp_dir, 'playbook.yml'), 'w') as f: f.write(playbook_yaml)

        print(f"[AnsibleTool] Running playbook on {inventory_host}...")
        r = ansible_runner.run(
            private_data_dir=temp_dir,
            inventory=os.path.join(temp_dir, 'inventory.json'),
            playbook=os.path.join(temp_dir, 'playbook.yml')
        )

        stats = r.stats
        if r.rc == 0:
            status, report = 'success', f"Playbook run successful.\nHost: {inventory_host}\nOK: {stats.get('ok', {}).get(inventory_host, 0)}\nChanged: {stats.get('changed', {}).get(inventory_host, 0)}\nFailed: {stats.get('failures', {}).get(inventory_host, 0)}"
        else:
            status, report = 'failure', f"Playbook run FAILED.\n"
            for event in r.events:
                if event['event'] == 'runner_on_failed':
                    report += json.dumps(event['event_data']['res'], indent=2)

        auth.log_activity(user_id, 'ansible_run', f"Playbook on {inventory_host}", status)
        return report
    except Exception as e:
        return f"Error running Ansible: {e}"

@tool("Code Modification Tool")
def code_modification_tool(file_path: str, new_content: str, user_id: int) -> str:
    """Writes or overwrites a file with new content. Use with EXTREME CAUTION."""
    print(f"\n[Tool Call: code_modification_tool] PATH: {file_path}")
    if not file_path.startswith('/app'):
        return "Access Denied: Code modification is restricted to the /app directory."
    try:
        with open(file_path, 'w') as f: f.write(new_content)
        auth.log_activity(user_id, 'code_mod_success', f"Overwrote file {file_path}", 'success')
        return f"Success: File {file_path} updated."
    except Exception as e:
        return f"Error writing file: {e}"

@tool("Reflect and Learn Tool")
def reflect_and_learn_tool(problem_summary: str, external_model: str, user_id: int) -> str:
    """Submits a complex problem (error log) to a superior external LLM for diagnostic advice."""
    print(f"\n[Tool Call: reflect_and_learn_tool] PROBLEM: {problem_summary[:50]}...")
    diagnostic_prompt = (f"DIAGNOSTIC REQUEST: You are analyzing code written by an agent. The agent failed with the following problem or error log: '{problem_summary}'. Your task is to provide the EXACT, CORRECTED CODE BLOCK and a brief (one-sentence) explanation of the fix. If a full code rewrite is needed, provide the full file content.")
    return external_llm_tool(service_name=external_model, prompt=diagnostic_prompt, user_id=user_id)
