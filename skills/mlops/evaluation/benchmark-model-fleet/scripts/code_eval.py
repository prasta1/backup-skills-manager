#!/usr/bin/env python3
"""Execution-scored coding evaluation.

Ground truth is "does the generated code run and produce the right values" --
not whether it contains particular words. This replaces, for the code family,
a 5-substring rubric that provably cannot tell a correct answer from a wrong
one (see prompts/code_execution.py header).

DESIGN NOTES
------------
* Scoring is per ASSERTION. 41 tasks x ~5 assertions ~= 200 graded points,
  against a measured ~4-task resolution floor for binary task scoring.
* Cost is recorded per task (prompt/completion tokens, wall seconds) so results
  can be normalised: tokens per SOLVED task is the number that matters for
  agent work, where verbosity is paid every turn.
* Model output is UNTRUSTED. It is executed in a separate short-lived Python
  subprocess with a hard timeout, never in this process. A benchmark that runs
  generated code in-process risks the harness itself.

Usage
-----
  code_eval.py --self-test                      # verify the instrument first
  code_eval.py --models mb-devstral-24b --endpoint http://host:8999
"""
import argparse
import json
import os
import re
import statistics as st
import subprocess
import sys
import tempfile
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_TASKFILE = os.path.join(_HERE, "..", "prompts", "code_execution.py")


def _load_tasks(path):
    """Load CODING_PROMPTS by path, matching parse_prompts_file's convention.

    (prompts/ is a plain directory, not a package, so a normal import fails.)
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("code_execution", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CODING_PROMPTS


CODING_PROMPTS = _load_tasks(_TASKFILE)

ASK = (
    "Write a Python solution for the task below.\n\n"
    "TASK: {prompt}\n\n"
    "Requirements: define a function named `{func}`. Use only the standard "
    "library. Output the COMPLETE code inside a single ```python code block "
    "with no explanation."
)

# A system message is sent on EVERY call for two reasons.
# 1. It is what real agent traffic looks like -- Hermes always sends one.
# 2. Without it, llama-server injects its own architecture-specific DEFAULT
#    system prompt. Measured on devstral: no system message -> 556 prompt
#    tokens for the message "hi"; with one -> 12. The Qwen models inject ~0.
#    Omitting it therefore charges one model 549 hidden tokens per call and
#    silently corrupts every cost comparison built on the results.
SYSTEM = "You are a precise coding assistant. Follow the task exactly."

CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def extract_code(text):
    """Pull the first fenced code block; fall back to the raw text."""
    if not text:
        return ""
    blocks = CODE_RE.findall(text)
    if blocks:
        # the longest block is most likely the implementation, not an example
        return max(blocks, key=len).strip()
    stripped = text.strip()
    if stripped.startswith("def ") or "\ndef " in stripped:
        return stripped
    return ""


# ---------------------------------------------------------------- worker
# SECURITY NOTE ON eval(): evaluating test expressions is this harness's whole
# purpose, and the evaluated strings come from prompts/code_execution.py -- a
# reviewed, version-controlled file -- never from model output. The model's
# code is the untrusted part, and it is compiled and executed only inside a
# disposable subprocess (run_tests) with a hard timeout and a stripped
# environment, so nothing untrusted touches the harness process itself.
WORKER = r'''
import json, sys, traceback
payload = json.load(sys.stdin)
ns = {}
out = {"import_error": None, "results": []}
try:
    exec(compile(payload["code"], "<model>", "exec"), ns)
except BaseException as e:
    out["import_error"] = "%s: %s" % (type(e).__name__, e)
    print(json.dumps(out)); sys.exit(0)

# Rebuild the test cases as real Python objects. They cannot arrive as JSON:
# JSON stringifies dict keys, so {1: 'a'} would come back as {"1": "a"} and
# every int-keyed expected value would compare unequal. The source is ours.
tests = eval(payload["tests"])  # noqa: S307

for expr, expected in tests:
    rec = {"expr": expr, "ok": False, "got": None, "err": None}
    try:
        # eval with ONE namespace for globals and locals: a lambda or
        # comprehension body resolves names in globals, not locals, so passing
        # locals separately makes solve() invisible inside them.
        got = eval(expr, ns)  # noqa: S307
        rec["got"] = repr(got)[:120]
        rec["ok"] = bool(got == expected)
    except BaseException as e:
        rec["err"] = "%s: %s" % (type(e).__name__, e)
    out["results"].append(rec)
print(json.dumps(out))
'''


def run_tests(code, tests, timeout=15):
    """Execute generated code + assertions in a disposable subprocess."""
    if not code.strip():
        return {"import_error": "no code block found", "results": []}
    payload = json.dumps({"code": code, "tests": repr(tests)})
    with tempfile.TemporaryDirectory() as td:
        wp = os.path.join(td, "worker.py")
        with open(wp, "w") as f:
            f.write(WORKER)
        try:
            p = subprocess.run(
                [sys.executable, wp], input=payload, capture_output=True,
                text=True, timeout=timeout, cwd=td,
                env={"PATH": "/usr/bin:/bin", "HOME": td},
            )
        except subprocess.TimeoutExpired:
            return {"import_error": "TIMEOUT after %ds" % timeout, "results": []}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"import_error": "worker produced no JSON: %s"
                                % (p.stderr[-200:] or p.stdout[-200:]),
                "results": []}


# ---------------------------------------------------------------- endpoint
def ask(endpoint, model, prompt, max_tokens, timeout=300):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
    except Exception as e:
        return None, time.time() - t0, "%s: %s" % (type(e).__name__, e)
    wall = time.time() - t0
    ch = d["choices"][0].get("message", {})
    content = ch.get("content") or ch.get("reasoning_content") or ""
    usage = d.get("usage") or {}
    return (content, wall, None, usage, d["choices"][0].get("finish_reason"))


def evaluate(model, endpoint, max_tokens, tasks, verbose=True):
    rows = []
    for i, t in enumerate(tasks, 1):
        prompt = ASK.format(prompt=t["prompt"], func=t["func"])
        res = ask(endpoint, model, prompt, max_tokens)
        if res[0] is None:
            rows.append({"id": t["id"], "difficulty": t["difficulty"],
                         "error": res[2], "passed": 0, "total": len(t["tests"]),
                         "tokens": 0, "wall": res[1]})
            if verbose:
                print("  [%2d/%d] %-26s ERROR %s" % (i, len(tasks), t["id"], res[2][:40]))
            continue
        content, wall, _, usage, finish = res
        code = extract_code(content)
        outcome = run_tests(code, t["tests"])
        results = outcome["results"]
        passed = sum(1 for r in results if r["ok"])
        total = len(t["tests"])
        toks = (usage.get("completion_tokens", 0) or 0)
        rows.append({
            "id": t["id"], "difficulty": t["difficulty"], "passed": passed,
            "total": total, "solved": passed == total,
            "tokens": toks, "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
            "wall": wall, "finish": finish, "import_error": outcome["import_error"],
            "code_chars": len(code),
            # Retain the code: without it a surprising result cannot be audited,
            # and an unauditable benchmark is indistinguishable from a bug.
            "code": code[:4000],
            "failed_exprs": [r["expr"] for r in results if not r["ok"]][:5],
            "errors": [r["err"] for r in results if not r["ok"] and r["err"]][:3],
        })
        if verbose:
            flag = "ok  " if passed == total else ("PART" if passed else "FAIL")
            print("  [%2d/%d] %-26s %s %d/%d  %5dtok %6.1fs%s"
                  % (i, len(tasks), t["id"], flag, passed, total, toks, wall,
                     "  <" + outcome["import_error"][:40] + ">"
                     if outcome["import_error"] else ""))
    return rows


def summarise(model, rows):
    n = len(rows)
    solved = sum(1 for r in rows if r.get("solved"))
    ap = sum(r["passed"] for r in rows)
    at = sum(r["total"] for r in rows)
    toks = sum(r["tokens"] for r in rows)
    pto = sum(r.get("prompt_tokens", 0) for r in rows)
    wall = sum(r["wall"] for r in rows)
    med_w = st.median([r["wall"] for r in rows]) if rows else 0
    return {
        "model": model, "tasks": n, "solved": solved,
        "solved_pct": round(100.0 * solved / n, 1) if n else 0,
        "assertions_passed": ap, "assertions_total": at,
        "assertion_pct": round(100.0 * ap / at, 1) if at else 0,
        "completion_tokens": toks, "prompt_tokens": pto,
        "wall_total": round(wall, 1), "wall_median": round(med_w, 2),
        "tokens_per_solved_task": round(toks / solved, 1) if solved else None,
        "wall_per_solved_task": round(wall / solved, 2) if solved else None,
    }


def print_summary(s):
    print()
    print("  %-22s %-14s" % (s["model"], ""))
    print("    solved           : %d/%d tasks (%.1f%%)"
          % (s["solved"], s["tasks"], s["solved_pct"]))
    print("    assertions       : %d/%d (%.1f%%)"
          % (s["assertions_passed"], s["assertions_total"], s["assertion_pct"]))
    print("    completion tokens: %d  (prompt %d)"
          % (s["completion_tokens"], s["prompt_tokens"]))
    print("    wall             : %.1fs total, %.2fs median/task"
          % (s["wall_total"], s["wall_median"]))
    if s["tokens_per_solved_task"]:
        print("    TOKENS PER SOLVED TASK: %s   WALL PER SOLVED TASK: %ss"
              % (s["tokens_per_solved_task"], s["wall_per_solved_task"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=[])
    ap.add_argument("--endpoint", default="http://127.0.0.1:9292")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--out", default=None)
    ap.add_argument("--self-test", action="store_true",
                    help="score the REFERENCE solutions -- must be 100%")
    ap.add_argument("--only", default=None, help="substring filter on task id")
    args = ap.parse_args()

    tasks = CODING_PROMPTS
    if args.only:
        tasks = [t for t in tasks if args.only in t["id"]]
    print("  %d tasks, %d assertions"
          % (len(tasks), sum(len(t["tests"]) for t in tasks)))

    if args.self_test:
        print("\n  === SELF-TEST: reference solutions (instrument validity) ===")
        bad = 0
        for t in tasks:
            out = run_tests(t["reference"], t["tests"])
            r = out["results"]
            p = sum(1 for x in r if x["ok"])
            if p != len(t["tests"]) or out["import_error"]:
                bad += 1
                print("    BROKEN  %-26s %d/%d %s"
                      % (t["id"], p, len(t["tests"]), out["import_error"] or ""))
                for x in r:
                    if not x["ok"]:
                        print("            %-34s got=%s err=%s"
                              % (x["expr"][:34], x["got"], x["err"]))
            else:
                print("    ok      %-26s %d/%d" % (t["id"], p, len(t["tests"])))
        print("\n  REFERENCE RESULT: %s  (%d/%d tasks fully passing)"
              % ("CLEAN" if not bad else "BROKEN -- %d task(s)" % bad,
                 len(tasks) - bad, len(tasks)))
        return 1 if bad else 0

    if not args.models:
        ap.error("need --models or --self-test")

    all_rows, summaries = {}, []
    for m in args.models:
        print("\n  === %s ===" % m)
        rows = evaluate(m, args.endpoint, args.max_tokens, tasks)
        all_rows[m] = rows
        s = summarise(m, rows)
        summaries.append(s)
        print_summary(s)

    if args.out:
        with open(args.out, "w") as f:
            json.dump({"summaries": summaries, "rows": all_rows}, f, indent=2)
        print("\n  wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
