---
name: observability-stack-setup
description: Use when setting up a Loki/Fluent Bit observability stack.
category: devops
---
# Observability Stack Setup (Loki/Fluent Bit)

This skill provides the procedure for establishing a robust logging and monitoring stack (Loki, Fluent Bit, and Grafana) tailored for the macOS environment and Hermes Agent.

## Procedure
1.  **Loki Installation:** Ensure Loki is installed and running as a service. 
    *   *Tool:* Use Homebrew (`sh.brew.loki`).
2.  **Log Shipping Configuration (Fluent Bit):** Install and configure Fluent Bit to ship logs from the designated Hermes log directory to Loki.
    *   *Procedure:* Configure Fluent Bit to tail all `.log` files in `~/.hermes/logs/`.
    *   *Tool:* `sh.brew.install fluent-bit`.
    *   *Pitfall:* Promtail is deprecated on modern macOS. Fluent Bit is the required, correct replacement for log shipping to Loki.
    *   *Persistence:* Fluent Bit has **no Homebrew service block**, so it needs a hand-written `~/Library/LaunchAgents/sh.brew.fluent-bit.plist` mirroring `sh.brew.loki.plist` (`RunAtLoad`, `KeepAlive`, logging to `/opt/homebrew/var/log/fluent-bit.log`), loaded with `launchctl bootstrap gui/$(id -u) <plist>`. Restarting it is safe: read offsets live in `fluent-bit.db`, so it resumes where it stopped and backfills the gap.
3.  **Grafana Data Source Provisioning:** Configure the required data sources in Grafana, pointing to internal endpoints.
4.  **Dashboard Creation:** Build an operational dashboard, ensuring log panels are filtered by job labels to resolve empty data views.
5.  **Maintenance:** If duplicate data sources (e.g., `loki-1`) appear, remove them manually from the Grafana Data Sources UI.

## Pitfalls & Lessons
*   **Log Location:** All Hermes agent logs are reliably generated and shipped from `~/.hermes/logs/`.
*   **Grafana Duplicates:** Provisioning scripts can occasionally create duplicate data source entries. Treat this as an expected UI cleanup task.
*   **Fluent Bit does not survive a reboot by default, and it fails silently.** Loki and Grafana are `brew services`-managed and come back on their own; Fluent Bit is not, so a hand-started one simply never returns. The other two then come up healthy and the dashboards render normally but **empty**, because nothing is feeding them. Check with `launchctl list | grep fluent` — a bare process with `PPID 1` and no `launchctl` entry is the unsupervised shape.
*   **`brew services info fluent-bit` is misleading.** It prints a `sh.brew.fluent-bit` label, which reads as brew being able to manage it. `brew services start fluent-bit` then fails with `Formula 'fluent-bit' has not implemented #plist, #service or provided a locatable service file.` The label is only what brew *would* use. Confirm with `start`, never `info`.