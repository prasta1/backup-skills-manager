# Qwen3.8-27B Sweep Paths

<!-- 2026-11-01: ukisai/Swift-1.5-Qwen3.8-27B-GGUF was DELETED from both
     machines (config, weights, HF cache). The Swift paths in this doc are
     historical - they no longer resolve. Kept as the record of that sweep. -->

Use when you are about to run an optimization comparison on the Qwen3.8-27B family
on this fleet. This file lists the specific model entries, quant options, and variant
configs that exist on this machine, and which pairs make sense to compare.

Load this before designing a Qwen3.8-27B comparison so you are comparing real configs
that exist here, not configs you assume exist.

## Models on this fleet that descend from Qwen3.8-27B

### llama-swap entries (loadable now)

| model id | name | base / variant | quant | MTP heads | spec type in config | path |
|---|---|---|---|---|---|---|
| `ms-swift-qwen3.8-27b` | Studio · Swift 1.5 Qwen3.8-27B · reasoning-efficient | Swift 1.5 adapter of Qwen3.8-27B | GGUF Q4_K_M | no | `ngram-simple` only | `~/models/gguf/swift-qwen3.8-27b/Swift-1.5-Qwen3.8-27B-Q4_K_M.gguf` |
| `ms-qwopus3.8-27b-flash` | Studio · Qwopus3.8-27B-Flash · speed + vision + MTP | Qwopus3.8-27B-Flash (Jackrong fork of Qwen3.8-27B) | GGUF Q4_K_M + MTP heads | yes | `draft-mtp,ngram-simple` with `--spec-draft-n-max 1` | `~/models/gguf/Jackrong/Qwopus3.8-27B-Flash-GGUF/Qwopus3.8-27B-Flash-MTP-Q4_K_M.gguf` + mmproj `mmproj-F32.gguf` |

Both are in the `ondemand` group with 15-min idle unload. Swift 1.5 is text-only (no mmproj
in its entry). Qwopus has vision via mmproj.

### On-disk weight trees not currently wired

| what | format | source repo | size on disk | path | notes |
|---|---|---|---|---|---|
| Qwen3.8-27B MLX 4-bit | MLX safetensors (3 shards) | `mlx-community/Qwen3.8-27B-MTP-4bit` | ~16 GB total | `~/models/lmstudio-community/Qwen3.8-27B-MLX-4bit/model-00001..00003-of-00003.safetensors` | MLX format, not GGUF; not loadable by llama-swap without conversion or an MLX serving path |
| Swift-Qwen3.8-27b-oQ4e-mtp | safetensors (4 shards) + tokenizer + imatrix report | `Yanun/Swift-Qwen3.8-27b-oQ4e-mtp` | ~20 GB total | `~/models/Yanun/Swift-Qwen3.8-27b-oQ4e-mtp/model-00001..00004-of-00004.safetensors` | Safetensors, not GGUF; also not directly loadable by llama-swap |

These two are on disk but not in llama-swap. To compare them you would either convert them to
GGUF or serve them through a different runtime. They are listed here so a sweep does not
duplicate work that already exists on disk.

### HF cache repos present (metadata only — no weight blobs)

| cache repo id | weight blobs on disk? | note |
|---|---|---|
| `models--ukisai--Swift-1.5-Qwen3.8-27B-GGUF` | yes — backed by the Swift 1.5 Q4_K_M GGUF in `~/models/gguf/swift-qwen3.8-27b/` | the one just installed; cache repo is a symlink structure to the blob under `~/models/.hf/hub/blobs/57/...` |
| `models--ukisai--Swift-Qwen3.8-27B-GGUF` | no — only a 24 KB metadata blob (`ddc404ce...`) | repo index only; the actual Swift 1.0 GGUF that used to exist under this namespace is gone |
| `models--mlx-community--Qwen3.8-27B-MTP-4bit` | no weight blobs in the HF cache store; safetensors live under `~/models/lmstudio-community/Qwen3.8-27B-MLX-4bit/` | the real file is outside the HF blob cache |
| `models--Yanun--Swift-Qwen3.8-27b-oQ4e-mtp` | no weight blobs in the HF cache store; safetensors live under `~/models/Yanun/...` | same pattern |

## Recommended comparison pairs

These are the comparisons that make sense given what is wired and installed on this machine.
Each pair holds as much constant as possible and varies one thing.

### Swift 1.5 vs base Qwen3.8-27B (variant comparison)

**What varies**: post-training (Swift 1.5 adapter vs base Qwen3.8-27B).

**What to hold constant**: quantization tier if you can find a base Qwen3.8-27B Q4_K_M GGUF
that is comparable; otherwise note the quant difference explicitly and treat quality comparisons
with that caveat.

**Why this comparison matters**: Swift 1.5 documentation claims 58.5% fewer thinking tokens and
0.35% higher GPQA-Diamond, for a 1.95x speed-up on copy-heavy tasks. The claim is about reasoning
token efficiency, so the most relevant benchmark is a prompt set that triggers thinking — not just
a generic coding prompt set. Use a prompt family that exercises reasoning, and capture both
tok/s and the thinking-token count if the API exposes it.

**Caveat**: Swift 1.5's headline speed-up is partly a thinking-token reduction, which means it is
partially a quality-of-output-per-token story and partially a raw-speed story. If you want to
compare raw decode speed independent of thinking behavior, force thinking off on both sides.

### Qwopus3.8-27B-Flash vs Swift 1.5 (variant + MTP comparison)

**What varies**: fork/post-training (Jackrong Qwopus fork vs UkisAI Swift 1.5) and MTP heads
(Qwopus has them, Swift 1.5 does not).

**What to hold constant**: quantization tier — both are Q4_K_M. Context size, batch size,
parallelism, and the ngram-simple component of the speculative config should be the same.

**Why this comparison matters**: Qwopus is documented on this fleet as 12.8% faster decoding vs
base Qwen3.8-27B with 80.7% MTP draft acceptance, and it is the only Qwen3.8-27B-family entry
on this fleet that has MTP heads wired. Comparing it to Swift 1.5 tells you whether MTP + the
Qwopus fork together beat Swift 1.5's reasoning-token efficiency on the workloads you care about.

**Caveat**: this is not a clean single-lever comparison — it varies both the variant and the
presence of MTP. If you want a clean MTP-only comparison, you would need two configs of the same
model with and without MTP, which does not exist on this fleet for Swift 1.5 (it has no MTP heads)
and may not exist as a non-MTP Qwopus config. Interpret the result as "Qwopus-with-MTP vs
Swift-1.5-without-MTP" and note the confound.

### Q4_K_M vs a higher or lower quant of the same model (quantization sweep)

**What varies**: quantization tier of the same model.

**What to hold constant**: model variant, context size, batch size, parallelism, speculative mode.

**On this fleet today**: the only Qwen3.8-27B-family GGUF wired is Swift 1.5 Q4_K_M. To sweep
quantization you would need additional quants of Swift 1.5 (or of another Qwen3.8-27B variant)
installed. The Swift 1.5 GGUF repo page lists more quants than Q4_K_M — Q5_K_M, Q6_K, Q8_0, and
lower quants — so a sweep is possible if you download another tier.

**What to check on the repo page before sweeping**: the quantization table with KLD wikitext @512,
KLD @32k, 99th-percentile KLD @32k, and Top-p @32k. For a long-context role, prefer the @32k tail
numbers over the @512 numbers when choosing which quants to compare.

### MTP on vs off (MTP-only comparison)

**What varies**: `--spec-type ngram-simple` vs `--spec-type draft-mtp,ngram-simple --spec-draft-n-max 1`.

**What to hold constant**: model variant, quant, context, batch, parallelism.

**On this fleet today**: the only Qwen3.8-27B-family model with MTP heads is Qwopus3.8-27B-Flash.
To run a clean MTP-only comparison you would create a second llama-swap entry for Qwopus with the
same model file and flags except `--spec-type ngram-simple` (no MTP), then benchmark both.

**Why this comparison matters**: the fleet's speculative policy notes that MTP acceptance on KAT-Coder
was 0.82, and on Qwopus the documented MTP draft acceptance is 80.7% — but acceptance rate is not
speed. The only way to know whether MTP helps on this hardware for this model is to measure it with
both configs and compare median tok/s. If MTP does not produce a measurable speed gain, drop the MTP
flags and keep ngram-simple only.

## What cannot be compared cleanly on this fleet today

- **Swift 1.5 MTP on vs off**: Swift 1.5 Q4_K_M does not have MTP heads, so there is no within-model
  MTP comparison possible for Swift 1.5 on this machine. You would need a Swift 1.5 GGUF that
  includes MTP heads, if one exists, or a different variant.
- **Base Qwen3.8-27B Q4_K_M vs Swift 1.5 Q4_K_M as a clean single-lever comparison**: this is only
  clean if the base model quant is actually installed. The base Qwen3.8-27B GGUF repo is present in
  the HF cache as metadata only; the actual base Q4_K_M GGUF is not on disk. To compare cleanly you
  would download the base quant first.
- **MLX 4-bit or Yanun oQ4e-mtp vs the GGUF fleet**: these are different formats/runtimes. A fair
  comparison would require either converting them to GGUF or benchmarking them through their native
  runtime and treating the runtime difference as a confound.

## Before you run a Qwen3.8-27B sweep

1. Decide which lever you are testing and pick the pair from the tables above.
2. Confirm the model ids you plan to compare are both served by llama-swap (`curl -s http://127.0.0.1:9292/v1/models` or `scripts/discover_endpoints.py`).
3. For any new config you create, verify the model file on disk matches the expected size and
   checksum before benchmarking.
4. Decide on max_tokens and thinking settings before the run and hold them constant across the pair.
5. Pick the prompt family that matches the claim you are testing — reasoning-token claims need
   reasoning prompts, not just generic coding prompts.

## References

- `skill_view(name='benchmark-model-fleet', file_path='references/optimization-comparisons.md')` —
  the lever mechanics and controlled-comparison methodology this file assumes.
- `skill_view(name='benchmark-model-fleet', file_path='references/benchmark-methodology.md')` —
  baseline benchmarking methodology.
- llama-swap config: `~/.hermes/llama-swap/config.yaml` — authoritative source for the model entries
  and flags in the tables above.
- Swift 1.5 GGUF repo page: `https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GGUF` — quant table,
  KLD numbers, and file sizes for any quantization sweep of Swift 1.5.
