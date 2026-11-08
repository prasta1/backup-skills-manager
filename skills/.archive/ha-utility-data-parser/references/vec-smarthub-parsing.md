# VEC SmartHub Cost Data Parsing Recipe

This document outlines the specific findings required to modify the `gagata/ha-smarthub-energy-sensor` integration to include cost data from Vermont Electric Co-op (VEC).

## Key Finding: Unified Endpoint
Cost data is not on a separate endpoint. It resides in the same response as usage data: `utility-usage/poll`.

## Data Block Structure
The cost information is contained in a sibling block within the main usage response:
```json
{
  "type": "COST",
  "series": "10809719",
  "value": [
    {"time": "...", "cost_in_cents": 150}
  ]
}
```
**Pitfall**: Many existing parsers only look for `type == "USAGE"`, ignoring the `type: "COST"` block entirely.
