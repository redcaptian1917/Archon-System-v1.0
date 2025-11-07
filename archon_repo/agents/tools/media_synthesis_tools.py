#!/usr/bin/env python3
# Archon Agent - Media Synthesis Tools

import json
import os
import requests
import uuid
import websocket
from crewai_tools import tool
from ..core import auth
from .helpers import COMFYUI_URL, COQUI_TTS_URL, _queue_comfy_prompt

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
