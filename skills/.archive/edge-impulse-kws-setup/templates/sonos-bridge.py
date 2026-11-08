# sonos_bridge.py

import asyncio
import time
from pysonos import SonosSpeaker

# Configuration
SONOS_IP = "192.168.1.100"  # Replace with your Sonos speaker IP
SONOS_ZONE = "Living Room"  # Replace with your zone name

# Keyword to action mapping
actions = {
    "play": lambda: sonos.play(),
    "pause": lambda: sonos.pause(),
    "jazz": lambda: sonos.set_uri("x-rincon-stream:0"),
    "classical": lambda: sonos.set_uri("x-rincon-stream:1"),
    "rock": lambda: sonos.set_uri("x-rincon-stream:2"),
    "news": lambda: sonos.set_uri("x-rincon-stream:3")
}

def handle_keyword(keyword):
    """
    Handle a keyword from the Thingy:53.
    """
    print(f"Received keyword: {keyword}")
    
    if keyword in actions:
        try:
            actions[keyword]()
            print(f"Executed action for '{keyword}'")
        except Exception as e:
            print(f"Error executing action for '{keyword}': {e}")
    else:
        print(f"Unknown keyword: {keyword}")

# Simulate BLE notification (replace with real BLE event handler)
def simulate_ble_event():
    """
    Simulates receiving a BLE event from Thingy:53.
    In practice, this would be replaced with actual BLE notification handling.
    """
    keywords = ["play", "pause", "jazz", "classical", "rock", "news"]
    
    for keyword in keywords:
        handle_keyword(keyword)
        time.sleep(2)  # Simulate delay between events

if __name__ == "__main__":
    # Initialize Sonos speaker
    sonos = SonosSpeaker(SONOS_IP)
    
    print("Sonos bridge initialized. Listening for keywords...")
    
    # For demonstration, simulate incoming BLE events
    simulate_ble_event()