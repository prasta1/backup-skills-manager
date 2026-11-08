# Exporters and scrape targets beyond macmon

The core stack scrapes macmon for SoC metrics. This reference covers the
second wave: OS-level and reachability exporters plus launchd agent health.

## node_exporter (studio hub)

- Mac Studio: `brew install node_exporter`, then put flags in
  `/opt/homebrew/etc/node_exporter.args` (brew's service wrapper reads it):
  ```
  --web.listen-address=:9100
  --collector.textfile.directory=/opt/homebrew/var/node_exporter/textfiles
  ```
  Start with `brew services start node_exporter`.

## blackbox_exporter (hub only)

- NOT in Homebrew core. The core formula named `blackbox` is StackExchange's
  secret-storage tool — do not install it. Grab the official darwin-arm64
  release binary from GitHub releases into /opt/homebrew/bin and manage with
  a launchd plist (RunAtLoad + KeepAlive):
  `blackbox_exporter --config.file=/opt/homebrew/etc/blackbox_exporter/blackbox.yml --web.listen-address=:9115`
- Blackbox_exporter runs on the Studio (hub) at `:9115`. Config (`blackbox.yml`) needs at least an `http_2xx` module with `preferred_ip_protocol: ip4`.
- The studio-local `blackbox-http` job probes `localhost:3001` (Grafana), `localhost:9090` (Prometheus), `localhost:9100` (node_exporter), and `localhost:9115` (blackbox).

## Scrape config shape (studio hub)

```yaml
  - job_name: "studio"
    static_configs:
      - targets: ["localhost:9199"]
        labels: { host: "studio" }
  - job_name: "node-studio"
    static_configs:
      - targets: ["localhost:9100"]
        labels: { host: "studio" }
  # tanker (Synology NAS) is deliberately NOT scraped — node_exporter was never installed
  # there (verified 2026-11-05: :9100 refused, nothing listening). A node-tanker job can only
  # ever report "down", i.e. a permanent false alarm. DSM's Storage Manager covers volume health.
  - job_name: "blackbox-http"
    metrics_path: /probe
    params: { module: [http_2xx] }
    static_configs:
      - targets:
        - "http://localhost:3001"   # Grafana
        - "http://localhost:9090"   # Prometheus
        - "http://localhost:9100"   # node_exporter Studio
        - "http://localhost:9115"   # blackbox self
        labels: { host: "studio" }
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9115
```

Always restart Prometheus after editing (`brew services restart prometheus`) —
the /-/reload endpoint is 403 unless --web.enable-lifecycle is set, which
brew's default args omit.

## Useful node_exporter queries

- Disk used % per host:
  `100 - (node_filesystem_avail_bytes{mountpoint="/",job="node-<host>"} / node_filesystem_size_bytes{mountpoint="/",job="node-<host>"} * 100)`
- CPU busy %: `100 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle",job="node-<host>"}[1m]) * 100)`
- Blackbox probe success: `probe_success` (1 = up; render as bool).

## Textfile collector for launchd agent health

`agent_health_textfile.sh` (installed at /opt/homebrew/bin) reads `launchctl
list`, auto-discovers agents matching `com.meemeep.*`, `com.macmon`,
`com.blackbox.*`, `sh.brew.(prometheus|grafana|node_exporter)`, and
`ai.(hermes|llama-swap|mnemosyne)`, and writes `agent_running{label}` +
`agent_last_exit_status{label}` gauges to the textfile dir. A launchd plist
with `StartInterval` 60 + `RunAtLoad` keeps it fresh. The gauges surface in
the Infra & Services dashboard as a stat panel — a dead agent reads 0 with
no alert rule needed. When adding a new launchd service to track, extend the
auto-discover regex inside the script.

## Grafana API notes

- Datasource health: `/api/datasources/uid/<uid>/health` (the
  `/api/datasources/<numeric-id>/health` route 404s on newer Grafana).
- First boot: admin/admin is live — rotate immediately via
  `/api/user/password`, then use the new password for every later call.
- Dashboard edit: GET /api/dashboards/uid/<uid> → mutate → POST
  /api/dashboards/db with overwrite:true. Drop `id` from the dashboard JSON
  before POSTing back.
- Units: `decmbytes` = MB, `decgbytes` = GB. Panel values divided by
  1073741824 are GB — pair them with decgbytes or the axis labels lie.
