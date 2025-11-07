# This is a PREVIEW of the new client code.
import requests

# The .onion address you just generated
AGENT_ONION_URL = "loremipsum123456789abcdefgvizx.onion"

# Tor's default SOCKS proxy port
proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'httpsG': 'socks5h://127.0.0.1:9050'
}

# The 'socks5h' prefix means "resolve the hostname (DNS)
# through the SOCKS proxy," which is required for .onion addresses.

def send_command_to_agent(command_string):
    target_url = f"http://{AGENT_ONION_URL}" # Note: It's port 80 now
    payload = {'command': command_string}
    
    try:
        response = requests.post(
            target_url,
            json=payload,
            proxies=proxies, # This is the new line
            timeout=60 # Tor can be slow
        )
        return response.json()
    except Exception as e:
        return {'error': str(e)}