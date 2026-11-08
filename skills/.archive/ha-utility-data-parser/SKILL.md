---
name: ha-utility-data-parser
description: Use when parsing custom utility data for HA integrations.
---
# Utility Data Integration Developer

## Procedure for Custom Integration
1. **Map Source Data:** Thoroughly analyze the provider's API (via documentation and existing integration source code) to map the required data (e.g., cost, consumption) to its exact location in the response.
2. **Verify HA Compatibility:** Check Home Assistant's Grid/Energy dashboard requirements to confirm the correct `GridSourceType` and necessary data attributes (`unit_class`, `unit_of_measurement`).
3. **Implement Parser:** Write the parsing logic to extract the required data, paying close attention to how the data block is nested within the overall API response structure.
4. **Test with Live Payload:** Always run integration tests using a raw payload captured from a live utility source to guarantee the parser can handle the real-world data block.

## Pitfalls
* **Payload Misidentification:** Assume data is on a separate endpoint. Always verify the entire response payload of the primary polling request first, as cost data is often a sibling block to usage data.
* **HA External Stat Configuration:** When exposing external statistics, explicitly use `unit_class=None` and `unit_of_measurement=None` in the configuration to prevent Home Assistant from incorrectly inferring currency or unit types.
* **Source Code Drift:** When modifying an existing integration, always check if the upstream API has changed its response structure (e.g., adding or removing data blocks) before applying changes.

## References
- `references/vec-smarthub-parsing.md`: Specific implementation details and data block structures for VEC/SmartHub utility cost parsing.
---