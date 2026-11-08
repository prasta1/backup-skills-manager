#!/usr/bin/env python3
"""Pairwise head-to-head between two llama-swap models on Hermes-shaped tasks.

Answers "should A replace B for this job": accuracy + generated-token cost +
latency, with ground truth DERIVED FROM LIVE ARTIFACTS rather than hand-written.
Complements scripts/benchmark.py, which answers the fleet-ranking question.

Read references/pairwise-head-to-head-protocol.md before changing a grader.

Usage:
    python3 head_to_head.py --models ms-lfm3-1.7b ms-qwen3.5-4b-mtp
    python3 head_to_head.py --models A B --maxtok 3000 --out /tmp/h2h.json

BEFORE RUNNING: diff the two `cmd:` lines in the llama-swap config. Every spec
flag, reasoning flag, mmproj and ctx size must match on both arms. An uncapped
arm against a capped one is not a comparison (see the protocol reference).
"""
import argparse, json, re, statistics, sys, time, urllib.request
from pathlib import Path

import yaml

HOME = Path.home()
DEF_LSS = HOME / ".hermes/llama-swap/config.yaml"
DEF_HC = HOME / ".hermes/config.yaml"
DEF_HAY = [
    HOME / ".hermes/logs/llama-server.log",
    HOME / ".hermes/skills/hermes/hermes-infrastructure/references/operations-notes.md",
]
HAY_BYTES = 90000

TOOLS = [
    {"type": "function", "function": {"name": "search_files", "description": "Search file contents or find files by name inside a directory tree.",
        "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}, "target": {"type": "string", "enum": ["content", "files"]}, "file_glob": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "patch", "description": "Targeted find-and-replace edit inside an existing file.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"]}}},
    {"type": "function", "function": {"name": "terminal", "description": "Execute a shell command on this machine and return its output.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "web_search", "description": "Search the public web for current information.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file with line numbers and pagination.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer"}, "limit": {"type": "integer"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "cronjob_manage", "description": "Create, list, enable, disable or delete scheduled Hermes jobs.",
        "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["create", "list", "enable", "disable", "delete"]}, "schedule": {"type": "string"}, "prompt": {"type": "string"}}, "required": ["action"]}}},
]

TOOL_TASKS = [
    ("tool-search", "Find every file under my skills directory that mentions LLAMA_SWAP_KEY.", "search_files", "pattern"),
    ("tool-patch", "Change the ttl on the ms-lfm3-1.7b entry from 900 to 1800.", "patch", "path"),
    ("tool-disk", "How much free space is on the root volume right now?", "terminal", "command"),
    ("tool-news", "What is the newest llama.cpp release tag?", "web_search", "query"),
    ("tool-read", "Show me the first 50 lines of ~/.hermes/config.yaml.", "read_file", "path"),
    ("tool-cron", "Set up a job that runs every morning at 7am.", "cronjob_manage", "action"),
]

IF_TASKS = [
    ("if-reverse", "Reply with exactly these five numbers in reverse order, space separated, and nothing else: 1 2 3 4 5", "exact", "5 4 3 2 1"),
    ("if-prime", "Answer with only the lowercase word yes or no, nothing else: is 17 a prime number?", "exact", "yes"),
    ("if-words", "Write exactly 8 words about Vermont in October. No more and no fewer.", "wordcount", 8),
    ("if-json", 'Reply with only a JSON object with exactly two keys: "ok" set to true and "n" set to 7. No other text.', "json", {"ok": True, "n": 7}),
]


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def build_args():
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs=2, required=True)
    p.add_argument("--endpoint", default="http://127.0.0.1:9292")
    p.add_argument("--config", default=str(DEF_LSS))
    p.add_argument("--hermes-config", default=str(DEF_HC))
    p.add_argument("--haystack", nargs="*", default=[str(x) for x in DEF_HAY])
    p.add_argument("--maxtok", type=int, default=1500,
                   help="give BOTH arms the same headroom; thinking models need 200+ before content appears")
    p.add_argument("--out", default=None)
    return p.parse_args()


def build_tasks(a):
    cfg = yaml.safe_load(Path(a.config).read_text())
    hc = yaml.safe_load(Path(a.hermes_config).read_text())
    cfg_text = Path(a.config).read_text()

    # keep the needle distinctive or the grader grades nothing
    others = [v.get("ttl") for k, v in cfg["models"].items() if k != "sushi"]
    assert cfg["models"]["sushi"]["ttl"] not in others, "ttl needle is not distinctive"

    extract = [
        ("ext-ttl", cfg_text, "In the YAML document above, what is the `ttl` value for the model whose key is `sushi`? Reply with the number only.",
         "number", str(cfg["models"]["sushi"]["ttl"])),
        ("ext-timeout", cfg_text, "In the YAML document above, what is the value of the top-level `healthCheckTimeout` key? Reply with the number only.",
         "number", str(cfg["healthCheckTimeout"])),
        ("ext-count", cfg_text, "How many model keys are defined under the top-level `models` key in the YAML document above? Reply with the number only.",
         "number", str(len(cfg["models"]))),
        ("ext-vision", Path(a.hermes_config).read_text(), "In the YAML document above, what model is configured under `auxiliary` -> `vision` -> `model`? Reply with the model id only.",
         "extract", [hc["auxiliary"]["vision"]["model"]]),
        ("ext-embed", cfg_text, "In the YAML document above, list the members of the `embeddings` group. Reply with the model keys only, comma separated.",
         "extract", list(cfg["groups"]["embeddings"]["members"])),
    ]

    pieces, missing = [], []
    for path in a.haystack:
        p = Path(path)
        if p.exists():
            pieces.append(p.read_text(errors="replace")[-HAY_BYTES:])
        else:
            missing.append(str(p))
    if missing:
        print(f"  WARN haystack file(s) absent, skipped: {missing}", file=sys.stderr)
    hay = "\n\n".join(pieces)

    needles = [
        ("lc-macmon", "what TCP port does macmon expose its metrics on", "9199"),
        ("lc-nodeexp", "what TCP port does node_exporter listen on", "9100"),
        ("lc-blackbox", "what TCP port do the blackbox HTTP probes use", "9115"),
        ("lc-gateway", "what port does the gateway API server listen on", "8642"),
    ]
    longctx = []
    for tid, q, want in needles:
        if not hay or want not in hay:
            print(f"  WARN needle {tid} ({want}) not in haystack, item skipped", file=sys.stderr)
            continue
        longctx.append((tid, hay + f"\n\nAccording to the documents above, {q}? Reply with the number only.", "number", want))
    return extract, longctx


def post(endpoint, model, messages, tools=None, maxtok=1500):
    body = {"model": model, "temperature": 0, "max_tokens": maxtok, "messages": messages}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(endpoint + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=900))
    dt = time.time() - t
    m = d["choices"][0]["message"]
    u = d.get("usage") or {}
    return {"content": m.get("content") or "", "reasoning": m.get("reasoning_content") or "",
            "tool_calls": m.get("tool_calls") or [], "finish": d["choices"][0].get("finish_reason"),
            "tokens": u.get("completion_tokens") or 0, "wall": dt}


def grade(kind, r, spec):
    c = norm(r["content"])
    if kind == "tool":
        want_tool, want_arg = spec
        if not r["tool_calls"]:
            return False, "no tool call", ""
        fn = r["tool_calls"][0]["function"]
        if fn.get("name") != want_tool:
            return False, f"called {fn.get('name')}", ""
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except Exception:
            return False, "args not JSON", ""
        if not str(args.get(want_arg, "")).strip():
            return False, f"missing arg {want_arg}", ""
        return True, "ok", ""
    if kind == "number":
        # a short answer with exactly one integer; a long reply is rambling, not a hit
        if not c:
            return False, "empty", "exhausted"
        if len(c) > 80:
            return False, f"rambling ({len(c)} chars)", "rambling"
        nums = re.findall(r"-?\d+", c)
        if len(nums) != 1:
            return False, f"{len(nums)} integers", ""
        return nums[0] == str(spec), f"got {nums[0]}", ""
    if kind == "extract":
        if not c:
            return False, "empty", "exhausted"
        miss = [e for e in spec if norm(e) not in c]
        return (not miss), (f"missing {miss[:2]}" if miss else "ok"), ""
    if kind == "exact":
        return c == norm(spec), f"got {c[:40]!r}", ("exhausted" if not c else "")
    if kind == "wordcount":
        if not c:
            return False, "empty", "exhausted"
        n = len(c.split())
        return n == spec, f"{n} words", ""
    if kind == "json":
        if not c:
            return False, "empty", "exhausted"
        try:
            o = json.loads(re.search(r"\{.*\}", r["content"], re.S).group(0))
        except Exception:
            return False, "no JSON", ""
        ok = o.get("ok") is spec["ok"] and o.get("n") == spec["n"] and len(o) == 2
        return ok, f"keys {sorted(o)}", ""
    return False, "unknown grader", ""


def main():
    a = build_args()
    extract, longctx = build_tasks(a)
    results = {}
    for model in a.models:
        print(f"\n===== {model} =====", flush=True)
        rows = []
        try:
            post(a.endpoint, model, [{"role": "user", "content": "Reply with exactly: ok"}], maxtok=300)
        except Exception as e:
            print(f"  WARMUP FAILED: {e}", file=sys.stderr, flush=True)
            results[model] = rows
            continue
        suite = ([("tool", t[0], t[1], "tool", (t[2], t[3]), TOOLS) for t in TOOL_TASKS]
                 + [("extract", t[0], t[1] + "\n\n" + t[2], t[3], t[4], None) for t in extract]
                 + [("longctx", t[0], t[1], t[2], t[3], None) for t in longctx]
                 + [("instr", t[0], t[1], t[2], t[3], None) for t in IF_TASKS])
        for cat, tid, prompt, kind, spec, tools in suite:
            try:
                r = post(a.endpoint, model, [{"role": "user", "content": prompt}], tools=tools, maxtok=a.maxtok)
            except Exception as e:
                print(f"  ERROR {tid:14s} {e}", file=sys.stderr, flush=True)
                continue
            ok, why, cls = grade(kind, r, spec)
            rows.append({"id": tid, "cat": cat, "ok": ok, "why": why, "class": cls,
                         "tokens": r["tokens"], "wall": r["wall"], "finish": r["finish"]})
            flag = "PASS" if ok else "FAIL"
            extra = f"  [{cls}]" if cls else ""
            print(f"  {flag} {tid:14s} {r['tokens']:4d} tok {r['wall']:5.1f}s  {why}{extra}", flush=True)
        results[model] = rows

    if a.out:
        Path(a.out).write_text(json.dumps(results, indent=2))

    print("\n===== SUMMARY =====")
    cats = ["tool", "extract", "longctx", "instr"]
    print(f"{'category':10s}" + "".join(f"{m:>22s}" for m in a.models))
    for cat in cats:
        line = f"{cat:10s}"
        for m in a.models:
            rs = [r for r in results.get(m, []) if r["cat"] == cat]
            line += f"{(sum(r['ok'] for r in rs))}/{len(rs):<20d}"
        print(line)
    for m in a.models:
        rs = results.get(m, [])
        if not rs:
            continue
        print(f"\n{m}: {sum(r['ok'] for r in rs)}/{len(rs)} correct | "
              f"{sum(r['tokens'] for r in rs)} tokens | {sum(r['wall'] for r in rs):.1f}s wall")
        print(f"   median {statistics.median([r['tokens'] for r in rs]):.0f} tok / "
              f"{statistics.median([r['wall'] for r in rs]):.2f}s")
    print("\nREMINDER: re-run every FAIL at 2-3x --maxtok before calling it a capability gap.")
    print("Report failure MODE, not just the score (see the protocol reference).")


if __name__ == "__main__":
    main()
