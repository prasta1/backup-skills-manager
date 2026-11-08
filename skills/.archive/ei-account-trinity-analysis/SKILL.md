---
name: ei-account-trinity-analysis
description: Analyze the Holy Trinity (data ingestion → model training → deployment) for Edge Impulse customer accounts
category: customer-success
trigger: When checking account health or Trinity completion status
---

# EI Account Trinity Analysis

Per SOUL.md: The Holy Trinity is the strongest indicator of engagement and expansion readiness.

## Trinity Definition
1. **Data Ingestion** — collect, import, or transfer data into Studio
2. **Model Training** — build or train an impulse
3. **Deployment** — move a finished model to a target device or runtime

## Pathology Detection

| Observed | Pathology | Bridging step |
|----------|-----------|---------------|
| Ingestion, no training | Data purgatory | Diagnose labeling bottleneck, data-quality wall, or unclear DSP path |
| Training, no deployment | Lab trap | Surface EON optimization and deployment target (MCU/latency issues) |
| Deployment, no new ingestion | One-and-done | Find use case #2 - they succeeded but plateaued |
| All three, low volume | Single-thread | Widen to adjacent users/teams |

## Analysis Commands

### Amplitude Event Validation
```bash
# Before querying, discover actual event names
# Never guess event names - silent failure mode
curl -u $AMPLITUDE_API_KEY:$AMPLITUDE_SECRET_KEY \
  "https://amplitude.com/api/2/events?limit=100"
```

### Customer Account Check
```python
# For each account, check Trinity legs
# Time window: trailing 30 days (default), compare to trailing 90 days
# Flag: any leg silent for full window = stalled
```

## Red Flags to Surface
- Trailing-90 comparison shows decline
- No activity in any leg for 60+ days
- Forum posting without corresponding Studio activity