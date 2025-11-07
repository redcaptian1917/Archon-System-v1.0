#!/usr/bin/env python3

import json
import auth
import db_manager
import ollama
import psycopg2
import os
import requests
import uuid
import websocket # New import for ComfyUI
import time
from crewai_tools import tool
from pgvector.psycopg2 import register_vector
import git

# --- Import all v21 tools ---
from fapc_tools_v21 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool,
    learn_fact_tool, recall_facts_tool, desktop_notification_tool,
    hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
    read_emails_tool, send_email_tool,
    metadata_scrubber_tool, os_hardening_tool, git_tool,
    get_stale_facts_tool, summarize_facts_tool, delete_facts_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool,
     add_secure_credential_tool, get_secure_credential_tool,
     notify_human_for_help_tool, generate_image_tool, python_repl_tool,
     learn_fact_tool, recall_facts_tool, desktop_notification_tool,
     hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
     read_emails_tool, send_email_tool, metadata_scrubber_tool, os_hardening_tool, git_tool,
     get_stale_facts_tool, summarize_facts_tool, delete_facts_tool)
# ---

# --- Media Service Endpoints ---
COMFYUI_URL = "http://comfyui:8188"
COQUI_TTS_URL = "http://coqui-tts:5002"
OUTPUT_DIR = "/app/outputs/comfyui" # This is the mounted volume

# --- NEW TOOL 1: ComfyUI (Image/Video) ---
# This is a helper function, not a tool
def _queue_comfy_prompt(prompt_workflow: dict) -> dict:
    """Sends a workflow to the ComfyUI API."""
    client_id = str(uuid.uuid4())
    
    # 1. Send the workflow
    post_data = json.dumps({'prompt': prompt_workflow, 'client_id': client_id}).encode('utf-8')
    req = requests.post(f"{COMFYUI_URL}/prompt", data=post_data)
    req.raise_for_status()
    prompt_id = req.json()['prompt_id']
    
    # 2. Listen on WebSocket for the result
    ws_url = f"ws://{COMFYUI_URL.split('//')[1]}/ws?clientId={client_id}"
    ws = websocket.create_connection(ws_url)
    
    try:
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executed' and message['data']['prompt_id'] == prompt_id:
                    # We're done
                    return message['data']['output']
            else:
                continue # It's a binary preview, ignore
    finally:
        ws.close()

@tool("ComfyUI Image Tool")
def comfyui_image_tool(prompt: str, negative_prompt: str, output_path: str, user_id: int) -> str:
    """
    Generates an image using ComfyUI with a basic SDXL workflow.
    - prompt: The positive prompt.
    - negative_prompt: The negative prompt.
    - output_path: The *filename* to save in the output dir (e.g., 'logo.png').
    - user_id: The user_id for logging.
    """
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
            "filename_prefix": output_path, "images": ["8", 0], "output_dir": "comfyui_outputs"
        }}
    }
    
    try:
        output = _queue_comfy_prompt(workflow)
        filename = output['images'][0]['filename']
        full_path = f"/app/outputs/comfyui/{filename}"
        
        auth.log_activity(user_id, 'image_gen_comfy', f"Prompt: {prompt}", 'success')
        return f"Success: Image generated and saved to {full_path}"
    except Exception as e:
        auth.log_activity(user_id, 'image_gen_comfy', f"Prompt: {prompt}", str(e))
        return f"Error running ComfyUI workflow: {e}"

# --- NEW TOOL 2: Text-to-Speech (Coqui) ---
@tool("Text-to-Speech Tool")
def text_to_speech_tool(text: str, output_path: str, user_id: int) -> str:
    """
    Generates speech from text using Coqui-TTS.
    - text: The text to synthesize.
    - output_path: The *filename* to save in the output dir (e.g., 'voiceover.wav').
    - user_id: The user_id for logging.
    """
    print(f"\n[Tool Call: text_to_speech_tool] TEXT: {text[:30]}...")
    
    try:
        response = requests.get(
            f"{COQUI_TTS_URL}/api/tts",
            params={'text': text},
            timeout=120
        )
        response.raise_for_status()
        
        # Save the audio file
        full_path = f"/app/outputs/coqui/{output_path}"
        with open(full_path, 'wb') as f:
            f.write(response.content)
            
        auth.log_activity(user_id, 'tts_gen', f"Text: {text[:30]}...", 'success')
        return f"Success: Audio file generated and saved to {full_path}"
        
    except Exception as e:
        auth.log_activity(user_id, 'tts_gen', f"Text: {text[:30]}...", str(e))
        return f"Error generating speech: {e}"

# NOTE: A 'StableVideoDiffusionTool' and 'MusicGenTool' would be added
# here, but they require much more complex workflows. We'll add them
# as a future upgrade, starting with this foundation.