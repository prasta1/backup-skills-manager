# Benchmark Methodology

## Test Setup

- **Endpoint**: llama-swap API at `http://127.0.0.1:9292` (OpenAI-compatible)
- **Model loading**: On-demand — llama-swap loads models when first requested. First request may take 30-300s for 20-30 GB models.
- **Retries**: 30 attempts with 5s delay for HTTP 503/502/504 (model swapping).
- **Timeout**: 300s per request (enough for 26 GB model load + inference).

## Coding Benchmarks

### Prompts
The built-in coding set (`scripts/prompts.py`) has 10 prompts; the `prompts/*.py` task families
(web_frontend, data_analysis, structured_extraction, tool_calling, instruction_following,
sql_generation) each define their own. The original audit used 4 prompts (csv_parser,
go_json_tags, rust_closure_borrow, npm_diff).

### Quality Scoring
- Each prompt has a deterministic scorer (`scripts/prompts.py`)
- 5 checks × 0.2 points = max 1.0
- Pattern-based (string matching), not LLM-judged
- Models without specific scorers default to 0.8 quality (text output > 100 chars)

### Thinking Mode Handling
- Non-thinking models: `max_tokens=512`, `enable_thinking` unset
- Qwen3 thinking models: Two configs tested:
  - `thinking_2k`: `max_tokens=2048`, thinking enabled (default)
  - `no_thinking`: `max_tokens=512`, `enable_thinking=false`
- **Finding**: Thinking overhead (2048 vs 512 tokens) provides zero quality improvement on these prompts. Output appears in `reasoning_content` field, `content` stays empty with max_tokens=512.

## Vision Benchmarks

### Prompts (4)
1. **describe_scene** — "Describe what you see in this image in detail."
2. **count_objects** — "How many people are in this image? Count carefully..."
3. **technical_detail** — "What technical equipment or tools can you identify?"
4. **contextual_reasoning** — "If this scene represents a real situation..."

### Image Input
- Local PNG file loaded as base64 data URI: `data:image/png;base64,...`
- **Critical**: llama-swap mmproj does NOT support URL image fetching. All URL-based image attempts fail.
- Test image: `test_image.png` (600×400, hiking scene via placehold.co)

### Vision Quality Scoring
- Not yet LLM-judged — uses char count as a proxy for output detail
- Future: Replace with semantic quality scoring

## Statistical Method

- 1 warmup + 3 timed runs per prompt per model
- tok/s = completion_tokens / elapsed_time
- **Median** of the 3 timed runs (robust against outliers from model loading)
- Warmup run also triggers model loading for on-demand models

## Scatter Plot Design

### Coding Speed × Quality
- X: median tok/s (higher = faster)
- Y: quality score 0-1 (higher = better)
- Bubble size: disk usage in GB (larger = more storage)
- Color: MoE (blue), Vision (orange), Standard (red)
- Deleted models: grey X markers with grey labels
- Legend: top-left, outside plot area

### Vision Speed × Output Detail
- X: vision tok/s
- Y: output character count (proxy for detail)
- Same color/marker scheme

### Speed × Efficiency
- X: coding tok/s
- Y: tok/s per GB (speed ÷ disk size)
- Shows diminishing returns: small models have 30-50x higher efficiency but no unique role


## Reasoning-Effort Sweeps (2026-10-11)

Measuring the optimal `reasoning_effort` for a single model (vs comparing models) needs a custom driver — `benchmark.py` has no effort passthrough and scores quality from the warmup only.

### Harness gaps that produce fake zeros
1. **The split-answer problem.** At effort ≥ low the response arrives across BOTH `content` and `reasoning_content` (sushi xhigh: content 276 chars, reasoning 1020). `benchmark.py` reads `content` *or* `reasoning_content` — either half alone false-0s prose prompts. **Join them before scoring.**
2. **The join is WRONG for strict-JSON prompts.** For a "JSON only, no prose, no fences" rubric, thinking prose breaks `json.loads` → joined text scores 0.2 regardless of actual ability, and low/med/xhigh look artificially worse than `off`. Score strict-JSON prompts on `content` alone. Verified 2026-10-11: joined=0.2 vs content=0.7–0.9 on the same runs.
3. **max_tokens must cover thinking.** xhigh burns up to the 4096 cap on prose prompts; 2048 truncates the answer at xhigh.
4. temp=0.0; 3 scored runs per (level, prompt), per-level medians.

### sushi results (Qwen3.8-Flash-Next 2bpw; levels `off/low/medium/xhigh` — no `high`, engine 400s anything else)

Judgment family, 84 scored runs (4 levels × 7 prompts × 3), driver + CSV at `~/.hermes/benchmark_results/sushi-effort-sweep-20261011/`:

| prompt | off | low | med | xhigh |
|---|---|---|---|---|
| agentic_coding | 0.60 | 0.80 | 0.80 | 0.80 |
| debugging_duplicates | 0.60 | 0.60 | 0.60 | **0.80** |
| password_validator | 0.90 | 0.80 | 0.80 | **1.00** |
| support_ticket_json | 0.90 | **0.70** | 0.90 | 0.90 |
| logic / math / practical | 1.00 | 1.00 | 1.00 | 1.00 |

Mean quality: off 0.857 · low 0.829 · medium 0.871 · xhigh 0.929. Median latency: 12 / 15 / 17 / 53 s. Mean reasoning tokens: 0 / ~530 / ~740 / ~2500.

**Interpretation:** thinking helps *code reasoning* (xhigh is the only rung lifting debugging + validator) but *hurts format-strict extraction* at low (severity drifts "critical"→"high"). off/low/medium near-tied overall — medium is the cheap safe rung. Whether xhigh's +0.025 mean for 3× latency is worth it depends on work mix; rubrics with coarse 0.2-step scoring may understate what extra thinking buys. Back-test against real decisions before locking xhigh as a default. (Hermes-side config: `reasoning_overrides: sushi: medium` in config.yaml pins this seat.)

### Operational pitfalls hit during the sweep
- **Foreground terminal caps kill long sweeps mid-run.** This box's foreground timeout ceilings (420s observed) SIGTERM anything longer. A killed sweep is expensive to re-run (~40 min of GPU burned) unless the driver writes **append-only per-row and resumes by skipping recorded (effort, prompt, run) triples** — do that in any >10-min driver, and launch with `background=true` (+`persist_on_release=true` if session-lifecycle risk exists).
- **Don't re-run a whole sweep to fix one prompt's scorer.** Patch only what's wrong, then delete only the affected artifact rows (e.g. the support_ticket_json rows scored on joined text) and resume — keep the valid rows.

### Ground-truth discipline
Effort sweeps must score against defined correct answers (judgment family rubrics), never observer-guessed labels — the clef-flash vs Laya bakeoff gave the opposite verdict on guessed vs real labels (2026-10-03 rule).

### Known-good driver reference
`sushi-effort-sweep-20261011/run_sweep.py` implements the correct pattern end-to-end: effort passthrough (`reasoning_effort` in body, omitted at `off`), joined scoring for prose prompts + content-only for the `STRICT_JSON_PROMPTS` set, 4096 max_tokens, append-only `sweep_rows.csv` + resume-by-(effort,prompt,run) skip, and a `sweep_summary.json` with per-level mean quality, per-prompt medians, median latency, and mean reasoning/completion tokens. Reuse or copy it for any effort sweep (same model or another). Note it hardcodes the llama-swap Studio URL + model id and loads `prompts/judgment.py` by path.

2. **Thinking overhead**: No quality gain from Qwen3 thinking modes at 4B scale (2048 tokens vs 512 = identical 0.80 quality)
3. **Vision efficiency**: qwen3-VL-8b matches muse-glimmer-30b detail (1034 chars) at 2.7x speed, 1/3 disk
4. **Quality leaders**: kat-coder-v25 (0.95 coding) and devstral-24b (0.95 coding) — both kept despite speed trade-offs
5. **MoE sweet spot**: qwen36-35b-a3b at 78 tok/s + 0.85 quality + vision capability — the most versatile model
