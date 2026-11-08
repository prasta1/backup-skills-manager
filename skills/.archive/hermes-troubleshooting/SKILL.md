---
name: hermes-troubleshooting
description: "Hermes infra: config, gateway, dashboard, WebUI, multiplexing, troubleshooting."
version: 1.1.0
license: MIT
author: Hermes Curator
tags: [hermes, troubleshooting, configuration, gateway, dashboard, webui, memory, backup, multiplexing]
metadata:
  hermes:
    tags: [hermes, troubleshooting, configuration, gateway, dashboard, webui, memory, backup, multiplexing]
---

# Hermes Agent Troubleshooting & Configuration

## Overview
This umbrella covers troubleshooting and configuration of Hermes Agent infrastructure: gateway processes, multi-profile setups, dashboard authentication, WebUI issues, memory providers, configuration management, and backup strategies.

## When to Use
- Gateway not connecting or restarting frequently
- "Invalid API key" errors on port 8642
- Profile switching shows "disconnected gateway"
- Dashboard login loop or auth failures
- WebUI 409 agent_runtime_stale
- Memory provider unavailable
- Provider configuration issues
- Need to back up Hermes config

## Skill Inventory

| Skill | Purpose | Status |
|---|---|---|
| hermes-agent-troubleshooting | Gateway, Tailscale, dashboard troubleshooting | absorbed |
| hermes-configuration | Config management, local models, distributed inference | absorbed |
| hermes-provider-configuration | Provider config and MoA presets | absorbed |
| hermes-themes | Color theme authoring | absorbed |
| hermes-backup | Git backup strategy | absorbed |
| hermes-desktop-plugins | Desktop plugin development | absorbed |
| hermes-agent-overview | Quick reference for capabilities | absorbed |
| gateway-config-snapshot | Config drift detection | support |
| mnemosyne-memory-availability-fix | Memory provider fix | support |
| hermes-multi-profile-gateway | Multi-profile gateway config, session isolation, token sync | absorbed |
| hermes-webui-operations | WebUI operations, 409 fix, model picker | absorbed |
| hermes-profile-authentication | Profile authentication and token management | absorbed |
| hermes-provider-cleanup | Provider cleanup after deletion | absorbed |
| hermes-webui-409-stale-runtime-fix | WebUI 409 conflict resolution | absorbed |
| hermes-desktop-gateway-oauth-setup | Desktop gateway OAuth setup, Tailscale redirect URI fixes | absorbed |
| switch-to-personal-project | Switch active Hermes project to Personal | absorbed |
| tui-widgets | Author live widget apps for the Hermes TUI dock | absorbed |

## Core Workflows

### Gateway Troubleshooting
1. Check gateway status: hermes gateway list
2. Check gateway logs: tail -f ~/.hermes/logs/gateway.error.log
3. For plugin crashes: check for SIDECARD_CRASHED errors, remove problematic credentials
4. For API server auth: set API_SERVER_KEY in ~/.hermes/.env
5. For session isolation: ensure /api/profiles/sessions respects profile parameter

### Multi-Profile Setup
1. Enable multiplexing: hermes config set gateway.multiplex_profiles true
2. Sync OAuth tokens from shared store to profile files
3. Verify token expiration times match across profiles

### Dashboard Authentication
1. Register dashboard: hermes dashboard register --username <name> --password <pass>
2. Fix session TTL: unset or set to 43200 (12h)
3. Check basic_auth config for empty passwords

### Configuration Management
1. Use hermes config set (never edit config.yaml directly)
2. Back up config regularly
3. Clean up .bak files

## Gateway Multiplexing (absorbed from hermes-multi-profile-gateway)

### Problem: Gateway keeps restarting every ~30s
**Root cause:** Plugin sidecar crashes (particularly Photon) cause continuous gateway restarts.
**Fix:** Remove Photon credentials, then disable via config, and remove stale state files. Clean restart via launchd.

### Problem: OAuth tokens diverge across profiles
**Root cause:** Separate per-profile gateway processes run independently; tokens diverge.
**Fix:** Enable single-process multiplexing, then verify tokens synchronized across profiles.

### Problem: Sessions from one profile appear in another
**Root cause:** Desktop sends profile query but API server returns default-profile sessions.
**Fix:** The /api/profiles/sessions endpoint must respect the profile parameter. Key file: gateway/platforms/api_server.py.

### Problem: Invalid API key errors after profile switch
**Root cause:** Shared store has fresh tokens; profile auth.json files have expired tokens.
**Fix:** Sync from shared store to profile files, and patch _check_auth to accept both headers.

**Scripts:** scripts/gateway-restart.sh, scripts/verify-multiplexing.sh
**Templates:** templates/gateway-multiplexing-config.yaml, templates/oauth-token-sync-recipe.md
**References:** references/multiplexing-behavior.md, references/oauth-token-sync-recipe.md

## Desktop Gateway OAuth Setup (absorbed from hermes-desktop-gateway-oauth-setup)

### Problem: Desktop shows "Could Not Reach Gateway" after OAuth redirect
**Root cause:** HTTPS host mismatch or TLS handshake failure on the client side.
**Fix:** Ensure connection.json on the client uses HTTP (not HTTPS) when connecting to a self-hosted gateway over Tailscale. See references/desktop-gateway-oauth-setup-session.md for the full session-specific troubleshooting guide and templates/connection.json.example for the correct configuration template.

## Profile Management: Switching to Personal Project (absorbed from switch-to-personal-project)

### Problem: Need to switch the active Hermes project to Personal
**Fix:** Switch the desktop sidebar project to Personal and optionally sync the terminal cwd. See references/switch-to-personal-project.md for the full guide.

## WebUI Operations (absorbed from hermes-webui-operations)

### Problem: 409 agent_runtime_stale on /api/chat/start
**Root cause:** The webui runs its own in-process agent runtime separate from the gateway. Stale modules in memory cause the guard to refuse chat/start.
**Fix:** Route webui chat through the gateway. Set config, export env vars, restart webui.
**Verify:** curl health endpoint, check GET /api/health/agent for gateway_chat: {enabled: true, backend: gateway}.

### Problem: Model picker not showing free-tier OpenRouter models
**Root cause:** Two-stage model list building. Stage 2 fails silently and falls back to 5 models only.
**Fix:** Ensure network connectivity to openrouter.ai.
**Script:** scripts/webui-model-debug.sh

### Problem: Duplicate default profiles in WebUI
Check on-disk layout. Inspect backend row builders. Fix at API layer by de-duping.
**Reference:** references/PROFILE_LIST_DEDUPE.md

### macOS Tailscale binding quirk
macOS Tailscale uses utun4, not tailscale0. Do not bind HTTP server to 100.x.x.x.
**Reference:** references/WEBSERVER_BINDING.md

## Backup Strategy (absorbed from hermes-backup)
Hermes config backup should follow a Configuration-Only principle — track config.yaml, memories, and skills, not runtime state. See references/hermes-backup.md for the full backup strategy including multi-machine setup (Mac Studio + MacBook Pro), launchd scheduling, secret scanning, and the .gitignore noise filter.

## Desktop Plugins (absorbed from hermes-desktop-plugins)
Write plugins for the Hermes desktop app: statusbar items, layout panes, command-palette commands, keybinds, routes, and themes. A plugin is a single ESM file loaded at runtime — no build step. See references/hermes-desktop-plugins-session.md for the full guide and templates/plugin.js for a starter template.

## Color Themes (absorbed from hermes-themes)
Author a Hermes skin — one YAML file that themes the CLI, TUI, and desktop GUI at once. See references/hermes-themes-session.md for the full guide and templates/skin.yaml for a starter template.

## Provider Configuration (absorbed from hermes-provider-configuration)
Configure AI providers in Hermes and set up Mixture of Agents (MoA) presets. See references/hermes-provider-configuration-session.md for the full guide. Templates include coding-auxiliary-models.yaml and moa-preset-examples.yaml.

## TUI Widgets & Dock Panels (absorbed from tui-widgets)

Author widget apps for the Hermes TUI (`hermes --tui`): glanceable ambient panels docked above the status bar, or modal overlays that own the keyboard. Widgets are plain ESM files the TUI loads at startup — no build step, no repo changes.

### When to use
- The user asks for a live panel in the TUI (ticker, clock, countdown, status card, API-backed readout).
- The user wants a custom modal tool (picker, calculator, viewer) bound to a slash command.

### Prerequisites
- The TUI must be in use (`hermes --tui`). Widgets do not render in the classic CLI or messaging platforms.
- Network-backed widgets need whatever credentials their API needs; fetch failures must land as an error phase, never a crash.

### How to run
1. Use `write_file` to create `~/.hermes/tui-widgets/<name>.mjs` (see `templates/clock.mjs` for a complete working widget).
2. If the TUI is running it hot-loads the file within ~a second (the widgets directory is watched); `/widgets-reload` forces a rescan.
3. The widget's id becomes its slash command automatically (`/<id>`), with its `help` in the `/` completion popover.
4. Auto-open: end `register(sdk)` with `sdk.openWidget(app, app.init(''))` — the widget docks itself the moment the file loads.

### Quick reference
A widget file default-exports `register(sdk)`:
```js
export default function register(sdk) {
  const { Box, Text, defineWidgetApp, h } = sdk
  defineWidgetApp({
    id: 'clock',
    help: 'live clock in the dock',
    mode: 'ambient',
    init: arg => ({ label: arg.trim() || 'UTC' }),
    reduce: (state, { ch, key }) => (key.escape || ch === 'q' ? null : state),
    render: ({ state, t }) => h(sdk.Dialog, { width: 24 }, h(Text, { color: t.color.label }, state.label))
  })
}
```

`sdk` contents: `defineWidgetApp`, `openWidget`, `updateWidget`, `isCtrl`, `React`, `h`, components `Box`, `Text`, `Dialog`, `Overlay`, `WidgetGrid`, `GridAreas`, and loaders `Shimmer`, `ShimmerRows`, `useShimmerPhase`. Use `ShimmerRows` for loading phases instead of a bare "loading…" line.

**Placement zones** (ambient mode): `dock-top`, `dock-bottom` (default), `top-left`, `top-right`, `bottom-left`, `bottom-right`. Set `width` on the app to match your Dialog — the rail reserves exactly that many columns.

**Charts**: `sdk.sparkline(series, width?)`, `sdk.sparkRows(series, width, rows)`, `sdk.gauge(ratio, width)`, `sdk.hbars(values, width)`. Keep a rolling series in component state (cap ~120 samples).

**Pitfalls:** No JSX or bare imports in `.mjs`; don't ship a modal without a close path; ambient widgets must stay ≤ ~6 rows; a thrown `register()` is logged — check `~/.hermes/logs/tui_gateway_crash.log`.

**Template:** `templates/clock.mjs` — complete working clock widget.

## NPM Override Safety (absorbed from npm-nanoid-override-safety)

### Problem: `npm install` in the web workspace drops the nanoid@3.3.18 override
**Root cause:** npm install can remove the `nanoid@^3: 3.3.18` override from the root `package.json`, re-introducing [GHSA-2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8) (high severity) in `sanitize-html` → `postcss` and `vite`.

**Fix:** See `references/npm-nanoid-override-safety.md` for the full procedure.

## References
- references/api-server-authentication-issue.md
- references/npm-nanoid-override-safety.md (absorbed from npm-nanoid-override-safety)
- references/web-ui-400-auth-callback.md
- references/multiplexing-behavior.md
- references/oauth-gateway-multiplexing.md
- references/oauth-token-sync-recipe.md
- references/photon-sidecar-crash-log-excerpt.md
- references/photon-credential-conflict-resolution.md
- references/authentication-root-cause-analysis.md
- references/fix-details.md
- references/fix-verification.md
- references/session-listing-bug.md
- references/user-experience-analysis.md
- references/user-preference-troubleshooting.md
- references/PROFILE_LIST_DEDUPE.md
- references/WEBSERVER_BINDING.md
- references/openrouter-free-tier-debug.md
- references/desktop-gateway-oauth-setup-session.md
- references/switch-to-personal-project.md
- references/distributed-prompt-optimization.md (absorbed from hermes-configuration)
- references/lmstudio-troubleshooting.md (absorbed from hermes-configuration)
- references/model-selection-strategies.md (absorbed from hermes-configuration)
- references/photon-imessage-setup.md (absorbed from hermes-configuration)
- references/profile-distributed-endpoints.md (absorbed from hermes-configuration)
- references/provider-organization.md (absorbed from hermes-configuration)
- references/hermes-backup.md (absorbed from hermes-backup)
- references/hermes-desktop-plugins-session.md (absorbed from hermes-desktop-plugins)
- references/hermes-themes-session.md (absorbed from hermes-themes)
- references/hermes-provider-configuration-session.md (absorbed from hermes-provider-configuration)
- references/duplicate-provider-fix.md (absorbed from hermes-provider-configuration)
- references/provider-resolution-chain.md (absorbed from hermes-provider-configuration)
- references/tailscale-remote-setup.md (absorbed from hermes-provider-configuration)
- templates/clock.mjs (absorbed from tui-widgets) — complete working clock widget example
