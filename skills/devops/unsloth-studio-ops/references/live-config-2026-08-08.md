# Unsloth Studio — live config snapshot (2026-08-08)

Captured from the Mac Studio (`studio.taile85139.ts.net`, user `macstudio`) via `ssh studio`. Read-only review; one live edit applied (rename `MacStudio` → `llama-swap`).

## llm_providers (after edit)
Columns: id(TEXT), provider_type(TEXT), display_name(TEXT), base_url(TEXT), is_enabled(INTEGER)

| display_name | provider_type | base_url                                  | is_enabled |
|--------------|--------------|-------------------------------------------|------------|
| MacBook      | custom       | https://macbookpro.taile85139.ts.net:1234/v1 | 1          |
| OpenRouter   | openrouter   | https://openrouter.ai/api/v1              | 1          |
| llama-swap   | custom       | http://127.0.0.1:9292/v1                  | 1          |

Notes:
- `MacBook` = laptop LM Studio over tailnet/HTTPS (only LM Studio tie). Interactive-only; fails when laptop GUI closed.
- `llama-swap` = Studio's local endpoint (LM Studio was removed from the Studio). Renamed from `MacStudio` this session.
- `OpenRouter` = cloud fallback, built-in provider_type.

## chat_projects.root_path (cross-machine trap check — all Studio-native, OK)
| name        | root_path                                                            |
|-------------|---------------------------------------------------------------------|
| Purina      | /Users/macstudio/Documents/Unsloth Studio/Projects/Purina-46b90dac  |
| Halo        | /Users/macstudio/Documents/Unsloth Studio/Projects/Halo-007fe0a2    |
| Intro to AI | /Users/macstudio/Documents/Unsloth Studio/Projects/Intro-to-AI-b4a1378e |
| Job Search  | /Users/macstudio/Documents/Unsloth Studio/Projects/Job-Search-84131d3b |

No `/Users/prasta/...` (laptop) paths → DB is Studio-native, no 500 risk on migration.

## launchd plists
- `com.unsloth.studio` — RunAtLoad + KeepAlive(true), execs start-studio.sh. Binds tailnet IP :8888. Audit: considered "wrong shape" for a non-daemon; still set AlwaysOn as of this date.
- `com.unsloth.studio/start-studio.sh` — polls `tailscale ip -4` (60×5s) before `unsloth studio -p 8888 -H <TSIP>`. Avoids launchd-vs-tailscaled crash loop.
- `com.unsloth.logrotate` — StartCalendarInterval 04:30 daily. Audit: flagged REMOVE (launchd wrong home for logrotate).

## DB path
/Users/macstudio/.unsloth/studio/studio.db (SQLite, WAL, per-request connections — live edits need no restart)
