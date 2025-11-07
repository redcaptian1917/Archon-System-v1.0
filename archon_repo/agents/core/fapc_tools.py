#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - MASTER TOOL LIBRARY (vFINAL)
#
# This file contains ALL (40+) tools for the Archon Agent
# and all its specialist crews. It is the "Armory."
#
# This file is the single source of truth for all agent capabilities.
# It is imported by `archon_ceo.py` and all specialist crews.
# -----------------------------------------------------------------

import json
import os
import requests
import uuid
import time
import subprocess
import base64
import sys
import shutil
import tempfile
import threading
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

# --- External Libraries ---
import bcrypt
import pyotp
import git
import ansible_runner
from twilio.rest import Client
from gvm.connections import TLSConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from openai import OpenAI
from anthropic import Anthropic
import qrcode
import cv2
import sounddevice as sd
import soundfile as sf
import numpy as np
import websocket
from pgvector.psycopg2 import register_vector
import psycopg2
import docker
import whisper
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from imapclient import IMAPClient

# --- Internal Imports ---
# These must be in the same directory or Python path
# (or handled by the Docker environment)
try:
    import auth
    import db_manager
except ImportError:
    print("CRITICAL: auth.py or db_manager.py not found.", file=sys.stderr)
    sys.exit(1)

# --- Decorator ---
from crewai_tools import tool

# --- Global Configuration ---
# These are loaded from Docker environment variables
AGENT_ONION_URL = os.getenv("KALI_AGENT_URL", "your_kali_agent.onion")
HARDWARE_AGENT_ONION_URL = os.getenv("PI_AGENT_URL", "your_pi_hardware_agent.onion")
TOR_SOCKS_PROXY = os.getenv("TOR_PROXY_URL", 'socks5h://tor-proxy:9050')

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://comfyui:8188")
COQUI_TTS_URL = os.getenv("COQUI_TTS_URL", "http://coqui-tts:5002")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

# This is a global, stateful session for the BrowserTool
browser_session = None

# Load the Whisper model once on startup
try:
    WHISPER_MODEL = whisper.load_model("base.en")
    print("[WhisperTool] Whisper 'base.en' model loaded successfully.")
except Exception as e:
    print(f"[WhisperTool ERROR] Could not load model: {e}", file=sys.stderr)
    WHISPER_MODEL = None


# ----------------------------------------
# --- SECTION 0: HELPER FUNCTIONS ---
# ----------------------------------------

def get_embedding(text_to_embed: str) -> list:
    """Generates an embedding vector for a string."""
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        response = client.embeddings(
            model='nomic-embed-text', # Standard embedding model
            prompt=text_to_embed
        )
        return response["embedding"]
    except Exception as e:
        print(f"[Embedding Error] {e}", file=sys.stderr)
        return None

def _send_agent_request(endpoint: str, payload: dict, is_hardware: bool = False) -> dict:
    """Helper: Sends a command securely over Tor to a worker agent."""
    onion_url = HARDWARE_AGENT_ONION_URL if is_hardware else AGENT_ONION_URL
    target_url = f"http://{onion_url}/{endpoint}"
    proxies = {'http': TOR_SOCKS_PROXY, 'https': TOR_SOCKS_PROXY}
    
    try:
        response = requests.post(target_url, json=payload, proxies=proxies, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {'error': f'Request Failed: {e}'}

def _get_twilio_client(user_id: int) -> Client:
    creds_json = get_secure_credential_tool('twilio_api', user_id)
    if 'Error' in creds_json: raise Exception("Twilio API credentials ('twilio_api') not found.")
    creds = json.loads(creds_json)
    return Client(creds['username'], creds['password'])

def _get_twilio_number(user_id: int) -> str:
    num_json = get_secure_credential_tool('twilio_phone_number', user_id)
    if 'Error' in num_json: raise Exception("Twilio phone number ('twilio_phone_number') not found.")
    return json.loads(num_json)['password']

def _get_email_servers(service_name: str):
    service_name = service_name.lower()
    if 'gmail' in service_name: return 'imap.gmail.com', 'smtp.gmail.com', 587
    if 'outlook' in service_name: return 'outlook.office365.com', 'smtp.office365.com', 587
    # Default for private servers
    domain = service_name.split('@')[-1]
    return f'imap.{domain}', f'smtp.{domain}', 587

def _queue_comfy_prompt(prompt_workflow: dict) -> dict:
    """Helper: Sends a workflow to the ComfyUI API."""
    client_id = str(uuid.uuid4())
    post_data = json.dumps({'prompt': prompt_workflow, 'client_id': client_id}).encode('utf-8')
    req = requests.post(f"{COMFYUI_URL}/prompt", data=post_data)
    req.raise_for_status()
    prompt_id = req.json()['prompt_id']
    
    ws_url = f"ws://{COMFYUI_URL.split('//')[1]}/ws?clientId={client_id}"
    with websocket.create_connection(ws_url) as ws:
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executed' and message['data']['prompt_id'] == prompt_id:
                    return message['data']['output'] # We're done
            else:
                continue # It's a binary preview, ignore

def _gvm_connect(user_id):
    """Helper: Connects to GVM and returns the Gmp protocol object."""
    creds_json = get_secure_credential_tool("gvm_admin", user_id)
    if 'Error' in creds_json:
        raise Exception(f"GVM credentials 'gvm_admin' not found.")
    creds = json.loads(creds_json)
    
    connection = TLSConnection(hostname="openvas", port=9390) # Docker service name
    transform = EtreeTransform()
    gmp = Gmp(connection=connection, transform=transform)
    gmp.connect(creds['username'], creds['password'])
    return gmp

# ----------------------------------------
# --- SECTION 1: CORE & DELEGATION TOOLS ---
# ----------------------------------------

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
    return f"Note: Delegation to {crew_name} will be handled by the CEO's internal logic."

# ----------------------------------------
# --- SECTION 2: C2 & CONTROL TOOLS ---
# ----------------------------------------

@tool("Secure CLI Tool")
def secure_cli_tool(command: str, user_id: int) -> str:
    """Executes a Bash/CLI command on the remote device agent (Kali/Debian)."""
    print(f"\n[Tool Call: secure_cli_tool] CMD: \"{command}\"")
    result = _send_agent_request('cli', {'command': command})
    
    if 'error' in result:
        auth.log_activity(user_id, 'cli_command', f"Command: {command}", f"failure: {result['error']}")
        return f"Error: {result['error']}"
    
    if result.get('returncode') == 0:
        auth.log_activity(user_id, 'cli_command', f"Command: {command}", 'success')
        return f"STDOUT:\n{result.get('stdout', '(No stdout)')}"
    
    error_detail = result.get('stderr', '(No stderr)')
    auth.log_activity(user_id, 'cli_command', f"Command: {command}", f"failure: {error_detail}")
    return f"STDERR:\n{error_detail}"

@tool("Click Screen Tool")
def click_screen_tool(x: int, y: int, user_id: int) -> str:
    """Clicks the mouse at the specified (x, y) coordinate on the remote agent's screen."""
    print(f"\n[Tool Call: click_screen_tool] COORDS: ({x}, {y})")
    result = _send_agent_request('click', {'x': x, 'y': y})
    auth.log_activity(user_id, 'click_tool', f"Clicked at ({x},{y})", 'success' if 'error' not in result else 'failure')
    return json.dumps(result)

@tool("Take Screenshot Tool")
def take_screenshot_tool(save_path: str, user_id: int) -> str:
    """Takes a screenshot of the remote agent's entire screen and saves it locally."""
    print(f"\n[Tool Call: take_screenshot_tool] SAVE_TO: \"{save_path}\"")
    result = _send_agent_request('screenshot', {})
    
    if 'error' in result:
        auth.log_activity(user_id, 'screenshot_fail', result['error'], 'failure')
        return f"Error: {result['error']}"
    
    try:
        image_bytes = base64.b64decode(result['image_base64'])
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        auth.log_activity(user_id, 'screenshot_success', f"Saved to {save_path}", 'success')
        return f"Success: Screenshot saved to {save_path}"
    except Exception as e:
        auth.log_activity(user_id, 'screenshot_fail', str(e), 'failure')
        return f"Error saving screenshot: {e}"

@tool("Hardware Type Tool")
def hardware_type_tool(text: str, user_id: int) -> str:
    """Types a string of text using the physical hardware (HID) agent."""
    print(f"\n[Tool Call: hardware_type_tool] TEXT: {text[:20]}...")
    result = _send_agent_request('type', {'text': text}, is_hardware=True)
    if 'error' in result:
        auth.log_activity(user_id, 'hw_type_fail', str(result['error']), 'failure')
        return f"Error: {result['error']}"
    auth.log_activity(user_id, 'hw_type', text, 'success')
    return "Hardware type command sent successfully."

@tool("Hardware Key Tool")
def hardware_key_tool(key: str, modifier: str = "", user_id: int = None) -> str:
    """Presses a special key (e.g., 'ENTER') or a combo using the physical hardware (HID) agent."""
    print(f"\n[Tool Call: hardware_key_tool] KEY: {modifier} + {key}")
    payload = {'key': key, 'modifier': modifier}
    result = _send_agent_request('key', payload, is_hardware=True)
    if 'error' in result:
        auth.log_activity(user_id, 'hw_key_fail', str(result['error']), 'failure')
        return f"Error: {result['error']}"
    auth.log_activity(user_id, 'hw_key', f"{modifier} + {key}", 'success')
    return "Hardware key command sent successfully."

@tool("Hardware Mouse Move Tool")
def hardware_mouse_move_tool(x: int, y: int, user_id: int) -> str:
    """Moves the mouse *relatively* using the physical hardware (HID) agent."""
    print(f"\n[Tool Call: hardware_mouse_move_tool] MOVE: ({x}, {y})")
    payload = {'x': x, 'y': y}
    result = _send_agent_request('mouse_move', payload, is_hardware=True)
    if 'error' in result:
        auth.log_activity(user_id, 'hw_mouse_fail', str(result['error']), 'failure')
        return f"Error: {result['error']}"
    auth.log_activity(user_id, 'hw_mouse', f"({x}, {y})", 'success')
    return "Hardware mouse move command sent."

# ----------------------------------------
# --- SECTION 3: SENSES & REASONING ---
# ----------------------------------------

@tool("Webcam Tool")
def webcam_tool(save_path: str, user_id: int) -> str:
    """Captures a single image from the agent's default webcam and saves it."""
    print(f"\n[Tool Call: webcam_tool] SAVE_TO: {save_path}")
    result = _send_agent_request('webcam', {})
    if 'error' in result:
        auth.log_activity(user_id, 'webcam_fail', result['error'], 'failure')
        return f"Error: {result['error']}"
    try:
        image_bytes = base64.b64decode(result['image_base64'])
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        auth.log_activity(user_id, 'webcam_success', f"Saved to {save_path}", 'success')
        return f"Success: Webcam image saved to {save_path}"
    except Exception as e:
        return f"Error saving image: {e}"

@tool("Listen Tool")
def listen_tool(save_path: str, duration: int = 5, user_id: int = None) -> str:
    """Records audio from the agent's default microphone and saves it as a WAV file."""
    print(f"\n[Tool Call: listen_tool] SAVE_TO: {save_path}")
    result = _send_agent_request('listen', {'duration': duration})
    if 'error' in result:
        auth.log_activity(user_id, 'listen_fail', result['error'], 'failure')
        return f"Error: {result['error']}"
    try:
        audio_bytes = base64.b64decode(result['audio_base64'])
        with open(save_path, 'wb') as f:
            f.write(audio_bytes)
        auth.log_activity(user_id, 'listen_success', f"Saved to {save_path}", 'success')
        return f"Success: Audio recording saved to {save_path}"
    except Exception as e:
        return f"Error saving audio: {e}"

@tool("Transcribe Audio Tool")
def transcribe_audio_tool(audio_path: str, user_id: int) -> str:
    """Transcribes an audio file (.wav, .mp3) into text using Whisper."""
    print(f"\n[Tool Call: transcribe_audio_tool] FILE: {audio_path}")
    if WHISPER_MODEL is None:
        return "Error: Whisper model is not loaded."
    if not os.path.exists(audio_path):
        return f"Error: Audio file not found at {audio_path}"
    try:
        result = WHISPER_MODEL.transcribe(audio_path, fp16=False)
        transcribed_text = result["text"]
        auth.log_activity(user_id, 'transcribe_success', f"Transcribed {audio_path}", 'success')
        return f"Transcribed text: {transcribed_text}"
    except Exception as e:
        return f"Error during transcription: {e}"

@tool("Analyze Screenshot Tool")
def analyze_screenshot_tool(image_path: str, prompt: str, user_id: int) -> str:
    """Analyzes a local screenshot using a multimodal AI (LLaVA)."""
    print(f"\n[Tool Call: analyze_screenshot_tool] IMG: \"{image_path}\"")
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        response = client.chat(
            model='llava:7b', # Assumes 'llava:7b' is pulled
            messages=[{'role': 'user', 'content': prompt, 'images': [image_base64]}],
            options={'temperature': 0.0}
        )
        result_text = response['message']['content']
        auth.log_activity(user_id, 'analyze_image', prompt, 'success')
        return result_text
    except Exception as e:
        return f"Error during vision analysis: {e}"

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

# ----------------------------------------
# --- SECTION 4: MEMORY & LEARNING ---
# ----------------------------------------

@tool("Learn Fact Tool")
def learn_fact_tool(fact: str, importance: int = 50, do_not_delete: bool = False, user_id: int = None) -> str:
    """Saves a new fact to the permanent knowledge base."""
    print(f"\n[Tool Call: learn_fact_tool] FACT: \"{fact[:50]}...\"")
    try:
        embedding = get_embedding(fact)
        if embedding is None: return "Error: Could not generate embedding."
        conn = db_manager.db_connect()
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO knowledge_base (owner_user_id, fact_text, embedding, importance_score, do_not_delete) VALUES (%s, %s, %s, %s, %s)",
                (user_id, fact, embedding, importance, do_not_delete)
            )
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'kb_learn', fact, 'success')
        return "Success: The fact has been learned and stored."
    except Exception as e:
        return f"Error learning fact: {e}"

@tool("Recall Facts Tool")
def recall_facts_tool(query: str, user_id: int) -> str:
    """Searches the knowledge base for relevant facts and refreshes them."""
    print(f"\n[Tool Call: recall_facts_tool] QUERY: \"{query}\"")
    try:
        query_embedding = get_embedding(query)
        if query_embedding is None: return "Error: Could not generate query embedding."
        conn = db_manager.db_connect()
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fact_id, fact_text, embedding <-> %s AS distance FROM knowledge_base WHERE owner_user_id = %s ORDER BY distance ASC LIMIT 3;",
                (query_embedding, user_id)
            )
            results = cur.fetchall()
            if not results: 
                conn.close()
                return "No relevant facts found in memory."
            
            fact_ids = [res[0] for res in results]
            formatted_results = "\n".join([f"- (ID: {fid}): {fact}" for fid, fact, dist in results])
            
            # Refresh 'last_accessed_at'
            cur.execute(
                "UPDATE knowledge_base SET last_accessed_at = CURRENT_TIMESTAMP WHERE fact_id = ANY(%s)",
                (fact_ids,)
            )
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'kb_recall', query, 'success')
        return f"Success: Retrieved {len(results)} relevant facts:\n{formatted_results}"
    except Exception as e:
        return f"Error recalling facts: {e}"

@tool("Get Stale Facts Tool")
def get_stale_facts_tool(older_than_days: int = 90, max_importance: int = 49, user_id: int = None) -> str:
    """Finds 'stale' facts that are candidates for summarization and deletion."""
    print(f"\n[Tool Call: get_stale_facts_tool]")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fact_id, fact_text FROM knowledge_base WHERE owner_user_id = %s AND do_not_delete = FALSE AND importance_score <= %s AND last_accessed_at < (CURRENT_TIMESTAMP - INTERVAL '%s days') LIMIT 100;",
                (user_id, max_importance, older_than_days)
            )
            results = cur.fetchall()
        conn.close()
        if not results: return "No stale facts found."
        facts = [{"id": fid, "text": ftext} for fid, ftext in results]
        return json.dumps(facts)
    except Exception as e:
        return f"Error getting stale facts: {e}"

@tool("Summarize Facts Tool")
def summarize_facts_tool(facts_to_summarize: str, user_id: int) -> str:
    """Takes a JSON list of facts and condenses them into a single, high-density summary."""
    print(f"\n[Tool Call: summarize_facts_tool]")
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        prompt = (f"You are a memory summarization AI. Condense the following old facts into a single, high-density paragraph. If the facts are noise, respond with 'None'.\n\nFACTS:\n{facts_to_summarize}")
        response = client.chat(model="llama3:8b", messages=[{'role': 'user', 'content': prompt}])
        summary = response['message']['content']
        auth.log_activity(user_id, 'kb_summarize', f'Summarized {len(facts_to_summarize)} facts.', 'success')
        return summary
    except Exception as e:
        return f"Error summarizing facts: {e}"

@tool("Delete Facts Tool")
def delete_facts_tool(fact_ids: list, user_id: int) -> str:
    """Permanently deletes a list of fact IDs from the knowledge base."""
    print(f"\n[Tool Call: delete_facts_tool] DELETING {len(fact_ids)} IDs")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM knowledge_base WHERE fact_id = ANY(%s) AND do_not_delete = FALSE RETURNING fact_id;",
                (fact_ids,)
            )
            deleted_count = cur.rowcount
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'kb_delete', f'Deleted {deleted_count} facts.', 'success')
        return f"Success: Permanently deleted {deleted_count} stale facts."
    except Exception as e:
        return f"Error deleting facts: {e}"

# ----------------------------------------
# --- SECTION 5: NETWORKING & OPSEC ---
# ----------------------------------------

@tool("VPN Control Tool")
def vpn_control_tool(action: str, user_id: int) -> str:
    """Controls the VPN sidecar container ('connect', 'disconnect', 'status')."""
    print(f"\n[Tool Call: vpn_control_tool] ACTION: {action}")
    try:
        client = docker.from_env()
        vpn_container = client.containers.get('archon-vpn')
        if action == 'connect': cmd = "protonvpn-cli connect -f"
        elif action == 'disconnect': cmd = "protonvpn-cli disconnect"
        elif action == 'status': cmd = "protonvpn-cli status"
        else: return "Error: Unknown VPN action."
        
        exit_code, output = vpn_container.exec_run(cmd)
        result = output.decode('utf-8')
        auth.log_activity(user_id, 'vpn_control', f"Action: {action}", 'success')
        return f"VPN {action} command executed. Result:\n{result}"
    except Exception as e:
        return f"Error controlling VPN container: {e}"

@tool("Execute via Proxy Tool")
def execute_via_proxy_tool(command_to_run: str, proxy_chain: list, user_id: int) -> str:
    """Executes a shell command *through* a specified proxy chain (Layering Tool)."""
    print(f"\n[Tool Call: execute_via_proxy_tool] CMD: {command_to_run}")
    config_path = f"/tmp/proxy_{uuid.uuid4()}.conf"
    config_content = "[ProxyList]\n" + "\n".join(proxy_chain)
    try:
        # We must write this *inside* the container, so /tmp is fine.
        with open(config_path, 'w') as f: f.write(config_content)
        full_cmd = f"proxychains4 -f {config_path} {command_to_run}"
        
        # We must use subprocess directly here, *not* secure_cli_tool,
        # as this command *is* the secure shell.
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            output = result.stdout
            status = 'success'
        else:
            output = result.stderr
            status = 'failure'
            
        auth.log_activity(user_id, 'proxy_exec', f"Chain: {proxy_chain} Cmd: {command_to_run}", status)
        return f"Command executed via proxy. Result:\n{output}"
    except Exception as e:
        return f"Error executing via proxy: {e}"
    finally:
        if os.path.exists(config_path): os.remove(config_path)

@tool("Network Interface Tool")
def network_interface_tool(action: str, interface: str = None, user_id: int = None) -> str:
    """Manages network interfaces on the host ('list', 'mac_randomize')."""
    print(f"\n[Tool Call: network_interface_tool] ACTION: {action}")
    # This tool calls the *worker* agent, as the host interfaces are there.
    if action == 'list': cmd = "nmcli device status"
    elif action == 'mac_randomize':
        if not interface: return "Error: 'mac_randomize' action requires an 'interface'."
        cmd = f"macchanger -r {interface}"
    else: return "Error: Unknown action."
    
    # We use secure_cli_tool to run this on the *worker*
    result = secure_cli_tool(cmd, user_id)
    auth.log_activity(user_id, 'net_interface_tool', f"Action: {action}", 'success')
    return f"Interface command '{action}' successful:\n{result}"

# ----------------------------------------
# --- SECTION 6: COMMS & BUSINESS ---
# ----------------------------------------

@tool("Comms Tool (Send SMS/Call)")
def comms_tool(to_number: str, message: str, is_call: bool = False, user_id: int = None) -> str:
    """Sends an SMS message or makes a voice call to a phone number."""
    print(f"\n[Tool Call: comms_tool] TO: {to_number} CALL: {is_call}")
    try:
        client = _get_twilio_client(user_id)
        from_number = _get_twilio_number(user_id)
        if is_call:
            twiml_message = f'<Response><Say>{message}</Say></Response>'
            client.calls.create(twiml=twiml_message, to=to_number, from_=from_number)
            action = "call_placed"
        else:
            client.messages.create(body=message, from_=from_number, to=to_number)
            action = "sms_sent"
        auth.log_activity(user_id, action, f"To: {to_number}", 'success')
        return f"Success: {action}."
    except Exception as e:
        return f"Error sending communication: {e}"

@tool("Read Emails Tool")
def read_emails_tool(email_service_name: str, folder: str = 'INBOX', criteria: str = 'UNSEEN', user_id: int = None) -> str:
    """Reads emails from a specified inbox."""
    print(f"\n[Tool Call: read_emails_tool] SERVICE: {email_service_name}")
    try:
        creds_json = get_secure_credential_tool(email_service_name, user_id)
        if 'Error' in creds_json: return creds_json
        creds = json.loads(creds_json)
        imap_server, _, _ = _get_email_servers(email_service_name)
        
        with IMAPClient(imap_server) as client:
            client.login(creds['username'], creds['password'])
            client.select_folder(folder, readonly=False)
            message_uids = client.search(criteria)
            if not message_uids: return "No new emails found."
            
            fetched_emails = []
            for uid, data in client.fetch(message_uids[-5:], ['ENVELOPE', 'BODY[TEXT]']).items():
                envelope = data[b'ENVELOPE']
                fetched_emails.append({
                    'uid': uid,
                    'from': f"{envelope.from_[0].name.decode('utf-8', 'ignore')} <{envelope.from_[0].mailbox.decode('utf-8', 'ignore')}@{envelope.from_[0].host.decode('utf-8', 'ignore')}>",
                    'subject': envelope.subject.decode('utf-8', 'ignore'),
                    'body': data[b'BODY[TEXT]'].decode('utf-8', 'ignore')[:500]
                })
        auth.log_activity(user_id, 'email_read', f"Read {len(fetched_emails)} emails", 'success')
        return json.dumps(fetched_emails)
    except Exception as e:
        return f"Error reading email: {e}"

@tool("Send Email Tool")
def send_email_tool(email_service_name: str, to_email: str, subject: str, body: str, user_id: int = None) -> str:
    """Sends an email."""
    print(f"\n[Tool Call: send_email_tool] TO: {to_email}")
    try:
        creds_json = get_secure_credential_tool(email_service_name, user_id)
        if 'Error' in creds_json: return creds_json
        creds = json.loads(creds_json)
        from_email, password = creds['username'], creds['password']
        _, smtp_server, smtp_port = _get_email_servers(email_service_name)

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg.set_content(body)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)
            
        auth.log_activity(user_id, 'email_send', f"Sent to {to_email}", 'success')
        return "Email sent successfully."
    except Exception as e:
        return f"Error sending email: {e}"

@tool("Desktop Notification Tool")
def desktop_notification_tool(title: str, message: str, user_id: int) -> str:
    """Sends a non-intrusive desktop notification to the user's GUI."""
    print(f"\n[Tool Call: desktop_notification_tool] TITLE: {title}")
    safe_title = title.replace("'", "\\'")
    safe_message = message.replace("'", "\\'")
    command = f"notify-send -a 'Archon' -i 'emblem-system' '{safe_title}' '{safe_message}'"
    result = _send_agent_request('cli', {'command': command})
    if 'error' in result or result.get('returncode') != 0:
        return f"Error sending notification: {result.get('stderr', 'Unknown')}"
    return "Notification sent successfully."

@tool("Notify Human for Help Tool")
def notify_human_for_help_tool(title: str, details: str, user_id: int) -> str:
    """Creates a 'Critical' priority task for a human user (e.g., for CAPTCHA)."""
    print(f"\n[Tool Call: notify_human_for_help_tool] TITLE: {title}")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (created_by_user_id, status, priority, title, details) VALUES (%s, %s, %s, %s, %s)",
                (user_id, 'blocked', 'Critical', title, details)
            )
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'notify_human', title, 'success')
        return "Success: Human user has been notified with a 'Critical' task."
    except Exception as e:
        return f"Error notifying human: {e}"


# ----------------------------------------
# --- SECTION 7: WEB BROWSER (SELENIUM) ---
# ----------------------------------------
class BrowserSession:
    """A stateful, persistent browser session for the agent."""
    def __init__(self):
        self.driver = None
        print("[BrowserTool] Session initialized.")

    def start_browser(self):
        global browser_session
        if self.driver:
            return "Browser is already running."
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # Route Selenium through Tor (via the Docker service 'tor-proxy')
            options.set_preference('network.proxy.type', 1)
            options.set_preference('network.proxy.socks', 'tor-proxy')
            options.set_preference('network.proxy.socks_port', 9050)
            options.set_preference('network.proxy.socks_remote_dns', True)
            
            service = Service(executable_path="/usr/local/bin/geckodriver")
            self.driver = webdriver.Firefox(service=service, options=options)
            browser_session = self
            return "Firefox browser started in headless, Tor-enabled mode."
        except Exception as e:
            return f"Error starting browser: {e}"

    def stop_browser(self):
        global browser_session
        if not self.driver:
            return "Browser is not running."
        try:
            self.driver.quit()
            self.driver = None
            browser_session = None
            return "Browser session stopped."
        except Exception as e:
            return f"Error stopping browser: {e}"

    def navigate(self, url: str):
        if not self.driver: return "Error: Browser not started."
        try:
            self.driver.get(url)
            return f"Navigated to {url}. Current page title: {self.driver.title}"
        except Exception as e: return f"Error navigating: {e}"

    def fill_form(self, selector: str, text: str):
        if not self.driver: return "Error: Browser not started."
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.clear(); element.send_keys(text)
            return f"Filled element '{selector}'."
        except Exception as e: return f"Error filling form: {e}"

    def click_element(self, selector: str):
        if not self.driver: return "Error: Browser not started."
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.click(); time.sleep(2) # Wait for page reaction
            return f"Clicked element '{selector}'."
        except Exception as e: return f"Error clicking element: {e}"

    def read_page(self):
        if not self.driver: return "Error: Browser not started."
        try:
            body = self.driver.find_element(By.TAG_NAME, 'body')
            return body.text[:4000] # Return first 4000 chars
        except Exception as e: return f"Error reading page: {e}"

@tool("Start Browser Tool")
def start_browser_tool(user_id: int) -> str:
    """Starts the persistent, headless, Tor-enabled Firefox browser session."""
    global browser_session
    if not browser_session:
        browser_session = BrowserSession()
    auth.log_activity(user_id, 'browser_start', 'Starting browser', 'success')
    return browser_session.start_browser()

@tool("Stop Browser Tool")
def stop_browser_tool(user_id: int) -> str:
    """Stops and closes the browser session."""
    global browser_session
    if not browser_session: return "Browser not running."
    auth.log_activity(user_id, 'browser_stop', 'Stopping browser', 'success')
    result = browser_session.stop_browser()
    browser_session = None # Ensure it's fully reset
    return result

@tool("Navigate URL Tool")
def navigate_url_tool(url: str, user_id: int) -> str:
    """Navigates the browser to a specific URL."""
    if not browser_session: return "Error: Browser not started. Use 'start_browser_tool' first."
    auth.log_activity(user_id, 'browser_navigate', f"Nav to {url}", 'success')
    return browser_session.navigate(url)

@tool("Fill Form Tool")
def fill_form_tool(selector: str, text: str, user_id: int) -> str:
    """Fills a form field with text, identified by a CSS selector."""
    if not browser_session: return "Error: Browser not started."
    auth.log_activity(user_id, 'browser_fill', f"Filling {selector}", 'success')
    return browser_session.fill_form(selector, text)

@tool("Click Element Tool")
def click_element_tool(selector: str, user_id: int) -> str:
    """Clicks a button or link, identified by a CSS selector."""
    if not browser_session: return "Error: Browser not started."
    auth.log_activity(user_id, 'browser_click', f"Clicking {selector}", 'success')
    return browser_session.click_element(selector)

@tool("Read Page Text Tool")
def read_page_text_tool(user_id: int) -> str:
    """Reads all visible text from the current webpage."""
    if not browser_session: return "Error: Browser not started."
    auth.log_activity(user_id, 'browser_read', 'Reading page text', 'success')
    return browser_session.read_page()


# ----------------------------------------
# --- SECTION 8: MEDIA SYNTHESIS ---
# ----------------------------------------

@tool("ComfyUI Image Tool")
def comfyui_image_tool(prompt: str, negative_prompt: str, output_path: str, user_id: int) -> str:
    """Generates an image using ComfyUI with a basic SDXL workflow."""
    print(f"\n[Tool Call: comfyui_image_tool] PROMPT: {prompt[:30]}...")
    
    # This is a minimal API workflow for SDXL (txt2img)
    # The agent's "Concept" agent will generate this in the future
    workflow = {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": int(time.time()), "steps": 25, "cfg": 7,
            "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0]
        }},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {
            "ckpt_name": "sd_xl_base_1.0.safetensors" # Assumes this model is in comfyui_models
        }},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {
            "filename_prefix": output_path, "images": ["8", 0], "output_dir": "/app/outputs/comfyui" # Use mounted dir
        }}
    }
    
    try:
        output = _queue_comfy_prompt(workflow)
        filename = output['images'][0]['filename']
        full_path = f"/app/outputs/comfyui/{filename}"
        
        auth.log_activity(user_id, 'image_gen_comfy', f"Prompt: {prompt}", 'success')
        return f"Success: Image generated and saved to {full_path}"
    except Exception as e:
        return f"Error running ComfyUI workflow: {e}"

@tool("Text-to-Speech Tool")
def text_to_speech_tool(text: str, output_path: str, user_id: int) -> str:
    """Generates speech from text using Coqui-TTS."""
    print(f"\n[Tool Call: text_to_speech_tool] TEXT: {text[:30]}...")
    try:
        response = requests.get(f"{COQUI_TTS_URL}/api/tts", params={'text': text}, timeout=120)
        response.raise_for_status()
        full_path = f"/app/outputs/coqui/{output_path}" # Use mounted dir
        with open(full_path, 'wb') as f: f.write(response.content)
        auth.log_activity(user_id, 'tts_gen', f"Text: {text[:30]}...", 'success')
        return f"Success: Audio file generated and saved to {full_path}"
    except Exception as e:
        return f"Error generating speech: {e}"

# ----------------------------------------
# --- SECTION 9: SECURITY & AUDITING ---
# ----------------------------------------

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
DB_PATH = "/app/offline_dbs"
EXPLOIT_DB_PATH = os.path.join(DB_PATH, "exploit-database")
CVE_LIST_PATH = os.path.join(DB_PATH, "cvelistV5")

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

# ----------------------------------------
# --- SECTION 10: SELF-IMPROVEMENT & INFRASTRUCTURE ---
# ----------------------------------------

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

@tool("Retrieve Audit Logs Tool")
def retrieve_audit_logs_tool(status_filter: str, days_ago: int, user_id: int) -> str:
    """Retrieves entries from the activity_logs table based on criteria."""
    print(f"\n[Tool Call: retrieve_audit_logs_tool] FILTER: {status_filter}")
    try:
        conn = db_manager.db_connect()
        threshold = datetime.now(timezone.utc) - timedelta(days=days_ago)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT log_id, timestamp, action_type, details FROM activity_logs WHERE status = %s AND timestamp > %s ORDER BY timestamp DESC LIMIT 20;",
                (status_filter, threshold)
            )
            results = cur.fetchall()
        conn.close()
        logs = [{'id': log_id, 'timestamp': str(ts), 'action': action, 'details': details} for log_id, ts, action, details in results]
        auth.log_activity(user_id, 'audit_log_retrieve', f"Retrieved {len(logs)} logs", 'success')
        return json.dumps(logs)
    except Exception as e:
        return f"Error retrieving logs: {e}"

# ----------------------------------------
# --- SECTION 11: CREDENTIALS (Internal) ---
# ----------------------------------------

@tool("Add Secure Credential Tool")
def add_secure_credential_tool(service_name: str, username: str, password: str, user_id: int) -> str:
    """
    Stores a new credential (like an email password or your phone number)
    securely in the encrypted database.
    """
    print(f"\n[Tool Call: add_secure_credential_tool] SERVICE: {service_name}")
    try:
        encrypted_data = db_manager.encrypt_credential(password)
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO credentials (owner_user_id, service_name, username, encrypted_password, encryption_nonce, encryption_tag) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, service_name, username, encrypted_data['encrypted_password'], encrypted_data['nonce'], encrypted_data['tag'])
            )
            conn.commit()
        conn.close()
        auth.log_activity(user_id, 'cred_add', f"Added credential for {service_name}", 'success')
        return f"Success: Credential for {service_name} stored securely."
    except Exception as e:
        return f"Error storing credential: {e}"

@tool("Get Secure Credential Tool")
def get_secure_credential_tool(service_name: str, user_id: int) -> str:
    """
    Retrieves a secure credential from the database.
    Returns a JSON string: {"username": "...", "password": "..."}
    """
    print(f"\n[Tool Call: get_secure_credential_tool] SERVICE: {service_name}")
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, encrypted_password, encryption_nonce, encryption_tag FROM credentials WHERE service_name = %s AND owner_user_id = %s ORDER BY credential_id DESC LIMIT 1;",
                (service_name, user_id)
            )
            result = cur.fetchone()
            conn.close()
            if not result:
                return f"Error: No credential found for '{service_name}'."
            
            username, enc_pass, nonce, tag = result
            password = db_manager.decrypt_credential(nonce, tag, enc_pass)
            if password is None:
                return "Error: Decryption failed! Master key may be incorrect."
            
            auth.log_activity(user_id, 'cred_get', f"Retrieved credential for {service_name}", 'success')
            return json.dumps({"username": username, "password": password})
    except Exception as e:
        return f"Error retrieving credential: {e}"

# ----------------------------------------
# --- SECTION 12: RESEARCH & ANALYSIS ---
# ----------------------------------------

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
        

# ----------------------------------------
# --- SECTION 13: USER ACCOUNT MANAGEMENT ---
# (for InternalAffairsCrew ONLY)
# ----------------------------------------
@tool("Auth Management Tool")
def auth_management_tool(action: str, username: str, user_id: int) -> str:
    """
    Manages user accounts. HIGHLY RESTRICTED.
    - action: The action to perform ('lock', 'unlock', 'delete').
    - username: The target username.
    - user_id: The *admin* user_id authorizing this.
    """
    print(f"\n[Tool Call: auth_management_tool] ACTION: {action} on USER: {username}")
    
    # This is a dangerous tool. Double-check the user is an admin.
    if auth.get_username_from_id(user_id) != 'william': # Or check privilege
        auth.log_activity(user_id, 'auth_tool_fail', f"Non-admin attempted to {action} {username}", 'failure')
        return "Error: This tool can only be run by the primary admin."

    conn = db_manager.db_connect()
    try:
        with conn.cursor() as cur:
            if action == 'lock':
                # Lock by setting password to an impossible hash
                impossible_hash = '$2b$12$THIS_IS_AN_IMPOSSIBLE_HASH_TO_PREVENT_LOGIN'
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE username = %s",
                    (impossible_hash, username)
                )
                msg = f"Account '{username}' has been successfully locked."
            elif action == 'unlock':
                # Unlock is complex; requires a password reset.
                # We will just log it and notify admin for now.
                auth.log_activity(user_id, 'auth_tool_unlock', f"Unlock requested for {username}", 'pending')
                return f"Unlock for '{username}' requires manual password reset. Admin notified."
            elif action == 'delete':
                cur.execute("DELETE FROM users WHERE username = %s", (username,))
                msg = f"Account '{username}' has been permanently deleted."
            else:
                return "Error: Unknown action. Use 'lock', 'unlock', or 'delete'."
            
            conn.commit()
        auth.log_activity(user_id, 'auth_tool_success', msg, 'success')
        return f"Success: {msg}"
        
    except Exception as e:
        conn.rollback()
        auth.log_activity(user_id, 'auth_tool_fail', str(e), 'failure')
        return f"Error managing account: {e}"
    finally:
        conn.close()
