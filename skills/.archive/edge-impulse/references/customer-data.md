# Edge Impulse Customer Data Files

## Location
Customer-specific subfolders under:
```
/Users/macstudio/Dropbox (Maestral)/claude-cowork-maestral/Edge Impulse/Customers/
```

## Core Customer Base Files
Two files constitute the current customer base:

| File | Description |
|------|-------------|
| `ei_customers` | Company list — master list of customer accounts |
| `ei_contacts` | Contact list — people associated with customer accounts |

**Note**: These files were referenced by the user but not found in the filesystem at the time of this session. They may be HubSpot CRM exports or internal CS operations files. The user's profile mentions "HubSpot CRM account/contact exports" and the CS Operations folder contains `hubspot-crm-exports-cs-all-customers-2026-03-12.csv`.

## Related Files Found
- `/Users/macstudio/Dropbox (Maestral)/claude-cowork-maestral/Edge Impulse/Customers/hubspot-crm-exports-cs-all-customers-2026-03-12.csv` — HubSpot CRM export (10KB, March 2026)
- Individual customer subfolders under the Customers directory (Allegion, CSEM, Daikin, Getac, Globalsense, Halma, JUMO, Küster, Masco, Nestle Purina, Polar Electro, Poly, Protect Animals With Satellites, Replior, SDGE, Sofar Ocean, Tridonic, Ultrahuman, University of Jyväskylä, Zwift)

## CS Operations Context
- User is Patrick Ruster, VP Customer Success at Edge Impulse
- Building CS copilot collaboration plan with HubSpot + Amplitude data
- Tracking 3 core Amplitude events: Training activity, Deployment activity, Data activity
- Default CS Operations folder: `/Users/macstudio/Dropbox (Maestral)/claude-cowork-maestral/Edge Impulse/CS Operations`

## Next Steps
When `ei_customers` and `ei_contacts` files are located or created, document their:
- File format (CSV, JSON, etc.)
- Schema/column structure
- Update frequency and source of truth
- How they relate to HubSpot CRM exports