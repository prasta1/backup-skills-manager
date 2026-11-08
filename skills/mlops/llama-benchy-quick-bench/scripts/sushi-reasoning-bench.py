#!/usr/bin/env python3
"""
sushi-reasoning-bench — paired A/B on reasoning: TTFT + tok/s.

Serves through llama-swap at 127.0.0.1:9292, model id `sushi` (MLX sushi
engine, Qwen3.8-Flash-Next 125B-A6B 2bpw pack).

Arms (request-level, via chat_template_kwargs on the live endpoint):
  A  enable_thinking=false                       (no thinking block)
  B  enable_thinking=true                        (thinking on, default budget)
  C  enable_thinking=true + reasoning_budget_tokens=N   (N via --budget)

Measured server behavior (2026-10-07, empirical):
  * Throttle knobs (all verified live on the llama-swap-served 'sushi',
      temp=0 sheep prompt):
    - TOP-LEVEL request field `reasoning_budget_tokens` = hard cap enforced
      at decode (64->329c, 128->537c/543c, 256->1073c, uncapped->2402c).
      IGNORED inside chat_template_kwargs (ctk placement: 2402c everywhere).
      It caps WITH effort present too: low+128->537c, low+256->1073c,
      low+512->1971c; xhigh+128->690c, xhigh+256->1136c; off+512->2046c.
    - TOP-LEVEL `reasoning_effort` = sushi's own per-arch table (this arch
      accepts off/low/medium/xhigh; 'minimal'/'high' 400-rejected). Traps:
      low/none/absent all render identically (2402c default thinking);
      medium = longer (2822c, prompt 68); xhigh AND the string 'off' BOTH
      force deep thinking running until max_tokens (7670c think, 0 answer,
      finish=length, prompt 110) — 'off' is NOT a disable. To turn thinking
      OFF: chat_template_kwargs {enable_thinking: False} (verified: 0 think,
      full answer at max_tokens).
    - Server flag `sushi --reasoning-budget <n>` exists in --help but is
      serve-time only; request-level cap above works without relaunch.
  * temperature=0 makes thinking arms near-deterministic (byte-identical
    2402c think across seeds/prompts at this cap): the ngram table re-samples
    prior rollouts, so think_tokens are flat and the paired design's job is
    measuring TTFT/throughput, not thinking-length variance. temp=1 is the
    default for honest variance; --temperature 0 is for pure decode/latency
    isolation.
  * Streaming emits usage/timings on the final chunks with
    stream_options.include_usage; we union whatever arrives. Server
    `timings.predicted_per_second` is trustworthy for decode tok/s;
    client wall-clock is the source of truth for TTFT.

What it measures per rep:
  ttft_any_ms    ms to the first token of any kind (prefill + first decode)
  ttft_answer_ms ms to the first ANSWER token (user sees text) — with
                 thinking on this = ttft_any + whole thinking phase
  tok_s_answer   answer tokens / visible-answer span (pure answer decode)
  tok_s_e2e      answer tokens / total wall time (user-perceived throughput)
  tok_s_decode   all completion tokens / decode span (server timings when
                 present, else client math)
  think_tokens   reasoning tokens (usage.completion_tokens_details when
                 present, else char/4 estimate marked [est])
  answer_tokens  completion_tokens - think_tokens

Why paired + interleaved: same prompt, arms alternate within each pair, pair
order randomized — linear thermal/scheduler drift cancels. Verdicts must
clear p<0.05 AND the minimum detectable effect; everything else is
INCONCLUSIVE by design.

Usage:
  python3 sushi-reasoning-bench.py ab    --arms A,B --pairs 8 --prompt-file p.txt
  python3 sushi-reasoning-bench.py ab    --arms A,B --budget 512   # thinking vs capped
  python3 sushi-reasoning-bench.py noise --arm B --reps 8 --metric tok_s_answer
"""
import argparse, json, random, statistics, sys, time, urllib.request
from math import erf, sqrt

BASE = 'http://127.0.0.1:9292/v1/chat/completions'
MODEL = 'sushi'

def make_arms(budget=None):
    # Arm A: thinking OFF via chat_template_kwargs enable_thinking=false
    # (verified: 0 think chars, full answer). Do NOT use reasoning_effort='off'
    # — that maps to xhigh deep-thinking (7670c think, 0 answer) and is not a
    # disable. Arm B: thinking ON (identical to sushi's default template
    # rendering). Arm C (only when --budget N given): thinking ON, hard-capped
    # at N reasoning tokens via the TOP-LEVEL request field
    # reasoning_budget_tokens (NOT inside chat_template_kwargs, where it is
    # ignored; top-level enforced: temp=0 think 128->537c, 256->1073c,
    # uncapped->2402c).
    arms = {
        'A': {'enable_thinking': False},
        'B': {'enable_thinking': True},
    }
    if budget is not None:
        arms['C'] = {'enable_thinking': True,
                     '_top': {'reasoning_budget_tokens': budget}}
    return arms

ARM_LABEL = {'A': 'thinking off', 'B': 'thinking on (default)',
             'C': 'thinking capped (--budget)'}

DEFAULT_PROMPT = ("A farmer has 17 sheep and sells some; a storm knocks down a barn roof, "
                  "three sheep escape through a hole that was not there before, and a neighbor "
                  "brings back twice the number he sold. How many sheep does the farmer have now, "
                  "and what assumptions did you make?")

# ------------------------------------------------------------ measurement
def stream_rep(prompt, arm_kwargs, max_tokens=8192, timeout=600,
               temperature=1.0, seed=None):
    ctk = dict(arm_kwargs)
    top = ctk.pop('_top', {})
    payload = {
        'model': MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': temperature,
        'stream': True,
        'stream_options': {'include_usage': True},
        'chat_template_kwargs': ctk,
    }
    payload.update(top)
    if seed is not None:
        payload['seed'] = seed
    req = urllib.request.Request(BASE, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.perf_counter()
    ttft_any = ttft_answer = None
    answer_t0 = None
    think_chars = ans_chars = 0
    usage = {}
    finish = None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.strip()
            if not line.startswith(b'data:'):
                continue
            body = line[5:].strip()
            if body == b'[DONE]':
                break
            try:
                d = json.loads(body)
            except json.JSONDecodeError:
                continue
            # union usage + timings from every chunk they ride on
            for k in ('usage', 'timings'):
                sub = d.get(k)
                if sub:
                    for key, val in sub.items():
                        if isinstance(val, dict):
                            usage.setdefault(key, {}).update(val)
                        elif val is not None:
                            usage[key] = val
            ch = (d.get('choices') or [{}])[0]
            if ch.get('finish_reason'):
                finish = ch['finish_reason']
            delta = ch.get('delta') or {}
            now = time.perf_counter() - t0
            rc = delta.get('reasoning_content') or delta.get('reasoning')
            c = delta.get('content')
            if rc:
                think_chars += len(rc)
                if ttft_any is None:
                    ttft_any = now
            if c:
                ans_chars += len(c)
                if ttft_answer is None:
                    ttft_answer = now
                    answer_t0 = now
                if ttft_any is None:
                    ttft_any = now
    total_elapsed = time.perf_counter() - t0
    answer_span = total_elapsed - answer_t0 if answer_t0 is not None else 0.0

    c_tok = usage.get('completion_tokens')
    rt = (usage.get('completion_tokens_details') or {}).get('reasoning_tokens')
    p_tok = usage.get('prompt_tokens')
    cached = (usage.get('prompt_tokens_details') or {}).get('cached_tokens', 0)
    exact = c_tok is not None
    if exact:
        think_tok = float(rt) if rt is not None else think_chars / 4.0
        ans_tok = float(c_tok) - think_tok
    else:
        think_tok = think_chars / 4.0
        ans_tok = ans_chars / 4.0

    # server timings when trustworthy, else client math
    tm = usage.get('timings') or {}
    pred_ms = tm.get('predicted_ms')
    pred_n = tm.get('predicted_n')
    decode_span = max(total_elapsed - (ttft_any or 0), 0.001)
    n_dec = c_tok if exact else (think_tok + ans_tok)
    tok_s_decode = (pred_n * 1000.0 / pred_ms) if (pred_ms and pred_n) \
        else n_dec / decode_span

    row = {
        'ttft_any_ms': (ttft_any or 0) * 1000,
        'ttft_answer_ms': (ttft_answer or 0) * 1000,
        'tok_s_answer': ans_tok / answer_span if answer_span else 0.0,
        'tok_s_e2e': ans_tok / total_elapsed if total_elapsed else 0.0,
        'tok_s_decode': tok_s_decode,
        'prompt_tokens': p_tok,
        'cached_tokens': cached,
        'think_tokens': think_tok,
        'answer_tokens': ans_tok,
        'total_elapsed_s': total_elapsed,
        'finish': finish,
        'exact_tokens': exact,
        'usage': usage or None,
    }
    return row

# ------------------------------------------------------------- statistics
def paired_test(diffs):
    n = len(diffs)
    if n < 2:
        return {'n': n, 'mean': statistics.mean(diffs) if n else 0.0,
                'sd': 0.0, 't': 0.0, 'p': 1.0, 'ci95': (0.0, 0.0)}
    mean = statistics.mean(diffs)
    sd = statistics.stdev(diffs)
    if sd == 0.0:
        return {'n': n, 'mean': mean, 'sd': 0.0,
                't': float('inf') if mean else 0.0, 'p': 0.0 if mean else 1.0,
                'ci95': (mean, mean)}
    se = sd / sqrt(n)
    t = mean / se
    tcrit = 1.96 + 2.0 / (n - 1)
    p = 2.0 * (1.0 - 0.5 * (1 + erf(abs(t) / sqrt(2))))
    return {'n': n, 'mean': mean, 'sd': sd, 'se': se, 't': t, 'p': p,
            'ci95': (mean - tcrit * se, mean + tcrit * se)}

def mde_pct(sd, mean_b, n_pairs):
    if n_pairs < 2 or mean_b == 0:
        return 0.0
    return (1.96 + 0.84) * sd / sqrt(n_pairs) / mean_b * 100

# ------------------------------------------------------------- harness
def interleaved_pairs(pairs, rng, arm_keys):
    if len(arm_keys) != 2:
        raise ValueError('exactly two arms required')
    seq = []
    for i in range(pairs):
        first = rng.choice([0, 1])
        order = [arm_keys[first], arm_keys[1 - first]]
        seq.append((order, i))
    rng.shuffle(seq)
    return seq

METRICS = ['ttft_answer_ms', 'ttft_any_ms', 'tok_s_answer', 'tok_s_e2e',
           'tok_s_decode', 'think_tokens', 'answer_tokens', 'total_elapsed_s']

def fmt(row):
    return (f"ttft_ans {row['ttft_answer_ms']:7.0f}ms  ttft_any {row['ttft_any_ms']:6.0f}ms  "
            f"tok/s_ans {row['tok_s_answer']:6.1f}  tok/s_e2e {row['tok_s_e2e']:6.1f}  "
            f"tok/s_dec {row['tok_s_decode']:6.1f}  "
            f"think {row['think_tokens']:5.0f}t  ans {row['answer_tokens']:4.0f}t  "
            f"wall {row['total_elapsed_s']:6.1f}s"
            + ('' if row.get('exact_tokens') else ' [est]'))

def run_ab(args):
    prompt = open(args.prompt_file).read().strip() if args.prompt_file else DEFAULT_PROMPT
    arms = make_arms(args.budget)
    keys = args.arms
    for k in keys:
        if k not in arms:
            sys.exit(f"unknown arm {k!r}; valid for this config: {sorted(arms)}")
    rng = random.Random(args.seed)
    results = {a: [] for a in keys}
    print(f"model={MODEL} arms={'/'.join(keys)} pairs={args.pairs} budget={args.budget} "
          f"({ARM_LABEL[keys[0]]} vs {ARM_LABEL[keys[1]]})")
    print("warming (1 rep/arm, discarded)")
    for a in keys:
        stream_rep(prompt, arms[a], max_tokens=args.max_tokens, seed=args.seed)
    for order, pi in interleaved_pairs(args.pairs, rng, keys):
        row = {}
        for arm in order:
            # same seed within the pair so both arms see the same sampling RNG start
            r = stream_rep(prompt, arms[arm], max_tokens=args.max_tokens,
                           temperature=args.temperature, seed=args.seed + pi)
            results[arm].append(r)
            row[arm] = r
        print(f"  pair {pi+1:2d} {fmt(row[keys[0]])}  [{keys[0]}]")
        print(f"          {fmt(row[keys[1]])}  [{keys[1]}]")
    report(results, keys, args)

def contrast(results, a, b, label):
    print(f"\n  contrast {label}:")
    for mt in METRICS:
        if mt not in results[a][0] or mt not in results[b][0]:
            continue
        va = [r[mt] for r in results[a]]
        vb = [r[mt] for r in results[b]]
        n = min(len(va), len(vb))
        if n < 2:
            continue
        diffs = [va[i] - vb[i] for i in range(n)]
        st = paired_test(diffs)
        ma, mb_ = statistics.mean(va[:n]), statistics.mean(vb[:n])
        pct = (st['mean'] / mb_ * 100) if mb_ else 0.0
        thr = mde_pct(st['sd'], mb_, n)
        verdict = 'SIGNIFICANT' if (st['p'] < 0.05 and abs(pct) > thr) else 'inconclusive'
        print(f"  {mt:18s} {a} {ma:9.1f}   {b} {mb_:9.1f}   "
              f"diff {st['mean']:+9.1f} ({pct:+7.1f}%)  p={st['p']:.4f}  "
              f"MDE {thr:5.1f}%  {verdict}")

def report(results, keys, args):
    a, b = keys
    print()
    print('=' * 78)
    contrast(results, a, b, f'{a} ({ARM_LABEL[a]}) minus {b} ({ARM_LABEL[b]})')
    out = {'arms': {x: results[x] for x in keys},
           'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
           'pairs': args.pairs, 'budget': args.budget,
           'max_tokens': args.max_tokens, 'temperature': args.temperature,
           'seed': args.seed}
    if args.json:
        json.dump(out, open(args.json, 'w'), indent=1)
        print(f"\nwrote {args.json}")

def run_noise(args):
    prompt = open(args.prompt_file).read().strip() if args.prompt_file else DEFAULT_PROMPT
    arms = make_arms(args.budget)
    arm = args.arm
    reps = []
    print(f"noise floor: arm {arm} ({ARM_LABEL[arm]}), {args.reps} reps, "
          f"metric {args.metric}, budget={args.budget}")
    for i in range(args.reps):
        r = stream_rep(prompt, arms[arm], max_tokens=args.max_tokens,
                       temperature=args.temperature, seed=args.seed + i)
        reps.append(r[args.metric])
        print(f"  rep {i+1:2d}/{args.reps}: {r[args.metric]:9.1f}  ({fmt(r)})")
    mean = statistics.mean(reps)
    sd = statistics.stdev(reps) if len(reps) > 1 else 0.0
    cv = sd / mean * 100
    half = len(reps) // 2
    drift = ((statistics.mean(reps[half:]) - statistics.mean(reps[:half]))
             / statistics.mean(reps[:half]) * 100) if half else 0.0
    print(f"\n  mean {mean:.1f}  sd {sd:.1f}  CV {cv:.2f}%  drift {drift:+.1f}%  "
          f"range {min(reps):.1f}-{max(reps):.1f}")
    for n in (4, 6, 8, 10):
        print(f"  MDE at n={n}: {mde_pct(sd, mean, n):.2f}%")
    if args.json:
        json.dump({'reps': reps, 'mean': mean, 'sd': sd, 'cv': cv,
                   'arm': arm, 'metric': args.metric}, open(args.json, 'w'), indent=1)

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    def common(p):
        p.add_argument('--prompt-file')
        p.add_argument('--max-tokens', type=int, default=8192)
        p.add_argument('--temperature', type=int, default=1)
        p.add_argument('--seed', type=int, default=0)
        p.add_argument('--budget', type=int, default=None,
                       help='reasoning_budget_tokens for arm C (and noise --arm C)')
        p.add_argument('--json')
    a = sub.add_parser('ab')
    common(a)
    a.add_argument('--arms', default='A,B', help='comma-separated pair, e.g. A,B')
    a.add_argument('--pairs', type=int, default=8)
    n = sub.add_parser('noise')
    common(n)
    n.add_argument('--arm', default='A')
    n.add_argument('--reps', type=int, default=8)
    n.add_argument('--metric', default='tok_s_answer')
    args = ap.parse_args()

    if args.cmd == 'ab':
        args.arms = [x.strip().upper() for x in args.arms.split(',') if x.strip()]
        if len(args.arms) != 2:
            ap.error('ab needs exactly two arms, e.g. --arms A,B')
        run_ab(args)
    else:
        args.arm = args.arm.upper()
        run_noise(args)

if __name__ == '__main__':
    main()
