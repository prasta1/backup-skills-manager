# Fleet Optimization Map (curated source of truth)

What each model family and the Apple-Silicon hardware supports, so the
catalog can report, per model, which optimizations are **enabled**, which are
**available** (supported but not on), and which are **untouched** (available
and never tuned). This is capability knowledge, not a measured fact — it is
the documented map the catalog reads, and it must be edited here, never in
the generated catalog.

## Text LLMs (llama.cpp on M-series)

| Optimization | What it does | Families it applies to | Typical default |
|---|---|---|---|
| MTP (multi-token prediction) | predicts N tokens ahead, big decode speedup | Qwen3.x, Gemma, Nemotron (models with MTP heads) | off unless `spec_type` set |
| Speculative decoding | draft model proposes, target verifies | any dense/MoE with a small draft | off |
| Flash attention | faster attention, lower memory | all (M-series supports it) | on in llama.cpp |
| KV-cache quantization | quantize the KV cache (q8_0/f16) | all | f16 (q8_0 available) |
| Parallel | concurrent request slots | all | 1 (higher = more memory) |
| Context size | max tokens per request | all | model max or lower |
| Quantization | Q4/Q5/Q6/Q8/bf16 weight precision | all | per-model choice |
| Batch size (ubatch) | tokens per compute step | all | 512 |
| Memory mapping | mlock / no-mmap | all | default |
| Prompt caching | reuse KV across requests | all | on |

## Image models (ComfyUI / Unsloth Studio)

| Optimization | What it does | Families it applies to | Typical default |
|---|---|---|---|
| Quantization | Q4/Q6/bf16 weight precision | Z-Image, Qwen-Image | Q4_K_M (Q6_K = better fidelity) |
| Steps | turbo 4-8 vs base 20-25 | Z-Image (turbo), Qwen-Image (base) | turbo: 6, base: 25 |
| Resolution | 512/1024/2048 | all | 1024 |
| LoRA | style/character adapters | all | none |
| Upscale (hires fix) | re-denoise at higher res | all | off |
| CFG | classifier-free guidance | Z-Image uses cfg=1 | 1 (Z-Image) |
| Sampler/scheduler | res_multistep/simple etc. | all | per-blueprint |

## Hardware (Apple Silicon)

- M-series supports: flash attention, speculative decoding, KV-cache quant,
  MTP (where the model has the head), unified-memory large ctx.
- 96GB Studio fits bf16 of most image families; 64GB MacBook needs GGUF
  quants for the big ones (flux.2-dev 112GB bf16 won't fit).

## How the catalog uses this

- `enabled` = read from config (text: spec_type/parallel/ctx/quant) or from
the file (image: quant/steps in the name).
- `available` = the map's row for the family, minus what's already enabled.
- `untouched` = available optimizations with no evidence of tuning (no config
  knob set, no benchmark run against them).
- The map is the single place to add a new optimization; the catalog just
  reads it.
