---
name: script-hardening
description: Hardens scripts against resource issues and state bleed.
---
# devops/script-hardening

Use when debugging or running system maintenance scripts, especially those governed by cron, where script failures due to resource exhaustion or state corruption are a risk.

## Procedure
1. **Validation (Pre-Run):** Always verify script syntax and logic using dry-run checks.
2. **Execution (Monitoring):** Run the script with resource bounding (`nice`) and time capping (`timeout`) to ensure predictable behavior under load.
3. **Correction (Mid-Run):** If a section is known to time out, inject controlled failures to test boundary conditions.
    - *Pitfall:* State variables (like `awk` counters or section flags) must be reset or guarded against "bleeding" into subsequent, non-failing sections when a skip occurs.
4. **Reporting (Post-Run):** Ensure the primary summary is honest.
    - *Pitfall:* Truncated or skipped sections must be explicitly called out in the TL;DR summary, not just buried in logs.
5. **Maintenance (Cleanup):** Always default to a dry-run (`-n`) for destructive commands (like `cleanup`) before mutation.

## Standing Rules
- **Prioritize honesty over padding:** Never present a failure to process data as a successful operation.
- **Resource awareness:** Use `timeout` to bound subprocesses; a section cap is a planned, bounded failure, not a system crash.

# References
# Guide for script robustness techniques, state guarding, and handling expected sentinel markers.
