# Edge Impulse KWS Setup Walkthrough

This document walks through setting up a complete keyword spotting pipeline on Edge Impulse for Nordic Thingy:53 to control Sonos speakers.

## Step 1: Project Preparation

Start with a clean Edge Impulse project. The project should be empty (no training/testing samples, no versions) to avoid conflicts with the initial impulse setup.

```bash
# Verify project is empty
curl -H "x-api-key: ei_61b005e13e7443fa17d062d34dde59e29ef382d69ffe0817" \
  https://studio.edgeimpulse.com/v1/api/1065371/raw-data?category=training&limit=1
```

## Step 2: Create Impulse Pipeline

Use the Edge Impulse Studio API to create a new impulse with:
- Input: time-series (for PDM microphones)
- DSP: mfcc (to extract audio features)
- Learn: keras-transfer-kws (for keyword classification)

```python
import requests, json

API_KEY = "ei_61b005e13e7443fa17d062d34dde59e29ef382d69ffe0817"
PROJECT_ID = 1065371
STUDIO = "https://studio.edgeimpulse.com/v1/api"
HEADERS = {"x-api-key": API_KEY, "Accept": "application/json"}

# Create new impulse
impulse = {
  "inputBlocks": [
    {
      "id": 1,
      "type": "time-series",
      "name": "Time series",
      "title": "Time series",
      "axes": ["accX"]
    }
  ],
  "dspBlocks": [
    {
      "id": 2,
      "type": "mfcc",
      "name": "MFCC features",
      "title": "MFCC Features",
      "axes": ["accX"],
      "implementationVersion": 1
    }
  ],
  "learnBlocks": [
    {
      "id": 3,
      "type": "keras-transfer-kws",
      "name": "KWS Classifier",
      "title": "Keyword Spotting Classifier",
      "dsp": [2],
      "implementationVersion": 1
    }
  ]
}

r = requests.post(f"{STUDIO}/{PROJECT_ID}/impulse", headers=HEADERS, json=impulse)
print(r.json())
```

## Step 3: Collect Training Data

Stream labeled audio samples from the Thingy:53 to Edge Impulse:

1. Use Nordic Thingy:53 SDK to capture PDM audio samples
2. Format each sample as a WAV file with JSON metadata (as shown in the skill)
3. Upload to Edge Impulse using Ingestion API:

```bash
# Example upload for training sample (label = "play")
curl -X POST https://ingestion.edgeimpulse.com/api/training/data \
  -H "x-api-key: ei_61b005e13e7443fa17d062d34dde59e29ef382d69ffe0817" \
  -H "x-label: play" \
  -H "x-file-name: thingy53_play_001.wav" \
  --data-binary @./thingy53_play_001.wav
```

## Step 4: Train Model

Start training job and wait for completion:

```bash
# Start training (using latest version)
r = requests.post(f"{STUDIO}/{PROJECT_ID}/jobs/train/1", headers=HEADERS)
job_id = r.json()['jobId']

# Poll job status
while True:
    status = requests.get(f"{STUDIO}/{PROJECT_ID}/jobs/{job_id}/status", headers=HEADERS)
    if status.json()['job']['finished']:
        break
    time.sleep(5)

# Check results
print(status.json())
```

## Step 5: Deploy to Device

Deploy the trained model to the Thingy:53:

```bash
# Start deployment (build C++ library)
r = requests.post(f"{STUDIO}/{PROJECT_ID}/deploy", headers=HEADERS, json={"deployType": "zip"})
deployment_url = r.json()['downloadUrl']

# Download and flash to Thingy:53 (via Nordic nRF Connect or similar)
```

## Step 6: Bridge to Sonos

Set up a local Python bridge on Mac Studio:

1. Install `pysonos` or use Home Assistant API
2. Map keywords to Sonos actions:

```python
# sonos_bridge.py
import asyncio, time
from pysonos import SonosSpeaker

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
  if keyword in actions:
    actions[keyword]()
```

3. Use BLE notifications to trigger bridge (e.g., via `bluetoothctl` or Nordic's BLE library)

## Step 7: Test & Refine

1. Test each keyword with the Thingy:53 and verify Sonos responds
2. Adjust training data or model parameters if needed
3. Tune sensitivity and add silence/noise class to prevent false triggers

## Notes

- The Thingy:53 microphones output PDM (Pulse Density Modulation) audio samples
- Edge Impulse supports time-series input with up to 3 axes (X, Y, Z)
- The KWS classifier can be trained with 5–8 keywords for best accuracy
- Use a dedicated "silence" class to prevent false triggers from ambient noise