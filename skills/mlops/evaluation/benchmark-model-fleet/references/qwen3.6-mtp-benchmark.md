---
model: Qwen3.6-35B-A3B
repo: unsloth/Qwen3.6-35B-A3B-MTP-GGUF
quant: UD-Q4_K_XL
disk_size: 22.85 GB
native_mtp: true
arch: Qwen3.6-35B-A3B-MoE
tensors: 753
experts: 256
draft_head: Q8_0
context_size: 262144
benchmarks:
  n-max_1:
    tok_s: 125.3
    acceptance: 0.970
  n-max_2:
    tok_s: 101.9
    acceptance: 0.921
    note: "Depth loses on fast models due to draft+verify overhead."
copy_heavy_test:
  prompt: rewrite
  draft_mtp_solo_tok_s: 126.6
  draft_mtp_ngram_tok_s: 148.6
  ngram_draft_tokens: 277
  ngram_acceptance: 0.498
  note: "Interleaved A/B confirms ngram-simple is beneficial for rewrite tasks."
decision: MTP is available but requires loss of --parallel 2 and --mmproj capabilities.
