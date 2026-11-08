#!/usr/bin/env python3
"""
Amplitude Discovery Script for Edge Impulse
Discovers event names and validates connection before querying
"""
import os
import requests
import json
from datetime import datetime, timedelta

API_KEY = os.getenv('AMPLITUDE_API_KEY')
SECRET_KEY = os.getenv('AMPLITUDE_SECRET_KEY')
PROJECT_ID = os.getenv('AMPLITUDE_PROJECT_ID')

def discover_events():
    """Discover available event types in the project"""
    url = "https://amplitude.com/api/2/events"
    try:
        response = requests.get(url, auth=(API_KEY, SECRET_KEY), timeout=30)
        if response.status_code == 200:
            events = response.json()
            print("✅ Amplitude connected successfully")
            print(f"\nEvent types discovered ({len(events)} total):")
            for event in events[:30]:  # Show first 30
                print(f"  - {event.get('event_type', 'unknown')}")
            if len(events) > 30:
                print(f"  ... and {len(events) - 30} more")
            return events
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Connection failed: {e}")

def validate_connection():
    """Basic connection test"""
    # Try a small export window
    start = (datetime.now() - timedelta(days=1)).strftime('%Y%m%dT%H')
    end = datetime.now().strftime('%Y%m%dT%H')
    
    url = f"https://amplitude.com/api/2/export?start={start}&end={end}"
    try:
        response = requests.get(url, auth=(API_KEY, SECRET_KEY), timeout=30)
        if response.status_code == 200:
            print(f"✅ Export API works - got {len(response.text)} bytes")
        else:
            print(f"⚠️ Export returned {response.status_code}")
    except Exception as e:
        print(f"❌ Export test failed: {e}")

if __name__ == "__main__":
    print("=== Amplitude Edge Impulse Setup ===")
    print(f"Project ID: {PROJECT_ID or 'NOT SET'}")
    
    if not API_KEY or not SECRET_KEY:
        print("\n❌ Set AMPLITUDE_API_KEY and AMPLITUDE_SECRET_KEY in environment")
        exit(1)
    
    discover_events()
    validate_connection()