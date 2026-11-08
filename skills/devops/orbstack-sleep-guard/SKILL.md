---
name: orbstack-sleep-guard
description: Prevent service restart loops during OrbStack guest sleep.
version: 1.0.0
---

# OrbStack Sleep Guard

Use when a macOS host uses OrbStack to run Docker containers, and local services become unreachable during OrbStack guest sleep events. This pattern makes a watchdog or health-check script distinguish "OrbStack asleep" from "service crashed", prevents futile auto-restart loops, and alerts with the correct remediation.

## Problem

OrbStack's Linux VM can enter software sleep independently of macOS host sleep (triggered by idle, power management, etc.). When the guest sleeps:

- `~/.orbstack/run/docker.sock` disappears or becomes unresponsive
- Port-forwards (e.g. `127.0.0.1:6333`, `0.0.0.0:8000`) drop
- Any `docker` command hangs or fails with "cannot connect to Docker daemon"
- launchd-based service restarts are futile until the guest wakes

Without detection, watchdogs spam DOWN alerts + auto-restart loops for the entire sleep window.

## Pattern

### 1. Early OrbStack probe (run before any Docker-backed service checks)

```bash
readonly ORBSTACK_SOCKET="$HOME/.orbstack/run/docker.sock"
ORBSTACK_DOCKER_UP=true

check_orbstack_docker() {
    ORBSTACK_DOCKER_UP=true
    if [[ ! -S "$ORBSTACK_SOCKET" ]]; then
        ORBSTACK_DOCKER_UP=false
        log "OrbStack docker socket missing ($ORBSTACK_SOCKET) — guest likely asleep"
        if check_alert_cooldown "orbstack_docker_socket"; then
            notify "😴 OrbStack Docker socket is unreachable. If docker-backed services are also down, this is an OrbStack sleep event — open OrbStack to wake the guest; bare service restarts won't help."
            set_alert_cooldown "orbstack_docker_socket"
        fi
        return
    fi
    if ! /usr/local/bin/docker info >/dev/null 2>&1; then
        ORBSTACK_DOCKER_UP=false
        log "OrbStack docker socket present but daemon unresponsive — guest likely asleep"
        if check_alert_cooldown "orbstack_docker_daemon"; then
            notify "😴 OrbStack Docker daemon is unresponsive. If docker-backed services are also down, this is an OrbStack sleep event — open OrbStack to wake the guest; bare service restarts won't help."
            set_alert_cooldown "orbstack_docker_daemon"
        fi
        return
    fi
    # Healthy — clear stale OrbStack alert state and reset docker-backed
    # service failure counters so a previous sleep event can't trigger an
    # immediate false auto-restart on the next real failure.
    rm -f "$HOME/nanoclaw/logs/.orbstack-sleep-alert-hold" 2>/dev/null || true
    for svc in <SERVICE_NAMES>; do
        json_state "s.setdefault('services', {})['$svc'] = {'status': 'up', 'failures': 0, 'alerted': False, 'restarts_in_window': 0, 'first_restart_at': 0}"
    done
}
```

Replace `<SERVICE_NAMES>` with a space-separated list of your docker-backed services (e.g. `Qdrant OneCLI`).

### 2. Guard docker-backed service checks

```bash
orbstack_skip() {
    if [[ "$ORBSTACK_DOCKER_UP" == "false" ]]; then
        log "Skipping $1 check — OrbStack docker daemon is unreachable"
        return 0
    fi
    return 1
}
```

Wrap each Docker-backed service:

```bash
# Before
check_service "Qdrant" "" "" "http://localhost:6333/healthz" "docker start qdrant 2>/dev/null"

# After
if ! orbstack_skip "Qdrant"; then
    check_service "Qdrant" "" "" "http://localhost:6333/healthz" "docker start qdrant 2>/dev/null"
fi
```

### 3. Root-cause fix

Disable OrbStack guest sleep so the docker socket stays live:

```bash
orb config set power.pause_in_sleep false
```

Or in OrbStack GUI: Settings → Advanced → uncheck "Pause in sleep".

## Why this works

- `check_orbstack_docker` runs first, before any service probe
- If OrbStack is asleep, docker-backed services are skipped entirely — no failure counters increment, no auto-restart loops, one clear alert with correct remediation
- On recovery, failure counters are flushed so services don't immediately false-alert on the next real incident
- Works with any number of Docker-backed services
- Does not affect non-Docker services (LM Studio, Hermes Gateway, etc.) — those still get their normal checks regardless of OrbStack state

## Pitfalls

- If you add a new Docker-backed service, remember to add it to `<SERVICE_NAMES>` in `check_orbstack_docker` so its counters get flushed on recovery
- The alert uses cooldowns (`orbstack_docker_socket`, `orbstack_docker_daemon`) so you don't get paged every 5 minutes during a long sleep event — one alert per cooldown window per failure mode
- `check_orbstack_docker` must be called **before** any docker-backed service checks, otherwise they run once and falsely accumulate failures before OrbStack is detected
