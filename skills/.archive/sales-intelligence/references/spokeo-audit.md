# Spokeo Broker Audit

## Overview
Spokeo is a data broker with a straightforward web form opt-out process, placing it in T1 tier.

## Key Characteristics
- Tier: T1 (no CAPTCHA)
- Method: Web form
- Special Notes:
  - Every listing must be opted out individually 
  - Requests process in 24-48 hours per their page
  - Full deletion follow-up: send-email --kind ccpa (CA) / generic to privacy@spokeo.com naming all listing URLs

## Audit Considerations
- Individual listing requirement means multiple submissions may be needed for complete removal
- Processing time is relatively quick (24-48 hours) but verification should be scheduled
- The email follow-up for full deletion is important for comprehensive removal

## URL Patterns and Quirks
- URL: https://www.spokeo.com/search
- Opt-out URL: https://www.spokeo.com/optout

## Handling 404s
Spokeo's URL structure is more predictable, so a 404 likely indicates either wrong pattern or no record.