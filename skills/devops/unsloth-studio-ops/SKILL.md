---
name: unsloth-studio-ops
description: "Audit/upgrade Unsloth Studio on this Mac Studio. Use on update/review/config asks."
---

# Unsloth Studio Ops

Review, edit, and troubleshoot the **Unsloth Studio** web app (AGPL tuning IDE — NOT Jupyter) that runs on Patrick's Mac Studio. Triggers on "review my unsloth config", "why does unsloth reference LM Studio", "fix the unsloth provider", "unsloth won't start", or "unsloth 500 on chat projects".

## Where it lives
Unsloth Studio runs on **this machine** (the Mac Studio, user `macstudio`). Everything below runs locally; no `ssh` hop. Most reviews are read-only; confirm before making any change.

> **2026-10-23: desktop app replaced the launchd server.** `/Applications/Unsloth.app` (0.1.909-beta, bundle `ai.unsloth.studio`) is now the Studio install, and it manages its own backend: bundled venv runs `unsloth studio --api-only -H 127.0.0.1 -p 8888` (loopback only). The `com.unsloth.studio` launchd agent + `start-studio.sh` tailnet-bound (`studio.taile85139.ts.net:8888`) shape documented below is RETIRED — no plist, no launchd job. Liveness check is now `curl http://127.0.0.1:8888/api/health` (loopback), not the tailnet URL. The CLI is installed too: `~/.local/bin/unsloth` → symlink to `~/.unsloth/studio/unsloth_studio/bin/unsloth` (bundled venv, core `2026.10.8`), on PATH (`~/.local/bin` is in .zshrc/.zprofile/.profile); commands: train, inference, chat, export, eval, list-checkpoints, doctor, run, install-kernels, studio, start, mcp. Same venv as the app, so versions track together.

> 2026-10-01: the MacBook is no longer an inference peer for Hermes (single engine is llama.cpp via llama-swap on the Studio, see MEMORY.md). The `MacBook` LM Studio provider row described below is historical; if it is still present, treat it as a candidate for removal rather than a thing to keep alive.

## Config is SQLite, not a file
The app config is a SQLite DB at `~/.unsloth/studio/studio.db` — there is **no yaml/toml to edit**. Key tables:
- `llm_providers` — the LLM backend endpoints (this is what "references LM Studio").
- `chat_projects` — project workspaces; holds `root_path` (see trap below).

### `llm_providers` schema gotcha
Full verified column set (`PRAGMA table_info`, 2026-10-04): `id`(TEXT), `provider_type`(TEXT), `display_name`(TEXT), `base_url`(TEXT), `is_enabled`(INTEGER), `created_at`(TEXT), `updated_at`(TEXT), `models_json`(TEXT, default `'[]'`), `available_models_json`(TEXT, default `'[]'`), `max_output_tokens`(INTEGER), `api_type`(TEXT, default `'chat_completions'`).

**Do NOT assume `name` / `enabled` columns** — a `SELECT ... WHERE name=...` or referencing `enabled` fails with "no such column". Same trap on other tables: `auth_user` has no `updated_at`, `credential_secrets` has no `id`. Always `PRAGMA table_info(<table>);` first, or select `display_name`/`is_enabled`.

### Live edits need no restart
The server opens per-request SQLite connections under WAL. A direct `UPDATE llm_providers SET display_name='llama-swap' WHERE display_name='MacStudio';` applies immediately — no server restart. API keys are **never** stored server-side (browser holds them RSA-encrypted per request), so there is nothing secret to scrub from the DB.

## Cross-machine root_path trap
`chat_projects.root_path` stores an absolute path. A row carrying a **laptop** path (`/Users/prasta/...`) makes `ensure_chat_project_workspace()` try to `mkdir` up to `/Users/prasta`, raise `PermissionError`, and **500 the entire `GET /api/chat/projects` list** — not just that project. When migrating or reviewing the DB, verify every `root_path` is `/Users/macstudio/...` (Studio-native). If you see `prasta` paths, that DB was written on the laptop and must be path-rewritten before use.

## launchd shape
Verified 2026-10-04 (server was re-enabled this session):
- `~/Library/LaunchAgents/com.unsloth.studio.plist` — **present and loaded** as `com.unsloth.studio`. `RunAtLoad:true` + `KeepAlive:true`, execs `~/.unsloth/studio/start-studio.sh`, stdout/stderr → `~/.unsloth/studio/logs/launchd.{out,err}.log`, `WorkingDirectory` `~/.unsloth/studio`, `ProcessType:Interactive`.
- Between 2026-09 and 2026-10-04 the plist and the job were **absent entirely** (not merely disabled) — the app was fully retired. If you ever find no `launchctl list | grep unsloth` output and no plist, that is the retired state, not a broken install.
- `start-studio.sh` polls `tailscale ip -4` (up to 5 min) before binding `-H <TSIP>:8888`. This avoids a crash-loop if launchd starts before tailscaled assigns the address. Bind is **tailnet-only** (not `0.0.0.0`) — keeps the UI off the LAN and the `--cloudflare` tunnel off. Because the wrapper resolves the IP live, a tailnet IP change needs no plist edit.
- `~/Library/LaunchAgents/com.unsloth.logrotate.plist` — **still absent** (never restored). Audit flagged REMOVE: launchd is the wrong home for logrotate; the server holds fds open so rename-style rotation would not work anyway. The purpose-built `~/.unsloth/studio/rotate-logs.sh` does copy-truncate instead and is the correct fix if you wire it to a daily timer. `logs/` reached 31 MB with a 7 MB `.1` while unattended.

### Bootstrapping the job
`launchctl bootstrap gui/$(id -u) <ABSOLUTE_PATH>` — modern syntax, no `load`/`unload`. **A relative plist path fails with `Input/output error` (errno 5)** even when `plutil -lint` passes and the file's mode/owner/xattrs match a working plist byte for byte. Do not go chasing permissions when you see that error; check the path first.

Verify the bind is genuinely tailnet-only — both of these MUST be refused:
```
lsof -nP -iTCP:8888 -sTCP:LISTEN     # expect TCP <tailnet-ip>:8888, never 0.0.0.0 or *:8888
curl -s -o /dev/null -w '%{http_code}\n' --max-time 6 "http://127.0.0.1:8888/api/health"    # expect 000 / refused
curl -s -o /dev/null -w '%{http_code}\n' --max-time 6 "http://$(ipconfig getifaddr en0):8888/api/health"  # expect 000 / refused
```
`/api/health` returning `{"status":"healthy",...}` over the tailnet IP is the liveness check. Unauthenticated `/api/*` routes correctly return **401**, not 404 — a 401 means the server is fine and you are simply not logged in.

## The "why does it reference LM Studio" answer — HISTORICAL
The `MacBook` → `https://macbookpro.taile85139.ts.net:1234/v1` row (laptop LM Studio over tailnet) **no longer exists**. Verified gone 2026-10-04. It was superseded by a llama.cpp row, matching the single-engine architecture in MEMORY.md. If you are reading a report that swears this row is there, re-run the query — the report predates the change.

Actual `llm_providers` as of 2026-10-04:

| display_name | provider_type | base_url | on |
|---|---|---|---|
| Mac Studio M3 Ultra | `llama_cpp` | `https://studio.taile85139.ts.net:9292/v1` | yes |
| OpenRouter | `openrouter` | `https://openrouter.ai/api/v1` | yes |
| OpenRouter | `openrouter` | `https://openrouter.ai/api/v1` | no |
| llama-swap-mbp | `custom` | `http://macbookpro.taile85139.ts.net:8999/v1` | no |
| llama-swap-studio | `custom` | `http://127.0.0.1:9292/v1` | no |

Notes:
- `llama-swap-mbp` is llama.cpp on the MacBook, **not** LM Studio — the port moved 1234 → 8999 and the engine changed. It is disabled, which is correct: the MBP is no longer a Hermes inference peer as of 2026-10-01.
- Two rows point at the same Studio llama-swap backend under different names (tailnet HTTPS enabled, loopback disabled), and OpenRouter is duplicated enabled+disabled. Harmless, but it means "which row is authoritative" has no single answer — check `is_enabled` before assuming.
- A separate, unrelated LM Studio mention survives in a beginner curriculum doc `~/Documents/Unsloth Studio/Projects/Intro-to-AI-*/sandbox/resources.md` that lists it as a local-LLM tool. Harmless.

### MacBook provider reliability (historical, applies only to the old `:1234` LM Studio row)
The old laptop LM Studio was **interactive-only** (GUI-gated): `com.lmstudio.watchdog` (RunAtLoad + StartInterval 300) restarted the server *only when the GUI app was open*. So `MacBook` provider requests failed whenever the laptop's LM Studio GUI was closed. **Do not** re-enable a headless LM Studio service on the laptop — the user deliberately removed it. Irrelevant now that the row is gone; do not resurrect it.

### MacBook provider reliability
The laptop LM Studio is **interactive-only** (GUI-gated). `com.lmstudio.watchdog` (RunAtLoad + StartInterval 300) restarts the server *only when the GUI app is open*; `autoStartOnLaunch:true` in `~/.lmstudio/.internal/http-server-config.json` starts it on app launch. So `MacBook` provider requests fail whenever the laptop's LM Studio GUI is closed. **Do not** re-enable a headless LM Studio service on the laptop — the user deliberately removed it. If the user wants `MacBook` always-on, surface the tradeoff; the fix is re-adding a headless daemon, which contradicts the stable design.

## Verification checklist (read-only review)
```
DB=~/.unsloth/studio/studio.db
sqlite3 -header -column "$DB" "SELECT display_name, provider_type, base_url, is_enabled FROM llm_providers;"
sqlite3 -header -column "$DB" "SELECT name, root_path FROM chat_projects;"
launchctl list | grep unsloth
```

## Version / upgrade pitfall (HISTORICAL — fixed upstream in core 2026.9.14)

**Do not expect this to reproduce.** As of core `2026.9.14`, `unsloth/__init__.py` no longer aliases `__version__` to the zoo — line ~263 imports from `._version`, line ~1607 from `._gpu_init`. So `import unsloth` now reports the **core** version, and core/zoo can sit at different versions without confusing the reported string. Verified 2026-10-04: core dist-info `2026.9.14`, `unsloth_zoo` `2026.9.9`, `import unsloth` → `2026.9.14` (matches core).

The rest of this section is retained because the verification habit is still the right way to answer "is my core current", and because an older install can still exhibit it. The original mechanism: `unsloth/__init__.py` did `__version__ = unsloth_zoo.__version__`, so the string from `import unsloth` was the **zoo's** version, not the core's.

- Symptom: `pip install -U unsloth==2026.8.8` reports "Requirement already satisfied" yet `import unsloth` still prints `2026.8.5`.
- Cause: the core released ahead of `unsloth_zoo` on PyPI (the zoo version may lag the core). pip installed core 2026.8.8, saw `unsloth_zoo>=2026.8.5` satisfied by 2026.8.5, and stopped. No `unsloth_zoo==2026.8.8` exists to pull.
- **This is NOT broken.** Prove the *core* is current by reading `unsloth-<ver>.dist-info/METADATA` `Version:` in the venv. That's the dist-info the running process loaded. Also confirm the live server PID maps to that venv (`ps -o command -p <pid>`).
- Fix: wait for the matching `unsloth_zoo` release, then a plain upgrade in the bundled venv flips the reported version. **Never hand-edit `__version__`** in source — it masks the real zoo version and can fool future upgrade logic.

### Upgrade location matters
Unsloth Studio ships the package in a **bundled venv**, not system site-packages: `~/.unsloth/studio/unsloth_studio/lib/python3.13/site-packages/`. Use that venv's pip/python — `~/.unsloth/studio/unsloth_studio/bin/pip install -U unsloth`. System `pip show unsloth` → "not found" is expected; this is not the install target. Watch the torch pin (`torch<2.12.0`, venv carries 2.10.0) — an upgrade that drags in a newer torch can break the running server.

## Pitfalls
- Don't edit a yaml/toml that doesn't exist — it's SQLite.
- Don't hardcode column names in sqlite queries (`display_name`/`is_enabled`, not `name`/`enabled`), and don't assume a column set you read from another table — `auth_user` has no `updated_at`, `credential_secrets` has no `id`. `PRAGMA table_info` first.
- Don't infer that two `app_settings` rows conflict — `model_memory_keep_resident` silently vetoes the idle TTL. Read `_residency_vetoes_unload()` before calling a config self-contradictory.
- Don't hand-write `openai_api_auto_unload_idle_seconds` into `app_settings` with sqlite — the 60s floor is UI-side validation only, so a stored 30 silently means 60.
- Don't `launchctl bootstrap` with a relative plist path; it fails with `Input/output error` even when `plutil -lint` passes. Absolute path, modern syntax.
- Don't treat an empty `launchctl list | grep unsloth` as a broken install — that was the retired state for ~a month before 2026-10-04.
- Don't `launchctl bootout` or edit the plist to change KeepAlive without confirming on-demand vs always-on with the user.
- Don't re-enable headless LM Studio on the laptop, and don't resurrect the removed `MacBook` `:1234` provider row.
- Don't "fix" the reported version by editing `unsloth/__init__.py` or `_gpu_init.py` — it hides the real zoo version.
- Don't run `pip install -U unsloth` against system pip to "fix" the version — it won't touch the bundled venv.
- Don't guess API route names from the DB schema; read `openapi.json` off the live server.
- Authoritative "what it is" detail (admin user, password reset, tailnet bind rationale) lives in the memory reference `reference_unsloth_studio.md` — read that for recovery paths, not for the ops procedure here.
- Don't diagnose "duplicate models in the picker" as one bug. It is three independent lists; see the picker-duplication section.
- Don't edit LM Studio's `~/.lmstudio/settings.json` by hand if LM Studio is installed: it rewrites the file on quit. Change the folder in its UI, or accept that your edit may be reverted.
- The bundled `~/.unsloth/llama.cpp/llama-server` can be NEWER than the llama-swap engine (0.8.0-dev build 11985 vs Homebrew 11960 on 2026-11-04). Check both before calling on-device "the older engine".

## Model memory residency controls (defaults are all off)

These are **not** in a yaml/toml — they live as rows in `app_settings` (SQLite) and default to False/0. They're read at model-load time via `model_memory_settings.py` and `openai_auto_switch_settings.py`.

| DB key | Default | Effect | llama.cpp flag |
|---|---|---|---|
| `model_memory_keep_resident` | `false` | Page-lock the model in VRAM after load (`--mlock`); **vetoes every idle TTL** (see below) | `--mlock` |
| `model_memory_no_ram_reserve` | `false` | Keep default mmap path (no `--mlock`); drop `--no-mmap` | (drops flag) |
| `openai_api_auto_switch_model` | `false` | Auto-load a GGUF named in `/v1` requests before serving | (runtime load) |
| `openai_api_auto_download_model` | `false` | Download a missing GGUF repo named in `/v1` requests | (runtime dl) |
| `openai_api_auto_unload_idle_seconds` | `0` (off) | Unload loaded model after N idle seconds (0 or >=60 only; min 60) | `--unload` on idle |
| `openai_api_auto_unload_keep_kv` | `true` | Persist KV cache to disk on idle unload | slot-save |
| `openai_api_auto_unload_api_only` | `false` | Only idle-unload models loaded via API, spare UI-loaded ones | (runtime filter) |

### Residency vetoes every idle TTL — read before tuning

`model_memory_keep_resident = true` makes the effective idle-unload TTL **0 (never unload)** regardless of what `openai_api_auto_unload_idle_seconds` says. The stored number is preserved and returns when residency is turned off. This is designed precedence, **not** a contradiction to "fix".

```python
# openai_auto_switch_settings.py
def _residency_vetoes_unload() -> bool:
    """Model Memory residency pins the weights, so no idle TTL applies."""
    return bool(get_keep_resident())

def get_auto_unload_idle_seconds() -> int:          # ~line 183
    if _residency_vetoes_unload():
        return 0
    stored = _stored_idle_seconds()
    if stored is not None:
        return _apply_idle_floor(stored) if get_openai_auto_switch_enabled() else 0
    env = _env_idle_seconds()                        # UNSLOTH_MODEL_IDLE_TTL
    return env if env is not None else 0
```

Two different readers, and using the wrong one misdiagnoses:
- `get_auto_unload_idle_seconds()` — **effective**, veto applied. What the idle loop runs on.
- `idle_unload_is_configured()` — the user's **stored** setting, veto deliberately ignored. Anything deciding whether to DISCARD saved KV state uses this, so enabling residency does not look like "idle unload was never configured" and silently drop cached context. Never read the effective `0` as "the setting is off".

**Never infer a conflict by reading two `app_settings` rows side by side.** Read the reconciling code, or query the effective value. Doing exactly this produced a confidently wrong "these two settings contradict, zero the timer" call on 2026-10-04.

### Where these live in the UI

`Settings → Model auto-switch (OpenAI API)`:
- **Idle auto-unload** — seconds field. Hint: "Free VRAM after this many idle seconds. 0 keeps it loaded, minimum 60."
- Keep chat context across idle unload → `openai_api_auto_unload_keep_kv` (KV to disk, up to 10 GB)
- Only unload models loaded by the API → `openai_api_auto_unload_api_only`
- Switch model by request → `openai_api_auto_switch_model`
- Switch image and video model by request → has its **own** idle TTL (`get_media_auto_unload_idle_seconds`), deliberately NOT inherited from the chat one, so upgrading does not start evicting image/video pipelines for anyone who had chat idle-unload on. Residency vetoes it the same way.

`Settings → Model memory` (lowercase "memory" — not "Model Memory"):
- Keep model in GPU memory → `model_memory_keep_resident`; its hint reads "Turns off idle auto-unload"
- Don't reserve system RAM for the model → `model_memory_no_ram_reserve`

### The 60s floor is enforced on UI write only

`_apply_idle_floor()` maps `<= 0` to 0 and raises anything in `(0, 60)` up to 60, so only **0 or >= 60** are honored — 30 does not mean 30, it means 60. The UI enforces the same rule ("Enter 0 to keep the model loaded, or at least 60 seconds"). **Writing `app_settings` with sqlite bypasses that validation**, leaving a stored `30` that looks valid while the reader silently uses 60. Validate by hand if you edit the table directly.

### Apple Silicon VRAM budget resolution

On macOS, Studio probes the Metal/GPU budget via `_apple_metal_memory_budget_bytes()` in `llama_cpp.py` (~line 5359):
1. Import `mlx.core` → read `mx.device_info()["max_recommended_working_set_size"]`
2. If MLX fails → fall back to `psutil.virtual_memory().total` (full RAM)
3. Multiply by `_APPLE_UNIFIED_MEMORY_FRACTION = 0.85`

The GPU selection logic at load time (`llama_cpp.py` ~line 11788):
- **Auto mode** (default): if the model fits within the Apple VRAM budget → emits `-ngl -1 --fit off` (full GPU, no auto-fit). If it doesn't fit → emits `--fit on` (llama.cpp auto-sizes the offload between GPU and system RAM).
- **Manual mode**: user specifies `gpu_layers` in the model picker. Studio emits `--gpu-layers N --fit off`. `-1` means all layers.

For a 22GB model (Qwen3.6-27B Q4_K_M) on a 64GB MacBook Pro: Studio will likely emit `--fit on` and let llama.cpp spill overflow layers to unified RAM. On the 96GB Studio, it may fit entirely in VRAM with `-ngl -1 --fit off`.

### Checking these settings

```bash
# Check DB for persisted model-memory settings
sqlite3 ~/.unsloth/studio/studio.db "SELECT key, value_json FROM app_settings WHERE key LIKE '%model_memory%' OR key LIKE '%auto_switch%' OR key LIKE '%auto_unload%' OR key LIKE '%idle%';"

# If none appear, defaults (all off) are in effect — this is the fresh-install state.
```

### Tuning recommendation for large-model work

On a 64GB+ MacBook Pro or 96GB Studio, flip `model_memory_keep_resident` ON via the UI (`Settings → Model memory → "Keep model in GPU memory"`). This page-pins weights and prevents between-request re-fault latency on large GGUFs. Safe when you have ≥3× the model size in RAM; unsafe on 16GB machines.

Enabling it **silently disables idle auto-unload** (see the veto above). Usually what you want on a big unified-memory box — one resident model, no re-fault — but it means any `openai_api_auto_unload_idle_seconds` already set stops having effect until residency goes off. Tell the user when you recommend it rather than leaving them to notice a dead field later.

### API route names

Providers/models are **not** `/api/llm-providers`. Live routes live under `/api/inference/*` (`models`, `loaded-models`, `models/{model_id}`) and `/api/hub/*` (`models-folder`, `cached-models`, `cached-gguf`, `hidden-models`), plus `/api/chat/projects`. Get the authoritative list from the running server: `curl -s http://<tailnet-ip>:8888/openapi.json`.

## Model picker: why one fleet shows up two or three times

The Downloaded tab and the Connected tab read different sources (local scan vs `llm_providers`) and nothing dedupes across them, so the same weights appear once per list covering them. The Downloaded tab itself also splits one directory into two sections when both LM Studio's `downloadsFolder` and a Studio scan folder point at it. Counts, the exact per-source section map, the levers, and the token-minting recipe for probing the API: `references/model-picker-duplication.md`. Check that before answering any "duplicate models" or "why is this model listed twice" ask.

## MacBook desktop-app diffusion API (learned 2026-10-14)

The laptop runs Unsloth.app (`0.1.907-beta`, backend `unsloth 2026.10.3`) at `~/.unsloth/studio/` with a manual `--api-only -H 127.0.0.1 -p 8888` backend beside the app. Distinct from the Studio tailnet server; the routes below are the same product surface.

- **Auth whack-a-mole**: the desktop app periodically re-mints auth sessions and invalidates tokens issued elsewhere. With the app running, API tokens 401 mid-run. **Quit the app before scripted generation** — it is a viewer only and cannot see the manual backend's state anyway. `agent_api_key.json` works for `/status`/`/models` GETs but NOT `/generate`; `/api/auth/desktop-login` with `~/.unsloth/studio/auth/.desktop_secret` is the only token `/generate` accepts.
- **The backend filters python-urllib clients**: a byte-identical request via urllib gets 401 `Not authenticated` while curl succeeds with the same token. Header tweaks (UA, Accept-Encoding, Connection) don't fix it. **Drive HTTP through `curl` subprocesses**; Python only for JSON assembly — and use `json.dumps(..., separators=(",",":"))` to match the compact body shape.
- **fp8/fp16 text-encoder quantization needs NVIDIA/AMD** (Ampere sm_80+) — on Apple silicon omit `text_encoder_quant` entirely; the load endpoint refuses `fp8` with a clear error.
- **API load of an edit-GGUF silently pulls ~30 GB of companion files** (text encoder + VAE) on top of the 13 GB quant. Always get explicit approval before kicking off a load that downloads. Gate large downloads like any other irreversible-cost action.
- **`generate` carries the edit workflows**: fields `workflow` (`edit`/`reference`/`outpaint`), `init_image`/`mask_image`/`reference_images` (base64 data URLs, ≤32 MB), `strength`, `localized_edit`, `upscale`. Response: `images[].id` → artifact lands at `~/.unsloth/studio/images/<id>.png`.
- **Timeout semantics**: a curl `-m` cut aborts the *client*, not the server job — orphaned renders keep computing and land in the gallery after your connection dies. Probe-test small renders leave junk images behind; clean `~/.unsloth/studio/images/` after auth debugging.
- **Idle-unload**: the Q8_0 base load unloads after TTL (15 min) — recheck `/api/inference/images/status` and reload before a rerun batch.
- **macOS sleep kills renders**: a long denoise crossing the display-idle timer gets system sleep and the job returns `"Diffusion generation was cancelled"` with no artifact (battery `displaysleep=2` min). Wrap renders in `caffeinate -di python3 run_x.py` — the runner survives, the pixels don't come back.

## References
- `references/live-config-2026-08-08.md` — the actual `llm_providers` rows and launchd plist contents captured this session, for diffing future state.
- `references/version-aliasing.md` — full diagnostic sequence for the `__version__` zoo-aliasing trap (proof the core is current despite a stale import string).
- `references/model-memory-settings.md` — session-specific detail: traced code paths, Apple Silicon VRAM resolution, and auto/manual offload branching.
- `references/model-picker-duplication.md` — why one fleet lists two or three times: picker section-to-source map, the LM Studio `downloadsFolder` trap, and the levers to pick a single owner.
