#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - LOCAL DEVICE AGENT (vFINAL)
#
# This is the "Software Worker" agent. It runs on the target
# machine (e.g., your Kali desktop or an 'Archon-Ops' server).
#
# It is a lightweight, secure web server that listens *only* on
# localhost. It receives commands from the 'Archon-Prime' server
# via its dedicated Tor Hidden Service.
#
# It provides the "hands" and "senses" for the main agent.
# -----------------------------------------------------------------

import http.server
import socketserver
import json
import subprocess
import sys
import tempfile
import os
import base64

# --- Import Worker-Side Dependencies ---
# These must be installed on the worker machine:
# pip install pyautogui opencv-python sounddevice soundfile numpy
import pyautogui
import cv2
import sounddevice as sd
import soundfile as sf
import numpy as np

# --- Configuration ---
HOST = "127.0.0.1"  # Listen ONLY on localhost (for Tor)
PORT = 8080       # The port Tor will forward to
AUDIO_SAMPLE_RATE = 44100
AUDIO_DURATION = 5  # Default 5 seconds

class CommandHandler(http.server.BaseHTTPRequestHandler):
    """
    Handles all incoming commands from the Archon-Prime server.
    Routes requests to the correct handler based on the URL path.
    """
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            # --- API Endpoint Router ---
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
                self._send_response(404, {'error': 'Not Found', 'message': f'Unknown endpoint: {self.path}'})

        except json.JSONDecodeError:
            self._send_response(400, {'error': 'Invalid JSON body.'})
        except Exception as e:
            print(f"[AGENT] Unhandled Error: {e}", file=sys.stderr)
            self._send_response(500, {'error': str(e)})

    # --- 1. CLI Handler ---
    def handle_cli(self, data):
        """Executes a shell command."""
        command = data.get('command')
        if not command:
            return self._send_response(400, {'error': 'No "command" provided.'})

        print(f"[AGENT] Received CLI: {command[:50]}...")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30 # 30-second timeout
            )
            response_data = {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            self._send_response(200, response_data)
        except subprocess.TimeoutExpired:
            self._send_response(500, {'error': 'Command timed out after 30 seconds.'})
        except Exception as e:
            self._send_response(500, {'error': f'Command execution failed: {e}'})

    # --- 2. GUI Click Handler ---
    def handle_click(self, data):
        """Clicks at a specific X, Y coordinate."""
        x = data.get('x')
        y = data.get('y')
        if x is None or y is None:
            return self._send_response(400, {'error': 'X and Y coordinates required.'})

        print(f"[AGENT] Received CLICK: ({x}, {y})")
        try:
            pyautogui.click(x=int(x), y=int(y))
            self._send_response(200, {'status': 'success', 'message': f'Clicked at ({x}, {y})'})
        except Exception as e:
            self._send_response(500, {'error': f'GUI Error: {e}'})

    # --- 3. GUI Screenshot Handler ---
    def handle_screenshot(self, data):
        """Takes a screenshot and returns it as a Base64 string."""
        print(f"[AGENT] Received SCREENSHOT request.")
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                pyautogui.screenshot(tmp_file.name)
                tmp_file_path = tmp_file.name
            
            with open(tmp_file_path, 'rb') as f:
                image_bytes = f.read()
            
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            os.remove(tmp_file_path)
            
            self._send_response(200, {'status': 'success', 'image_base64': image_base64})
        except Exception as e:
            self._send_response(500, {'error': f'Screenshot Error: {e}'})

    # --- 4. Senses: Webcam Handler ---
    def handle_webcam(self, data):
        """Captures an image from the default webcam."""
        print(f"[AGENT] Received WEBCAM request.")
        try:
            # 0 is the default webcam
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return self._send_response(500, {'error': 'Could not open webcam. Is it connected?'})
            
            # Allow camera to auto-adjust
            time.sleep(0.5) 
            
            ret, frame = cap.read()
            cap.release() # Release camera immediately
            
            if not ret:
                return self._send_response(500, {'error': 'Could not capture frame.'})
            
            # Encode frame as JPEG for smaller size
            _, buffer = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            self._send_response(200, {'status': 'success', 'image_base64': img_base64})
            
        except Exception as e:
            self._send_response(500, {'error': f'Webcam Error: {e}'})

    # --- 5. Senses: Microphone Handler ---
    def handle_listen(self, data):
        """Records audio from the default microphone."""
        print(f"[AGENT] Received LISTEN request.")
        try:
            fs = AUDIO_SAMPLE_RATE
            duration = int(data.get('duration', AUDIO_DURATION))
            
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

    # --- Helper: Send Response ---
    def _send_response(self, http_code, data):
        """Helper function to send a JSON response."""
        self.send_response(http_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response_bytes = json.dumps(data).encode('utf-8')
        self.wfile.write(response_bytes)

    # Silence the default HTTP server logs for cleanliness
    def log_message(self, format, *args):
        return

def main():
    try:
        with socketserver.TCPServer((HOST, PORT), CommandHandler) as httpd:
            print(f"--- FAPC Local Device Agent (vFINAL) ---")
            print(f"SECURITY: Listening ONLY on http://{HOST}:{PORT}")
            print(f"STATUS: Ready for commands via Tor Hidden Service.")
            print(f"Endpoints: /cli, /click, /screenshot, /webcam, /listen")
            print("(Press Ctrl+C to stop)")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[AGENT] Shutdown signal received.")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"[AGENT FATAL] Port {PORT} is already in use. Is another agent running?", file=sys.stderr)
        else:
            print(f"[AGENT FATAL] OSError: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[AGENT FATAL] An unknown error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
