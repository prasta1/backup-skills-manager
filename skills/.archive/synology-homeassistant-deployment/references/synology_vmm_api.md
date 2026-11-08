# Synology Virtualization API Guide

## API Endpoint
The primary entry point for VM operations is the `SYNO.Virtualization.API`.

## Critical VM Configuration Pitfalls
When importing the OVA, the following configuration must be correct to prevent boot failure:

- **SATA/SCSI Controller:** Ensure the virtual machine is configured with a compatible storage controller.
- **Firmware:** Correct firmware emulation (e.g., UEFI) is mandatory. Incorrect configuration of these layers is the primary cause of VM hanging or immediate failure after import.
- **Authentication:** All API requests must be authenticated using an administrative account.
