# Amplitude API Setup

## Getting Your API Credentials
1. Log into Amplitude → Settings → Projects
2. Find your project → API Key and Secret Key
3. For exports: use the Export API (requires Secret Key)

## Environment Setup
```bash
```text
AMPLITUDE_API_KEY=...
AMPLITUDE_SECRET_KEY=...
AMPLITUDE_PROJECT_ID=...
```

## Quick Test Script
```python
import os
import requests
from datetime import datetime, timedelta

api_key = os.getenv('AMPLITUDE_API_KEY')
secret_key = os.getenv('AMPLITUDE_SECRET_KEY')

# Test connection
url = f"https://amplitude.com/api/2/export?start={datetime.now() - timedelta(days=1)}"
response = requests.get(url, auth=(api_key, secret_key))

if response.status_code == 200:
    print("✅ Amplitude API connected successfully")
    print(f"Got {len(response.text)} bytes of event data")
else:
    print(f"❌ API error: {response.status_code}")
```

## Common Endpoints
- `/export` - Raw event data (last 365 days)
- `/users` - User metadata and properties  
- `/cohorts` - Defined cohorts
- `/segments` - Segmented analysis

## Data Format Expectations
- Events include: user_id, event_type, timestamp, event_properties
- Time in UTC milliseconds
- JSON lines format (not array)