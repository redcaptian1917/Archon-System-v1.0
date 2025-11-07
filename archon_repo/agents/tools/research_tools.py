#!/usr/bin/env python3
# Archon Agent - Research & Analysis Tools

import json
import requests
import subprocess
import sys
from crewai_tools import tool
from openai import OpenAI
from anthropic import Anthropic
from ..core import auth
from .credential_tools import get_secure_credential_tool
from .helpers import TOR_SOCKS_PROXY

@tool("External LLM Tool")
def external_llm_tool(service_name: str, prompt: str, user_id: int) -> str:
    """Calls an external, non-local LLM (like GPT, Grok, Claude)."""
    print(f"\n[Tool Call: external_llm_tool] SERVICE: {service_name}")
    try:
        api_key_name = f"api_{service_name.split('-')[0]}"
        if 'gpt' in service_name: api_key_name = 'api_openai'
        if 'claude' in service_name: api_key_name = 'api_anthropic'

        creds_json = get_secure_credential_tool(api_key_name, user_id)
        if 'Error' in creds_json: return creds_json
        api_key = json.loads(creds_json)['password']

        http_client = requests.Session()
        http_client.proxies = {'http': TOR_SOCKS_PROXY, 'https': TOR_SOCKS_PROXY}

        if 'gpt' in service_name:
            client = OpenAI(api_key=api_key, http_client=http_client)
            response = client.chat.completions.create(model=service_name, messages=[{"role": "user", "content": prompt}])
            result_text = response.choices[0].message.content
        elif 'claude' in service_name:
            client = Anthropic(api_key=api_key, http_client=http_client)
            response = client.messages.create(model=service_name, max_tokens=2048, messages=[{"role": "user", "content": prompt}])
            result_text = response.content[0].text
        elif 'grok' in service_name:
            response = http_client.post("https://api.x.ai/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json={"model": "grok-1", "messages": [{"role": "user", "content": prompt}]})
            response.raise_for_status()
            result_text = response.json()['choices'][0]['message']['content']
        else:
            return f"Error: Unknown external LLM service '{service_name}'."

        auth.log_activity(user_id, 'external_llm_call', f"Success: Got response from {service_name}", 'success')
        return f"Response from {service_name}:\n{result_text}"
    except Exception as e:
        return f"Error calling external LLM: {e}"

@tool("Python REPL Tool")
def python_repl_tool(code: str, user_id: int) -> str:
    """
    Executes a block of Python code in a sandboxed REPL.
    You MUST use this for all math, physics, data analysis.
    You can use libraries like 'numpy', 'pandas', 'scipy'.
    You MUST use a 'print()' statement to see the result.
    """
    print(f"\n[Tool Call: python_repl_tool]")
    print(f"  - CODE: \"{code}\"")
    try:
        # Use 'sys.executable' to run python in the same venv
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        output = result.stdout
        auth.log_activity(user_id, 'python_repl', f"Code executed: {code}", 'success')
        return f"Execution successful. Output:\n{output}"
    except subprocess.CalledProcessError as e:
        error_msg = f"Python Error:\n{e.stderr}"
        auth.log_activity(user_id, 'python_repl', f"Code failed: {code}", error_msg)
        return error_msg
    except Exception as e:
        return f"Tool Error: {e}"
