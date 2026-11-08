# That's Them Broker Audit

## Overview
That's Them is a data broker that requires CAPTCHA handling, placing it in T2 tier.

## Key Characteristics
- Tier: T2 (CAPTCHA required)
- Method: Web form
- Special Notes:
  - Opt-out form is gated by a Cloudflare Turnstile CAPTCHA (so tier is T2 without a captcha-clearing browser backend; T1 with Browserbase)
  - All 7 fields are marked required by the form (Full Name, Street Address, City, State, ZIP, Email, Phone)
  - ADDRESS path requires the ZIP and joins street+city+state+ZIP with hyphens

## Audit Considerations
- The CAPTCHA requirement means this broker needs a cloud browser or stealth mode for full automation
- The form requires extensive information, making it more sensitive to data disclosure
- ZIP requirement is particularly important for address-based searches

## URL Patterns and Quirks
- URL: https://thatsthem.com/
- Search patterns:
  - Name: https://thatsthem.com/name/{First}-{Last}/{City}-{ST}
  - Phone: https://thatsthem.com/phone/{areacode}-{prefix}-{line}
  - Email: https://thatsthem.com/email/{email}
  - Address: https://thatsthem.com/address/{Street}-{City}-{ST}-{ZIP}
- Opt-out URL: https://thatsthem.com/optout

## Handling 404s
That's Them has strict URL formatting requirements. A 404 here likely indicates incorrect formatting or missing required fields.