# LFM2.5 (and any reasoning-template model) — Validation Protocol

**Origin:** 2026-10-13 session, validated against LFM2.5-24B-A2B (Unsloth UD-Q4_K_XL, LiquidAI QAD-Q4_0) on llama.cpp 0.6.0 (build 11429) via llama-swap. Protocol is model-agnostic.

## Why this protocol exists

Three things silently wreck naive local-model testing:

1. **Reasoning models burn enormous token budgets by default and may never answer.** LFM2.5's chat template hardcodes `assistant\n thinking` as the generation prompt — *every* request starts with thinking and the default budget is unrestricted. One test hit the 512-token cap while still thinking: empty `content`, `finish: length`.
2. **The flags that sound like they fix it don't.** `--reasoning off` and `--no-reasoning-preserve` do NOT stop thinking. The template overrides them.
3. **A single "correct" answer is not verification.** At an unsafe setting, one draw can look perfect and the next three are wrong. Sample greedily, 3+ draws.

## The three validation prompts

| # | Class | Prompt | Expected |
|---|---|---|---|
| P1 | Word-problem trick | `A farmer has 17 sheep and 9 goats. All but 8 run away. How many are left? Answer briefly.` | 8 |
| P2 | Two-step algebra | `Alice has twice as many apples as Bob. Carol has 5 more than Alice. Together they have 65. How many does Bob have? Answer with just the number.` | 12 |
| P3 | Fact recall | `What is the capital of Vermont? Answer in one word.` | Montpelier |

P1 = over-thinking class; P2 = genuine multi-step (gut-checks whether the thinking budget is adequate); P3 = zero-reasoning cheap answer.

## Harness

Standalone server, isolated per arm (only the last flag varies):

```bash
/opt/homebrew/bin/llama-server --port 5999 --batch-size 2048 --ubatch-size 2048 \
  --model /path/to/model.gguf --ctx-size 131072 --parallel 1 -fa on \
  --spec-type ngram-simple -ctk q8_0 -ctv q8_0 \
  --reasoning-budget 0    # arm A; arm B: 256; arm C: no flag
for i in $(seq 1 90); do curl -s -o /dev/null http://127.0.0.1:5999/health && echo up && break; sleep 1; done
```

Probe (greedy, read every field):

```bash
curl -s http://127.0.0.1:5999/v1/chat/completions -H 'Content-Type: application/json' -d '{
    "model": "x",
    "messages": [{"role":"user","content":"Alice has twice as many apples as Bob. Carol has 5 more than Alice. Together they have 65. How many does Bob have? Answer with just the number."}],
    "max_tokens": 512, "temperature": 0
  }' | python3 -c "
import json,sys
r = json.load(sys.stdin)
if 'error' in r: print('ERROR:', r['error']); sys.exit()
ch = r['choices'][0]['message']
print('content:', repr(ch.get('content'))[:400])
print('reasoning_content len:', len(ch.get('reasoning_content') or ''))
print('finish:', r['choices'][0].get('finish_reason'))
t = r.get('timings', {})
print('tokens:', t.get('prompt_n'), '->', t.get('predicted_n'))
print('pred tok/s:', t.get('predicted_per_second'))
"
```

**Fields:** `content` = final answer; `reasoning_content` length = token-budget gauge; `finish_reason` = `stop` (natural) vs `length` (runaway, empty content); `predicted_n` = total output tokens; `predicted_per_second` = speed.

Multi-draw loop (REQUIRED, temp 0):

```bash
for i in 1 2 3; do curl -s http://127.0.0.1:5999/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"x","messages":[{"role":"user","content":"Alice has twice as many apples as Bob. Carol has 5 more than Alice. Together they have 65. How many does Bob have? Answer with just the number."}],"max_tokens":512,"temperature":0}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); ch=r['choices'][0]['message']; print(f\"draw: content={ch.get('content')!r} reasoning_len={len(ch.get('reasoning_content') or '')} finish={r['choices'][0].get('finish_reason')}\")"; done
```

## The three traps (demonstrated)

1. **Default runs away:** empty content, `finish: length`. No budget on a reasoning-template model = unrestricted thinking.
2. **`--reasoning off` / `--no-reasoning-preserve` don't stop thinking.** Server log: `chat template supports preserving reasoning, it is enabled by default`. `--no-reasoning-preserve` only controls whether PRIOR thinking is re-emitted in history, not whether new thinking is generated. Template generation prompt is literally `assistant\n thinking`.
3. **Per-request `reasoning_budget` is IGNORED by llama-server** (1,105 chars of reasoning came back with budget 0 in the body). Budget is a server flag only, set in the llama-swap `cmd:` / llama-server invocation.

## A/B results (LFM2.5-24B-A2B, both quants, 2026-10-13)

**ms-lfm2.5-24b (UD-Q4_K_XL):**

| Config | P1 riddle | P2 algebra | P3 fact | Tokens (P2) | tok/s |
|---|---|---|---|---|---|
| no flag | ❌ no answer (512+ still thinking) | ✅ 12 (356 tok) | — | 356 | 100.5 |
| budget 0 | ✅ 8 (32 tok) | ❌ 15,15,15 (4 tok, greedy) | — | 4 | ~70-75 |
| budget 256 | ✅ 8 (282 tok) | ✅ 12 (270 tok) | ✅ Montpelier (164 tok) | 270 | 116.2 |

**ms-lfm2.5-24b-qad (QAD-Q4_0):**

| Config | P1 riddle | P2 algebra | P3 fact | Tokens (P2) | tok/s |
|---|---|---|---|---|---|
| no flag | ✅ 8 (293 tok) | ✅ 12 (339 tok) | — | 339 | 115.2 |
| budget 0 | ✅ 8 (49 tok) | ❌ 10 (4 tok) | — | 4 | 103.7 |
| budget 256 | ✅ 8 | ✅ 12 (211 tok) | — | 211 | 122.2 |

Conclusions: (1) budget 0 is NOT safe on multi-step reasoning for either build — one single draw looked right, then failed 3/3 greedy. (2) 256 kept correctness on every prompt and REDUCED tokens (339→211, 356→270) at HIGHER tok/s. (3) Speed is roughly flat across arms (~100-130); budget trades tokens and correctness, not raw throughput.

## Extra observations

- **Tool-call reflexes (UD build):** at 256, answered algebra via `<|tool_call_start|>[bash(command=\'echo "12"\')]<|tool_call_end|>` — correct but NOT a clean string. Consumers must handle tool_call output. QAD answered plain text.
- **"Reasoning-only" is a myth (QAD):** documented initially as "never switches to content" — false; switched to content in every run (after 293/339/950 reasoning tokens). Both builds: think-then-answer, byte-identical chat templates.
- **Version-check:** config comment claimed llama.cpp 0.5.0/b11146 while binary was 0.6.0/b11429. `llama-server --version` before trusting flag behavior.
- **No MTP heads on LFM2.5** (428 tensors, zero nextn) — `--spec-type ngram-simple` only; draft-mtp pointless on this arch.

## Acceptance checklist

- [ ] Greedy (temp 0), 3+ draws per prompt, all three classes
- [ ] `finish_reason` = `stop` on every draw, never `length`
- [ ] `content` non-empty on every draw
- [ ] Multi-step prompt correct on every draw
- [ ] No tool_call/wrapper text leaking into consumer output (or consumer handles it)
- [ ] Reasonable `predicted_n` (≤300 for a 2-step problem on this box)
- [ ] Flag verified in the live process cmd, not assumed from config (llama-swap `/running` or `ps`)
