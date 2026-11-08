# Splash engine — Apple-silicon inference

Splash (github.com/incoai/splash) is a standalone Metal inference engine
built around the Qwen3.8-27B and Qwen3.6-35B-A3B families. It is a separate
server, not a llama-swap backend: `brew install incoai/tap/splash`,
`splash serve --model OWNER/REPO:VARIANT`, then bench the same model with the
same llama-benchy harness against whichever llama-swap twin serves it.

## Measured (2026-10-18, MacBook M5 Pro 20-core)

Swift-1.5 Q4_K_M, pp2048/tg128, 4 runs, same llama-benchy 0.4.0 both arms,
fully isolated (all other engines unloaded and asserted down):

| Engine | Decode (tg128) | TTFT (pp2048) | Prefill note |
|---|---|---|---|
| Splash 1.3.2 | 42.15 ± 3.37 tok/s | 3.03 s | unmeasurable via llama-benchy (prefix cache) |
| llama.cpp (llama-swap bare draft-mtp) | 20.42 ± 1.92 tok/s | 7.50 s | 273.6 t/s |

Ratio: **2.07x decode, ~2.5x TTFT**, same byte-identical weights
(SHA256-matched local GGUF == HF cache blob). Advisory numbers only: bigger
std on Splash (±3.37 vs ±1.92) and 4 runs per arm.

## On/off toggle (MacBook LaunchAgent)

Splash is registered on the MacBook but **off by default** — llama-swap and
`mb-qwen3.8-27b-swift1.5` remain the default path, untouched. Run the Swift
model with Splash only when you want it:

```bash
# START (on demand):
ssh macbook 'launchctl kickstart gui/501/com.prasta.splash-qwen38'
# wait for 'Ready' in ~/.hermes/logs/splash-qwen38.out.log, then use :8100

# STOP (back to llama.cpp default):
ssh macbook 'launchctl bootout gui/501 ~/Library/LaunchAgents/com.prasta.splash-qwen38.plist'
# re-register after bootout (bootout unloads it; bootstrap re-registers without starting):
ssh macbook 'launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.prasta.splash-qwen38.plist'
```

The plist: `~/Library/LaunchAgents/com.prasta.splash-qwen38.plist`, model
`ukisai/Swift-1.5-Qwen3.8-27B-GGUF:Q4_K_M`, port 8100, `--idle-release 10m`
(frees weights after 10 min idle — resident-but-cheap), `--max-memory 40G`
(leave room on the 64 GB box), `RunAtLoad=false` (never auto-starts).
`--idle-release` defaults to 10 m anyway; the plist pins it explicitly.

Why not KeepAlive: a crash during a manual session should not silently
restart the engine and hold 40 GB. `bootout` unloads the registration, so a
manual session is fully torn down; the next `bootstrap` re-registers the
plist without starting it. This is the "run with Splash AND without"
pattern — nothing commits at login, both paths stay one command away.

## Studio deployment (2026-10-23)

The Studio runs TWO Splash 1.4.0 instances as LaunchAgents (user macstudio),
added 2026-10-23. Same on/off pattern as the MacBook — RunAtLoad=false,
KeepAlive=false, manual kickstart only:

| Label | Port | Model | Served id |
|---|---|---|---|
| com.macstudio.splash-qwen38 | 8100 | ukisai/Swift-1.5-Qwen3.8-27B-GGUF:Q4_K_M | ms-qwen3.8-27b-swift1.5 |
| com.macstudio.splash-qwen36-35b | 8102 | unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | ms-qwen3.6-35b-a3b |

Both bind `--host 100.89.133.43` (tailnet, NOT 127.0.0.1 — a discovery script
that probes loopback false-reports DOWN; `explore_engines.py` now probes
tailnet first). Both: `--max-memory 40G`, `--idle-release 10m`, `--no-webui`,
`--served-model-name ms-*` + `--announce-served-name`. Logs:
`~/.hermes/logs/splash-qwen38.{out,err}.log` and
`~/.hermes/logs/splash-qwen36-35b.{out,err}.log`.

llama-swap still serves those same two ids locally (llama.cpp twins with MTP),
so Splash is a parallel endpoint, NOT the default path — nothing routes to
:8100/:8102 automatically. Same as the MacBook convention.

Perf audit 2026-10-23 (Splash 1.4.0, M3 Ultra 60-core):
- Measured short-input decode: qwen38 ~65-82 tok/s at 3.3-4.0
  tok/cycle; qwen36-35b ~334-360 tok/s at 6.7-7.0 tok/cycle. llama.cpp twins:
  ~30.5 / ~125.3 tok/s. Splash ≈ 2x / 2.8x faster, plus 256K native context
  vs the twins' 64K.
- Auto-selected DFlash2 drafts are the CORRECT ones. No fine-tune draft exists
  for Swift-1.5: the packaged SiliconSpecies/Swift-1.5-Qwen3.8-27B-Splash
  ships incoai/Qwen3.8-27B-DFlash2 byte-identical, and its card states
  "Swift-1.5's drafter acceptance matches Swift-1.0's". The lower tok/cycle on
  qwen38 vs the A3B draft is expected, not a misconfiguration.
- ANE FFN split active on the dense 27B (share 0.41; 38.6 vs 61.4 ms per
  2048-row FFN layer), recalibrated cache ~5s; not applicable to the MoE
  (routing stays on GPU; ane_ffn_bytes 0 in /status is normal there).
- int8 KV, full 256K context resident, all experts resident (no SSD
  streaming — weights fit the 40G budget).
- NOT set, by choice: `--persistent-cache` (prefix cache lives in system TMP,
  up to 32 GiB auto quota, wiped on restart), `--language-only` (both load
  ~0.9GB of vision weights), `--idle-release off` (10m idle frees weights;
  an idle instance sits at ~1.5GB resident and the first request pays a
  15-75s reload — parity with llama-swap's ttl 900).
- MacBook caveat from the same day: two boot attempts failed with "not enough
  free memory to start" (macOS reserve protected, system pressure critical)
  while something else held memory — 40G max-memory on the 64GB box is not a
  guarantee of boot when other workloads are resident. Lower --max-memory or
  free memory first.

## Rules and traps

- **`--model` is HF `OWNER/REPO[:VARIANT]` only — no local GGUF path.** The
  `--model` arg accepts an upstream Hugging Face model ref, not a file or
  directory. To bench a fine-tune that already sits on disk, point at the
  upstream repo it came from (e.g. `ukisai/Swift-1.5-Qwen3.8-27B-GGUF:Q4_K_M`);
  Splash reuses the HF hub cache and stores resolved weights under
  `~/Library/Application Support/Splash/models/`. First run fetches a
  matching DFlash2 draft automatically (3.85 GB for the 27B draft) plus the
  target weights (~18 GB for a 27B Q4).
- **Local files land in the HF cache byte-identical.** A half-finished
  download may still be reusable: check
  `~/.cache/huggingface/hub/models--<owner>--<repo>/blobs/` for a blob the
  size of the local GGUF before re-downloading. Observed: the 18.37 GB
  download completed into the cache before the process was killed, so the
  restart reused it and loaded weights in 4 s.
- **The auto-selected draft is trained on the BASE model, not your
  fine-tune.** Acceptance on a fine-tune is unverified, so expected speedup
  is BELOW Splash's advertised 4.5-5.3x for base Qwen3.8-27B (74-92 tok/s).
  Measured 2.07x on the Swift-1.5 fine-tune; cite the repo README only for
  the base model. The Metal kernels alone carry a large gain even when the
  draft's proposals get rejected.
- **Splash's prefix cache poisons llama-benchy's prefill row.** Splash
  reuses cached prefixes automatically, so pp t/s reads absurd (observed
  ~273K t/s) and ttfr is meaningless. Trust the decode (tg) row; for cold
  prefill numbers use a no-cache protocol or label them cached-context only.
- **Check ports with netstat, not lsof.** 8021 on the MacBook is held by
  launchd (invisible to per-user lsof — netstat shows `launchd:1` as the
  listener) and `splash serve --port 8021` fails "Address already in use" on
  a port lsof reports free. 8100 was clean. Test candidates with `netstat
  -anv -p tcp | grep LISTEN` (matches `\.<port> .*LISTEN`).
- **Isolate cross-engine arms.** Both engines on one box share Metal and
  memory. `pkill -f "splash serve"` kills the python wrapper; the native
  engine (`.../engine/splash serve-native ...`) may keep draining for
  several seconds and still hold the GPU — `kill -9` that PID and confirm
  `pgrep -fl splash` is empty before starting the other arm (the protocol's
  "asserted at 0" step).
- **`Ready` is the last log line.** After "Weights loaded" Splash calibrates
  the ANE FFN split (~30 s), then starts serving; `/ready` returns
  `{"status":"ready"}`. The model is resident; `--idle-release off` keeps it
  loaded across idle periods.
- **API is OpenAI-compatible** on the chosen port (Chat Completions,
  Responses, Anthropic Messages), vision ships in the model package unless
  `--language-only`. Agent wrappers exist (`splash hermes` / claude / codex /
  opencode / pi).
- **Engine identity in `/v1/models`**: Splash reports `model`, `name`,
  `description` with a human label plus a `models` array and
  `owned_by: splash`; llama-swap reports `name`/`description` populated from
  config and nothing else. `explore_engines.py` classifies by endpoint name.

## Worked example bits

```bash
brew install incoai/tap/splash
nohup splash serve --model ukisai/Swift-1.5-Qwen3.8-27B-GGUF:Q4_K_M \
  --port 8100 --no-webui > /tmp/splash-bench.log 2>&1 &
# wait for 'Ready' in the log, then:
llama-benchy --base-url http://127.0.0.1:8100/v1 \
  --model ukisai/Swift-1.5-Qwen3.8-27B-GGUF:Q4_K_M \
  --tokenizer Qwen/Qwen3.8-27B \
  --pp 2048 --tg 128 --runs 4 --latency-mode api --exact-tg
# llama.cpp twin arm (isolated, after pkill -9 splash):
llama-benchy --base-url http://100.68.81.83:8999/v1 \
  --model mb-qwen3.8-27b-swift1.5 --tokenizer Qwen/Qwen3.8-27B \
  --pp 2048 --tg 128 --runs 4 --latency-mode api --exact-tg
```

Keep a benchmark of a fine-tune labeled with the draft caveat (base-trained
draft, acceptance unverified) so a later reader does not expect base-model
speedups from a fine-tune arm.
