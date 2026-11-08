---
name: edge-impulse-kws-setup
description: Set up an Edge Impulse keyword spotting project for Nordic Thingy:53 with Sonos control.
category: mlops
---

# Edge Impulse Keyword Spotting Setup

This skill guides users through setting up a complete keyword spotting pipeline on Edge Impulse for Nordic Thingy:53 to control Sonos speakers.

## Target Setup

- Device: Nordic Thingy:53 (PDM microphones)
- Audio Pipeline: MFCC/Spectral features for keyword spotting
- Target: Sonos household speakers via local API/HA

## Prerequisites

1. Edge Impulse project with API key and project ID
2. Sonos API access (local HA or web API)
3. Mac Studio with Python 3.9+ and `requests` installed

## Workflow Overview

1. **Project Setup** - Create a new impulse with audio input, MFCC DSP, and KWS classifier
2. **Data Collection** - Stream labeled audio from Thingy:53 to Edge Impulse
3. **Training & Deployment** - Train model and deploy to device
4. **Sonos Bridge** - Set up local Python service to handle BLE triggers

## Implementation Notes

### Block IDs and Types

When setting up an impulse via API, block IDs must be unique integers > 0. The API requires specific block types:
- Input: time-series (for PDM microphones)
- DSP: mfcc or spectral-analysis (for audio features)
- Learn: keras-transfer-kws (for keyword spotting)
- Post-processing: optional

### Project State

If project is new (no samples, no versions), start with clean impulse creation.
If project has samples or versions, consider updating existing impulse.

### Edge Impulse API

Use the Studio API (`https://studio.edgeimpulse.com/v1`) for:
- Project metadata
- Impulse definition (create/update)
- Raw data management
- Training jobs and deployment

Use the Ingestion API (`https://ingestion.edgeimpulse.com`) for:
- Data upload (raw audio samples)

### Sample Upload Format

Edge Impulse expects audio samples in WAV format, with JSON metadata:
```json
{
  "protected": { "ver": "v1", "alg": "none", "iat": 1735689600 },
  "signature": "empty",
  "payload": {
    "device_name": "Thingy:53",
    "device_type": "PDM",
    "interval_ms": 10,
    "sensors": [{ "name": "accX", "units": "m/s2" }],
    "values": [[0.1], [0.2]]
  }
}
```

### Training & Deployment

Training jobs are asynchronous. Poll the job status until `.job.finished` is true.
Deployment builds a C++ library or Arduino sketch that can run on the Thingy:53.

## Sonos Integration

1. Set up local Python bridge (e.g., using `python-sonos` or `pysonos`)
2. Map keywords to actions (play, pause, genre)
3. Use BLE notifications to trigger the Python handler
4. Handle Sonos API authentication (e.g., local HA or web tokens)

## User Preferences

- Use concise, direct responses without fluff
- Prefer prose over bullet lists
- Values accuracy over agreeableness

## Troubleshooting

1. If API calls fail, check:
   - API key validity (start with `ei_`)
   - Project ID is numeric
   - Network access to Edge Impulse endpoints

2. For block type mismatches:
   - Fetch OpenAPI spec: `https://studio.edgeimpulse.com/openapi.yml`
   - Search for `InputBlockType`, `DspBlockType`, `LearnBlockType` enum values

3. For training job failures:
   - Check `/api/{projectId}/jobs/{jobId}/stdout/download` for error logs
   - Verify sample labels and training data format

## Example Usage

```bash
# Set credentials
export EI_API_KEY="ei_..."
export EI_PROJECT_ID="123456"

# Create impulse for KWS pipeline
python3 -c "
import requests, json

API_KEY = 'ei_...'
PROJECT_ID = 123456
STUDIO = 'https://studio.edgeimpulse.com/v1/api'
HEADERS = {'x-api-key': API_KEY, 'Accept': 'application/json'}

# Create new impulse (empty)
impulse = {
  'inputBlocks': [
    {'id': 1, 'type': 'time-series', 'name': 'Time series', 'title': 'Time series', 'axes': ['accX']},
  ],
  'dspBlocks': [
    {'id': 2, 'type': 'mfcc', 'name': 'MFCC features', 'title': 'MFCC Features', 'axes': ['accX'], 'implementationVersion': 1},
  ],
  'learnBlocks': [
    {'id': 3, 'type': 'keras-transfer-kws', 'name': 'KWS Classifier', 'title': 'Keyword Spotting Classifier', 'dsp': [2], 'implementationVersion': 1},
  ]
}

r = requests.post(f'{STUDIO}/{PROJECT_ID}/impulse', headers=HEADERS, json=impulse)
print(r.json())
"
```

## Reference Files

- `references/edge-impulse-kws-setup.md` - Detailed project setup walkthrough
- `scripts/ei-kws-config.py` - Configures initial impulse structure for KWS projects
- `templates/sonos-bridge.py` - Example Python bridge script for Sonos control

## Future Improvements

1. Add support for multi-device project templates
2. Include automatic Sonos API token discovery and setup
3. Add integration with Edge Impulse Studio UI for interactive setup
4. Expand to support other speaker platforms (Apple TV, Chromecast)