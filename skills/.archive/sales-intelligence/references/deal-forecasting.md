---
name: deal-forecasting
description: Analyze HubSpot deal pipeline, calculate forecasts, and provide expansion recommendations
category: business-development
trigger: when user needs quarterly forecasting, deal scoring, or expansion strategy
---

# Deal Forecasting & Strategy

## Forecasting Methodology

### Weighted Pipeline
- Sum(value × probability) for all open deals
- Segment by: current quarter, next quarter, pipeline health
- Adjust weights based on: usage signals, relationship health, support signals

### Forecast Categories
- **Commit**: 90%+ probability, signed LOIs
- **Likely**: 70-89% probability, strong champion
- **Possible**: 50-69% probability, some engagement
- **Long Shot**: <50% probability, minimal contact

## Deal Scoring Framework

### Expansion Deal Scoring
- Usage growth rate (Amplitude) - weight: 30%
- Team growth (LinkedIn/company data) - weight: 20%
- Champion engagement (meetings, emails) - weight: 25%
- Support interaction quality - weight: 15%
- Competitive landscape - weight: 10%

### Renewal Deal Scoring
- Current usage vs contract value - weight: 30%
- Days to renewal - weight: 20%
- Recent meeting cadence - weight: 25%
- Support ticket trends - weight: 15%
- Contract value vs tier fit - weight: 10%

## Quarterly Planning

### Coverage Ratio Targets
- Enterprise: 4x coverage ratio
- Mid-market: 3x coverage ratio
- SMB: 2x coverage ratio

### Expansion Quota Allocation
- Bottoms-up: sum expansion scores × average expansion rate
- Top-down: align with company growth targets
- Adjust for: seasonality, product launches, market conditions

## Action Recommendations
- Deals to accelerate (champion outreach, executive support)
- At-risk renewals to save (usage review, discount discussion)
- Expansion opportunities to pursue (usage-based outreach, case studies)