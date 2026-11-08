# Execution-based coding evaluation

`scripts/code_eval.py` + `prompts/code_execution.py`.

## Why it exists

The code family's original quality score is a **5-substring pattern match** per
prompt (`scripts/benchmark.py` + `prompts/*.py`). It cannot distinguish a
correct answer that omits a keyword from a wrong answer that includes it.

Demonstrated, not theorised — on `rust_closure_borrow`:

| model | rubric score | actual answer |
| -- | -- | -- |
| coder | **0.60** | correct borrow-checker diagnosis; never typed `FnOnce`/`move` |
| devstral | **0.80** | called a by-reference capture a `FnOnce` closure — **wrong mechanism** |

The rubric ranked the wrong answer above the right one. That column is
vocabulary matching, and any model decision built on it is unfounded.

## How it works

* Ground truth is **execution**: the generated code runs and its values either
  match or they don't.
* Scoring is **per assertion** — 42 tasks x ~5 assertions = ~210 graded points,
  against a measured ~4-task resolution floor for binary task scoring.
* Cost is recorded per task (prompt tokens, completion tokens, wall) and
  reported as **tokens and seconds per SOLVED task** — the numbers that matter
  for agent work, where verbosity is paid on every turn.
* Generated code is retained in the JSON so a surprising result can be audited.

## Run it

```bash
# ALWAYS FIRST -- proves the instrument, costs seconds, catches bad task data
python3 scripts/code_eval.py --self-test

python3 scripts/code_eval.py \
  --models mb-devstral-24b mb-kat-coder-v2.5 \
  --endpoint http://100.68.81.83:8999 \
  --max-tokens 2048 --out results.json

python3 scripts/code_eval.py --models X --only parse_simple_expr   # subset
```

## Pitfalls (all hit for real)

**1. ALWAYS send a system message. This one silently corrupts cost data.**

llama-server injects its own architecture-specific DEFAULT system prompt when a
request carries no `system` role. Measured on `mb-devstral-24b`, message `hi`:

```
no system message   -> 556 prompt tokens
+ system "x"        ->   7
+ system (short)    ->  12
```

The Qwen models inject ~0. So omitting the system role charges *one model*
~549 hidden tokens per call and makes it look 4x more expensive than it is.
Real agent traffic always carries a system prompt, so the overhead cannot occur
in production — it is purely a harness artifact, and it lands on exactly one
model, which is the worst possible shape.

**2. `--self-test` is not optional.** It caught four defects before any model
ran: expected values round-tripped through JSON (which stringifies dict keys,
zeroing every int-keyed task); `eval` given separate globals/locals (breaking
any lambda or comprehension with `NameError`); and two errors in the task data
itself — a contradictory expected value and a reference that could not solve
its own task. All four would have produced a plausible-looking table.

**3. Python scoping inside `eval`.** The worker evaluates with ONE namespace for
globals and locals. Passing them separately makes `solve()` invisible inside a
lambda or comprehension body.

**4. Do not round-trip this config through `yaml.safe_dump`.** It drops
comments, and `llama-swap/config.yaml` carries the retirement notes and measured
evidence for the fleet. Edit by targeted text replacement, assert the match is
unique, and verify comment count is unchanged.

**5. `--max-tokens` must clear the reasoning budget.** A truncated answer is a
failed task, not a slower one. 2048 on these models; the original 512 default
scored a reasoning model at 0.55 that fair measurement puts at 0.85.

## Interpreting results

**Accuracy gaps below ~3 tasks on a 42-item set are NOT significant** — run
McNemar on the discordant pairs before claiming an ordering. In practice all
three coder models land within 2 tasks of each other.

**Lean on cost, not accuracy.** Token and wall counts are deterministic and
repeat; a 1-task accuracy gap is not. The defensible finding is "A costs Nx
what B costs for the same result", not "A is better than B".

**A failure is not always a capability gap.** Check the retained code. One
model's `parse_simple_expr` failure was an algorithmically correct
recursive-descent parser missing `nonlocal idx` on three nested functions — a
real bug, correctly caught, but a scoping slip rather than an inability.
