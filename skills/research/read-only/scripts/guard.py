#!/usr/bin/env python3
"""Fingerprint a directory tree before a read-only investigation, and diff it after.

Two modes:

    guard.py snapshot <path> --out <file>   record the state of <path>
    guard.py check    <path> --out <file>   compare <path> against that record

`check` exits 0 when nothing changed, 1 when something did, 2 on a usage or
setup error. Every file under 2 MiB is hashed with SHA-256, so a same-second,
same-size edit is still caught; larger files are compared on size and mtime.

Directories that cannot be read are reported as SKIPPED and are a coverage gap,
not a pass. Stdlib only, portable.
"""

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

HASH_LIMIT = 2 * 1024 * 1024  # files at or above this are compared by size+mtime

# VCS internals churn on their own — `git status` rewrites .git/index's stat
# cache every run — so they would false-positive on a clean tree. Version-control
# state is captured semantically by git_fingerprint() instead.
EXCLUDE_DIRS = {".git", ".hg", ".svn", "__pycache__", ".venv", "node_modules",
                ".mypy_cache", ".pytest_cache", ".ruff_cache"}


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(root: Path):
    """Yield (relpath, record) for every file, plus skipped paths.

    `onerror` is required: with the default None, os.walk silently swallows
    permission errors and an unreadable directory looks exactly like an empty one.
    """
    records = {}
    skipped = []

    def onerror(exc):
        skipped.append(f"{getattr(exc, 'filename', '?')} ({getattr(exc, 'strerror', exc)})")

    for dirpath, dirnames, filenames in os.walk(root, onerror=onerror, followlinks=False):
        here = Path(dirpath)
        dirnames[:] = [d for d in sorted(dirnames)
                        if not Path(here, d).is_symlink() and d not in EXCLUDE_DIRS]
        for name in sorted(filenames):
            full = here / name
            if full.is_symlink():
                try:
                    records[str(full.relative_to(root))] = {
                        "kind": "symlink",
                        "target": os.readlink(full),
                    }
                except OSError as exc:
                    skipped.append(f"{full} ({exc.strerror})")
                continue
            try:
                st = full.lstat()
            except OSError as exc:
                skipped.append(f"{full} ({exc.strerror})")
                continue
            rec = {
                "kind": "file",
                "size": st.st_size,
                "mtime_ns": st.st_mtime_ns,
                "mode": stat.S_IMODE(st.st_mode),
            }
            if st.st_size < HASH_LIMIT:
                try:
                    rec["sha256"] = hash_file(full)
                except OSError as exc:
                    skipped.append(f"{full} ({exc.strerror})")
                    continue
            records[str(full.relative_to(root))] = rec
    return records, skipped


def git_fingerprint(root: Path):
    """HEAD sha plus a hash of `git status --porcelain`, when root is in a repo."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=30,
    )
    return {
        "head": head.stdout.strip() if head.returncode == 0 else None,
        "status_sha256": hashlib.sha256(out.stdout.encode()).hexdigest(),
        "status_lines": len([l for l in out.stdout.splitlines() if l.strip()]),
    }


def snapshot(root: Path, out: Path):
    started = time.time()
    records, skipped = walk(root)
    payload = {
        "root": str(root.resolve()),
        "taken_at": time.time(),
        "elapsed_s": round(time.time() - started, 2),
        "file_count": len(records),
        "skipped": skipped,
        "git": git_fingerprint(root),
        "files": records,
    }
    out.write_text(json.dumps(payload), encoding="utf-8")
    print(f"snapshot: {len(records)} files under {root} in {payload['elapsed_s']}s -> {out}")
    if skipped:
        print(f"SKIPPED {len(skipped)} unreadable path(s) — coverage gap, not a pass:")
        for item in skipped[:20]:
            print(f"  - {item}")
        if len(skipped) > 20:
            print(f"  ... and {len(skipped) - 20} more")


def check(root: Path, out: Path):
    if not out.exists():
        print(f"ERROR: no snapshot at {out}", file=sys.stderr)
        return 2
    before = json.loads(out.read_text(encoding="utf-8"))
    records, skipped = walk(root)
    old = before.get("files", {})

    created = sorted(set(records) - set(old))
    deleted = sorted(set(old) - set(records))
    modified = []
    for rel in sorted(set(records) & set(old)):
        a, b = old[rel], records[rel]
        if a.get("kind") != b.get("kind") or a != b:
            why = []
            if a.get("kind") != b.get("kind"):
                why.append("type changed")
            elif a.get("sha256") and a.get("sha256") != b.get("sha256"):
                why.append("content changed")
            elif a.get("target") != b.get("target"):
                why.append("symlink target changed")
            elif a.get("size") != b.get("size"):
                why.append(f"size {a.get('size')} -> {b.get('size')}")
            elif a.get("mtime_ns") != b.get("mtime_ns"):
                why.append("mtime changed")
            elif a.get("mode") != b.get("mode"):
                why.append(f"mode {a.get('mode')} -> {b.get('mode')}")
            else:
                why.append("metadata changed")
            modified.append((rel, "; ".join(why)))

    git_now = git_fingerprint(root)
    git_before = before.get("git")
    git_note = None
    if git_before and git_now:
        if git_before.get("head") != git_now.get("head"):
            git_note = f"HEAD {git_before.get('head')} -> {git_now.get('head')}"
        elif git_before.get("status_sha256") != git_now.get("status_sha256"):
            git_note = (
                f"git status changed ({git_before.get('status_lines')} -> "
                f"{git_now.get('status_lines')} lines)"
            )

    total = len(created) + len(deleted) + len(modified) + (1 if git_note else 0)
    if total == 0:
        print(f"READ-ONLY HELD: {len(records)} files under {root}, nothing changed")
        if skipped:
            print(f"NOTE {len(skipped)} path(s) unreadable during check — partial coverage")
        return 0

    print(f"VIOLATION: {total} change(s) under {root}")
    for rel in created:
        print(f"  created  {rel}")
    for rel in deleted:
        print(f"  deleted  {rel}")
    for rel, why in modified:
        print(f"  modified {rel}  ({why})")
    if git_note:
        print(f"  git      {git_note}")
    if skipped:
        print(f"  NOTE     {len(skipped)} path(s) unreadable during check — partial coverage")
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["snapshot", "check"])
    ap.add_argument("path", help="root of the tree to fingerprint")
    ap.add_argument("--out", required=True, help="snapshot file to write or read")
    args = ap.parse_args()

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    return snapshot(root, out) if args.mode == "snapshot" else check(root, out)


if __name__ == "__main__":
    sys.exit(main())
