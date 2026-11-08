---
name: edge-impulse-customer-success
description: Customer success copilot for Edge Impulse - Trinity analysis, renewal risk, expansion opportunities following SOUL.md framework
category: customer-success
trigger: when analyzing Edge Impulse customer accounts, renewal status, or usage health
---

# Edge Impulse Customer Success

**Governing framework**: `SOUL.md` in the project root. This skill provides operational workflows; SOUL.md defines tone, priorities, and Trinity interpretation.

## Key Principles (from SOUL.md)

- **Logo retention is priority #1** - churn risk outranks upside
- **Holy Trinity** = Data Ingestion → Model Training → Deployment
- **Usage health is diagnostic** - not the goal itself
- **Draft, don't send** - autonomous boundary is the send button

## Trinity Pathologies & Bridging Steps

| Observed | Pathology | Bridge |
|----------|-----------|--------|
| Ingestion, no training | Data purgatory | Diagnose labeling bottleneck or DSP path |
| Training, no deployment | Lab trap | Surface EON optimization, target/runtime obstacle |
| Deployment, no new ingestion | One-and-done | Find use case #2 - plateaued accounts don't expand |

## Analysis Workflow

### 1. Account Health Scan
```bash
# From project directory
python scripts/account_health_analyzer.py
```

### 2. Amplitude Trinity Validation
**Event names are project-specific. NEVER guess them.** Use the discovered vocabulary:

- **Data Ingestion**: `data ingested`, `features generation started/completed`, `impulse block customized`  
- **Training**: `training started/completed`, `model retrain started/completed`
- **Deployment**: `impulse deployment started/completed`

### 3. Missing Amplitude Signal Protocol (Per SOUL.md §5)

When no Amplitude data exists for an account, this is diagnostic evidence NOT a gap. Distinguish:

1. No data collected (instrumentation off) - Check if account uses the platform
2. No activity occurred (account quiet) - Diagnostic of churn risk  
3. Activity occurred but wasn't instrumented (unknown) - Ask what tools they use

### 4. Cross-Reference Findings (From Session)

Analyzing 19 CRM accounts against Amplitude:
- **5 accounts show platform signal**: Halma, Masco, Sofar Ocean, Poly, University of Jyväskylä
- **14 accounts show no Amplitude signal** (including $100K Polar Electro renewal)

This absence is a finding: accounts without signal are more often quiet than simply offline.

### 3. Renewal Prioritization
1. Past-due accounts (Polar Electro: $100K, renewal 2026-04-19)
2. Within 30 days (Allegion: $35K, renewal 2026-04-24)
3. Within 90 days (all others)

### 4. Expansion Signal Check
- All 3 Trinity legs active + healthy volume = expansion-ready
- Find adjacent use cases (Line A → Line B)
- Widen beyond single-threaded practitioners

## Data Sources

| Source | Access | Notes |
|--------|--------|-------|
| Amplitude | API key/secret | Validate events before querying |
| HubSpot | Flat file CSV only | MCP connects to personal account (Peregrine) - DO NOT USE |
| Edge Impulse | Studio monitoring | Check project status vs usage data |
| Forum | forum.edgeimpulse.com | Leading indicator for friction |

## References

- `SOUL.md` - Governing copilot framework
- `scripts/account_health_analyzer.py` - CSV health scanner
- `Territory & Market Data/Metabase Territory Analytics/` - ETL pipeline