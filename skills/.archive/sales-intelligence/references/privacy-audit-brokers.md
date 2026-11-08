# Data Broker Privacy Audit (absorbed from privacy-audit-brokers)

This reference consolidates the former `privacy-audit-brokers` skill. It provides a structured approach to conducting targeted privacy audits for specific data brokers, particularly focusing on the MyLife, Radaris, SmartBackgroundChecks, Spokeo, and That's Them brokers.

## When to Use

- "Audit my privacy exposure on MyLife, Radaris, SmartBackgroundChecks, Spokeo, That's Them"
- "Check specific data brokers for personal information exposure"
- "Targeted privacy assessment for these specific brokers"

## Audit Process

1. **Preparation**: 
   - Ensure the `unbroker` skill is properly configured
   - Confirm that the target brokers are supported and have current records in the broker database

2. **Execution**:
   - Use `pdd.py plan` to get the search vectors and requirements for the specified brokers
   - Process each broker's search vectors by:
     - Reading the broker reference (`references/brokers/<id>.json`)
     - Running every search vector from `pdd.py plan` (filtered to your brokers)
     - Building URLs from `search.url_patterns` and heed `url_format_quirks`
   - A 404 is INCONCLUSIVE (not `not_found`) - treat as such and fall back to the on-site search box

3. **Results**:
   - Document findings for each broker
   - Highlight any special considerations or quirks specific to the broker (e.g., CAPTCHA requirements, special URL formats)
   - Note any brokers that require human intervention or special handling

## Broker-Specific Considerations

### MyLife
- Tier: T3 (phone callback required)
- Method: Phone
- Special Notes: Often pushes a driver's-license upload or a call to (888) 704-1900. Emailing privacy@mylife.com with name + profile link is an alternative.

### Radaris
- Tier: T2 (CAPTCHA required)
- Method: Web form
- Special Notes: 
  - CAPTCHA requires a captcha-clearing browser backend (T1 with Browserbase)
  - The /control-privacy form REQUIRES the per-person NUMBERED profile URL
  - If there is no View Profile button for the subject, email customer-service@radaris.com

### SmartBackgroundChecks
- Note: This broker was not found in the current broker database, so no specific audit process can be defined.

### Spokeo
- Tier: T1 (no CAPTCHA)
- Method: Web form
- Special Notes:
  - Every listing must be opted out individually 
  - Requests process in 24-48 hours per their page
  - Full deletion follow-up: send-email --kind ccpa (CA) / generic to privacy@spokeo.com naming all listing URLs

### That's Them
- Tier: T2 (CAPTCHA required)
- Method: Web form
- Special Notes:
  - Opt-out form is gated by a Cloudflare Turnstile CAPTCHA (so tier is T2 without a captcha-clearing browser backend; T1 with Browserbase)
  - All 7 fields are marked required by the form (Full Name, Street Address, City, State, ZIP, Email, Phone)
  - ADDRESS path requires the ZIP and joins street+city+state+ZIP with hyphens

## Handling 404s

A 404 on a constructed URL means WRONG PATTERN, not "no record present". 
- Re-check the broker's `search.url_patterns` / `url_format_quirks` and rebuild the URL
- Fall back to the on-site search box: `browser_navigate` to the search page, `browser_type` the raw query, `browser_click` Search, then read the canonical result URL the site lands on
- Only after the site's own search returns an empty result set do you record `not_found`