# Current stack baseline — for gap evaluations

Verify live before relying; tool versions and loadouts drift. This is the baseline to map "compare X to what we have" questions onto.

## Browser automation

- Hermes built-in browser tools: headless Chromium, a11y snapshots, click/type/navigate/vision — interactive agent-in-the-loop browsing, zero setup, no keys. Default for anything asked in-session.
- Chrome DevTools MCP (~29 tools): evaluate_script, network inspection, Lighthouse, perf traces — debugging and QA, not durable automation.
- computer_use / cua-driver: background desktop automation without focus steal — for native apps, not web scripting.
- cron + terminal + curl: API-accessible sites need no browser at all.
- Remaining gap: unattended, version-controlled, scripted browser automation with typed structured output — what Stagehand-class SDKs (act/observe/extract/agent) add. Only adopt when a real recurring workflow exists (JS-rendered pages curl can't read, or embedding in a product); if so: Python + local Chrome + standalone script, no agent framework. Browserbase cloud (paid) adds session replay, captcha solving, identity — optional, not the default.

## Monitoring & dashboards

- **Deployed (2026-09-07):** macmon serve (:9199, launchd) on Studio + MacBook; Prometheus 3.14 (:9090, loopback-only, brew) + Grafana 13.2 (:3001, brew) on the Studio as the always-on hub. Fleet dashboard at http://studio.taile85139.ts.net:3001/d/macmon-system/system-monitoring.
- macmon is the telemetry source: pipe JSON for the tmux terminal dashboard (GPU util/power/freq, CPU P+E cores, RAM, swap, fans, package power); `macmon serve` exposes /json and /metrics (Prometheus format) and `--install` creates a launchd service.
- Gap that remains: Alertmanager-to-Telegram alerting and PromQL queries pulled by the Daily Brief — the persistence and browser view are done, alerting is not.
- Operations, ports, first-boot, and pitfalls: see the **prometheus-grafana-monitoring** skill (templates/ + verified metric list there).
