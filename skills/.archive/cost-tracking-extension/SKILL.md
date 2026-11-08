---
name: cost-tracking-extension
description: How to extend Hermes cost tracking to new providers
---

# Cost Tracking Extension

This skill documents how to extend the Hermes cost tracking system to support new providers.

## Overview
Hermes maintains a `cost-snapshots/` directory where it logs usage data for various providers. Currently, this includes OpenRouter but not Nous Research.

The system follows a pattern:
1. A provider-specific data structure is defined (e.g., `openrouter.json`)
2. The data is written to a JSON file in the cost-snapshots directory
3. Each snapshot includes date, used amount, and limit (when available)

## Implementation Process

### 1. Create the provider-specific file structure
- Create a new file in `cost-snapshots/<provider>.json`
- Format should match the existing pattern:
```json
{
  "provider": "openrouter",
  "snapshots": [
    {
      "date": "2026-07-05",
      "used": 0.82567804,
      "limit": null
    }
  ]
}
```

### 2. Extend the snapshot logic (if needed)
- The `account_usage.py` file already contains logic for building snapshots for various providers
- For new providers, you may need to:
  - Add the logic to generate snapshots for that provider
  - Update cron jobs or tracking mechanisms to include new providers

### 3. Add provider-specific logic to existing infrastructure
- Check if the provider has a similar structure to OpenRouter or Nous (which already exists)
- If it's a new provider, extend the snapshot creation to include that provider

## Example Implementation
When adding support for a new provider like "Nous Research":
1. Add the provider-specific logic to `hermes-agent/agent/account_usage.py`
2. Ensure the snapshot generation for that provider is included in the tracking system
3. The cron jobs or periodic tasks should be updated to include this provider in their snapshot collections

## Pitfalls to Avoid
1. **File format inconsistencies**: Ensure all provider files follow the same structure
2. **Missing credential handling**: New providers may require specific credential management
3. **Rate limiting**: Some providers have rate limits that affect snapshot collection

## Example Snapshot Format
```json
{
  "provider": "nous",
  "snapshots": [
    {
      "date": "2026-07-12",
      "used": 15.25,
      "limit": 30.0
    }
  ]
}
```

## Related Skills
- `hermes-agent`: Core Hermes agent functionality
- `account-usage`: Provider-specific account usage tracking logic

## When to Use This Skill
- When extending Hermes cost tracking to new providers
- When implementing provider-specific account usage reporting
- When working with cost tracking and quota monitoring in Hermes

## Verification Steps
1. Ensure the new provider file is created in `cost-snapshots/`
2. Confirm that snapshots are properly formatted JSON
3. Validate that the data structure matches existing patterns
4. Verify that the provider can be properly identified in logs and reports

## Customization Notes
- The skill is focused on the generic process of provider extension, not specific implementation details
- Provider-specific implementation details should be documented in the relevant provider skills or documentation