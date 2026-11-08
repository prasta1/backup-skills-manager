#!/usr/bin/env python3
"""
gallery.py — Organize ComfyUI outputs into the gallery with names and manifests.

The ComfyUI server writes every SaveImage into its own output directory —
the single CLI install at <home>/ComfyUI/output. (Comfy Desktop's
<home>/ComfyUI-Shared/output spool was retired with Desktop 2026-10-23.)
That dir is a staging spool: files pile up with meaningless names
(qwen21_00037_.png) and no record of what produced them. ``gallery.py sweep``
reads the embedded ComfyUI metadata (the prompt + workflow JSON in PNG tEXt
chunks), then moves each file into the gallery grouped by MONTH:

    <gallery>/<YYYY-MM>/<slug>_<seed>_<NN>.<ext>

All of a month's generations assemble flat in that one folder, with ONE
manifest.json per month indexing every run and file. Spool copies whose
sha256 already exists in the gallery (e.g. a script run that also downloaded
them) are removed from the spool by default — the gallery is the archive,
the spool is staging.

Usage:
    gallery.py sweep                 # sweep the known local server spools
    gallery.py sweep --dirs /path/a /path/b
    gallery.py sweep --dry-run       # show what would move/delete; change nothing
    gallery.py list                  # gallery contents, newest first
    gallery.py list --match cat --seed 42 --json

Layout overrides: $COMFY_GALLERY (gallery root), $COMFY_SPOOL_DIRS (colon
list of spool dirs to sweep by default).

Stdlib-only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import sys
import zlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    GALLERY_ROOT, PROMPT_KEYS,
    SERVER_OUTPUT_DIRS, embed_human_params, emit_json, finalize_downloads,
    gallery_month_dir, iter_nodes, media_type_from_filename, slugify,
)

# File types SaveImage and friends write. Everything else in a spool
# (logs, .json sidecars, the Desktop placeholder file) stays put.
MEDIA_EXTS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".mp4", ".webm", ".mov", ".avi", ".mkv",
    ".wav", ".mp3", ".flac", ".ogg", ".m4a",
    ".glb", ".obj", ".ply", ".gltf",
}

PNG_SIG = b"\x89PNG\r\n\x1a\n"

DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Param fields worth carrying into the sweep manifest when found in metadata.
_PARAM_INTS = ("seed", "noise_seed", "steps", "cfg", "denoise", "width", "height")
_PARAM_STRS = ("sampler_name", "scheduler", "sampler")


# =============================================================================
# PNG metadata (ComfyUI embeds prompt + workflow JSON in tEXt/iTXt chunks)
# =============================================================================

def read_png_metadata(path: Path) -> dict[str, str]:
    """Return {keyword: text} for the tEXt/iTXt chunks of a PNG. Empty on error."""
    try:
        data = path.read_bytes()
    except OSError:
        return {}
    if data[:8] != PNG_SIG:
        return {}
    out: dict[str, str] = {}
    pos = 8
    n = len(data)
    while pos + 8 <= n:
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"tEXt":
            key, _, val = chunk.partition(b"\x00")
            try:
                out[key.decode("latin-1")] = val.decode("latin-1")
            except Exception:
                pass
        elif ctype == b"iTXt":
            # keyword\0 comp_flag comp_method lang\0 translated\0 text
            key, rest = chunk.split(b"\x00", 1)
            if len(rest) < 2:
                continue
            flag, method = rest[0], rest[1]
            rest2 = rest[2:]
            lang_end = rest2.find(b"\x00")
            if lang_end < 0:
                continue
            trans_end = rest2.find(b"\x00", lang_end + 1)
            if trans_end < 0:
                continue
            text = rest2[trans_end + 1:]
            try:
                if flag == 1 and method == 0:
                    text = zlib.decompress(text)
                out[key.decode("latin-1")] = text.decode("utf-8", "replace")
            except Exception:
                pass
        if pos >= n:
            break
    return out


def extract_run_info(workflow: dict) -> tuple[str, dict]:
    """Pull (prompt, params) out of the API-format workflow embedded in a PNG."""
    prompt = ""
    params: dict = {}
    for _, node in iter_nodes(workflow):
        inputs = node.get("inputs", {}) or {}
        for k, v in inputs.items():
            if k in PROMPT_KEYS and isinstance(v, str) and len(v) > len(prompt):
                prompt = v
        for k in _PARAM_INTS:
            v = inputs.get(k)
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)) and k not in params:
                params[k] = v
        for k in _PARAM_STRS:
            v = inputs.get(k)
            if isinstance(v, str) and k not in params:
                params[k] = v
    return prompt.strip(), params


def cache_key_from_png(path: Path) -> tuple[str, int | None, dict]:
    """(slug, seed, params) for a spool file, from embedded metadata when present."""
    meta = read_png_metadata(path) if path.suffix.lower() == ".png" else {}
    wf_raw = meta.get("prompt", "")
    if wf_raw:
        try:
            wf = json.loads(wf_raw)
        except json.JSONDecodeError:
            wf = None
        if isinstance(wf, dict):
            prompt, params = extract_run_info(wf)
            seed = params.get("seed") or params.get("noise_seed")
            seed = int(seed) if isinstance(seed, (int, float)) else None
            slug = slugify(prompt) if prompt else slugify(path.stem)
            return slug, seed, params
    return slugify(path.stem), None, {}


# =============================================================================
# Archive index
# =============================================================================

def build_archive_index(gallery: Path) -> dict[str, str]:
    """sha256 → manifest path for every file already recorded in the gallery."""
    index: dict[str, str] = {}
    if not gallery.exists():
        return index
    for mf in gallery.rglob("manifest.json"):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        for f in data.get("files", []) or []:
            h = f.get("sha256")
            if h:
                index.setdefault(h, str(mf))
    return index


# =============================================================================
# Sweep
# =============================================================================

def preview_month_dir(gallery: Path, month: str) -> Path:
    """Dry-run twin of gallery_month_dir: computes the month path, creates nothing."""
    return gallery / month


def sweep(spool_dirs: list[Path], gallery: Path, *, dry_run: bool,
          delete_dupes: bool) -> int:
    gallery = gallery.expanduser().resolve()
    archive = build_archive_index(gallery)
    now = datetime.now()
    month = now.strftime("%Y-%m")

    print(f"gallery: {gallery}")
    print(f"archive index: {len(archive)} file(s) already in the gallery\n")

    moved = skipped = dupes = 0
    for spool in spool_dirs:
        spool = spool.expanduser().resolve()
        if not spool.is_dir():
            print(f"- spool missing, skipping: {spool}")
            continue
        if spool == gallery or gallery in spool.parents:
            print(f"- refusing to sweep {spool}: it is inside the gallery (or is the gallery)")
            continue
        print(f"== sweeping {spool}")

        groups: dict[str, Path] = {}
        group_params: dict[str, dict] = {}
        counters: dict[str, int] = {}
        files_in_group: dict[str, list[dict]] = {}
        used_names: set[str] = set()

        for p in sorted(spool.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in MEDIA_EXTS:
                continue
            slug, seed, params = cache_key_from_png(p)
            size = p.stat().st_size
            if size == 0:
                continue

            n = counters.get(slug, 0) + 1
            counters[slug] = n

            if slug not in groups:
                if dry_run:
                    groups[slug] = preview_month_dir(gallery, month)
                else:
                    groups[slug] = gallery_month_dir(gallery, now=now)
                group_params[slug] = params
                files_in_group[slug] = []
            month_dir = groups[slug]

            base = f"{slug}" + (f"_{seed}" if seed is not None else "")
            candidate = month_dir / f"{base}_{n:02d}{p.suffix}"
            i = n
            while str(candidate.relative_to(gallery)) in used_names or candidate.exists():
                i += 1
                candidate = month_dir / f"{base}_{i:02d}{p.suffix}"
            used_names.add(str(candidate.relative_to(gallery)))
            target = candidate

            # Exact-byte duplicate of something already in the gallery → staging junk.
            h = hashlib.sha256()
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() in archive:
                dupes += 1
                if delete_dupes and not dry_run:
                    p.unlink()
                    print(f"  [delete] duplicate of archived file: {p.name}")
                elif dry_run:
                    print(f"  [would-delete] duplicate of archived file: {p.name}")
                else:
                    print(f"  [skip] duplicate already archived: {p.name}")
                continue

            src_rel = p.parent.relative_to(spool) if p.parent != spool else Path("")
            entry = {
                "file": str(target),
                "filename": p.name,
                "type": media_type_from_filename(p.name),
                "subfolder": str(src_rel),
                "seed": seed,  # may be None; finalize only records non-None
            }
            if dry_run:
                print(f"  [move] {p.relative_to(spool)} → {target.relative_to(gallery)}")
                moved += 1
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(target))
            if target.suffix.lower() == ".png":
                embed_human_params(target)
            entry["file"] = str(target)
            files_in_group[slug].append(entry)
            moved += 1

        if dry_run:
            continue

        for slug in groups:
            month_dir = groups[slug]
            entries = files_in_group[slug]
            if not entries:
                continue
            # A group is "one run" (uniform seed) if every file shares a seed;
            # a same-prompt batch of distinct seeds gets seed=null at the group
            # level, with each file's seed recorded in the files list.
            seeds = {e["seed"] for e in entries if e.get("seed") is not None}
            group_seed = seeds.pop() if len(seeds) == 1 else None
            finalize_downloads(
                entries, run_dir=month_dir, slug=slug, seed=group_seed,
                prompt_id="", workflow_ref="sweep", workflow_sha1="",
                host="", args=group_params.get(slug, {}), warnings=[],
                rename=False, source="sweep",
            )
            tag = f", seed={group_seed}" if group_seed is not None else ", mixed seeds (per file)"
            print(f"  merged {slug} into {month_dir}/manifest.json "
                  f"({len(entries)} file(s), slug={slug!r}{tag})")

    print(f"\n{moved} moved, {dupes} duplicates removed/skipped, {skipped} skipped")
    # Exit 0 even when nothing moved — a clean poll is success (scheduled runs
    # should only signal nonzero on real errors, not on "nothing to do").
    return 0


# =============================================================================
# Reorganize (legacy day-layout → month-layout migration)
# =============================================================================

def reorganize(gallery: Path, *, dry_run: bool) -> int:
    """Flatten the legacy per-day/per-run layout into month folders.

    Old layout (pre-2026-10-18): <gallery>/<YYYY-MM-DD>/<slug>_<HHMMSS>/
    (and batch runs nested one level deeper as run_NNNN_s<seed>/), each with
    its own manifest.json. New layout: <gallery>/<YYYY-MM>/ with all files
    flat and ONE merged manifest.json per month.

    Reads each legacy run manifest, moves its files into the month folder
    (collision-safe), and merges the run record into the month manifest.
    Files are already named <slug>_<seed>_<NN>, so they keep their names.
    Empty legacy dirs are pruned. Returns 0.
    """
    gallery = gallery.expanduser().resolve()
    if not gallery.exists():
        print(f"gallery not found: {gallery}")
        return 0
    day_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    moved = merged = pruned = 0
    for day_dir in sorted(gallery.iterdir()):
        if not day_dir.is_dir() or not day_re.match(day_dir.name):
            continue
        month = day_dir.name[:7]  # YYYY-MM
        month_dir = gallery / month
        if not dry_run:
            month_dir.mkdir(parents=True, exist_ok=True)
        for mf in sorted(day_dir.rglob("manifest.json")):
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                continue
            files = data.get("files")
            if not isinstance(files, list) or not files:
                continue
            slug = data.get("slug") or mf.parent.name
            seed = data.get("seed")
            params = data.get("params") or {}
            entries: list[dict] = []
            for f in files:
                if not isinstance(f, dict):
                    continue
                src = mf.parent / f.get("file", "")
                if not src.is_file():
                    continue
                # Collision-safe target name in the month folder.
                base = Path(f.get("file", "")).stem
                target = month_dir / (base + Path(f.get("file", "")).suffix)
                i = 2
                while target.exists() and target.resolve() != src.resolve():
                    target = month_dir / f"{base}_{i}{Path(f.get('file', '')).suffix}"
                    i += 1
                if dry_run:
                    print(f"  [move] {src.relative_to(gallery)} → {target.relative_to(gallery)}")
                else:
                    src.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(target))
                entries.append({
                    "file": str(target),
                    "filename": f.get("source") or src.name,
                    "type": f.get("type") or media_type_from_filename(src.name),
                    "subfolder": f.get("subfolder", ""),
                    "seed": f.get("seed", seed),
                })
                moved += 1
            if not entries:
                continue
            if not dry_run:
                finalize_downloads(
                    entries, run_dir=month_dir, slug=slug, seed=seed,
                    prompt_id=data.get("prompt_id") or "",
                    workflow_ref=data.get("workflow") or "legacy",
                    workflow_sha1=data.get("workflow_sha1") or "",
                    host=data.get("host") or "", args=params, warnings=[],
                    rename=False, source=data.get("source") or "legacy",
                )
                merged += 1
                # The run's record is now in the month manifest; drop the
                # legacy per-run manifest so its dir can be pruned.
                try:
                    mf.unlink()
                except OSError:
                    pass
        if not dry_run:
            # Prune now-empty legacy dirs (run dirs, then the day dir).
            for d in sorted(day_dir.rglob("*"), reverse=True):
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
                    pruned += 1
            if day_dir.is_dir() and not any(day_dir.iterdir()):
                day_dir.rmdir()
                pruned += 1
    print(f"\n{moved} file(s) moved, {merged} run(s) merged, {pruned} empty dir(s) pruned")
    return 0


# =============================================================================
# List
# =============================================================================

def list_gallery(gallery: Path, *, match: str | None = None,
                 seed: int | None = None, since: str | None = None,
                 json_out: bool = False) -> int:
    rows: list[dict] = []
    if gallery.exists():
        for mf in sorted(gallery.rglob("manifest.json"), reverse=True):
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                continue
            files = data.get("files")
            if not isinstance(files, list) or not files:
                continue  # batch-level manifest (indexes runs, has no files)
            # Find the <YYYY-MM> (new layout) or <YYYY-MM-DD> (legacy) ancestor.
            month = next((p.name for p in mf.parents
                          if re.fullmatch(r"\d{4}-\d{2}", p.name)), "")
            if not month:
                month = next((p.name for p in mf.parents if DAY_RE.match(p.name)), "")
            # New merged month manifest: slug/seed/params live per-run.
            runs_by_id = {r.get("run_id"): r for r in data.get("runs", []) or []
                          if isinstance(r, dict)}
            for f in files:
                if not isinstance(f, dict):
                    continue
                run = runs_by_id.get(f.get("run_id")) or {}
                row = {
                    "date": month,
                    "run": f.get("run_id") or run.get("run_id") or mf.parent.name,
                    "slug": f.get("slug") or data.get("slug"),
                    "seed": f.get("seed", data.get("seed")),
                    "file": f.get("file"),
                    "type": f.get("type"),
                    "size": f.get("size"),
                    "manifest": str(mf),
                }
                params = run.get("params") or data.get("params") or {}
                prompt = ""
                for k in PROMPT_KEYS:
                    v = params.get(k)
                    if isinstance(v, str) and v:
                        prompt = v
                        break
                row["prompt"] = prompt[:80]
                rows.append(row)

    if since:
        rows = [r for r in rows if r["date"] >= since]
    if seed is not None:
        rows = [r for r in rows if r["seed"] == seed]
    if match:
        m = match.lower()
        rows = [r for r in rows if (
            m in (r["slug"] or "").lower()
            or m in (r["file"] or "").lower()
            or m in (r["prompt"] or "").lower()
        )]

    rows.sort(key=lambda r: (r["date"], r["run"]), reverse=True)

    if json_out:
        emit_json({"total": len(rows), "entries": rows})
        return 0

    if not rows:
        print("gallery is empty (or no matches)")
        return 1
    print(f"{len(rows)} file(s)\n")
    print(f"{'date':<9} {'slug':<40} {'seed':<14} {'size':>8}  file")
    print("-" * 100)
    for r in rows:
        print(f"{r['date']:<9} {(r['slug'] or '')[:40]:<40} "
              f"{str(r['seed']):<14} {r['size'] or 0:>7.0f}  {r['file']}")
    return 0


# =============================================================================
# CLI
# =============================================================================

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Organize ComfyUI server outputs into the gallery.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("sweep", help="move spool files into the gallery")
    sp.add_argument("--dirs", nargs="*", default=None,
                    help=f"spool dirs to sweep (default: {', '.join(str(d) for d in SERVER_OUTPUT_DIRS)})")
    sp.add_argument("--gallery", default=None, help="gallery root (default: $COMFY_GALLERY or ~/Pictures/ComfyUI)")
    sp.add_argument("--dry-run", action="store_true", help="show what would happen; change nothing")
    sp.add_argument("--keep-dupes", action="store_true",
                    help="don't delete spool copies that are already in the gallery")

    rp = sub.add_parser("reorganize",
                        help="flatten legacy per-day/per-run layout into month folders")
    rp.add_argument("--gallery", default=None, help="gallery root (default: $COMFY_GALLERY or ~/Pictures/ComfyUI)")
    rp.add_argument("--dry-run", action="store_true", help="show what would move; change nothing")

    lp = sub.add_parser("list", help="list gallery contents")
    lp.add_argument("--gallery", default=None)
    lp.add_argument("--match", default=None, help="substring filter on slug/file/prompt")
    lp.add_argument("--seed", type=int, default=None)
    lp.add_argument("--since", default=None, help="only months >= YYYY-MM (legacy dates >= YYYY-MM-DD work too)")
    lp.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    gallery = Path(args.gallery).expanduser() if args.gallery else GALLERY_ROOT

    if args.cmd == "sweep":
        dirs = [Path(d).expanduser() for d in args.dirs] if args.dirs else list(SERVER_OUTPUT_DIRS)
        return sweep(dirs, gallery, dry_run=args.dry_run, delete_dupes=not args.keep_dupes)
    if args.cmd == "reorganize":
        return reorganize(gallery, dry_run=args.dry_run)
    return list_gallery(gallery, match=args.match, seed=args.seed,
                        since=args.since, json_out=args.json)


if __name__ == "__main__":
    sys.exit(main())