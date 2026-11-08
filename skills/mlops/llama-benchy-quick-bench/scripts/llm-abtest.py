#!/usr/bin/env python3
"""
llm-abtest — interleaved paired A/B harness for llama.cpp inference tuning.

The problem it solves: single-run flag comparisons on this box produce
differences smaller than run-to-run variance. Measured noise floor on
ms-ministral-3-3b was CV 1.75% with a -1.6% downward drift inside a single
10-second window. Anything under ~2% is not a finding.

Design rules this enforces:
  1. Arms are INTERLEAVED, never sequential. A drifting box biases the
     second arm; alternating within each pair cancels linear drift.
  2. Order within each pair is RANDOMIZED, so warm-up and position effects
     land on both arms equally instead of always favouring one.
  3. Output length is PINNED (min_tokens). Otherwise you are timing
     early-EOS luck, not the model.
  4. A difference must clear the minimum detectable effect at the measured
     noise level before it is called a win. Default verdict is inconclusive.
  5. Two-sample t-test is WRONG here. Arms share a machine and a thermal
     state, so the samples are paired; a paired test on the within-pair
     differences is the correct instrument and is strictly more powerful.

Server-level levers (--parallel, --ctx-size, -ctk/-ctv, --batch-size ...)
require a process restart, so this spawns one private llama-server per arm
and interleaves requests across both. That costs 2x model memory and it does
NOT touch the llama-swap config or the production endpoint on :9292.

Usage
  # noise floor on the live endpoint, no config changes at all
  llm-abtest.py noise  --model ms-ministral-3-3b --pairs 8

  # server-level lever: two private servers, interleaved
  llm-abtest.py ab --model gemma-4-26b-moe --flag --parallel=2 \
      --pairs 8 --tokens 128

  # request-level lever against the live endpoint
  llm-abtest.py ab --model ms-gemma-4-26b-moe --request temperature=0.7 \
      --pairs 6

  # concurrency question (does --parallel actually help under load?)
  llm-abtest.py ab --model gemma-4-26b-moe --flag --parallel=2 \
      --pairs 6 --concurrency 4
"""
import argparse, json, math, os, random, signal, statistics, subprocess
import sys, time, urllib.error, urllib.request
from datetime import datetime

# ---------------------------------------------------------------- statistics

def _betacf(a, b, x, itmax=300, eps=3e-16, fpmin=1e-300):
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """Regularized incomplete beta I_x(a,b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log1p(-x))
    front = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + b * math.log1p(-x) + a * math.log(x)) * _betacf(b, a, 1.0 - x) / b


def t_sf(t, df):
    """Two-sided p-value for a Student t statistic."""
    if df <= 0:
        return 1.0
    t = abs(t)
    if t == 0.0:
        return 1.0
    return betainc(df / 2.0, 0.5, df / (df + t * t))


def t_ppf(p, df):
    """Inverse t CDF by bisection. p in (0,1)."""
    lo, hi = -400.0, 400.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        # two-sided tail at mid
        if t_sf(mid, df) > p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def paired_test(diffs):
    """One-sample t-test on within-pair differences vs 0.

    Returns dict with mean, sd, t, p, ci95, cohens_d.
    """
    n = len(diffs)
    if n == 0:
        return {'n': 0, 'mean': 0.0, 'sd': 0.0, 'se': 0.0, 't': 0.0, 'p': 1.0,
                'ci95': (0.0, 0.0), 'cohens_d': 0.0}
    mean = statistics.mean(diffs)
    if n < 2:
        return {'n': n, 'mean': mean, 'sd': 0.0, 't': 0.0, 'p': 1.0,
                'ci95': (0.0, 0.0), 'cohens_d': 0.0}
    sd = statistics.stdev(diffs)
    if sd == 0.0:
        return {'n': n, 'mean': mean, 'sd': 0.0,
                't': float('inf') if mean else 0.0,
                'p': 0.0 if mean else 1.0,
                'ci95': (mean, mean), 'cohens_d': float('inf') if mean else 0.0}
    se = sd / math.sqrt(n)
    t = mean / se
    p = t_sf(t, n - 1)
    tcrit = t_ppf(0.05, n - 1)          # 95% two-sided
    half = tcrit * se
    d = mean / sd                        # Cohen's d for paired samples
    return {'n': n, 'mean': mean, 'sd': sd, 'se': se, 't': t, 'p': p,
            'ci95': (mean - half, mean + half), 'cohens_d': d}


def mde(sd, n_pairs, power=0.80, alpha=0.05):
    """Minimum detectable effect, in the same units as the measurement.

    MDE = (t_{alpha/2} + t_{power}) * sd / sqrt(n)

    NOTE t_ppf here is a TWO-SIDED inverse (it inverts t_sf, the two-sided
    tail), so the power term must be looked up at 2*(1-power) = 0.40 for 80%
    power. Passing 1-power = 0.20 targets the 90th percentile instead and
    inflates MDE by ~1.17x at n=10, which silently shrinks the set of
    findings that clear the bar.
    """
    if n_pairs < 2 or sd == 0:
        return 0.0
    df = n_pairs - 1
    t_a = t_ppf(alpha, df)
    t_b = t_ppf(2.0 * (1.0 - power), df)
    return (t_a + t_b) * sd / math.sqrt(n_pairs)

# ---------------------------------------------------------------- transport

def post_json(url, payload, timeout=600):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def measure(url, model, tokens, concurrency=1, timeout=600, seed=0):
    """One rep. Returns aggregate tok/s.

    concurrency>1 fires that many requests simultaneously and reports
    aggregate throughput -- the only honest way to evaluate --parallel,
    since a single client cannot see a second slot's effect.
    """
    def one(i):
        payload = {'model': model,
                   'messages': [{'role': 'user', 'content': PROMPT}],
                   'max_tokens': tokens, 'min_tokens': tokens,
                   'temperature': 0, 'seed': seed + i}
        d = post_json(url, payload, timeout)
        tm = d.get('timings') or {}
        return tm.get('predicted_n', 0), tm.get('predicted_per_second', 0.0)

    t0 = time.perf_counter()
    if concurrency == 1:
        n, rate = one(seed)
        el = time.perf_counter() - t0
        return {'tok_s': rate, 'tokens': n, 'elapsed': el, 'per_req': [rate]}

    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        res = list(ex.map(one, range(concurrency)))
    el = time.perf_counter() - t0
    total = sum(r[0] for r in res)
    return {'tok_s': total / el if el else 0.0, 'tokens': total,
            'elapsed': el, 'per_req': [r[1] for r in res]}

PROMPT = ("Explain in detail how a bicycle rear derailleur shifts gears, "
          "including the role of the cable tension and the limit screws.")

# ---------------------------------------------------------------- servers

def _resident_model_gb():
    """Total RSS of resident llama-server processes, in GB."""
    try:
        out = subprocess.run(['ps', '-o', 'rss=,command=', '-ax'],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return 0.0
    total = 0
    for line in out.splitlines():
        if 'llama-server --port' in line and 'grep' not in line:
            parts = line.strip().split(None, 1)
            if parts and parts[0].isdigit():
                total += int(parts[0])
    return total / 1048576.0


def _preflight_memory(weight_gb, ctx):
    """Fail early and legibly rather than dying as 'Insufficient Memory'.

    Metal's buffer pool is much smaller than system RAM on unified memory, so
    the practical ceiling is not total free pages. Two full-size servers plus
    whatever llama-swap already holds is the thing that breaks.
    """
    resident = _resident_model_gb()
    need = 2 * weight_gb + 2.0        # weights x2 plus KV/compute overhead
    print(f'  preflight: need ~{need:.0f} GB for both arms; '
          f'llama-swap already holds {resident:.1f} GB resident')
    if resident > 1.0:
        print('  WARNING: resident models will contend for the Metal buffer '
              'pool. If a server dies with "Insufficient Memory", unload them '
              'first (they return after ttl) or pass --ctx to shrink the KV '
              'cache further.')
    try:
        out = subprocess.run(['sysctl', '-n', 'hw.memsize'],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        total_gb = int(out) / 1e9
        print(f'  preflight: {total_gb:.0f} GB physical, '
              f'~{total_gb - resident - need:.0f} GB headroom after both arms')
    except Exception:
        pass


def _split_flags(text):
    """Split a flag string, normalising --name=value to --name value.

    llama.cpp's arg parser rejects --parallel=2 ("invalid argument"), so the
    equals form has to become two argv entries. Accepting both spellings
    here means callers can use whichever reads better on the command line.
    """
    out = []
    for tok in (text or '').split():
        if tok.startswith('--') and '=' in tok:
            name, _, val = tok.partition('=')
            out.extend([name, val])
        else:
            out.append(tok)
    return out


class Server:
    """A private llama-server on its own port. Never touches :9292."""

    def __init__(self, model_path, port, flags, ctx=None, binary=None):
        self.model_path = model_path
        self.port = port
        self.flags = flags
        self.ctx = ctx
        self.binary = binary or '/opt/homebrew/bin/llama-server'
        self.proc = None
        self.log = None

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}'

    def start(self, timeout=600):
        cmd = [self.binary, '--port', str(self.port), '--host', '127.0.0.1',
               '--model', self.model_path]
        if self.ctx:
            cmd += ['--ctx-size', str(self.ctx)]
        cmd += self.flags
        self.log = open(f'/tmp/abtest-{self.port}.log', 'w')
        self.proc = subprocess.Popen(
            cmd, stdout=self.log, stderr=subprocess.STDOUT,
            preexec_fn=os.setsid)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f'server on :{self.port} exited rc={self.proc.returncode}; '
                    f'see /tmp/abtest-{self.port}.log')
            try:
                with urllib.request.urlopen(f'{self.url}/health', timeout=3) as r:
                    if r.status == 200:
                        return self
            except Exception:
                pass
            time.sleep(1.0)
        self.stop()
        raise TimeoutError(f'server on :{self.port} not healthy in {timeout}s')

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
                self.proc.wait(timeout=30)
            except Exception:
                try:
                    os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
                except Exception:
                    pass
        if self.log:
            try:
                self.log.close()
            except Exception:
                pass
            self.log = None
        self.proc = None

    def sanity(self, model, tokens=32):
        """Refuse to time a server that is not actually coherent."""
        d = post_json(f'{self.url}/v1/chat/completions', {
            'model': model,
            'messages': [{'role': 'user',
                          'content': 'What is the capital of France? One word.'}],
            'max_tokens': 96, 'temperature': 0}, 300)
        m = d['choices'][0]['message']
        blob = ((m.get('content') or '') + ' ' + (m.get('reasoning_content') or '')).lower()
        return 'paris' in blob, blob[:120]

# ---------------------------------------------------------------- harness

def interleaved_pairs(pairs, rng):
    """Yield (order, pair_index). order is [0,1] or [1,0], randomized.

    Interleaving is the whole point: measuring all of arm A then all of arm B
    hands any drift entirely to one arm.
    """
    seq = []
    for i in range(pairs):
        first = rng.choice([0, 1])
        seq.append(([first, 1 - first], i))
    rng.shuffle(seq)          # also randomize which pair comes when
    return seq


def run_noise(args):
    url = f'http://127.0.0.1:{args.port}/v1/chat/completions'
    rng = random.Random(args.seed)
    rates = []
    for i in range(args.pairs):
        r = measure(url, args.model, args.tokens, args.concurrency, seed=i)
        rates.append(r['tok_s'])
        print(f'  rep {i+1:2d}/{args.pairs}: {r["tok_s"]:8.2f} tok/s')
    return summarize_noise(rates, args)


def summarize_noise(rates, args):
    mean = statistics.mean(rates)
    sd = statistics.stdev(rates) if len(rates) > 1 else 0.0
    cv = sd / mean * 100 if mean else 0.0
    half = len(rates) // 2
    drift = ((statistics.mean(rates[half:]) - statistics.mean(rates[:half]))
             / statistics.mean(rates[:half]) * 100) if half else 0.0
    print()
    print(f'  model   {args.model}   {args.tokens} pinned output tokens')
    print(f'  runs    {len(rates)}')
    print(f'  mean    {mean:.2f} tok/s')
    print(f'  sd      {sd:.2f}')
    print(f'  CV      {cv:.2f} %')
    print(f'  drift   {drift:+.2f} %  (2nd half vs 1st)')
    print(f'  range   {min(rates):.2f} - {max(rates):.2f}')
    print()
    for n in (4, 6, 8, 10, 12):
        print(f'  MDE at n={n:2d}: {mde(sd, n):6.2f} %')
    return {'rates': rates, 'mean': mean, 'sd': sd, 'cv': cv, 'drift': drift,
            'model': args.model, 'tokens': args.tokens,
            'pairs': args.pairs, 'concurrency': args.concurrency,
            'timestamp': datetime.now().isoformat(timespec='seconds')}


def run_ab(args):
    rng = random.Random(args.seed)
    servers, targets = [], []

    if args.flag:
        # server-level: two private servers, base arm vs candidate arm
        # Context is NOT the variable under test here, and leaving it at the
        # model's trained maximum makes each private server try to allocate a
        # full-size KV cache. Two of those exhausts the Metal buffer pool
        # ("Insufficient Memory") even on a 96 GB box. Pin it small.
        ctx = args.ctx if args.ctx else 8192
        base_flags, cand_flags = [], []
        for f in (args.flag if isinstance(args.flag, list) else [args.flag]):
            cand_flags.extend(_split_flags(f))
        if args.base:
            base_flags = _split_flags(args.base)
        p1, p2 = args.port_a, args.port_b
        weight_gb = os.path.getsize(args.model_path) / 1e9
        print(f'  context pinned to {ctx} for both arms (not under test)')
        _preflight_memory(weight_gb, ctx)
        a = Server(args.model_path, p1, base_flags, ctx)
        b = Server(args.model_path, p2, cand_flags, ctx)
        print(f'  starting arm A  :{p1}  flags={base_flags or "(none)"}')
        print(f'  starting arm B  :{p2}  flags={cand_flags}')
        print(f'  NOTE: both arms resident at once = ~2x '
              f'{os.path.getsize(args.model_path)/1e9:.1f} GB of weights.')
        try:
            a.start(); servers.append(a)
            b.start(); servers.append(b)
            for s, label in ((a, 'A'), (b, 'B')):
                ok, blob = s.sanity(args.served_name)
                if not ok:
                    raise RuntimeError(
                        f'arm {label} failed coherence check (got: {blob!r}); '
                        f'refusing to benchmark a broken server')
                print(f'  arm {label} coherent')
            targets = [a.url + '/v1/chat/completions',
                       b.url + '/v1/chat/completions']
        except Exception:
            for s in servers:
                s.stop()
            raise
    else:
        targets = [f'http://127.0.0.1:{args.port}/v1/chat/completions'] * 2

    # warmup both arms, discarded
    print(f'  warming ({args.warmup} rep/arm, discarded)')
    for u in targets:
        for _ in range(args.warmup):
            measure(u, args.served_name, args.tokens, args.concurrency)

    payload_extra = {}
    for kv in (args.request or []):
        k, _, v = kv.partition('=')
        try:
            payload_extra[k] = json.loads(v)
        except json.JSONDecodeError:
            payload_extra[k] = v

    results = {0: [], 1: []}
    try:
        order_seq = interleaved_pairs(args.pairs, rng)
        for order, pi in order_seq:
            row = {}
            for arm in order:
                r = measure(targets[arm], args.served_name, args.tokens,
                            args.concurrency, seed=pi * 10 + arm)
                results[arm].append(r['tok_s'])
                row[arm] = r['tok_s']
            d = row[0] - row[1]
            print(f'  pair {pi+1:2d}/{args.pairs}  A={row[0]:8.2f}  '
                  f'B={row[1]:8.2f}  diff={d:+7.2f} tok/s  '
                  f'({d/row[1]*100:+5.2f}%)')
    finally:
        for s in servers:
            s.stop()
        if servers:
            print('  private servers stopped')

    return report(results, args)


def report(results, args):
    a, b = results[0], results[1]
    ma, mb = statistics.mean(a), statistics.mean(b)
    # pair k of arm A vs pair k of arm B (both saw the same seed block)
    diffs = [a[i] - b[i] for i in range(min(len(a), len(b)))]
    st = paired_test(diffs)
    sd_pool = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
    thr = mde(sd_pool, len(diffs))
    pct = (st['mean'] / mb * 100) if mb else 0.0
    thr_pct = (thr / mb * 100) if mb else 0.0
    ci_pct = (st['ci95'][0] / mb * 100, st['ci95'][1] / mb * 100)

    if st['p'] < 0.05 and abs(pct) > thr_pct:
        verdict = 'WIN  (B faster)' if pct > 0 else 'LOSS (B slower)'
    elif st['p'] < 0.05:
        verdict = 'INCONCLUSIVE (significant but below MDE)'
    else:
        verdict = 'INCONCLUSIVE (no detectable difference)'

    print()
    print('=' * 66)
    print(f'  arm A  {args.flag and (args.base or "no extra flags") or "live endpoint"}')
    print(f'  arm B  {args.flag and " ".join(args.flag) or "request: " + str(args.request)}')
    print(f'  model  {args.served_name}   pairs={args.pairs}   '
          f'tokens={args.tokens}   concurrency={args.concurrency}')
    print('=' * 66)
    print(f'  A mean  {ma:8.2f} tok/s')
    print(f'  B mean  {mb:8.2f} tok/s')
    print(f'  paired diff  {st["mean"]:+7.2f} tok/s  ({pct:+.2f}%)')
    print(f'  95% CI       [{ci_pct[0]:+.2f}%, {ci_pct[1]:+.2f}%]')
    print(f'  t({st["n"]-1}) = {st["t"]:.3f}   p = {st["p"]:.4f}')
    print(f'  Cohen d      {st["cohens_d"]:+.3f}')
    print(f'  noise sd     {sd_pool:.2f} tok/s')
    print(f'  MDE          {thr_pct:.2f}%   (must be exceeded to count)')
    print()
    print(f'  VERDICT: {verdict}')
    print()
    return {'arm_a': a, 'arm_b': b, 'mean_a': ma, 'mean_b': mb,
            'diff_tok_s': st['mean'], 'diff_pct': pct,
            'ci95_pct': list(ci_pct), 't': st['t'], 'p': st['p'],
            'cohens_d': st['cohens_d'], 'noise_sd': sd_pool,
            'mde_pct': thr_pct, 'verdict': verdict,
            'model': args.served_name, 'pairs': args.pairs,
            'tokens': args.tokens, 'concurrency': args.concurrency,
            'flag_b': args.flag, 'base_flags': args.base,
            'request_b': args.request, 'seed': args.seed,
            'timestamp': datetime.now().isoformat(timespec='seconds')}

# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    def common(p):
        p.add_argument('--model', required=True, help='served model id')
        p.add_argument('--pairs', type=int, default=8)
        p.add_argument('--tokens', type=int, default=128,
                       help='pinned output tokens (min_tokens); raise for stable t/s')
        p.add_argument('--concurrency', type=int, default=1)
        p.add_argument('--warmup', type=int, default=1)
        p.add_argument('--seed', type=int, default=0)
        p.add_argument('--port', type=int, default=9292)
        p.add_argument('--json', help='write full result JSON here')

    n = sub.add_parser('noise', help='noise floor against the live endpoint')
    common(n)
    n.set_defaults(func=run_noise)

    a = sub.add_parser('ab', help='interleaved paired A/B')
    common(a)
    a.add_argument('--flag', action='append',
                   help='llama-server flag for arm B, e.g. --parallel=2. '
                        'Repeatable. Triggers private-server mode.')
    a.add_argument('--base', help='flags for arm A, e.g. "--parallel=1"')
    a.add_argument('--request', action='append',
                   help='request param for arm B, e.g. temperature=0.7')
    a.add_argument('--model-path', help='GGUF path (required with --flag)')
    a.add_argument('--served-name', help='id to send in the request body')
    a.add_argument('--ctx', type=int, help='--ctx-size for both arms')
    a.add_argument('--port-a', type=int, default=9391)
    a.add_argument('--port-b', type=int, default=9392)
    a.set_defaults(func=run_ab)

    args = ap.parse_args()
    if getattr(args, 'served_name', None) is None:
        args.served_name = args.model
    if getattr(args, 'flag', None) and not args.model_path:
        ap.error('--flag needs --model-path (private-server mode)')

    try:
        out = args.func(args)
    except KeyboardInterrupt:
        print('\ninterrupted', file=sys.stderr)
        return 130
    except Exception as e:
        print(f'\nERROR: {e}', file=sys.stderr)
        return 1

    if args.json:
        with open(args.json, 'w') as f:
            json.dump(out, f, indent=1)
        print(f'wrote {args.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
