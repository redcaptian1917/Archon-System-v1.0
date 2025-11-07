#!/usr/bin/env python3
# Archon Agent - Tool Helper Functions

import os
import json
import requests
import uuid
import websocket
from twilio.rest import Client
from gvm.connections import TLSConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeTransform
from ..core.credential_tools import get_secure_credential_tool

# --- Global Configuration ---
AGENT_ONION_URL = os.getenv("KALI_AGENT_URL", "your_kali_agent.onion")
HARDWARE_AGENT_ONION_URL = os.getenv("PI_AGENT_URL", "your_pi_hardware_agent.onion")
TOR_SOCKS_PROXY = os.getenv("TOR_PROXY_URL", 'socks5h://tor-proxy:9050')

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://comfyui:8188")
COQUI_TTS_URL = os.getenv("COQUI_TTS_URL", "http://coqui-tts:5002")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
GVM_HOST = os.getenv("GVM_HOST", "openvas")
GVM_PORT = int(os.getenv("GVM_PORT", 9390))

DB_PATH = "/app/offline_dbs"
EXPLOIT_DB_PATH = os.path.join(DB_PATH, "exploit-database")
CVE_LIST_PATH = os.path.join(DB_PATH, "cvelistV5")

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
    try:
        domain = service_name.split('@')[-1]
        return f'imap.{domain}', f'smtp.{domain}', 587
    except Exception:
        return 'imap.example.com', 'smtp.example.com', 587


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

    connection = TLSConnection(hostname=GVM_HOST, port=GVM_PORT) # Docker service name
    transform = EtreeTransform()
    gmp = Gmp(connection=connection, transform=transform)
    gmp.connect(creds['username'], creds['password'])
    return gmp
