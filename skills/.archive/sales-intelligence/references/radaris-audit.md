# Radaris Broker Audit

## Overview
Radaris is a data broker that requires CAPTCHA handling, placing it in T2 tier.

## Key Characteristics
- Tier: T2 (CAPTCHA required)
- Method: Web form
- Special Notes: 
  - CAPTCHA requires a captcha-clearing browser backend (T1 with Browserbase)
  - The /control-privacy form REQUIRES the per-person NUMBERED profile URL
  - If there is no View Profile button for the subject, email customer-service@radaris.com

## Audit Considerations
- The CAPTCHA requirement means this broker needs a cloud browser or stealth mode for full automation
- The profile URL requirement is particularly sensitive - incorrect URLs will result in failed submissions
- When no View Profile button exists for the subject, a fallback to email is required

## URL Patterns and Quirks
- URL: https://radaris.com/
- Search pattern: https://radaris.com/p/{First}/{Last}/
- Opt-out URL: https://radaris.com/control-privacy

## Handling 404s
Radaris URL patterns can be tricky - a 404 here likely indicates an incorrect pattern or missing data, not absence of record.