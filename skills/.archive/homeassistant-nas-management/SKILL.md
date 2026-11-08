---
name: homeassistant-nas-management
description: Procedure for stable HA on Synology NAS via VMM.
---

# Home Assistant (HA) on NAS Management

This procedure ensures a stable, secure, and maintainable Home Assistant environment on Synology NAS.

## 1. Initial Deployment (VMM)
*   **Tool:** Virtual Machine Manager (VMM).
*   **Image:** Use the official HA OS OVA/QCOW2. Do not use Core-only or Docker.
*   **Pitfall:** VMM must use **UEFI**; HA will not boot on Legacy BIOS.

## 2. Data Integrity & Backup (CRITICAL)
*   **Procedure:** Use the HA UI (Settings → System → Backups) to create backups.
*   **Pitfall:** **Never** store these backups in the NAS shared volume (`@appdata`). The Synology package manager will delete them upon uninstall/cleanup.
*   **Rule:** Backups must reside within the HA VM's internal disk.

## 3. Access and Networking
*   **Procedure:** Use the HA Tailscale Add-on. This assigns HA a stable `100.x.y.z` Tailscale IP, enabling secure, remote access via Tailscale.
*   **Pitfall:** The NAS often acts as a routing gateway for the local subnet (`192.168.5.x`). While this allows LAN access, Tailscale provides a more consistent, secure alternative.

## 4. Maintenance & Operations
*   **Updates:** Use the HA Supervisor/Add-on Store.
*   **Status Check:** Do **not** use generic Linux logging (`journalctl`). Use the HA-native CLI (`ha core info`, `ha supervisor info`).
*   **SSH Administration:** Use `ssh -t prasta@100.102.22.38 'sudo command'`. The `-t` flag allocates a required pseudo-terminal (PTY) for `sudo` to read your password.

### See `references/haos-pitfalls.md` for technical depth.