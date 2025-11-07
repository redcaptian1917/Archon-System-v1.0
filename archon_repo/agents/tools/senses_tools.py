#!/usr/bin/env python3
# Archon Agent - Senses & Reasoning Tools

import os
import base64
import ollama
from crewai_tools import tool
import whisper
from ..core import auth
from .helpers import _send_agent_request

WHISPER_MODEL = None
if WHISPER_MODEL is None:
    try:
        WHISPER_MODEL = whisper.load_model("base.en")
        print("[WhisperTool] Whisper 'base.en' model loaded successfully.")
    except Exception as e:
        print(f"[WhisperTool ERROR] Could not load model: {e}", file=sys.stderr)
        WHISPER_MODEL = None

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

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
        result = WHISPER_MODEL.transcribe(audio_path, fp16=False) # fp16=False for CPU
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
