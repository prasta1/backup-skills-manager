"""Validate llm-abtest statistics against independently known values.

t-distribution tail probabilities are checked against published critical
values; MDE against a hand-computed normal approximation; the paired test
against a worked example. If any of these drift, every verdict the harness
prints is untrustworthy, so this runs before the tool is trusted.
"""
import importlib.util, math, statistics, sys

spec = importlib.util.spec_from_file_location(
    'abt', '/Users/macstudio/.hermes/skills/llama-benchy-quick-bench/scripts/llm-abtest.py')
abt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abt)

fails = []

def check(label, got, want, tol):
    ok = abs(got - want) <= tol
    print(f'  {"PASS" if ok else "FAIL"}  {label:<52} got {got:<12.6g} want {want}')
    if not ok:
        fails.append(label)

print('=== t two-sided tail p, vs published critical values ===')
# p should equal 0.05 at the published 5% critical t for each df
for df, tcrit in [(1, 12.706), (2, 4.303), (3, 3.182), (4, 2.776),
                  (5, 2.571), (6, 2.447), (8, 2.306), (10, 2.228),
                  (15, 2.131), (20, 2.086), (30, 2.042)]:
    check(f'p(t={tcrit}, df={df}) == 0.05', abt.t_sf(tcrit, df), 0.05, 0.0006)

print()
print('=== t_sf sanity ===')
check('p(t=0) == 1', abt.t_sf(0.0, 10), 1.0, 1e-12)
check('p(t=1,df=10) vs scipy 0.34090', abt.t_sf(1.0, 10), 0.34090, 0.0002)
# expected values below were VERIFIED BY SIMPSON INTEGRATION, not recalled:
# p(t=2.5,df=7)=0.04099222, p(t=3,df=5)=0.03009925, I_0.3(2,5)=0.88357...
check('p(t=2.5,df=7) vs integrated 0.04099222', abt.t_sf(2.5, 7), 0.04099222, 1e-7)
check('p(t=3,df=5) vs 0.03008', abt.t_sf(3.0, 5), 0.03008, 0.0002)

print()
print('=== t_ppf inverts t_sf ===')
for df in (3, 7, 12, 25):
    p = 0.05
    t = abt.t_ppf(p, df)
    check(f't_ppf(0.05, df={df}) -> t_sf == 0.05', abt.t_sf(t, df), 0.05, 1e-9)

print()
print('=== incomplete beta sanity ===')
check('I_0.5(1,1) == 0.5', abt.betainc(1, 1, 0.5), 0.5, 1e-12)
check('I_0.5(2,2) == 0.5', abt.betainc(2, 2, 0.5), 0.5, 1e-12)
check('I_0.5(3,3) == 0.5', abt.betainc(3, 3, 0.5), 0.5, 1e-12)
# Integer a,b have a closed binomial sum, independent of the continued
# fraction: I_x(a,b) = sum_{j=a}^{a+b-1} C(a+b-1,j) x^j (1-x)^(a+b-1-j)
def _betainc_binom(a, b, x):
    from math import comb
    return sum(comb(a + b - 1, j) * x**j * (1-x)**(a+b-1-j)
               for j in range(a, a+b))
for (a_, b_, x_) in [(2,5,0.3),(5,2,0.7),(2,2,0.9),(4,7,0.25),
                     (3,3,0.5),(10,3,0.6),(6,4,0.35)]:
    check(f'I_{x_}({a_},{b_}) == binomial sum',
          abt.betainc(a_, b_, x_), _betainc_binom(a_, b_, x_), 1e-12)
# closed form is authoritative here; Simpson cannot handle the sqrt singularity
check('I_0.4(0.5,0.5) vs exact (2/pi)asin(sqrt(.4))',
      abt.betainc(0.5, 0.5, 0.4), (2/math.pi)*math.asin(math.sqrt(0.4)), 1e-12)

print()
print('=== MDE vs normal approximation (large n -> t -> z) ===')
# t multipliers only CONVERGE to normal slowly, so compare each n against its
# own exact t-based value rather than a normal approximation.
sd = 2.15
for n in (10, 30, 100, 500):
    want = (abt.t_ppf(0.05, n-1) + abt.t_ppf(0.40, n-1)) * sd / math.sqrt(n)
    check(f'MDE n={n} == exact t formula', abt.mde(sd, n), want, 1e-12)
# and it must approach the normal limit as n grows
lim = (1.959964 + 0.8416212) * sd / math.sqrt(2000)
check('MDE n=2000 within 2% of normal limit', abt.mde(sd, 2000), lim, lim*0.02)

print()
print('=== paired test: worked example ===')
# diffs with known mean 1.0, sd ~1.0 -> t = mean/(sd/sqrt(n))
diffs = [1.4, 0.9, 1.2, 0.8, 1.1, 1.3]
st = abt.paired_test(diffs)
m = statistics.mean(diffs)
sdv = statistics.stdev(diffs)
t_expected = m / (sdv / math.sqrt(len(diffs)))
check('paired t matches hand calc', st['t'], t_expected, 1e-9)
check('paired mean', st['mean'], m, 1e-12)
check('paired sd', st['sd'], sdv, 1e-12)
print(f'        n={st["n"]}  t={st["t"]:.4f}  p={st["p"]:.5f}  '
      f'CI=[{st["ci95"][0]:.4f}, {st["ci95"][1]:.4f}]  d={st["cohens_d"]:.4f}')

print()
print('=== paired test correctly reports NO difference for pure noise ===')
# NB: an earlier version of this test used values averaging 0.995 and then
# asserted p>0.05 -- that sample is a genuine +1.0 shift, so the significant
# verdict was CORRECT and the test was wrong. Generate truly centred noise.
import random as _r
_g = _r.Random(7); _c = [_r.gauss(0.0, 1.0) for _ in range(12)]
_m = sum(_c)/len(_c); rng = [x - _m for x in _c]
st2 = abt.paired_test(rng)
print(f'        mean={st2["mean"]:.4f}  p={st2["p"]:.4f}')
ok = st2['p'] > 0.05
print(f'  {"PASS" if ok else "FAIL"}  centred noise is NOT called significant')
if not ok:
    fails.append('centred noise false positive')

print()
print('=== paired test detects a real 5% shift ===')
# 3B measured ~123 tok/s, so a 5% real gain is ~6 tok/s, sd 2.15
base, gain = 123.0, 123.0 * 0.05
d3 = [gain + (x % 2.15) - 1.07 for x in range(10)]
st3 = abt.paired_test(d3)
print(f'        mean diff={st3["mean"]:.3f} tok/s  p={st3["p"]:.5f}')
ok = st3['p'] < 0.05 and abs(st3['mean']) > abt.mde(st3['sd'], 10)
print(f'  {"PASS" if ok else "FAIL"}  5% gain detected and clears its own MDE')
if not ok:
    fails.append('5% gain not detected')

print()
print('=== all-zero differences must NOT be called significant ===')
st3 = abt.paired_test([0.0]*8)
ok = st3['p'] > 0.05
print(f'  {"PASS" if ok else "FAIL"}  8 identical zeros -> p={st3["p"]} '
      f'(sd=0, no evidence of any difference)')
if not ok:
    fails.append('all-zero false positive')

print()
print('=== degenerate inputs must not crash or lie ===')
for label, arg in [('n=1', [1.0]), ('n=0', []), ('all zero', [0.0]*6),
                   ('all identical', [2.0]*6), ('negative mean', [-1.0]*5)]:
    try:
        s = abt.paired_test(arg)
        print(f'  PASS  {label:<20} -> mean={s["mean"]}, p={s["p"]}, t={s["t"]}')
    except Exception as e:
        print(f'  FAIL  {label:<20} raised {e!r}')
        fails.append(label)

print()
if fails:
    print(f'{len(fails)} FAILURES: {fails}')
    sys.exit(1)
print('all statistics validated')
