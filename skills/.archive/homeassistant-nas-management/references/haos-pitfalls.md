---
title: HAOS Migration & Pitfalls
---

## Core vs. Supervisor
*   **Core:** The Python application engine. Lacks the Supervisor package manager.
*   **Supervisor:** The operating system layer built into HA OS. It manages updates, dependencies, and add-ons.
**Pitfall:** Using a Core-only image prevents the installation and management of essential community add-ons.

## OVA Import & UEFI
*   **Requirement:** HA requires UEFI to boot.
*   **Pitfall:** If VMM uses Legacy BIOS, the VM will fail to boot.

## Package Management Risks
*   **Pitfall:** Storing HA backups in the `@appdata` folder on the NAS. The Synology package manager will delete these files when the package is uninstalled.
*   **Rule:** Backups must be created and stored within the HA VM's internal disk structure.

## Process Discovery
*   **Pitfall:** Using generic Linux process monitoring or logging (`ps`, `journalctl`).
*   **Rule:** Use the HA-specific CLI (`ha core info`, `ha supervisor info`). This queries the HA internal state, which is the only source of truth regarding system health.