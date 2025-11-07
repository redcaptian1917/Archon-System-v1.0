#!/usr/bin/env python3

import json
import auth
import whisper  # New import
import os
from crewai_tools import tool

# --- Import all v15 tools ---
from fapc_tools_v15 import (
    secure_cli_tool, click_screen_tool, take_screenshot_tool,
    analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
    start_browser_tool, stop_browser_tool, navigate_url_tool,
    fill_form_tool, click_element_tool, read_page_text_tool,
    add_secure_credential_tool, get_secure_credential_tool,
    notify_human_for_help_tool, generate_image_tool, python_repl_tool,
    learn_fact_tool, recall_facts_tool, desktop_notification_tool,
    hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
    read_emails_tool, send_email_tool,
    webcam_tool, listen_tool
)
_ = (secure_cli_tool, click_screen_tool, take_screenshot_tool,
     analyze_screenshot_tool, delegate_to_crew, defensive_nmap_tool,
     start_browser_tool, stop_browser_tool, navigate_url_tool,
     fill_form_tool, click_element_tool, read_page_text_tool,
     add_secure_credential_tool, get_secure_credential_tool,
     notify_human_for_help_tool, generate_image_tool, python_repl_tool,
     learn_fact_tool, recall_facts_tool, desktop_notification_tool,
     hardware_type_tool, hardware_key_tool, hardware_mouse_move_tool,
     read_emails_tool, send_email_tool, webcam_tool, listen_tool)
# ---

# --- NEW TOOL: Transcribe Audio (Hearing Brain) ---
# Load the model once when the script is loaded.
# 'base.en' is small, fast, and good for English.
# Use 'medium.en' for higher accuracy if you have the VRAM.
try:
    WHISPER_MODEL = whisper.load_model("base.en")
    print("[TranscribeTool] Whisper 'base.en' model loaded successfully.")
except Exception as e:
    print(f"[TranscribeTool ERROR] Could not load Whisper model: {e}")
    WHISPER_MODEL = None

@tool("Transcribe Audio Tool")
def transcribe_audio_tool(audio_path: str, user_id: int) -> str:
    """
    Transcribes an audio file (.wav, .mp3) into text using Whisper.
    - audio_path: The local path to the audio file (e.g., 'recording.wav').
    - user_id: The user_id for logging.
    Returns the transcribed text.
    """
    print(f"\n[Tool Call: transcribe_audio_tool] FILE: {audio_path}")
    
    if WHISPER_MODEL is None:
        return "Error: Whisper model is not loaded."
    if not os.path.exists(audio_path):
        return f"Error: Audio file not found at {audio_path}"
        
    try:
        # Transcribe the audio
        result = WHISPER_MODEL.transcribe(audio_path, fp16=False)
        transcribed_text = result["text"]
        
        if not transcribed_text:
            return "No speech detected."
        
        auth.log_activity(user_id, 'transcribe_success', f"Transcribed {audio_path}", 'success')
        return f"Transcribed text: {transcribed_text}"
        
    except Exception as e:
        auth.log_activity(user_id, 'transcribe_fail', str(e), 'failure')
        return f"Error during transcription: {e}"