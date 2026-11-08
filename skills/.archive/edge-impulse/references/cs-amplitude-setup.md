# Edge Impulse Analytics Setup

## Environment Configuration

Load these from environment variables:

```text
AMPLITUDE_API_KEY=...
AMPLITUDE_SECRET_KEY=...
AMPLITUDE_PROJECT_ID=...
```

## Event Discovery (REQUIRED before any queries)

Amplitude events are project-specific. Never guess an event name.

```python
import requests, os

API_KEY = os.getenv('AMPLITUDE_API_KEY')
SECRET_KEY = os.getenv('AMPLITUDE_SECRET_KEY')

# Discover available events
url = "https://amplitude.com/api/2/events"
response = requests.get(url, auth=(API_KEY, SECRET_KEY))
events = response.json()
```

## Trinity Events to Look For

Based on SOUL.md, we need to validate these event types exist:
- **Data Ingestion**: Look for upload/transfer/insert events
- **Model Training**: Look for training/impulse/learn events
- **Deployment**: Look for deploy/deployment/target events

## API Quick Reference

| Endpoint | Purpose |
|----------|---------|
| `/api/2/events` | List available event types |
| `/api/2/export` | Raw event data (last 365 days) |
| `/api/2/users` | User metadata and properties |

Time format: Unix milliseconds or YYYYMMDDTHH format for start/end parameters.