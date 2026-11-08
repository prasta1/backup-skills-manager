# Model picker duplication (Downloaded vs Connected)

Verified 2026-11-04 against Unsloth.app 0.1.914-beta / core 2026.11.1 on the Mac Studio.

## The picker's tabs read different data sources

Tabs are Recommended / **Downloaded** / **Connected**. Nothing dedupes across them, so the same
weights appear once per list that covers them.

**Downloaded tab** is built from `GET /api/models/local`, partitioned by each row's `source` field,
with no cross-source dedupe. In `chat-*.js` the sections are separate filters over the same array
and the helpers involved (`aN`, `gN`) only sort:

| `source` | picker section |
|---|---|
| `models_dir` | Local models (scan of `models_dir`) |
| `lmstudio` | LM Studio |
| `custom` | Custom folders (the registered scan folders) |
| `ollama`, `hermes`, `omlx` | Custom folders |
| `hf_cache` | none of these; rendered in the Hub/Unsloth list with a Downloaded badge |

**Connected tab** is `GET /api/providers/` (enabled `llm_providers` rows), each model keyed
`external::<provider_id>::<url-encoded model>`.

## The 2026-11-04 case: 19 models listed three times

Two triggers, benign on their own:

1. **LM Studio's `downloadsFolder` was set to `/Users/macstudio/models/gguf`**, which is also the
directory registered as a Studio scan folder. `lmstudio_model_dirs()` reads
`~/.lmstudio/settings.json` -> `downloadsFolder`, so the same 19 directories came back as 19
`lmstudio` rows AND 19 `custom` rows, with *identical* `id` values (the absolute paths). Every
fleet model therefore appeared twice inside the Downloaded tab, once under "LM Studio" and once
under "Custom folders".
2. **That same directory is what llama-swap serves.** All 20 GGUF dirs under `~/models/gguf` had a
llama-swap entry pointing at them (21 entries total; `ms-minicpm-v-4.7` and `-hires` share one dir),
reachable through the enabled `llama_cpp` provider row, so each also appeared in Connected.

`source: models_dir` was 0 rows throughout: the route resolves `./models` against the backend's cwd,
which is `/`, so `models_dir` is `/models` (nonexistent). The "Local models" section is empty by
construction on this box, not by intent. `hf_cache` held a different set (diffusion pipelines,
embeddings, training bases), so it produced no cross-list twin.

## Levers (pick ONE owner for the fleet)

- Drop the on-device listing: `DELETE /api/hub/scan-folders/{id}` (ids from
`GET /api/hub/scan-folders`; the UI path is the picker's Custom folders folder manager). Removes the
`custom` rows only.
- Drop the LM Studio listing: change the downloads folder in LM Studio's own UI (its default
`~/.lmstudio/models` is usually empty). Removes the `lmstudio` rows only. Studio re-reads
settings.json on each scan, no restart. Prefer the UI over hand-editing the JSON: LM Studio rewrites
that file on quit and will revert the edit.
- Drop the Connected listing: disable the matching `llm_providers` row (`is_enabled = 0`, applies
live, no restart).

Before recommending a side, count the tuning: llama-swap entries carry per-model ctx-size, MTP /
ngram spec flags, `--jinja` and reasoning budgets that an on-device load does not inherit, and
`sushi` (MLX) plus the MacBook's `mb-*` fleet exist ONLY as connections. Counterweight: the bundled
`~/.unsloth/llama.cpp/llama-server` was NEWER than the llama-swap engine at the time of this note
(0.8.0-dev build 11985 vs Homebrew 11960), and Studio's picker exposes per-model context / GPU-layer
config the connection rows do not.

## Reading the real UI without guessing (throwaway Chrome over CDP)

The desktop app is a webview on the same backend, so a headless Chrome against `127.0.0.1:8888`
renders the identical UI. This is the only reliable way to answer "what do I actually see", and it
beats reading the minified bundle.

1. `curl -s -X POST http://127.0.0.1:8888/api/auth/desktop-login -H 'Content-Type: application/json' -d "{\"secret\":\"$(cat ~/.unsloth/studio/auth/.desktop_secret)\"}"` -> `access_token` + `refresh_token`.
2. Launch a scratch Chrome: `--remote-debugging-port=9223 --user-data-dir=<scratch>/uschrome --headless=new --no-first-run about:blank` (background it; the daily Chrome has no debug port, and `screencapture` fails without Screen Recording permission).
3. Drive `ws://127.0.0.1:9223/devtools/page/<id>` (websocket-client is in system python3). Navigate to `/`, then `localStorage.setItem('unsloth_auth_token', ...)` and `('unsloth_auth_refresh_token', ...)`, then reload. A full navigation to `/models` 401s; navigate to `/chat` and use the sidebar's **"Model hub"** button (client-side nav) instead. There are no `<a>` links to route by.
4. Chat picker: click the button whose text is `Select model`, then click the tab by exact text (`On Device`, `Connected`). Read `document.body.innerText`.
5. Model hub On Device tab: click sidebar `Model hub`, then the `On Device` tab (URL becomes `/hub?tab=downloaded`).
6. Both lists are **virtualized**: `document.body.innerText` only shows rendered rows. Scroll `[data-hub-scroll]` in steps and accumulate rows.

### What each surface actually renders (2026-11-04, after both local sources were removed)

- Chat picker -> On Device: 13 rows. `UNSLOTH` = `Qwen3.6-35B-A3B-GGUF`, `Qwen3.5-4B-MTP-GGUF`; `OTHER MODELS` = Qwen3.5-9B, 2x incoai DFlash2, qwen3.6-35b-a3b-vl-mtp-mxfp8, BAAI/bge-m3, google/embeddinggemma-2, 4x mlx whisper. `FINE-TUNED` and `CUSTOM FOLDERS` empty.
- Model hub -> On Device: 11 rows, same two Unsloth GGUFs plus Qwen-Image-2.1-Turbo(-GGUF), Qwen3.5-9B, the incoai drafts, flint, mxfp8.
- Both are `hf_cache` rows from `/api/hub/local`, i.e. **Studio's own HF cache** (`~/.cache/huggingface/hub`), NOT the scan folder. Removing scan folders cannot empty this list; only deleting cached repos (hub row -> delete) or moving the cache home can.
- Two of those rows are the same weights llama-swap serves: `unsloth/Qwen3.6-35B-A3B-GGUF` shares an inode with `~/models/gguf/unsloth/Qwen3.6-35B-A3B-MTP-GGUF/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf` (the retired non-MTP repo name, hardlinked to the MTP file), and `unsloth/Qwen3.5-4B-MTP-GGUF` is the repo `ms-qwen3.5-4b-mtp` loads. Verify with an inode comparison before calling a cached repo a duplicate; `du` alone is misleading (the hardlink twin shows 23 GB but adds no disk).
- UNRESOLVED: the hub header counters read `17 Cache / 20 Local` while the API returns 29 `hf_cache` rows and 0 local-source rows, and the list renders 11. Do not trust those two numbers as model counts until someone reconciles them.

## Minting a token to probe the API

```
curl -s -X POST http://127.0.0.1:8888/api/auth/desktop-login \
  -H 'Content-Type: application/json' \
  -d "{\"secret\":\"$(cat ~/.unsloth/studio/auth/.desktop_secret)\"}"
```

Returns `{"access_token": ..., "refresh_token": ...}`. Use `Authorization: Bearer <access_token>`.
Drive it with curl; python-urllib clients get 401 with the same token. Every other `/api/*` route is
401 without it. `/openapi.json` is the authoritative route list.
