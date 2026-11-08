# Photon iMessage Platform Setup

## What is Photon?
Photon is a managed service that provides iMessage integration for Hermes through a persistent gRPC connection. It handles Apple line allocation and abuse prevention without requiring users to run their own Mac relay.

## Status Check
```bash
hermes photon status
```

Shows: device token, dashboard project, spectrum project id, project secret, registered number, assigned iMessage line, Node binary, sidecar deps.

## Configuration Path
In `~/.hermes/config.yaml`:
```yaml
platforms:
  photon:
    enabled: true  # or false (default)
```

## Prerequisites
- Photon account at [app.photon.codes](https://app.photon.codes)
- Node.js 18.17+ on PATH (`node --version`)
- Phone number capable of iMessage

## Setup Flow
```bash
hermes photon setup --phone +15555554567
```

This:
1. Device-code login (opens https://app.photon.codes/ for approval)
2. Finds or creates the "Hermes Agent" project on your account
3. Enables Spectrum and reads the project's Spectrum id
4. Registers your phone number as a Spectrum user
5. Prints your assigned iMessage line (the number to text)
6. Runs `npm install` in the sidecar directory

## Credentials Location
- `~/.hermes/.env`: `PHOTON_PROJECT_ID`, `PHOTON_PROJECT_SECRET`
- `~/.hermes/auth.json`: device token and dashboard project id under `credential_pool.photon`

## Authorization Options

### DM Pairing (Default)
Unknown senders receive a pairing code → approve with:
```bash
hermes pairing approve photon <CODE>
```

### Pre-authorize Numbers
```bash
PHOTON_ALLOWED_USERS=+15555554567,+15555556543
```

### Open Access (Dev Only)
```bash
PHOTON_ALLOW_ALL_USERS=true
```

## Mention Gating (Group Chats)
```yaml
gateway:
  platforms:
    photon:
      enabled: true
      require_mention: true
      mention_patterns:
        - '(?i)@?hermes\b[,:\-]?'
```

Or via env vars: `PHOTON_REQUIRE_MENTION`, `PHOTON_MENTION_PATTERNS`

## Starting the Gateway
```bash
hermes gateway start
```

Expected output:
```
[photon] connected — sidecar on 127.0.0.1:8789, streaming inbound over gRPC
```

## Common Issues

| Symptom | Fix |
|---------|-----|
| `sidecar deps : ✗ run hermes photon install-sidecar` | Run `hermes photon install-sidecar` |
| `device token : ✗ missing` | Run `hermes photon setup` to log in |
| `No iMessage line assigned yet` | Re-run setup or check dashboard |
| Sidecar won't start | Verify Node 18.17+ and sidecar install |

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `PHOTON_PROJECT_ID` | from .env | Spectrum project id |
| `PHOTON_PROJECT_SECRET` | from .env | Project secret |
| `PHOTON_SIDECAR_PORT` | `8789` | Loopback port |
| `PHOTON_SIDECAR_AUTOSTART` | `true` | Spawn sidecar automatically |
| `PHOTON_NODE_BIN` | `which node` | Override Node binary path |
| `PHOTON_HOME_CHANNEL` | (unset) | Default space id for cron |
| `PHOTON_ALLOWED_USERS` | (unset) | E.164 allowlist |
| `PHOTON_ALLOW_ALL_USERS` | `false` | Dev only |
| `PHOTON_REQUIRE_MENTION` | `false` | Wake word in groups |
| `PHOTON_DASHBOARD_HOST` | `app.photon.codes` | Dashboard host |
| `PHOTON_SPECTRUM_HOST` | `spectrum.photon.codes` | Spectrum API host |

## Limits
- Free tier: 5,000 messages per server per day
- Free tier: 50 new-conversation initiations per shared line per day
- Inbound attachments: metadata-only (can't read bytes)
- Outbound attachments: supported (images, voice, video, docs)