# Pairwise head-to-head protocol

Use when the question is "should model A replace model B **for this job**", not
"rank the fleet". `benchmark.py` plus the Notion/Grist sinks answer the fleet
question. This answers the two-model decision, and it records two axes a fleet
sweep does not: **generated-token cost** and **whether a failure was capability
or exhaustion**.

Do not build a second rubric library for this. `prompts/tool_calling.py`,
`structured_extraction.py`, `instruction_following.py` and `judgment.py` already
exist with defined correct answers. Reach for those first; use
`scripts/head_to_head.py` when you want the pairwise metric set and code-derived
ground truth in one pass.

## The three traps, in the order they bite

These are not hypothetical. They produced a **wrong conclusion** in the first
run of the LFM3-vs-Qwen comparison (2026-10-28), which was only caught by
re-running.

### 1. Budget parity — never compare a capped model to an uncapped one

A model running `--reasoning-budget 256` and a model with no cap are not two
samples of a model, they are two different configurations. Measured:

| setup | Qwen3.5-4B | LFM3-1.7B |
|---|---|---|
| Qwen **uncapped**, LFM3 capped 256 (invalid) | 15/19, 9870 tok, 186.0s | 16-17/19, 5410 tok, 49.0s |
| **both capped 256** | 17/19, 4454 tok, 127.2s | 16-17/19, 5410 tok, 49.0s |

The first run said the 1.7B beat the 4B by two tasks. Run fairly, the two are
**tied at 17/19**. **Diff the two `cmd:` lines side by side before running** —
every spec flag, reasoning flag, mmproj, and ctx size. A flag present on one arm
and not the other invalidates the comparison, and nothing in the output says so.

Fixing it also found a live misconfiguration: `ms-qwen3.5-4b-mtp` had no cap and
was burning 1500-3000 reasoning tokens on trivial prompts, returning **empty
content** on three tasks. Capping it improved accuracy AND halved the cost. The
confound check is worth running for its own sake.

### 2. Budget exhaustion masquerading as capability

Before recording any failure as "the model can't", re-run that item alone at
2-3x the token budget and read what came back. Three distinct outcomes:

- **Empty content, `finish_reason: length`** — the thinking block ate the whole
  allowance. Not a capability result. Re-run; if it passes at a higher budget it
  was a budget artifact. (Same family as the existing "0.00 quality with a full
  512-token completion" pitfall, generalised: the trap is any model that emits
  `reasoning_content` before `content`.)
- **Rambling, `finish_reason: length`, an answer buried in it** — the model has
  no stopping discipline on that prompt shape. That IS a real finding, and it is
  a *worse* one than an empty reply for unattended use.
- **Clean `finish_reason: stop`, wrong answer** — a genuine capability miss.

### 3. Graders that pass a wrong answer

**Substring matching over a model's own prose is unsafe.** A count question
graded as `expected in content` **passed LFM3 while it was confidently answering
24 instead of 22**, because its rambling enumeration listed a `22` somewhere
among thirty model names. The bug flattered the worse-behaved model.

Rules for numeric/extract answers:

- Require a **short** reply. `len(normalized) > 80 chars` on a "reply with the
  number only" prompt is a fail, whatever integers it contains.
- Extract integers and require **exactly one** match, rather than a substring hit.
- Keep a `rambling` fail reason distinct from `missing` so the report says which.
- For list answers, require every element present (that direction is safe).
- When a model returns tool-call XML in `content` with no tools defined, that is a
  hallucinated call, not an answer. Grade it as a failure explicitly.

## Ground truth without authoring a rubric

Derive the expected answers **from the live artifacts** at run time, not from a
hand-written constant:

```python
cfg = yaml.safe_load(open(llama_swap_config))
truth_n_models = len(cfg["models"])           # a count question
sushi_ttl      = cfg["models"]["sushi"]["ttl"] # a distinctive-value question
```

This cannot drift from reality, needs no rubric review, and makes the grader
self-falsifying. Two conditions:

- **Assert the needle is distinctive.** A ttl that happens to equal several other
  entries grades nothing; `assert target != other_value` before running.
- **Assert long-context needles still exist in the haystack.** If the haystack is
  a live log plus a live notes file, a needle can vanish when the file is
  rewritten — skip that item with a warning instead of scoring a guaranteed fail.

For instruction-following, make the constraint mechanical: exact string equality,
word count, or `json.loads` plus a key/type check. Never a judgement call.

## Metrics to record per task, per model

- `correct` (bool) and a `why` string
- **`completion_tokens`** — the real cost, thinking included. This is the axis
  that decides most cheap-worker questions, and it is invisible in tok/s.
- `wall` seconds, and the median across tasks (one cold long-context prefill will
  otherwise dominate a sum)
- `finish_reason` — `length` flags every trap-2 case
- resident RSS once warm, from `ps` on the llama-server child

## Protocol

1. Fix both arms' `cmd:` to identical spec/reasoning settings. Re-check after.
2. Warm up each model before the first graded task, so the cold load is not
   charged to task 1.
3. Run one model **fully**, then the other. They are `swap: true` in the same
   ondemand group, so alternating thrashes the model cache.
4. Grade mechanically. Print `PASS/FAIL tid tokens wall why` per line.
5. **Re-run every failure at 2-3x budget** and classify it as exhausted,
   rambling, or genuinely wrong. Report the classification, not just the score.
6. Read the failure MODE, not only the count. Confident wrongness and
   hallucinated tool calls are worse for unattended work than an empty reply,
   and a tie on score hides that.
7. Write the header clues into the fleet entry's `description:` — the reasoning
   trap and the caller-side `max_tokens` floor especially. A future session that
   meets an empty reply will otherwise file it as a broken model.

## Worked result (2026-10-28, Studio, both arms capped at 256)

19 tasks: 6 tool selection, 5 extraction from real config files, 4 long-context
needles in a ~40k-token haystack, 4 instruction following. Temp 0. Run twice.

| | LFM3-1.7B r1 | Qwen3.5-4B r1 | LFM3-1.7B r2 | Qwen3.5-4B r2 |
|---|---|---|---|---|
| Accuracy (corrected grader) | 16/19 | 17/19 | 17/19 | 17/19 |
| Completion tokens | 5410 | 4454 | 5348 | 4454 |
| Wall | 49.0s | 127.2s | 49.3s | 129.2s |
| Median latency | 1.47s | 2.80s | 1.52s | 3.03s |
| RSS | 1.57GB | 5.71GB | — | — |

**The accurate headline is a dead tie at 17/19, failing the SAME two items**
(`tool-patch` and `ext-count`), with the 1.7B winning ~2.6x wall and 3.6x memory
and the 4B using ~17% fewer tokens. A vendor's "beats model X" claim did not
reproduce against the larger model already in the fleet, which is the usual
outcome and the reason this protocol exists.

### What the two runs disagree about — read this before reporting any margin

Run 1 differed from run 2 in exactly one place: **LFM3 failed the
`lc-blackbox` long-context item in run 1 by emitted tool-call XML
with no tools defined, and passed it cleanly in run 2.** That single flip is the
whole difference between 16/19 and 17/19.

So: at `temperature 0`, on `--parallel 1`, these servers are **not** deterministic
across runs on borderline items. Qwen's `ext-count` answer also drifted, 16 then
15 (wrong both times, differently wrong). Two consequences:

- **A one-task margin is noise. Say "tie".** Reporting 17-16 as a win is exactly
  the error the budget-parity trap produced earlier in the same session.
- **An unstable failure is not a "failure mode".** The fabricated tool call was
  written up as a distinguishing weakness after run 1. It did not reproduce, so
  the honest statement is "observed once, not stable" — which is weaker than
  either "it does this" or "it doesn't". Re-run before attributing character.
- **Quadratic in cost:** at ~50s per model per run, buying a second run is cheap
  next to publishing a conclusion that reverses under it.

Items that were stable across runs and are real: both models fail `tool-patch`
(neither picks `patch` for an edit request; one reaches for `cronjob_manage`, the
other for `search_files`), and both fail `ext-count` against a true value of 22.
LFM3 rambles to the token ceiling there; Qwen answers confidently and wrongly in
under 300 tokens.

## Honest limits of this harness

- The long-context haystack was ~40k tokens. An agent turn needs 64k+. Do not
  cite a 40k pass as evidence a model is agent-ready.
- Single run per task at temp 0. Determinism is assumed, not proven; treat a
  1-task margin as a tie.
- 19 tasks is enough to separate "same class" from "different class", not enough
  to rank close models. Report it as a tie when it is one.
