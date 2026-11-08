---
name: synology-homeassistant-deployment
category: devops
description: Use when deploying HAOS to a Synology NAS via OVA import.
---
# Home Assistant OS on Synology Deployment

This skill provides the robust workflow and pitfalls for deploying Home Assistant OS (HAOS) using an OVA import on a Synology NAS via the Virtualization API.

## Procedure
1. **Verify Requirements:** Confirm the NAS hardware meets HAOS specifications.
2. **Locate Image Source:** HAOS is provided as a complete VM package, not a container image. The correct repository is `home-assistant/operating-system`.
3. **Download and Verify:** Obtain the OVA file and verify its SHA256 checksum against the official GitHub release digest to prevent corruption.
4. **NAS API Setup:** Authenticate with the Synology Virtualization API (`SYNO.Virtualization.API`).
5. **Import VM:** Execute the import command, ensuring the virtual hardware (SATA controller, UEFI firmware) matches HAOS requirements.

## Pitfalls
*   **OVA vs. Docker:** Do not attempt to run HAOS via Docker; its Supervisor architecture is native to the OVA.
*   **API Auth:** Virtualization API calls require administrative authentication to function.
*   **Image Source:** Generic "HAOS image" searches are unreliable; always use the official GitHub release assets.
