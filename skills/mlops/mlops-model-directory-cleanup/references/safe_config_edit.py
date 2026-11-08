#!/usr/bin/env python3
"""Safe, comment-preserving editor for llama-swap config.yaml.

WHY THIS EXISTS
---------------
config.yaml on these boxes carries 50-95 lines of hand-written measured research
(throughput tables, MTP acceptance rates, rejected-experiment notes). A
yaml.safe_load() -> yaml.safe_dump() round-trip silently deletes every comment.
The prose IS the record of why the flags are what they are, and it has already
saved work: the Studio recommends `--spec-type draft-mtp,ngram-simple
--spec-draft-n-max 1`, while the MBP header records that the SAME recipe measured
-70%, -36% and -14% there. Never port flags between hosts without measuring.

THE CONTRACT
------------
1. Read raw text into a buffer. All edits are text surgery on that buffer.
2. Parse the buffer with yaml.safe_load() ONLY to read/validate - never to dump.
3. Every edit asserts its anchor text is present VERBATIM and aborts if not.
4. Validate the edited buffer: parses, target keys exist, counts are as expected,
   and every NON-TARGET block is byte-identical to the original.
5. Only then write. Copy to a dated .bak first.

Members-list styles differ per box and MUST be detected, never assumed:
  Studio: block style        members:
                              - ms-model
  MBP:    flow style         members: [mb-model, mb-model]

Usage: import and call add_model(P, mid, name, desc, cmd, group="ondemand", ttl=900)
"""
import os
import re
import shutil
import sys

import yaml


def _abort(msg):
    print("ABORT:", msg)
    sys.exit(1)


def _load(path):
    with open(path) as f:
        raw = f.read()
    try:
        parsed = yaml.safe_load(raw)
    except Exception as exc:  # noqa: BLE001
        _abort(f"existing config does not parse: {exc}")
    if parsed is None:
        _abort("existing config parsed as None")
    return raw, parsed


def _member_span(body):
    """Locate the members list inside a group body. Returns
    ('flow', start, end, inner) or ('block', idx, None, None).

    The flow regex must match the FIRST ']' because group(1) EXCLUDES the
    closing bracket - so body[end:] already starts with ']'. Appending your own
    ']' produces ']]' and a parse error.
    """
    flow = re.search(r"(?s)members:\s*\[(.*?)\]", body)
    if flow:
        return "flow", flow.start(1), flow.end(1), flow.group(1)
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == "members:":
            return "block", i, None, lines
    _abort("no members: list found in group body")


def _append_member(body, new_ids):
    style, a, b, extra = _member_span(body)
    if style == "flow":
        inner = extra.rstrip()
        sep = "" if inner.endswith(",") else ", "
        return (body[:a] + inner + sep + ", ".join(new_ids) + body[b:])
    lines = extra
    i = a
    j = i + 1
    while j < len(lines) and lines[j].startswith("    - "):
        j += 1
    for mid in reversed(new_ids):          # reversed: each insert lands at j
        lines.insert(j, f"    - {mid}")
    return "\n".join(lines)


def _assert_untouched(old, new, skip_models=(), groups_changed=()):
    """Every model block and every untouched group must be byte-identical."""
    for mid, block in old["models"].items():
        if mid in skip_models:
            continue
        if new["models"].get(mid) != block:
            _abort(f"pre-existing model {mid} was MUTATED")
    for gid, grp in old["groups"].items():
        if gid in groups_changed:
            before = [m for m in grp["members"] if m not in groups_changed or True]
            after = new["groups"][gid]["members"]
            if after[: len(grp["members"])] != grp["members"]:
                _abort(f"group {gid}: existing member order changed")
            for key in ("swap", "exclusive", "persistent"):
                if key in grp and new["groups"][gid].get(key) != grp[key]:
                    _abort(f"group {gid}: {key} changed")
            continue
        if new["groups"].get(gid) != grp:
            _abort(f"group {gid} was MUTATED")
    for key in old:
        if key not in ("models", "groups") and new.get(key) != old[key]:
            _abort(f"top-level key {key} was MUTATED")


def add_model(path, mid, name, description, cmd, group="ondemand", ttl=900,
              date="20261002"):
    """Add a model block and register it in `group`. Idempotent-ish: aborts if
    the id already exists so a partial prior write is never doubled up."""
    raw, old = _load(path)

    # Guard against a REAL key, not prose. A description may legitimately contain
    # the model id as text; matching bare text false-positives on that.
    if re.search(r"(?m)^\s{2}" + re.escape(mid) + r"\b", raw):
        _abort(f"{mid} already present as a key - prior write? inspect manually")

    model_path = None
    m = re.search(r"--model\s+(\S+)", cmd)
    if m:
        model_path = m.group(1)
        if not os.path.exists(model_path):
            _abort(f"model path does not exist: {model_path}")
    if "--mmproj" in cmd:
        proj = re.search(r"--mmproj\s+(\S+)", cmd).group(1)
        if not os.path.exists(proj):
            _abort(f"mmproj path does not exist: {proj}")

    block = (
        f"  {mid}:\n"
        f'    name: "{name}"\n'
        f"    description: >-\n      {description}\n"
        f"    cmd: |-\n"
        + "".join("      " + line + "\n" for line in cmd.rstrip().split("\n"))
        + f"    ttl: {ttl}\n\n"
    )

    anchor = re.search(r"(?m)^groups:", raw)
    if not anchor:
        _abort("no top-level 'groups:' key")
    new_raw = raw[: anchor.start()].rstrip("\n") + "\n\n" + block + raw[anchor.start():]

    gm = re.search(r"(?ms)^  " + re.escape(group) + r":\n(.*?)(?=^  [a-z-]+:\n|\Z)", new_raw)
    if not gm:
        _abort(f"group {group} not found")
    new_raw = (new_raw[: gm.start(1)]
               + _append_member(gm.group(1), [mid])
               + new_raw[gm.end(1):])

    try:
        new = yaml.safe_load(new_raw)
    except Exception as exc:  # noqa: BLE001
        _abort(f"edited buffer does not parse: {exc}")
    if new is None:
        _abort("edited buffer parsed as None")

    if mid not in new["models"]:
        _abort(f"{mid} missing from models after edit")
    if new["groups"][group]["members"][-1] != mid:
        _abort(f"{mid} is not last in {group} members")
    if len(new["models"]) != len(old["models"]) + 1:
        _abort(f"model count {len(new['models'])} != {len(old['models']) + 1}")
    if len(new["groups"][group]["members"]) != len(old["groups"][group]["members"]) + 1:
        _abort("member count wrong")
    if new["models"][mid]["ttl"] != ttl:
        _abort("ttl not set")
    _assert_untouched(old, new, skip_models=(mid,), groups_changed=(group,))

    shutil.copy2(path, f"{path}.bak-{date}")
    with open(path, "w") as f:
        f.write(new_raw)
    print(f"WROTE {path}")
    print(f"  +{mid} -> group {group} (ttl {ttl})")
    print("  all pre-existing models byte-identical: VERIFIED")


def audit(path):
    """Read-only report: orphans, missing paths, group membership."""
    _, c = _load(path)
    member_of = {}
    for gid, grp in c.get("groups", {}).items():
        for mid in grp.get("members") or []:
            member_of.setdefault(mid, []).append(gid)
    missing, orphans = [], []
    for mid, blk in c["models"].items():
        if mid not in member_of:
            orphans.append(mid)
        for flag in ("--model", "--mmproj"):
            for pa in re.findall(flag + r"\s+(\S+)", blk.get("cmd", "")):
                if not os.path.exists(pa):
                    missing.append((mid, pa))
    print(f"{path}: {len(c['models'])} models, {len(c.get('groups', {}))} groups")
    print(f"  orphaned (in models:, in no group): {orphans or 'none'}")
    print(f"  missing paths: {len(missing)}")
    for mid, pa in missing:
        print(f"    {mid}: {pa}")
    return orphans, missing


if __name__ == "__main__":
    for target in sys.argv[1:]:
        audit(target)