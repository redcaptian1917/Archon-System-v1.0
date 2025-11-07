#!/usr/bin/env python3

import http.server
import socketserver
import json
import subprocess
import sys
import tempfile
import os
import base64

# New imports for Senses
import pyautogui
import cv2
import sounddevice as sd
import soundfile as sf
import numpy as np

# --- Configuration ---
HOST = "127.0.0.1"  # Listen ONLY on localhost (for Tor)
PORT = 8080
AUDIO_SAMPLE_RATE = 44100
AUDIO_DURATION = 5  # Default 5 seconds

class CommandHandler(http.server.BaseHTTPRequestHandler):
    """
    Handles CLI, GUI, and new Sensory commands.
    """
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            # Route based on the URL path
            if self.path == '/cli':
                self.handle_cli(data)
            elif self.path == '/click':
                self.handle_click(data)
            elif self.path == '/screenshot':
                self.handle_screenshot(data)
            elif self.path == '/webcam':
                self.handle_webcam(data)
            elif self.path == '/listen':
                self.handle_listen(data)
            else:
                self._send_response(404, {'error': 'Not Found'})

        except Exception as e:
            print(f"[AGENT] Error: {e}", file=sys.stderr)
            self._send_response(500, {'error': str(e)})

    # --- CLI / GUI Handlers (Unchanged) ---
    def handle_cli(self, data):
        command = data.get('command')
        if not command:
            return self._send_response(400, {'error': 'No command provided.'})
        print(f"[AGENT] Received CLI: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        self._send_response(200, {'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode})

    def handle_click(self, data):
        x, y = data.get('x'), data.get('y')
        if x is None or y is None:
            return self._send_response(400, {'error': 'X and Y coordinates required.'})
        print(f"[AGENT] Received CLICK: ({x}, {y})")
        pyautogui.click(x=int(x), y=int(y))
        self._send_response(200, {'status': 'success', 'message': f'Clicked at ({x}, {y})'})

    def handle_screenshot(self, data):
        print(f"[AGENT] Received SCREENSHOT request.")
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            pyautogui.screenshot(tmp_file.name); tmp_file_path = tmp_file.name
        with open(tmp_file_path, 'rb') as f: image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        os.remove(tmp_file_path)
        self._send_response(200, {'status': 'success', 'image_base64': image_base64})

    # --- NEW SENSORY HANDLERS ---
    
    def handle_webcam(self, data):
        """Captures an image from the default webcam."""
        print(f"[AGENT] Received WEBCAM request.")
        try:
            # 0 is the default webcam
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return self._send_response(500, {'error': 'Could not open webcam.'})
            
            ret, frame = cap.read()
            cap.release() # Release camera immediately
            
            if not ret:
                return self._send_response(500, {'error': 'Could not capture frame.'})
            
            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            self._send_response(200, {'status': 'success', 'image_base64': img_base64})
            
        except Exception as e:
            self._send_response(500, {'error': f'Webcam Error: {e}'})

    def handle_listen(self, data):
        """Records audio from the default microphone."""
        print(f"[AGENT] Received LISTEN request.")
        try:
            fs = AUDIO_SAMPLE_RATE
            duration = data.get('duration', AUDIO_DURATION)
            
            print(f"[AGENT] Recording for {duration} seconds...")
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
            sd.wait()  # Wait for recording to complete
            print("[AGENT] Recording complete.")

            # Save to a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                sf.write(tmp_file.name, recording, fs)
                tmp_file_path = tmp_file.name
            
            # Read bytes and encode
            with open(tmp_file_path, 'rb') as f:
                audio_bytes = f.read()
            
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            os.remove(tmp_file_path)
            
            self._send_response(200, {'status': 'success', 'audio_base64': audio_base64})

        except Exception as e:
            self._send_response(500, {'error': f'Microphone Error: {e}'})

    # --- Helper Functions ---
    def _send_response(self, http_code, data):
        self.send_response(http_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response_bytes = json.dumps(data).encode('utf-8')
        self.wfile.write(response_bytes)

    def log_message(self, format, *args):
        return # Silence logs

def main():
    try:
        with socketserver.TCPServer((HOST, PORT), CommandHandler) as httpd:
            print(f"--- FAPC Local Device Agent (v3 - Senses) ---")
            print(f"Listening on http://{HOST}:{PORT}")
            print(f"Endpoints: /cli, /click, /screenshot, /webcam, /listen")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[AGENT] Shutting down.")
    except Exception as e:
        print(f"[AGENT FATAL] {e}", file=sys.stderr)

if __name__ == "__main__":
    main()