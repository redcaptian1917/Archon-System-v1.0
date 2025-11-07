#!/usr/bin/env python3

import json
import auth
import db_manager
import ollama
import psycopg2
import os
import requests
import uuid
import websocket
import time
from crewai_tools import tool
from pgvector.psycopg2 import register_vector
import git

# --- Import all v22 tools ---
from fapc_tools_v22 import (
    # ... (all your v22 tools) ...
    comfyui_image_tool, text_to_speech_tool
)
_ = (comfyui_image_tool, text_to_speech_tool) # etc.
# ---

# --- Import key tools from v22 ---
from fapc_tools_v22 import get_secure_credential_tool

# --- NEW: Import External API Clients ---
from openai import OpenAI
from anthropic import Anthropic

# --- Tor Proxy Config ---
TOR_SOCKS_PROXY = 'socks5h://tor-proxy:9050'
proxies = {'http': TOR_SOCKS_PROXY, 'https': TOR_SOCKS_PROXY}

# --- NEW TOOL: External LLM (Phone-a-Friend) ---

@tool("External LLM Tool")
def external_llm_tool(service_name: str, prompt: str, user_id: int) -> str:
    """
    Calls an external, non-local LLM (like GPT, Grok, Claude)
    to solve a problem, get real-time info, or get a second opinion.
    - service_name: The model to use (e.g., 'gpt-4o', 'grok', 'claude-3-opus').
    - prompt: The user's prompt.
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: external_llm_tool] SERVICE: {service_name}")
    
    try:
        # 1. Get the API Key for the requested service
        api_key_name = f"api_{service_name.split('-')[0]}" # e.g., 'api_gpt' -> 'api_openai'
        if 'gpt' in service_name: api_key_name = 'api_openai'
        if 'claude' in service_name: api_key_name = 'api_anthropic'
        
        creds_json = get_secure_credential_tool(api_key_name, user_id)
        if 'Error' in creds_json:
            return creds_json
        api_key = json.loads(creds_json)['password']

        # 2. Create a proxied HTTP client for the APIs
        # This forces all external API calls through Tor
        http_client = requests.Session()
        http_client.proxies = proxies

        # 3. Route to the correct API
        
        # --- OPENAI (GPT) ---
        if 'gpt' in service_name:
            client = OpenAI(api_key=api_key, http_client=http_client)
            response = client.chat.completions.create(
                model=service_name, # e.g., "gpt-4o"
                messages=[{"role": "user", "content": prompt}]
            )
            result_text = response.choices[0].message.content

        # --- ANTHROPIC (CLAUDE) ---
        elif 'claude' in service_name:
            client = Anthropic(api_key=api_key, http_client=http_client)
            response = client.messages.create(
                model=service_name, # e.g., "claude-3-opus-20240229"
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            result_text = response.content[0].text
        
        # --- GROK (X-AI) ---
        elif 'grok' in service_name:
            # Grok uses a standard requests-based API
            response = http_client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-1",
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            response.raise_for_status()
            result_text = response.json()['choices'][0]['message']['content']

        else:
            return f"Error: Unknown external LLM service '{service_name}'."
        
        auth.log_activity(user_id, 'external_llm_call', f"Success: Got response from {service_name}", 'success')
        return f"Response from {service_name}:\n{result_text}"

    except Exception as e:
        auth.log_activity(user_id, 'external_llm_fail', f"Failed to call {service_name}", str(e))
        return f"Error calling external LLM: {e}"
```

---

### 5. ⬆️ Upgrade `archon_ceo.py`

1.  Open `archon_ceo.py`.
2.  Change the import from `fapc_tools_v22` to `fapc_tools_v23`.
3.  Add `external_llm_tool` to the import list and the `archon_agent`'s `tools` list.
4.  Update the `backstory` to teach Archon *when* to use this new, powerful tool.

**New `archon_agent` backstory (excerpt):**
```python
    backstory=(
        "You are Archon, the central coordinator AI. Your primary goal is to "
        "successfully complete the user's task using your own crews and "
        "local tools. You must be efficient and secure.\n\n"
        "**META-REASONING & ESCALATION (NEW):**\n"
        "Your local models are fast and secure. External models (GPT, Grok) "
        "are slow, expensive, and send data to a 3rd party. You must "
        "**ONLY** use the 'external_llm_tool' as a last resort IF:\n"
        "1. Your local models or crews have failed to solve a complex "
        "   coding, math, or reasoning problem.\n"
        "2. The user *explicitly* asks for real-time information (e.g., "
        "   'What's the market sentiment on X?' - use 'grok').\n"
        "3. The user *explicitly* asks for a comparison or a different "
        "   style of reasoning (e.g., 'What does GPT-4o think?').\n\n"
        "**MEMORY WORKFLOW:**\n"
        "1. **Recall:** Before starting, use 'recall_facts_tool'...\n"
        # ... (rest of your backstory) ...
    ),
```

---

### 6. 🚀 How to Use It

You can now give Archon commands that force it to escalate.

**Example 1: Solving a Problem It Can't**
```bash
docker-compose exec archon-app ./archon_ceo.py "My local 'llama3' model is struggling to solve this advanced physics problem: [insert complex problem]. Escalate this to 'claude-3-opus' and give me the answer."
```
* **Archon (Thought):** "The user's local model failed, and they are *explicitly* asking for 'claude-3-opus'. My instructions state this is a valid use of the 'external_llm_tool'."
* **Action:** `external_llm_tool(service_name="claude-3-opus-20240229", prompt="[...problem...]", user_id=1)`
* **Final Answer:** "Response from claude-3-opus-20240229: [The solved physics problem]."

**Example 2: Real-time Data (for PlausiDen)**
```bash
docker-compose exec archon-app ./archon_ceo.py "Delegate to the PlausiDenCrew: 'I need to generate a fake browsing history for a user in Berlin. First, use the 'external_llm_tool' with 'grok' to find out the top 5 *local news stories* trending in Berlin, Germany *right now*.' Then, use the BrowserTool to generate a history based on those real-time topics."