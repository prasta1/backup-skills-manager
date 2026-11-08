#!/usr/bin/env python3
"""Simple Calendar API wrapper for cron jobs - Python 3.9 compatible."""

import json
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Suppress Python 3.9 EOL warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Add scripts to path
SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_PATH = Path.home() / '.hermes' / 'google_token.json'
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
]

# Default calendar for "busy things"
BUSY_THINGS_CAL_ID = 'fcnhb05jqcj16pktf3v4s1v1ss@group.calendar.google.com'


def get_credentials():
    """Load and refresh credentials from token file."""
    if not TOKEN_PATH.exists():
        print(json.dumps({"error": "Not authenticated", "message": "Run setup.py --auth-url first"}), file=sys.stderr)
        sys.exit(1)
    
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Update token file
        token_data = json.loads(TOKEN_PATH.read_text())
        token_data['access_token'] = creds.token
        token_data['expiry'] = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + 3600,
            tz=timezone.utc
        ).isoformat()
        TOKEN_PATH.write_text(json.dumps(token_data, indent=2))
    
    if not creds.valid:
        print(json.dumps({"error": "Token invalid", "message": "Re-run setup"}), file=sys.stderr)
        sys.exit(1)
    
    return creds

def list_events(**kwargs):
    """List calendar events."""
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
    
    now = datetime.now(timezone.utc)
    time_min = kwargs.get('start', now.isoformat())
    time_max = kwargs.get('end', (now + timedelta(days=30)).isoformat())
    
    # Use busy things calendar by default unless specified otherwise
    calendar_id = kwargs.get('calendar', BUSY_THINGS_CAL_ID)
    
    results = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=kwargs.get('max', 10),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = []
    for e in results.get('items', []):
        events.append({
            'id': e.get('id', ''),
            'summary': e.get('summary', '(no title)'),
            'start': e.get('start', {}).get('dateTime', e.get('start', {}).get('date', '')),
            'end': e.get('end', {}).get('dateTime', e.get('end', {}).get('date', '')),
            'location': e.get('location', ''),
            'description': e.get('description', ''),
            'status': e.get('status', ''),
            'calendar': calendar_id,
        })
    
    print(json.dumps(events, indent=2, ensure_ascii=False))

def list_calendars():
    """List all calendars the user has access to."""
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
    
    results = service.calendarList().list().execute()
    calendars = []
    
    for calendar in results.get('items', []):
        calendars.append({
            'id': calendar.get('id', ''),
            'summary': calendar.get('summary', '(no title)'),
            'primary': calendar.get('primary', False),
            'secondary': calendar.get('secondary', False),
        })
    
    print(json.dumps(calendars, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python simple_calendar.py [list|calendars] [options]", file=sys.stderr)
        print("  list [--max N] [--calendar ID] [--start DATE] [--end DATE]", file=sys.stderr)
        print("  calendars", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'calendars':
        list_calendars()
    elif command == 'list':
        # Parse args
        args = {}
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == '--max' and i + 1 < len(sys.argv):
                args['max'] = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == '--start' and i + 1 < len(sys.argv):
                args['start'] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--end' and i + 1 < len(sys.argv):
                args['end'] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--calendar' and i + 1 < len(sys.argv):
                args['calendar'] = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        
        list_events(**args)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)