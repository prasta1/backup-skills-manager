---
name: edge-impulse-monitoring
description: Monitor customer projects in Edge Impulse studio, track deployment status, and identify renewal/expansion opportunities
category: customer-success
trigger: when user needs to check customer Edge Impulse project health or deployment status
---

# Edge Impulse Studio Monitoring

## Quick Setup
- Auth via `EDGE_IMPULSE_API_KEY` and studio credentials
- Access via Edge Impulse REST API or CLI

## Common Monitoring Patterns

### Customer Project Health Check
```bash
# List projects with deployment status
# Query: last deployment date, model accuracy, data ingestion rates
# Check: failed deployments, stale projects (no updates >30 days)
```

### Deployment Status Tracking
- Active deployments: production firmware running
- Model updates: recent retraining signals
- Data pipeline: continuous vs batch ingestion
- Compute usage: embedded vs Linux vs enterprise

### Renewal/Expansion Signals
- Growing data volumes = more expensive tier needed
- Multiple active projects = expansion opportunity
- Model accuracy dropping = success check-in needed
- Failed deployments = at-risk customer signal

## Integration Opportunities
- Cross-reference: Edge Impulse customer IDs with HubSpot company records
- Alert: when customer projects show deployment anomalies
- Report: quarterly usage summaries for customer business reviews