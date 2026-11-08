# MyLife Broker Audit

## Overview
MyLife is a data broker that requires phone callback for opt-out, placing it in T3 tier.

## Key Characteristics
- Tier: T3 (phone callback required)
- Method: Phone
- Special Notes: Often pushes a driver's-license upload or a call to (888) 704-1900. Emailing privacy@mylife.com with name + profile link is an alternative.

## Audit Considerations
- Phone callback requirement means this will always require human intervention for full removal
- Email alternative (privacy@mylife.com) may be more automated but should be verified as functional
- The "driver's-license upload" requirement suggests this is likely a high-risk target for personal data exposure

## URL Patterns and Quirks
- URL: https://www.mylife.com
- Opt-out URL: https://www.mylife.com/privacyrequest

## Handling 404s
MyLife's URL structure may not be as predictable as others, so a 404 should trigger a fallback to the on-site search functionality.