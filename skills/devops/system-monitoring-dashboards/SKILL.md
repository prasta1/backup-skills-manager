---
name: system-monitoring-dashboards
description: Live terminal dashboards for Apple Silicon resource use.
version: 0.1.0
author: Hermes
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Monitoring, Performance, Terminal, Apple Silicon, Inference]
---

# Live Resource Monitoring Dashboards (Apple Silicon)

Renders live, terminal-native dashboards for system resource consumption on Apple
Silicon Macs — specifically tuned for watching llama-swap / llama.cpp inference
loads. Uses macmon's `pipe` subcommand (sudoless, Apple Silicon only) as the
sole data source. Renders via pure-python ANSI so it works in tmux, Terminal,
iTerm2, and the built-in Hermes terminal without extra Python packages.

What it does NOT do: cross-platform dashboarding (this is Apple Silicon-only
via macmon), GUI/Chart.app overlays, long-term persistence, or network stats.
It is a live view, not a logger.

stdlib only (json, subprocess, signal, time). macmon is the only external
dependency and must be pre-installed.

## When to Use

- "Show me a live resource monitor while a model is running"
- "I want to see GPU utilization and power during inference"
- "Pull up a quick system dashboard before kicking off a long encode"
- "What's the quickest way to spot thermal throttling during llama-server runs"
- "Render resource consumption in the Hermes terminal without leaving it"

## Prerequisites

macmon installed and on PATH or at `/opt/homebrew/bin/macmon`:

```bash
brew install macmon
```

macOS 12+ on Apple Silicon (M1/M2/M3 family). The `macmon pipe` subcommand
reads Apple's ARM performance counters and is the only source of GPU compute
utilization on Apple Silicon without root.

Python 3.9+ (system or Homebrew). Verified on Python 3.14.

## How to Run

The dashboard runs in the foreground. Invoke through the `terminal` tool:

```
/opt/homebrew/bin/python3.14 scripts/mtop_dashboard.py
```

Or inside a background tmux pane via the `terminal` tool for a persistent
live view that does not block your session:

```
terminal(command="tmux new-session -d -s mtop 'python3.14 scripts/mtop_dashboard.py'")
```

Read the captured pane: `terminal(command="tmux capture-pane -t mtop -p")`.

## Quick Reference

```
/opt/homebrew/bin/macmon pipe                 stream JSON, one sample/sec default
macmon pipe -i 500                            stream every 500ms
macmon serve -p 9090                          HTTP: /json + /metrics (Prometheus)
tmux new-session -d -s mtop '<script>'        run dashboard in background pane
tmux capture-pane -t mtop -p                  read current dashboard frame
tmux kill-session -t mtop                     stop the dashboard
```

macmon JSON sample keys used by the dashboard:
`gpu_usage` (array [freq, ratio]), `gpu_power`, `gpu_freq_mhz`,
`cpu_scaled_ratio`, `cpu_power`, `pcpu_freq_mhz`, `ecpu_freq_mhz`,
`memory` (ram_total / ram_usage / swap_total / swap_usage), `fans`
(array of max_rpm / name / rpm), `all_power`, `ane_power`.

## Procedure

1. Confirm macmon is installed and runnable through the `terminal` tool:

   ```
   /opt/homebrew/bin/macmon --version
   ```

   Expect output like `macmon 0.8.2`.

2. Confirm Python can read one sample via the `terminal` tool:

   ```
   /opt/homebrew/bin/macmon pipe -i 1000 2>/dev/null | head -n 1 | /opt/homebrew/bin/python3.14 -c "import sys,json; print(json.load(sys.stdin).keys())"
   ```

3. Launch the dashboard. For a non-blocking live view, start it in a tmux
   pane:

   ```
   tmux new-session -d -s mtop '/opt/homebrew/bin/python3.14 scripts/mtop_dashboard.py'
   ```

   The dashboard hides the cursor and clears the screen on each refresh
   (ANSI `\033[2J\033[H`), updates once per second, and renders:
   - GPU: utilization %, power (W), core frequency (MHz) + meter bar
   - CPU: scaled utilization %, power (W), P/E-core frequencies + bar
   - MEM: used/total GiB + percentage + bar
   - SWAP: used/total GiB + bar (only shown when swap is configured)
   - FAN: per-fan name:rpm/max_rpm (only shown when fans present)
   - PKG: total package power + ANE power

4. Read the live frame:

   ```
   tmux capture-pane -t mtop -p
   ```

   Each capture shows the most recent macmon sample.

5. To stop:

   ```
   tmux kill-session -t mtop
   ```

   Ctrl-C also exits cleanly (restores cursor, no stack trace).

## Pitfalls

- macmon `pipe` has no `--count` or `-n` flag for sampling N lines. To grab
  a single sample, rely on downstream consumption (e.g. `head -n 1` or reading
  one line in Python). Do NOT add `-n 1` to macmon.
- macmon `pipe` does not exit when its stdout pipe closes in all versions;
  always terminate the process explicitly (the script does this via SIGTERM
  in the Popen cleanup, or kill the tmux session).
- GPU utilization (`gpu_active_ratio` / `gpu_usage[1]`) reads 1.0 when the
  GPU is active at all — during llama-server inference this saturates near
  100%, which is expected, not an error.
- On an idle Studio, `cpu_power` and `ane_power` may report 0.0W. This is a
  macOS SMC sampling artifact, not a data-source failure.
- The dashboard hardcodes macmon at `/opt/homebrew/bin/macmon`. If macmon
  installed elsewhere, update the `MACMON` constant in `scripts/mtop_dashboard.py`.
- ANSI clear-screen (`\033[2J\033[H`) requires a real terminal or tmux pane.
  It will not render usefully in a plain log file.

## Verification

Run the dashboard briefly and capture one frame:

```
tmux new-session -d -s mtop '/opt/homebrew/bin/python3.14 scripts/mtop_dashboard.py'
sleep 2
tmux capture-pane -t mtop -p
tmux kill-session -t mtop
```

A successful run shows a populated dashboard with GPU utilization bar, CPU
bar, MEM bar, fan RPM lines, and package power — all non-zero values from a
live macmon sample. The last line reads:
`── mtop: live macmon feed · Ctrl-C to exit ──`.
