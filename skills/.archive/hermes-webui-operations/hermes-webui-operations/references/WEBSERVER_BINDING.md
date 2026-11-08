# Web UI Service Binding on macOS

MacOS Tailscale uses `utun4`, not `tailscale0`.

Do not attempt to bind the HTTP server directly to a Tailscale `100.x.x.x` address. The correct delivery path is:

1. Hermes web UI listens on `127.0.0.1:8787` inside the host.
2. `tailscale serve` maps HTTPS tailnet address to localhost.
3. Tailnet device auth plus web UI password auth form the security boundary.

Client-side check:
- `ifconfig | grep 100.`
- Expect `utun4` active with the Studio tailnet IP.

Server-side binding check:
- `lsof -nP -iTCP:8787 -sTCP:LISTEN`
- Expect localhost only.

## Why terminal output mismatches can happen in Hermes

Separate Hermes terminal sessions can see different service state. After any launchd-managed restart, confirm with the listener check and `tailscale serve status`, not just shell env or expected state.
