---
name: amplitude-analytics
description: Pull and analyze Amplitude data for Edge Impulse customer health (Trinity validation)
category: customer-success
trigger: when validating event names or pulling customer usage data for health assessment
---

# Amplitude Analytics for Edge Impulse

## Per SOUL.md Section 3 & 6
**Event and property names are project-specific. Discover them before filtering. Never guess an event name.**

A query built on a hallucinated event name returns a plausible-looking empty result, and an empty result reads as "this account is dead." That failure mode is silent and expensive.

## Event Discovery First
```bash
# Always run this to discover actual event vocabulary
curl -u "$AMPLITUDE_API_KEY:$AMPLITUDE_SECRET_KEY" \
  "https://amplitude.com/api/2/events?limit=100"
```

## Trinity Validation Queries
- **Data Ingestion**: Look for upload/transfer events
- **Model Training**: Look for training/job events  
- **Deployment**: Look for deploy/deployment events

## Window Defaults (Per SOUL.md Section 4)
- Trailing 30 days for current activity
- Trailing 90 days for trend comparison
- "Stalled": leg was active, now silent for full window
- Always name the window used in reports

## Quick Setup
- Store `AMPLITUDE_API_KEY`, `AMPLITUDE_SECRET_KEY`, and `AMPLITUDE_PROJECT_ID` in a local env/secret store
- Use direct REST API calls with basic auth from those env vars

## Common Analysis Patterns

### Product Usage Health Score
```bash
# Query events by company/user in time window
# Ensure AMPLITUDE_API_KEY and AMPLITUDE_SECRET_KEY are set in the environment
curl -u "$AMPLITUDE_API_KEY:$AMPLITUDE_SECRET_KEY" \
  "https://amplitude.com/api/2/export?start=$(date -d '30 days ago' +%Y%m%dT%H)&end=$(date +%Y%m%dT%H)"
```

### Cohort Analysis for Expansion Signals
- Query: active users by feature over time
- Look for: increasing usage patterns = upsell readiness
- Query: power user behaviors = product adoption champions

### Churn Risk Indicators
- Query: declining weekly active days
- Query: reduced feature engagement
- Query: spike in support-related events

## Customer Success Queries

### Account Usage Deep Dive
```bash
# Events for specific user/company ID
# Group by: event_type, daily_active_users, retention
# Timeframe: last 60 days, compare to previous period
```

### Feature Adoption Tracking
- Track: new feature usage by existing customers
- Correlate: feature adoption with deal stage progression
- Identify: customers using >80% of features = expansion targets

## Integration with HubSpot
- Use HubSpot company_id as Amplitude user property
- Join: Amplitude usage data + HubSpot deal stages
- Automate: health scores → HubSpot custom properties