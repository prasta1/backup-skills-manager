---
name: edge-ml-deployment
description: "Deploy ML models to edge devices via APIs."
version: 1.0.0
author: Hermes Curator
license: MIT
tags: [edge-ml, model-deployment, edge-impulse, embedded-ml, device-deployment]
metadata:
  hermes:
    tags: [edge-ml, model-deployment, edge-impulse, embedded-ml, device-deployment]
---

# Edge ML Model Deployment

Deploy machine learning models to edge devices using Edge Impulse Studio and Ingestion APIs. This umbrella consolidates the former `edge-impulse` skill.

## When to Use

- "Upload training data to Edge Impulse"
- "Trigger a training job and wait for completion"
- "Export a C++ library deployment"
- "Deploy a keyword spotting model to Nordic Thingy"

## Edge Impulse Studio API

Manage Edge Impulse projects via the Studio and Ingestion APIs.

### Prerequisites

- `EI_API_KEY` — Edge Impulse API key (starts with `ei_`)
- `EI_PROJECT_ID` — numeric project ID

### API Reference

Base URL: https://studio.edgeimpulse.com/v1
Authentication: `x-api-key: <EI_API_KEY>`
Full reference: `references/api-reference.md` (absorbed from `edge-impulse`)

### Python Skeleton

```python
import os, requests
API_KEY = os.environ.get("EI_API_KEY")
PROJECT_ID = int(os.environ.get("EI_PROJECT_ID"))
STUDIO = "https://studio.edgeimpulse.com/v1/api"
INGEST = "https://ingestion.edgeimpulse.com/api"
s = requests.Session()
s.headers.update({"x-api-key": API_KEY, "Accept": "application/json"})
def get(path, **params):
    r = s.get(f"{STUDIO}/{PROJECT_ID}{path}", params=params)
    r.raise_for_status()
    d = r.json()
    if not d.get("success"): raise RuntimeError(d.get("error", "unknown"))
    return d
def post(path, body=None, base=STUDIO):
    r = s.post(f"{base}/{PROJECT_ID}{path}" if base == STUDIO else f"{base}{path}", json=body)
    r.raise_for_status()
    d = r.json()
    if not d.get("success"): raise RuntimeError(d.get("error", "unknown"))
    return d
```

### Instructions

1. Understand the task from the user's request.
2. Use curl/shell for one-off requests, Python for scripts.
3. For long-running jobs: poll `GET /api/{projectId}/jobs/{jobId}/status` until `.job.finished` is true.

## CLI Tool

`scripts/ei-cli.py` wraps Edge Impulse APIs:
```bash
python3 scripts/ei-cli.py login --api-key ei_your_key
python3 scripts/ei-cli.py samples list --project 123456
python3 scripts/ei-cli.py jobs watch job-123456
```

## Data Visualization

`scripts/visualize_samples.py` generates multi-panel plots of sensor data.

## References

- `references/api-reference.md` — API endpoint reference (absorbed from `edge-impulse`)
- `references/ei-cli-reference.md` — CLI tool reference (absorbed from `edge-impulse`)
- `references/kws-setup.md` — Keyword Spotting walkthrough (absorbed from `edge-impulse`)
- `references/source.md` — Source documentation (absorbed from `edge-impulse`)
