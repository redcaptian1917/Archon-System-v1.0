#!/usr/bin/env python3

import http.server
import socketserver
import json
import subprocess
import sys
import pyautogui # New import
import tempfile  # New import
import os        # New import
import base64    # New import

# --- Configuration ---
HOST = '127.0.0.1' # Listen ONLY on localhost (for Tor)
PORT = 8080

class CommandHandler(http.server.BaseHTTPRequestHandler):
    """
Handles CLI, Click, and Screenshot commands.
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
            else:
                self._send_response(404, {'error': 'Not Found'})

        except Exception as e:
            print(f"[AGENT] Error: {e}", file=sys.stderr)
            self._send_response(500, {'error': str(e)})

    def handle_cli(self, data):
        """Executes a shell command."""
        command = data.get('command')
        if not command:
            return self._send_response(400, {'error': 'No command provided.'})

        print(f"[AGENT] Received CLI: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)

        response_data = {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
        self._send_response(200, response_data)

    def handle_click(self, data):
        """Clicks at a specific X, Y coordinate."""
        x = data.get('x')
        y = data.get('y')
        if x is None or y is None:
            return self._send_response(400, {'error': 'X and Y coordinates required.'})

        print(f"[AGENT] Received CLICK: ({x}, {y})")
        try:
            # Move and click
            pyautogui.click(x=int(x), y=int(y))
            self._send_response(200, {'status': 'success', 'message': f'Clicked at ({x}, {y})'})
        except Exception as e:
            self._send_response(500, {'error': f'GUI Error: {e}'})

    def handle_screenshot(self, data):
        """Takes a screenshot and returns it as a Base64 string."""
        print(f"[AGENT] Received SCREENSHOT request.")
        try:
            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                pyautogui.screenshot(tmp_file.name)
                tmp_file_path = tmp_file.name

            # Read the file's bytes
            with open(tmp_file_path, 'rb') as f:
                image_bytes = f.read()

            # Encode bytes as Base64 string
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Clean up the temp file
            os.remove(tmp_file_path)

            self._send_response(200, {'status': 'success', 'image_base64': image_base64})

        except Exception as e:
            self._send_response(500, {'error': f'Screenshot Error: {e}'})

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
            print(f"--- FAPC Local Device Agent (v2) ---")
            print(f"Listening on http://{HOST}:{PORT}")
            print("Endpoints: /cli, /click, /screenshot")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[AGENT] Shutting down.")

if __name__ == "__main__":
    main()