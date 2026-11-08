# Field derivations and known fleet facts

Every field in `catalog.json` is read from config, measured from disk, or left
`null`. This file records how each one is derived so a surprising value can be
traced to its source instead of trusted.

## Derived from `cmd:` (authoritative)

| Field | Source flag | Notes |
|-------|-------------|-------|
| `gguf_path` | `--model` | Absolute path from the config |
| `mmproj_path` | `--mmproj` | Absent = text-only |
| `ctx_size` | `--ctx-size` | Total context, not per-request |
| `parallel` | `--parallel` | Concurrent slots per model |
| `spec_type` | `--spec-type` | `ngram-simple`, `draft-mtp,ngram-simple`, etc. |

The `mtp` column in the table shows `mtp` only when `spec_type` contains `mtp`.

## Measured from disk (authoritative)

`gguf_size_gb` / `mmproj_size_gb` are measured in GiB. These override any size
written in the description prose. `granite-4.2-3b` advertises 2.2GB and
measures 2.09; that is rounding, not a conflict.

A directory-backed engine (sushi's MLX pack) is summed recursively —
`os.path.getsize` on a directory returns the directory entry size, which made
sushi report `0` until 2026-10-23. It now reports the measured 64.8 GiB.

## Multi-host

Rows are tagged `host: studio` or `host: macbook`. The MacBook config is read
from `/Volumes/prasta/.hermes/llama-swap/config.yaml` only while that share is
mounted; when it is not, the MacBook fleet is skipped with a warning (never a
failure). MacBook `--model` paths are written for `/Users/prasta/...` and are
translated to `/Volumes/prasta/...` before touching disk; the original path is
kept in `gguf_path` and the translated one in `gguf_resolved`.

## Usage history

`usage` (`requests`, `input_tokens`, `output_tokens`, `last_used`) is read from
llama-swap's `activity.sqlite` — the Studio's in place, the MacBook's (when
mounted) copied to scratch first because an SMB-hosted WAL-mode sqlite cannot
be opened in place. A model absent from every log gets `has_usage: false`,
never a zero guess. The HTML viewer exposes `Reqs` and `Last used` as sortable
columns and offers `no bench` / `no usage` / `cold` (neither) filter chips so
unmeasured, unused models float to the top.

## Heuristic (leave `null` rather than guess)

- `quant` — regex over the GGUF filename stem.
- `params_total_b` — leading `\d+B` in the stem.
- `params_active_b` — an `A3B`/`E4B` token, else `(\d+)B active` in the
  description.
- `arch` — **read from the GGUF header first**, via `gguf_arch()`: it parses
  `general.architecture` and `<arch>.expert_count` out of the metadata KV
  block, so it is a measurement and it outranks every name heuristic. Only
  when the weights cannot be read (directory-backed engines like the sushi MLX
  pack, or a file absent on the reading host) does it fall back to the older
  path: `moe` if an active-count token is present, else `dense`, with the
  audited `ARCH_OVERRIDES` list winning (gemma-4-e4b, gpt-oss-20b,
  kat-coder-v2.5, laguna-xs-2.1, sushi, ...). An earlier bug looked up
  `ARCH_OVERRIDES.get("", ...)` and silently dropped every override, so
  gpt-oss-20b and sushi reported `dense`; and the name-only path mis-called
  `ms-kat-coder-v2.5` and `ms-laguna-xs-2.1` dense while calling
  `ms-qwen3.5-4b-mtp` MoE, whose header carries no `*.expert_count` at all.
- `capabilities` — from the model **id** and group only. The description is
  never consulted; see below.

### Why the description is not consulted for capability

The first version matched the free-text description and got it visibly wrong:

- `ms-gemma-4-26b-moe` → "code", because the pattern `cod` matched somewhere
  in the prose.
- `ms-gpt-oss-20b` → "extraction", because its description says "Hindsight
  memory **extraction**/consolidation bakeoff".

Prose is where provenance and decisions live, not taxonomy. The id and the
group are the only stable signals. A model can carry more than one capability
(devstral is `code+vision`), so the field is a list, not a scalar.

## Known `null` values and why they are left alone

| Model | Null field | Reason |
|-------|-----------|--------|
| `ms-gemma-4-e4b` | `params_total_b` | "E4B" states 4B *active*; the total is never stated |
| `ms-bge-*` | both | BGE encoders are conventionally not described in B |
| `ms-kat-coder-v2.5` | both | Filename is `KAT-Coder-V2.5-Dev`, no size token |
| `ms-glm-4.6-vision` | both | `GLM-4.6V-Flash`, no size token |
| `ms-muse-glimmer-30b` | `params_active_b` | 30B stated, MoE active count not |

Filling these in by hand would make the catalog a second source of truth,
which is the exact failure this tool exists to prevent. If you learn a real
number, put it in the config description and re-derive.

## The naming defect this catalog exposes

A digit in an id does not mean one thing across the fleet:

- `ms-granite-4.2-3b` — 3B **dense**.
- `ms-gemma-4-e4b` — 4B **active** of a larger MoE.
- `ms-qwen3.5-4b-mtp` — 4B **dense** with an MTP head. "MTP" is multi-token
  prediction, not an expert layout: the header carries no `*.expert_count`.
- `ms-qwen3.6-35b-a3b` — 35B total, 3B active.
- `ms-gpt-oss-20b` — 20B total, 3.6B active.
- `ms-kat-coder-v2.5`, `ms-laguna-xs-2.1` — 256-expert MoE each, with nothing
  in the name to say so.

`total_b` and `active_b` are separate columns precisely so this ambiguity is
visible instead of baked into the key. Do not "fix" it by renaming; the ids
are referenced by skills, crons, and watchdogs, and the 2026-09-10 rename
already demonstrated the cost.

## Unsloth "UD" quants: the name overstates the precision

A `UD-Q4_K_XL` filename is Unsloth's *dynamic* quant label, not a uniform
precision. The actual file is a mixed-precision layout dominated by 3-bit
Q3_K_M with Q4_K_S, Q3_K_L, and IQ2_XS tensors — so it lands barely above a
plain Q4_K_M/Q4_K_S in size, and is effectively *lower* average precision than
a uniform 4-bit quant despite the "XL" name. Verified 2026-10-22 on
`ms-devstral-24b` (UD-Q4_K_XL: 179 Q3_K_M / 58 Q4_K_S / 25 Q3_K_L / 20 IQ2_XS)
and `ms-qwen3-vl-8b` (same pattern).

`general.quantized_by = Unsloth` records the vendor, not the scheme — Unsloth
ships both standard and UD quants. The honest read is the **tensor-type mix**,
not the filename or the `file_type` field:

- **UD signature:** mixed types including IQ2_XS and Q3_K_L. A uniform quant
  never contains IQ2_XS.
- **Standard signature:** one dominant type (q4_K/q5_K/q6_K) with f32 norms.

`general.file_type` is unreliable for Unsloth files: UD files report 15
(MOSTLY_Q4_K_M) as a convention, so it neither confirms nor refutes the
filename. When the catalog's `quant` (regexed from the filename) disagrees
with what a size differential implies, read the tensor types with gguf-py
before trusting either.

## Backslash-escaped symlinks (resolved 2026-09-29)

`--check` reported four entries whose GGUF symlinks pointed at
`/Users/macstudio\.hf\/hub/...` — Windows-style separators on a Unix path.
On a case-insensitive APFS volume these resolve to nothing while `ls -la`
still shows a plausible-looking link, so they went unnoticed until a load
test. `ms-qwopus3.8-27b-flash` (16.8GB GGUF + 1.8GB mmproj) and
`ms-qwen3.5-4b-mtp` (2.8GB) were both unloadable; the weights were present
in `~/.hf/hub` the whole time, so no re-download was needed. (That path is now historical:
the surviving model was canonicalized into `~/models/gguf/unsloth/Qwen3.5-4B-MTP-GGUF/`, and
`~/.hf` holds only whisper-large-v3-turbo. Look in `~/models/gguf` first — the llama-swap
config's `--model` path is the authority.)

Fixed with `ln -sfn` to forward-slash targets, then verified three ways:
the link resolves, the GGUF header reads *through* it, and the model
generates a correct answer through llama-swap. `ms-qwopus3.8-27b-flash`
was later cut from the fleet on vision-benchmark grounds; its `.hf` blobs
went with it.

**If this recurs**, the check that catches it is reading bytes through the
link, not just `[ -e ]`:
`head -c4 "$link" | xxd -p` should print `47475546` for a GGUF.

## Benchmark merge

`bench` takes the newest CSV (by mtime) that mentions each model, **not** the
newest CSV overall. Rows with a non-empty `error` column are skipped. A model
absent from all successful rows gets `bench: null` rather than a stale number.

Quality scores come from `benchmark-model-fleet`'s deterministic pattern
matchers. They are not comparable across task families, and a `0.0` often
means the model put its output in a reasoning block rather than that it
failed.
