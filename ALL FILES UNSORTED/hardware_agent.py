#!/usr/bin/env python3

import http.server
import socketserver
import json
import sys
import time

# --- Device Configuration ---
KEYBOARD_DEV = "/dev/hidg0"
MOUSE_DEV = "/dev/hidg1"
HOST = "127.0.0.1"  # Listen ONLY on localhost for Tor
PORT = 8081

# --- HID Keycode Map (Partial) ---
# This map translates characters to their raw USB HID keycodes.
# A full map is very large, but this covers basics.
KEY_CODES = {
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08, 'f': 0x09,
    'g': 0x0A, 'h': 0x0B, 'i': 0x0C, 'j': 0x0D, 'k': 0x0E, 'l': 0x0F,
    'm': 0x10, 'n': 0x11, 'o': 0x12, 'p': 0x13, 'q': 0x14, 'r': 0x15,
    's': 0x16, 't': 0x17, 'u': 0x18, 'v': 0x19, 'w': 0x1A, 'x': 0x1B,
    'y': 0x1C, 'z': 0x1D,
    '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21, '5': 0x22, '6': 0x23,
    '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,
    ' ': 0x2C,
    'ENTER': 0x28,
    'ESCAPE': 0x29,
    'BACKSPACE': 0x2A,
    'TAB': 0x2B,
    '-': 0x2D, '=': 0x2E, '[': 0x2F, ']': 0x30, '\\': 0x31,
    ';': 0x33, "'": 0x34, '`': 0x35, ',': 0x36, '.': 0x37, '/': 0x38,
    'F1': 0x3A, 'F2': 0x3B, 'F3': 0x3C, 'F4': 0x3D, 'F5': 0x3E, 'F6': 0x3F,
    'F7': 0x40, 'F8': 0x41, 'F9': 0x42, 'F10': 0x43, 'F11': 0x44, 'F12': 0x45,
    'CAPSLOCK': 0x39,
}

MOD_CODES = {
    'LCTRL': 0x01,
    'LSHIFT': 0x02,
    'LALT': 0x04,
    'LGUI': 0x08, # "Super" or "Windows" key
    'RCTRL': 0x10,
    'RSHIFT': 0x20,
    'RALT': 0x40,
    'RGUI': 0x80,
}

# --- HID Control Functions ---

def send_key(key, modifier=0x00):
    """Sends a single keystroke (press and release)."""
    # 8-byte report: [Mod] [0] [Key1] [Key2] [Key3] [Key4] [Key5] [Key6]
    buf = bytearray(8)
    buf[0] = modifier
    buf[2] = key
    
    try:
        with open(KEYBOARD_DEV, 'rb+') as kbd:
            # Send key press
            kbd.write(buf)
            # Send "key up" (all null bytes)
            kbd.write(bytearray(8))
    except Exception as e:
        print(f"[AGENT ERROR] Failed to write to keyboard: {e}", file=sys.stderr)

def send_mouse(button=0, x=0, y=0):
    """Sends a relative mouse movement."""
    # 4-byte report: [Button] [X] [Y] [Wheel]
    buf = bytearray(4)
    buf[0] = button
    
    # Convert x and y to signed 1-byte integers (-127 to 127)
    buf[1] = x.to_bytes(1, 'little', signed=True)[0]
    buf[2] = y.to_bytes(1, 'little', signed=True)[0]
    
    try:
        with open(MOUSE_DEV, 'rb+') as mouse:
            mouse.write(buf)
    except Exception as e:
        print(f"[AGENT ERROR] Failed to write to mouse: {e}", file=sys.stderr)

def type_string(text_to_type):
    """Types a full string, handling basic modifiers."""
    for char in text_to_type:
        key_code = 0x00
        mod_code = 0x00
        
        if char.isupper():
            mod_code = MOD_CODES['LSHIFT']
            key_code = KEY_CODES.get(char.lower())
        elif char in KEY_CODES:
            key_code = KEY_CODES.get(char)
        elif char == '\n':
            key_code = KEY_CODES.get('ENTER')
        else:
            print(f"[AGENT WARN] Unsupported char: {char}", file=sys.stderr)
            continue

        if key_code:
            send_key(key_code, mod_code)
            time.sleep(0.01) # Small delay

# --- HTTP Server ---

class HardwareControlHandler(http.server.BaseHTTPRequestHandler):
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            if self.path == '/type':
                text = data.get('text')
                if text:
                    print(f"[AGENT] Received TYPE: {text[:20]}...")
                    type_string(text)
                    self._send_response(200, {'status': 'success', 'message': f'Typed string.'})
                else:
                    self._send_response(400, {'error': 'No "text" provided.'})
            
            elif self.path == '/key':
                key = data.get('key', '').upper()
                mod = data.get('modifier', '').upper()
                
                key_code = KEY_CODES.get(key, 0x00)
                mod_code = MOD_CODES.get(mod, 0x00)
                
                if key_code:
                    print(f"[AGENT] Received KEY: {mod} + {key}")
                    send_key(key_code, mod_code)
                    self._send_response(200, {'status': 'success', 'message': f'Sent key {key}'})
                else:
                    self._send_response(400, {'error': f'Invalid key: {key}'})

            elif self.path == '/mouse_move':
                x = int(data.get('x', 0))
                y = int(data.get('y', 0))
                
                # Clamp values to -127 to 127
                x = max(-127, min(127, x))
                y = max(-127, min(127, y))
                
                print(f"[AGENT] Received MOUSE_MOVE: ({x}, {y})")
                send_mouse(button=0, x=x, y=y)
                self._send_response(200, {'status': 'success', 'message': f'Moved mouse ({x}, {y})'})
            
            else:
                self._send_response(404, {'error': 'Not Found'})

        except Exception as e:
            print(f"[AGENT ERROR] {e}", file=sys.stderr)
            self._send_response(500, {'error': str(e)})

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
        with socketserver.TCPServer((HOST, PORT), HardwareControlHandler) as httpd:
            print(f"--- FAPC Hardware Control Agent ---")
            print(f"Listening on http://{HOST}:{PORT}")
            print(f"Controlling Keyboard: {KEYBOARD_DEV}")
            print(f"Controlling Mouse:    {MOUSE_DEV}")
            print("Listening for commands over Tor... (Press Ctrl+C to stop)")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[AGENT] Shutting down.")
        sys.exit(0)
    except OSError as e:
        print(f"[AGENT FATAL] Could not bind to port {PORT}. {e}", file=sys.stderr)
    except FileNotFoundError:
        print(f"[AGENT FATAL] HID devices not found.", file=sys.stderr)
        print("            Is the hid-setup.sh service running?", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()