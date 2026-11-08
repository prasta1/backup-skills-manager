---
name: renewal-pipeline-reports
description: Weekly renewal pipeline tracking, forecasting, and at-risk customer identification
category: customer-success
trigger: weekly pipeline review, renewal forecasting, or at-risk customer monitoring
---

# Renewal Pipeline Reports

## Weekly Pipeline Snapshot
```bash
# Query HubSpot deals: close date next 90 days, renewal-stage deals
# Segment by: committed, likely, at-risk, overdue
# Calculate: forecast value, coverage ratios
```

## Forecasting Framework
- Deal probability × value for each renewal window (30/60/90 days out)
- Weight by: current usage, relationship strength, support ticket volume
- Flag: deals with declining usage or no recent contact

## At-Risk Identification
- Usage decline >20% month-over-month
- No meetings in 60 days
- Support tickets increasing
- Deal stage stalled >30 days
- Edge Impulse projects inactive >30 days

## Report Template
### Renewals Next 30 Days
- Count, Total ARR, Coverage ratio
- Key accounts and action items

### Expansion Opportunities
- Accounts with usage >80% of tier threshold
- Customers with multiple active projects
- Companies with employee growth

### Action Items
- Follow-ups due this week
- Champions to engage at flagged accounts
- QBRs to schedule