---
name: automated-customer-alerts
description: Proactive monitoring and alerting for customer health signals across HubSpot, Amplitude, and Edge Impulse
category: customer-success
trigger: when user wants automatic monitoring of customer accounts
---

# Automated Customer Alerts

## Alert Types & Thresholds

### Usage-Based Alerts (Amplitude)
- **Decline Alert**: Usage drops >25% vs previous week
- **Growth Alert**: Usage increases >50% indicating expansion opportunity
- **Churn Risk**: >30 days without key feature events
- **Power User Alert**: New team member shows high engagement

### Deployment-Based Alerts (Edge Impulse)
- **Stale Project**: No updates in 30 days
- **Failed Deployment**: Any deployment failure
- **Scale Alert**: Data volume approaching tier limit
- **Inactive Model**: Production deployment showing no inference

### Engagement-Based Alerts (HubSpot)
- **No Contact**: >60 days since last meeting logged
- **Deal Stalled**: Deal stage unchanged for 30 days
- **New Contact**: Key stakeholder changes at account
- **Support Volume**: Support tickets spike month-over-month

## Delivery Preferences
- Slack: #customer-alerts channel with threads per account
- Email: Digest format (daily/weekly)
- Direct: Real-time for high-severity red flags

## Implementation
- Run daily via cronjob
- Cross-reference all three data sources per account
- Generate ranked list of priority accounts to contact
- Include: action summary and next best step

## Severity Levels
- **Critical**: Failed deployments + declining usage
- **Warning**: Usage decline OR stale relationship
- **Opportunity**: Usage growth + deal advancement signals