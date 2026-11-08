# image-gen — local image generation (picker + executor)

Generate images on the local fleet (Mac Studio M3 Ultra, MacBook Pro M5) via
ComfyUI and Unsloth Studio. No cloud image APIs, no tokens beyond the local
Unsloth agent keyfile. Two scripts share one config contract:

- `picker.py` — interactive model menu + settings dialog; emits a request JSON.
- `executor.py` — runs a request against the engine, downloads PNGs, logs every
  run to a history file, and can retry the last failed generation.

## Install

- Python 3.9+ with **PyYAML** (`/usr/bin/python3` on macOS has it; otherwise
  `pip3 install --user pyyaml`). `jsonschema` is optional (used when importable
  for strict request validation; the picker/executor fall back to config-bounds
  + envelope checks without it).
- The engines must be running and reachable (see config.yaml `machines`):
  - Studio ComfyUI at `http://127.0.0.1:8188` (no auth).
  - Unsloth Studio on either machine at `http://127.0.0.1:8888` (bearer key in
    the `auth.keyfile` path; the MacBook is reached over `ssh macbook`).
- Nothing is auto-started or auto-downloaded. Unverified models are listed but
  not offered until a live probe confirms their weights.

## Usage

```sh
# interactive: pick a model, answer the dialogs, pipe straight to the executor
python3 picker.py | python3 executor.py --request -

# scripted (non-interactive)
python3 picker.py --model studio:comfyui:z-image-turbo \
    --prompt "a red tractor in a field" --defaults -o req.json
python3 executor.py --request req.json

# retry the last failed generation (reuses its exact request)
python3 executor.py --retry

# useful flags
python3 executor.py --request req.json --out /tmp/img --quiet
python3 executor.py --retry --history /custom/history.jsonl
```

Exit codes: `0` success, `1` failure, `130` interrupted. Results go to stdout
as JSON; status/progress lines and errors go to stderr (`--quiet` silences the
status lines, not errors).

## History

Every run — success, error, or interrupt — appends one JSON line to the history
file (`defaults.history_file`, default `~/Pictures/image-gen/history.jsonl`;
override with `--history`). Each entry records the timestamp, status, model,
machine, backend, prompt, negative prompt, resolved settings (including the
actual seed used), output paths, elapsed time, and the full request object.
`--retry` reads the last non-success entry and replays its request verbatim, so
a pinned seed is preserved; a `null` seed rolls a fresh random one.

## Configuration (`config.yaml`)

- `defaults` — `output_dir`, `history_file`, `timeout_seconds`, `retries`.
- `machines.<id>` — name, `reachability` (`local` | `ssh`), `ssh_host`/`user`
  for ssh machines, and `backends.<id>` with `base_url`, `auth` (`none` or
  `bearer` + `keyfile`), protocol/notes.
- `models[]` — stable id `<machine>:<backend>:<slug>`, `machine`, `backend`,
  `display`, `availability` (`verified` | `unverified`), `weights` + `graph`
  (ComfyUI) or `repo`/`gguf_filename`/`model_kind` (Unsloth), `server_limits`,
  and a per-setting map (`default`/`min`/`max`/`multiple_of`/`choices`/`note`).

### Adding a new model

1. Pick an existing `machine`/`backend` (or add the machine first, below).
2. Append a `models[]` entry with a stable id, `display`, and a `settings` map.
   Match the backend's `multiple_of` (ComfyUI 8, Unsloth 32) and mark bounds
   `verified` only where the server confirms them.
3. ComfyUI: set `graph.blueprint` (editor JSON, converted via
   `comfy_editor_to_api.py --raw --schema-out` into `graphs/`) or
   `graph.api_graph` (pre-converted API JSON), and list `weights`.
4. Unsloth: set `repo` (+ `gguf_filename` + `model_kind: gguf` for single-file
   GGUF repos) and mirror `server_limits` from `/api/inference/images/status`.
5. Probe it live (ComfyUI `object_info` / Unsloth `images/status`) and run one
   real generation end-to-end.
6. Only then set `availability: verified`. Keep the id forever — renaming
   breaks history and retry.

### Adding a new machine

1. Add `machines.<id>` with `name`, `reachability` (`local` = loopback on this
   host; `ssh` = reachable via `ssh <ssh_host>`), `ssh_host`/`user` for ssh
   machines, and `backends.<id>` (`type` `comfyui`|`unsloth`, `base_url`,
   `auth`).
2. For ssh machines, auth headers must ride a `curl -K-` stdin config over ssh
   (`-H` args don't survive the ssh argv boundary → 401). Never curl a
   loopback `base_url` from the Studio expecting the MacBook's port.
3. Add `models[]` entries referencing `<new-machine>:<backend>:<slug>` and
   verify each as above.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `nothing listening at <url>` | Engine not running. Start ComfyUI (`comfy launch`) or Unsloth Studio; pick the other machine. |
| HTTP 401/403 | Unsloth key drift. The executor tries each `minted[]`/`saved[]` candidate; restart the app to mint a fresh key. |
| HTTP 404 | Endpoint/route not found — server version may not expose it; check config protocol notes. |
| HTTP 503 | Model not loaded yet; the executor loads it first. If it persists, check `images/status`. |
| `no Unsloth key authenticated` | Keyfile empty or all candidates stale; restart Unsloth Studio. |
| `width and height must be equal` | ComfyUI Qwen-Image-2.1-int8 uses a single resolution param. |
| `not a multiple of` | ComfyUI needs multiples of 8, Unsloth of 32. |
| `area limit exceeded` | Unsloth caps output at 4300800 px (e.g. 2752×2752 max). |
| `did not finish within Ns` | Generation exceeded `defaults.timeout_seconds`; raise it or check the queue. |
| `no failed generation in history to retry` | Nothing non-success in the history file; run a request first. |
| History not written | Check `defaults.history_file` is writable; failures only warn to stderr. |
| `settings.steps: N below min` | Request violates the model's config bounds; re-run the picker. |
