# Optimization Comparisons

Use when you have already established a baseline (via `scripts/benchmark.py`) and now
want to methodically test optimization levers — MTP, speculative decoding strategy,
quantization tier, model variant — and decide what to keep. This is the "before vs after
the lever" layer that `benchmark-model-fleet` does not yet cover.

**What it covers**: the levers worth pulling on this fleet, how to set each one up in
llama-swap, how to design a controlled comparison so the numbers are interpretable, what
to measure, and how to read the results.

**What it does not cover**: baseline fleet benchmarking (that is `scripts/benchmark.py`)
or model lifecycle management (loading/unloading, disk cleanup, that's llama-swap config
operations). It also does not cover academic task benchmarks (MMLU, GSM8K) — use
lm-evaluation-harness for that.

## The Levers

### 1. Quantization tier

Different Q//IQ quants of the same model trade size, token quality (KLD vs BF16), and
decode speed. Lower bit-depths save RAM/disk but can lose accuracy — especially at long
context (32k+) where tail divergence matters more than the 512-token wikitext number.

**How to test**: install two quants of the same model in separate llama-swap entries
(different model ids, different `--model` paths, same llama-server flags otherwise), then
benchmark both with identical prompts and scoring. Compare median tok/s, quality score, and
the 32k-tail behavior if the model is used at long context.

**What to read on the GGUF repo page**: the quantization table with KLD wikitext @512 vs
@32k, the 99th-percentile KLD @32k, and the Top-p @32k column. The @32k tail is the more
discriminating number for long-context use; the @512 number is easiest to satisfy and least
useful for discriminating quants.

**Decision rule of thumb**: if two quants have close @512 KLD but one is clearly worse on
the 32k tail, prefer the better-tail quant for long-context roles and the smaller one only
for short-context / cache-pressure roles.

### 2. Speculative decoding — `--spec-type`

llama-server (this fleet's runtime) supports four speculative modes. They are set with
`--spec-type` in the llama-swap model entry `cmd`.

| value | what it does | when it helps | when it does not |
|---|---|---|---|
| `none` | no speculative decoding | baseline; always safe | — |
| `ngram-simple` | drafts from repeated ngrams already in context | copy-heavy work (code edits, rewrites, extraction) — ~2x there; free on free-form generation | free-form creative generation where context has few repeats |
| `draft-mtp` | model's own MTP head drafts tokens | models with MTP heads built in; can add speed when acceptance is high | models without MTP heads (the flag is a no-op, not an error) |
| `draft-simple` | separate draft model drives speculation | only when a draft model has been measured to win (rare on this fleet) | default choice — do not reach for this without a measurement |

**Policy note (this fleet, set 2026-09-25)**: ngram-simple is on everywhere. It is ~2x on
copy-heavy work and free on free-form generation, and it measured within ±1% of baseline on
gemma-26b, qwen3-coder-30b, and devstral-24b at `--parallel 2`. Do not disable it on a
model that has it working unless you have a reason.

**Critical rule (this fleet)**: `--spec-type draft-mtp` stacks with `--spec-type ngram-simple`
as `--spec-type draft-mtp,ngram-simple`. The MTP draft's n-max is pinned to 1 because the
default of 3 is slower than no MTP at all on the models that carry MTP heads. Do not raise
n-max above 1 without a new measurement on this hardware.

**Critical rule (this fleet)**: separate draft models (`--spec-type draft-simple -md`) were
tested and rejected on 2026-09-25, twice. Qwen3.5-4B drafting Qwopus-27B hit 0.95 acceptance
and still ran 44% slower; Ministral-3-3B drafting Devstral-24B hit 0.99 acceptance at mean
draft length 3.98/4 and still ran 21% slower. The cost is the per-step overhead of driving a
second model forward pass (~100ms/step, about 3x a full target forward pass), not the draft's
compute or accuracy — so no acceptance rate can save it. Do not re-try this without a llama.cpp
change. EAGLE3 heads do not exist for mistral3 or qwen35.

### 3. MTP heads — `--spec-type draft-mtp` + `--spec-draft-n-max`

Multi-Token Prediction heads let the model draft more than one token per step from its own
forward pass. Only models whose GGUF includes the MTP head can use this — checking is not
optional, because a GGUF without the head silently ignores the flag.

**How to tell if a GGUF has MTP heads**: check the repo page / README for "MTP" in the file
description, or inspect the GGUF metadata. On this fleet the MTP-headed models are the ones
with `--spec-type draft-mtp,ngram-simple` in their llama-swap entries (KAT-Coder V2.5 Dev,
Qwopus3.8-27B-Flash, Qwen3.5-4B-MTP, NuExtract3). Swift 1.5 Qwen3.8-27B Q4_K_M does NOT
have MTP heads — its entry uses ngram-simple only.

**How to test MTP**: take a model that has MTP heads, run it once with `--spec-type ngram-simple`
and once with `--spec-type draft-mtp,ngram-simple --spec-draft-n-max 1`, everything else equal,
and compare median tok/s and quality. If the MTP run is not measurably faster, the heads are
not helping on this workload and you keep ngram-simple only.

**What to measure**: median tok/s is the headline; acceptance rate is the diagnostic. Llama.cpp
can emit per-step speculative acceptance stats in its log — capture that if you need to explain
why MTP is or is not helping. A high acceptance rate with slower end-to-end speed means the
per-step overhead is the bottleneck, not the draft quality.

### 4. Model variant — same base, different post-training

When two models share a base architecture and tokenizer but differ in post-training (Swift vs
base, Qwopus fork vs base, MTP-headed vs not), the right comparison is controlled: same
quantization tier where possible, same llama-server flags except the variant-specific ones,
same prompts, same scoring.

**Example (this fleet)**: Swift 1.5 Qwen3.8-27B vs base Qwen3.8-27B — Swift 1.5 uses 58.5%
fewer thinking tokens and scores 0.35% higher on GPQA-Diamond, for a 1.95x speed-up on
copy-heavy tasks. That is a model-variant comparison, not a quantization comparison.

**Example (this fleet)**: Qwopus3.8-27B-Flash (Jackrong fork of Qwen3.8-27B, Q4_K_M + MTP
heads, 12.8% faster decoding vs base, 80.7% MTP draft acceptance) vs a non-MTP Qwen3.8-27B
quant — this is both a variant comparison and an MTP comparison in one.

### 5. Context size, batch size, parallelism

These are llama-server flags that affect speed and memory behavior independently of the model
choice:
- `--ctx-size`: larger contexts cost more memory and can slow decode; match it to the role's
  real need rather than maxing it everywhere.
- `--parallel`: number of parallel sequences; 1 vs 2 vs higher affects throughput in batch
  scenarios. This fleet runs most on-demand models at `--parallel 1` and the daily driver at
  `--parallel 2`.
- `--batch-size` / `--ubatch-size`: batch sizing for the server; set consistently across
  compared entries so the comparison is not confounded by batching differences.

When comparing two models or two configs, hold these constant unless the thing you are testing
is specifically the context or parallelism behavior.

## Controlled Comparison Methodology

The core discipline: change one lever at a time and hold everything else equal. A comparison
that changes quantization, speculative mode, and context size simultaneously is not a comparison
— it is a pile of confounds.

### Set up the baseline first

Before testing any lever, establish a baseline number for the model in its current configuration:
- which model id, which llama-swap entry, which llama-server flags
- median tok/s on the benchmark prompts you care about
- quality score on the same prompts
- context size, batch size, parallelism, speculative mode
- model file path and quant level

Record the baseline in the comparison notes before changing anything. A comparison with no
written baseline is just a pair of numbers with no provenance.

### Design the run

For each lever you want to test:
1. Make a copy of the llama-swap entry (new model id, same everything except the lever under
   test). Do not edit the live entry in place — edit a copy so the baseline entry is still
   loadable for a re-run if the numbers look wrong.
2. Reload llama-swap so it sees both entries.
3. Run the same benchmark prompts, same scoring, same max_tokens and thinking settings, on the
   baseline entry and the test entry.
4. Record median tok/s, quality, any speculative-specific diagnostics, and the model file size.

### What to compare

| metric | what it tells you |
|---|---|
| median tok/s (decode speed) | the headline speed number; compare across the two runs |
| quality score (same rubric) | whether the lever cost accuracy on the tasks you care about |
| model file size (GB) | disk/RAM cost of the config; relevant for quant sweeps |
| speculative acceptance rate (if available) | diagnostic for why an MTP/draft change did or did not help |
| long-context tail behavior (if relevant) | whether a quant's @512 number was hiding a 32k problem |

### How to read the result

- **Speed up, quality same or better** → keep the lever, wire it into the entry.
- **Speed up, quality worse** → decide whether the quality loss is acceptable for the role.
  If yes, keep it with that caveat noted. If no, revert.
- **No speed change, quality same** → the lever is not doing anything useful here. Remove it
  (e.g. drop MTP flags from a model whose heads are not helping).
- **No speed change, quality worse** → the lever is a net negative. Revert.
- **Speed worse** → the lever is a regression regardless of quality. Revert unless you have a
  specific reason to keep it (e.g. a quality gain large enough to justify the speed cost for a
  specific high-stakes role).

### One lever per comparison

Do not test MTP + quantization + context size in one run and try to attribute the result to any
of them. If you need to test two levers, run three configs: baseline, lever A only, lever A+B.
That way you can see the marginal effect of B on top of A.

## llama-swap Config Mechanics for Optimization Tests

### Adding a comparison entry

Each tested config needs its own model id in the llama-swap `models:` block. The id is the key
used in `--models` on the benchmark script and in the `groups.members` list. Reusing the same id
for two different configs is the most common way to accidentally compare nothing.

A minimal new entry shape (copy an existing one and change model id, name, description, cmd, and
group membership):

```yaml
  ms-<variant>-<quant>:
    name: "Studio · <readable name>"
    description: "<what is different from baseline, why it exists>"
    cmd: '${llama-server} --port ${PORT} --batch-size 2048 --ubatch-size 2048
      --model /Users/macstudio/models/.../<file>.gguf
      --ctx-size <ctx> --parallel <n> -fa on --spec-type <spec> [--spec-draft-n-max 1]
      -ctk q8_0 -ctv q8_0
      '
    ttl: 900
```

Then add the new id to the right group under `groups:` (usually `ondemand` for a test entry)
so llama-swap will swap it in on request.

### Reloading after editing the config

After editing `~/.hermes/llama-swap/config.yaml`, reload llama-swap so it reads the new entry.
On this fleet the proxy is on `:9292`. Confirm with `curl -s http://127.0.0.1:9292/v1/models`
that the new model id appears before benchmarking it — a missing id usually means the reload did
not land or the entry has a syntax problem that made llama-swap skip it.

### Confirming the model id is actually served

`scripts/discover_endpoints.py` (in the benchmark-model-fleet skill) lists the model ids each
endpoint reports. Run it before benchmarking a new entry — a stale id that the server does not
serve hard-404s and burns the retry budget. The benchmark script itself skips ids not in the
server's `/v1/models` list with a warning.

### GGUF provenance for variant comparisons

When comparing variants of the same model (e.g. two quants, or Swift 1.5 vs a base quant), verify
the on-disk file is the one you think it is before benchmarking. Check the file size against the
repo's listed size for that quant, and if the repo publishes a checksum, match it. A 17.4 GB Q4_K_M
that is actually an 18.0 GB file from a different release will silently produce a different result.

## Qwen3.8-27B-Specific Sweep Paths

The Qwen3.8-27B family on this fleet has a defined set of levers worth sweeping, documented in
`references/qwen38-27b-sweep-paths.md`. Load that file when you are about to run a Qwen3.8-27B
optimization comparison — it lists the specific model entries, quant options, and variant configs
that exist on this machine and which pairs make sense to compare.

## Measurement Harness

Use `scripts/benchmark.py` from the benchmark-model-fleet skill for the actual runs. The harness
already handles warmup + 3 timed runs, median tok/s, deterministic quality scoring, and CSV output.
For optimization comparisons the key settings are:

- `--endpoint` — point at the same endpoint for baseline and test runs (default `llama-swap-studio`
  = `http://127.0.0.1:9292`).
- `--models` — pass the baseline model id for the baseline run and the test model id for the test
  run (or run them in the same invocation with both ids).
- `--max-tokens` / `--enable-thinking` — hold these constant across compared runs. For Qwen3
  thinking models, the methodology note applies: with `max_tokens=512` and thinking on, output
  lands in `reasoning_content` and the quality scorer sees empty `content`; use `--enable-thinking
  false` with `max_tokens=512` or `--max-tokens 2048` with thinking enabled, consistently across
  the comparison.
- `--prompts-file` — use the same prompt family for baseline and test. Different families use
  different rubrics and do not produce comparable quality numbers.
- `--vision` / `--image-path` — for vision model comparisons, use the same test image and same
  vision prompts.

### Capturing speculative-specific diagnostics

The benchmark harness records median tok/s and quality. For MTP or draft-model comparisons you
may also want the per-step speculative acceptance rate. Capture that from llama-server's log
(output to a file you control) rather than trying to infer it from tok/s alone — a speed change
without the acceptance rate is hard to interpret. If the log is not available, the comparison is
still valid for the speed/quality question; it just cannot answer the "why" question.

## Pitfalls

- **Comparing two runs with different max_tokens or thinking settings**: the tok/s and quality
  numbers are not comparable. Always hold these constant across the comparison pair.
- **Editing the baseline entry in place instead of making a copy**: if the test config is worse,
  you have lost the baseline entry and have to reconstruct it from memory. Always add a new id.
- **Forgetting to reload llama-swap after editing the config**: the benchmark runs against the
  old config's entry, not the new one. Confirm the new id appears in `/v1/models` before running.
- **Benchdding a stale id that the server does not serve**: burns retry budget and produces zeros.
  Preflight with `discover_endpoints.py` or confirm in `/v1/models`.
- **Comparing quants without checking the 32k tail**: a quant that looks equivalent at 512 tokens
  can diverge badly at 32k. If the role uses long context, the @32k KLD and Top-p numbers on the
  GGUF repo page are more relevant than the @512 number.
- **Reading tok/s as the only number**: a faster config that loses quality on your actual prompts
  is not a win for your use case. Always compare quality alongside speed.
- **Assuming MTP is active because the flag is set**: if the GGUF does not carry MTP heads, the
  flag is a no-op. Confirm the GGUF has MTP heads before attributing any speed difference to MTP.
- **draft-simple with a separate draft model without measuring first**: on this fleet this was
  tested and rejected twice. Do not assume a draft model will help; measure it and expect it to be
  a net loss unless llama.cpp changes.

## Verification

After a comparison run, confirm the result is real and reproducible before wiring the winning
config into the live entry:

1. Confirm the new model id appears in `curl -s http://127.0.0.1:9292/v1/models`.
2. Confirm the model file on disk matches the expected size and, if available, checksum.
3. Re-run the benchmark on the winning config once more to confirm the number holds (one fast
   run can be a fluke from caching or a cold-start artifact).
4. If the winning config is meaningfully better, replace the live entry's cmd with the winning
   config (or add the winning config as the live entry and retire the test entry from the group).

## References

- `skill_view(name='benchmark-model-fleet', file_path='references/benchmark-methodology.md')` —
  baseline benchmarking methodology (prompts, scoring, statistical method, scatter plot design).
- `skill_view(name='benchmark-model-fleet', file_path='references/qwen38-27b-sweep-paths.md')` —
  Qwen3.8-27B-specific levers, model entries, and quant/variant comparison pairs on this fleet.
- `skill_view(name='benchmark-model-fleet', file_path='references/model-config.json')` — model
  metadata source of truth for plots and reports.
- llama-swap config: `~/.hermes/llama-swap/config.yaml` — the authoritative source for model
  entries, flags, and group membership on this fleet.
