#!/usr/bin/env python3
"""
fleet_catalog.py — derive a queryable inventory of the llama-swap model fleet.

Reads every llama-swap config (studio + macbook, when the share is mounted),
measures every model on disk, resolves group membership and capability, folds
in the newest benchmark CSV that mentions each model, and emits catalog.json +
catalog.md.

Read-only with respect to the fleet. The catalog is disposable: delete it and
nothing is lost. That property is the whole point — it cannot drift, because
it is never edited by hand.

Usage:
    fleet_catalog.py                 # write catalog.json + catalog.md
    fleet_catalog.py --check         # validate only, write nothing, exit 1 on problems
    fleet_catalog.py --no-bench      # skip CSV merge
    fleet_catalog.py --strict        # treat warnings as failures
    fleet_catalog.py --no-mb         # skip the macbook config entirely
    fleet_catalog.py --open          # also open catalog.html in the default browser after writing
    fleet_catalog.py --out-dir DIR   # write somewhere other than OUT_DIR_DEFAULT

Artifacts land in OUT_DIR_DEFAULT — the iCloud Hermes infra folder — unless
--out-dir overrides it.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("error: pyyaml missing. pip3 install pyyaml")


# --------------------------------------------------------------------------
# Multi-host sources. The MacBook's config is only readable while its home
# share is mounted at /Volumes/prasta; its --model paths are written for
# /Users/prasta/... and must be translated before touching disk from here.
# --------------------------------------------------------------------------
def esc(v) -> str:
    """HTML-escape a value for safe embedding in generated pages."""
    if v is None:
        return ""
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


MB_CONFIG = Path("/Volumes/prasta/.hermes/llama-swap/config.yaml")
MB_PATH = ("/Users/prasta", "/Volumes/prasta")
HOSTS = ["studio", "macbook"]

# --------------------------------------------------------------------------
# Where the four artifacts land: the iCloud Hermes infra folder, so the
# catalog shows up on the MacBook and the iPhone on its own. One folder, two
# local paths — the MacBook sees it at /Users/prasta/Library/Mobile
# Documents/com~apple~CloudDocs/Hermes/infra/fleet-catalog. The path holds
# spaces and a literal tilde, so quote it in every shell command, and never
# re-hardcode it elsewhere: readers resolve catalog.json from here.
# --------------------------------------------------------------------------
OUT_DIR_DEFAULT = (
    "~/Library/Mobile Documents/com~apple~CloudDocs/Hermes/infra/fleet-catalog"
)

# --------------------------------------------------------------------------
# Tokenizer map. Verified 2026-09-28 with
# llama_benchy.corpus.LightweightTokenizer.from_pretrained().
# Keep in sync with the llama-benchy-quick-bench skill's references/tokenizers.md.
# "unresolved" means the canonical repo is gated (401) and no substitute has
# been load-tested — it does NOT mean gpt2 is acceptable.
# --------------------------------------------------------------------------
TOKENIZERS = {
    "ms-devstral-24b": ("mistralai/Devstral-Small-2-24B-Instruct-2512", "verified"),
    "ms-gemma-4-26b-moe": ("google/gemma-4-26B-A4B-it", "verified"),
    "ms-gemma-4-12b": ("google/gemma-4-12B-it", "verified"),
    "ms-gemma-4-e4b": ("google/gemma-4-E4B-it", "verified"),
    "ms-glm-4.6-vision": ("zai-org/GLM-4.6V-Flash", "verified"),
    "ms-kat-coder-v2.5": ("Kwaipilot/KAT-Coder-V2.5-Dev", "verified"),
    "ms-qwen3.6-35b-a3b": ("Qwen/Qwen3.6-35B-A3B", "verified"),
    "ms-qwen3-coder-30b": ("Qwen/Qwen3-Coder-30B-A3B-Instruct", "verified"),
    "ms-qwen3-vl-8b": ("Qwen/Qwen3-VL-8B-Instruct", "verified"),
    "ms-gpt-oss-20b": ("openai/gpt-oss-20b", "verified"),
    "ms-granite-4.2-3b": ("ibm-granite/granite-4.2-3b", "verified"),
    "ms-granite-4.2-8b": ("ibm-granite/granite-4.2-8b", "verified"),
    "ms-ministral-3-3b": ("mistralai/Ministral-3-3B-Instruct-2512", "verified"),
    "ms-qwen3.5-4b-mtp": ("Qwen/Qwen3.5-4B", "verified"),
    "ms-qwopus3.8-27b-flash": ("Qwen/Qwen3.8-27B", "substitute"),
    "ms-nuextract3": ("Qwen/Qwen3.5-4B", "substitute"),
    "ms-muse-glimmer-30b": (None, "unresolved"),
    # Embeddings: served, but no tokenizer needed and not chat-benchmarkable.
    "ms-bge-m3-1024": (None, "n/a-embeddings"),
    "ms-bge-reranker-v2-m3": (None, "n/a-embeddings"),
}

# Quantization tokens as they appear in GGUF filenames.
QUANT_RE = re.compile(
    r"(UD-Q\d+_[A-Z0-9_]+|MXFP\d|MXFP4|Q\d+_[A-Z0-9_]+|IQ\d+_[A-Z0-9_]+|F16|F32|BF16)",
    re.IGNORECASE,
)

# Params from a filename stem, e.g. "Qwen3-Coder-30B-A3B" -> total 30, active 3.
TOTAL_B_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)B(?![ \w])", re.IGNORECASE)
ACTIVE_B_RE = re.compile(r"[AE](\d+(?:\.\d+)?)B(?![ \w])", re.IGNORECASE)

# Description prose that states active params, e.g. "MoE 3.6B active".
DESC_ACTIVE_RE = re.compile(
    r"(?:MoE|A3B|active)[^.;]{0,24}?(\d+(?:\.\d+)?)\s*B\s*active", re.IGNORECASE
)
DESC_SIZE_RE = re.compile(r"\((\d+(?:\.\d+)?)\s*GB\)", re.IGNORECASE)

CAPABILITY_ORDER = ["embedding", "extraction", "code", "vision", "general"]

# Explicit overrides where the id alone is not enough. Deliberately short:
# anything derivable from the id is derived, so these stay auditable. The
# free-text description is NOT consulted — see infer_capabilities.
CAPABILITY_OVERRIDES = {
    "ms-nuextract3": "extraction",
}

# MoE shapes the filename does not state (no A#B/E#B token but genuinely MoE).
# Fallback ONLY. The GGUF header's expert_count is the authoritative source
# (see gguf_arch below) and is consulted first; this list exists for entries
# whose weights cannot be read - directory-backed engines and files absent on
# the host that is reading the config.
#
# Corrected 2026-11-01 against the headers: ms-qwen3.5-4b-mtp is DENSE (arch
# qwen35, with no *.expert_count field at all - "MTP" is a
# multi-token-prediction head, not an expert layout), while
# ms-kat-coder-v2.5 and ms-laguna-xs-2.1 are MoE (qwen35moe / laguna, 256
# experts each) and were missing from this list entirely.
ARCH_OVERRIDES = {
    "ms-gemma-4-e4b": "moe",
    "ms-gemma-4-26b-moe": "moe",
    "ms-gpt-oss-20b": "moe",
    "mb-gpt-oss-20b": "moe",
    "ms-qwen3.6-35b-a3b": "moe",
    "ms-kat-coder-v2.5": "moe",
    "ms-laguna-xs-2.1": "moe",
    "ms-qwopus3.8-27b-flash": "moe",
    "ms-muse-glimmer-30b": "moe",
    "sushi": "moe",
}


# GGUF metadata value types, per the format spec. UINT8 is 0 - never prepend a
# sentinel type: an off-by-one here shifts every constant and desyncs the whole
# KV walk, which surfaces as a MemoryError on a garbage read() length rather
# than as a clean parse error.
_GGUF_FIXED = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
_GGUF_SIGNED = {1, 3, 5, 11}
_GGUF_STR = 8
_GGUF_ARR = 9


def _gguf_skip(f, t: int) -> None:
    """Advance past one metadata value."""
    if t == _GGUF_STR:
        f.seek(int.from_bytes(f.read(8), "little"), 1)
    elif t == _GGUF_ARR:
        et = int.from_bytes(f.read(4), "little")
        n = int.from_bytes(f.read(8), "little")
        if et in _GGUF_FIXED:
            f.seek(_GGUF_FIXED[et] * n, 1)
        elif et == _GGUF_STR:
            for _ in range(n):
                f.seek(int.from_bytes(f.read(8), "little"), 1)
        else:
            for _ in range(n):
                _gguf_skip(f, et)
    elif t in _GGUF_FIXED:
        f.seek(_GGUF_FIXED[t], 1)
    else:
        raise ValueError(f"unknown gguf type {t}")


def gguf_arch(path: str | None) -> str | None:
    """Return 'moe' or 'dense' read from the GGUF header, else None.

    expert_count is a measurement; deriving the architecture from the model id
    is an inference. So this outranks every name heuristic and the caller
    applies it last. Only the metadata KV block at the head of the file is
    read, so it stays cheap on model-sized weights. Directory-backed engines
    (the sushi MLX pack) and unreadable files return None, and the caller
    falls back to the id/ARCH_OVERRIDES derivation.

    Deliberately stdlib-only: this runs under the weekly cron's
    /usr/bin/python3, which has pyyaml but no gguf-py or numpy. Reading raw
    bytes also sidesteps gguf-py's parts/data indexing, where
    int(parts[data[-1]]) raises TypeError on a multi-element array and a bare
    except turns that into a silent wrong answer.

    Order-independent: general.architecture and *.expert_count are both
    captured in a single pass, so a writer emitting them out of order is still
    classified correctly.
    """
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"GGUF":
                return None
            f.read(4)   # version
            f.read(8)   # tensor_count
            n_kv = int.from_bytes(f.read(8), "little")
            exp = None
            seen_arch = False
            for _ in range(n_kv):
                klen = int.from_bytes(f.read(8), "little")
                if not 0 < klen < 4096:
                    return None
                key = f.read(klen).decode("utf-8", "replace")
                t = int.from_bytes(f.read(4), "little")
                if key == "general.architecture" and t == _GGUF_STR:
                    slen = int.from_bytes(f.read(8), "little")
                    if not 0 < slen < 256:
                        return None
                    f.read(slen)
                    seen_arch = True
                elif key.endswith(".expert_count") and t in _GGUF_FIXED:
                    exp = int.from_bytes(
                        f.read(_GGUF_FIXED[t]), "little", signed=t in _GGUF_SIGNED
                    )
                else:
                    _gguf_skip(f, t)
            if exp is not None:
                return "moe" if exp > 0 else "dense"
            return "dense" if seen_arch else None
    except Exception:
        return None


def host_path(host: str, p: str | None) -> str | None:
    """Translate a config path into one resolvable from THIS machine."""
    if not p or host != "macbook":
        return p
    if p.startswith(MB_PATH[0]):
        return MB_PATH[1] + p[len(MB_PATH[0]):]
    return p


def parse_cmd(cmd: str) -> dict:
    """Pull the flags we care about out of a llama-server command line."""
    if not cmd:
        return {}
    # The config stores this as a folded/quoted multi-line string; shlex with
    # posix=True handles the single-quoted wrapper. ${PORT} etc are macros
    # that expand at llama-swap load time and are irrelevant here.
    try:
        toks = shlex.split(cmd, posix=True)
    except ValueError:
        toks = cmd.split()

    out: dict = {}
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in ("--model", "--mmproj", "--ctx-size", "--parallel", "--spec-type",
                 "--spec-draft-n-max", "-md", "--n-gpu-layers", "--batch-size"):
            if i + 1 < len(toks):
                out[t] = toks[i + 1]
                i += 2
                continue
        i += 1
    return out


def file_size_gb(p: str | None) -> float | None:
    """Measure a file OR a directory in GiB.

    Directory-backed engines (sushi's MLX pack, 65 GiB) used to report 0
    because os.path.getsize on a directory returns the directory entry size.
    A directory is summed recursively — the catalog reports measured bytes,
    never the advertised size.
    """
    if not p:
        return None
    try:
        if os.path.isdir(p):
            total = 0
            for root, _dirs, files in os.walk(p):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        continue
            return round(total / (1024 ** 3), 2)
        return round(os.path.getsize(p) / (1024 ** 3), 2)
    except OSError:
        return None


def infer_params(mid: str, stem: str, desc: str) -> tuple[float | None, float | None, str]:
    """Return (params_total_b, params_active_b, arch).

    Never guesses. If the total is not stated in the filename or the
    description, it stays None. A wrong number is worse than a missing one.
    ARCH_OVERRIDES must win over derivation: it is the audited truth where
    the filename is silent. This whole function is the FALLBACK path -
    gguf_arch() reads the header and the caller applies that value last.
    """
    arch = "dense"
    if mid in ARCH_OVERRIDES:
        arch = "moe"

    active = None
    m = ACTIVE_B_RE.search(stem)
    if m:
        active = float(m.group(1))
    if active is None:
        m = DESC_ACTIVE_RE.search(desc or "")
        if m:
            active = float(m.group(1))

    total = None
    if active is not None:
        # An "A3B"/"E4B" token is active-only; the leading number is the total.
        m = TOTAL_B_RE.search(stem)
        if m and float(m.group(1)) > active:
            total = float(m.group(1))
        arch = "moe"
    else:
        m = TOTAL_B_RE.search(stem)
        if m:
            total = float(m.group(1))
            # "27b" in the id alone doesn't prove MoE; only the A3B shape does.
            if re.search(r"[AE]\d+B", stem):
                arch = "moe"

    return total, active, arch


def infer_capabilities(model_id: str, has_mmproj: bool, group: str) -> list[str]:
    """Return every capability that applies, most specific first.

    Driven by the model id and group ONLY — never the free-text description.
    Descriptions contain incidental words that produce wrong answers: an
    earlier version matched "cod" anywhere in the prose and classified
    gemma-4-26b-moe as code, and matched "extraction" in gpt-oss-20b's
    "Hindsight memory extraction bakeoff" and called it an extractor.

    A model can legitimately be several things at once (devstral is a code
    model that also carries an mmproj), so this returns a list. Forcing one
    label loses information the fleet actually has.
    """
    if group == "embeddings" or re.search(r"bge-|nomic-embed", model_id):
        return ["embedding"]

    caps: list[str] = []
    if model_id in CAPABILITY_OVERRIDES:
        caps.append(CAPABILITY_OVERRIDES[model_id])

    low = model_id.lower()
    if re.search(r"coder|devstral|kat-coder", low):
        caps.append("code")
    if re.search(r"nuextract", low):
        caps.append("extraction")
    if has_mmproj:
        caps.append("vision")
    if not caps:
        caps.append("general")

    seen: set[str] = set()
    return [c for c in caps if not (c in seen or seen.add(c))]


def load_bench(results_dir: Path) -> dict:
    """Fold in the newest benchmark CSV that mentions each model.

    Per-model, not global-newest: a model skipped in the last run should still
    show its most recent numbers rather than nulling out.
    """
    out: dict = {}
    if not results_dir.is_dir():
        return out

    # Recursive: benchmark runners write to <results_dir>/<run>/raw/*.csv, so a
    # flat glob finds nothing and silently nulls every bench field. Superseded
    # piles are excluded so a stale run cannot outrank a live one.
    files = sorted(
        (p for p in results_dir.rglob("*.csv") if "_superseded" not in p.parts),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for f in files:
        try:
            with f.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    mid = (row.get("model") or "").strip()
                    if not mid or mid in out:
                        continue
                    if (row.get("error") or "").strip():
                        continue
                    try:
                        med = float(row.get("median_tok_s") or 0) or None
                        q = float(row.get("quality_score") or 0)
                    except ValueError:
                        continue
                    if med is None:
                        continue
                    out[mid] = {
                        "tok_s": round(med, 1),
                        "quality": round(q, 2),
                        "source": f.name,
                        "mtime": datetime.fromtimestamp(
                            f.stat().st_mtime, timezone.utc
                        ).isoformat(),
                    }
        except OSError:
            continue
    return out


def load_usage(activity_dbs: list[Path]) -> dict:
    """Fold in per-model usage from llama-swap activity logs.

    Mechanically derived, like the benchmark merge: request count, input and
    output token totals, and last-used epoch. A model absent from every log is
    genuinely unused (or logs pruned) — it gets nothing, never a zero guess.
    sqlite3 is stdlib, matching the no-new-deps rule.

    Multiple DBs are merged (Studio + MacBook when the share is mounted). An
    SMB-hosted sqlite cannot be opened in place (locking), so a remote DB is
    copied to scratch first.
    """
    out: dict = {}
    import sqlite3
    for db in activity_dbs:
        if not db.is_file():
            continue
        local = db
        if str(db).startswith("/Volumes/"):
            # A WAL-mode sqlite is not a single file: the -wal holds recent
            # transactions and the -shm the shared-memory index. Copying only
            # the .sqlite yields an inconsistent snapshot that sqlite refuses
            # to open. Copy the trio so the snapshot is self-consistent.
            local = Path("/Users/macstudio/.hermes/cache/scratch") / (
                f"activity-{db.parent.name}.sqlite"
            )
            try:
                import shutil
                shutil.copyfile(db, local)
                for suffix in ("-wal", "-shm"):
                    src = Path(str(db) + suffix)
                    if src.is_file():
                        shutil.copyfile(src, Path(str(local) + suffix))
            except OSError:
                continue
        try:
            con = sqlite3.connect(f"file:{local}?mode=ro", uri=True)
            try:
                cur = con.execute(
                    """
                    SELECT model_id,
                           COUNT(*),
                           SUM(COALESCE(input_tokens, 0)),
                           SUM(COALESCE(output_tokens, 0)),
                           MAX(ts_created)
                    FROM activity
                    GROUP BY model_id
                    """
                )
                for mid, n, inp, outp, last in cur.fetchall():
                    out[mid] = {
                        "requests": int(n),
                        "input_tokens": int(inp or 0),
                        "output_tokens": int(outp or 0),
                        "last_used_epoch": int(last) if last is not None else None,
                        "last_used": datetime.fromtimestamp(
                            int(last), timezone.utc
                        ).strftime("%Y-%m-%d")
                        if last
                        else None,
                    }
            finally:
                con.close()
        except Exception:
            continue
    return out


def build(config_path: Path, results_dir: Path, mb_config: Path | None = None,
          activity_dbs: list[Path] | None = None) -> tuple[list[dict], list[str]]:
    """Load every reachable host config and merge rows, tagged by host."""
    errors: list[str] = []
    warnings: list[str] = []

    sources: list[tuple[str, Path]] = [("studio", config_path)]
    if mb_config is not None:
        if mb_config.is_file():
            sources.append(("macbook", mb_config))
        else:
            warnings.append(
                f"macbook config not mounted at {mb_config} — MacBook fleet NOT included"
            )

    bench = load_bench(results_dir)
    usage = load_usage(activity_dbs or [])
    rows: list[dict] = []

    for host, cpath in sources:
        try:
            cfg = yaml.safe_load(cpath.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            sys.exit(f"error: cannot read {cpath}: {e}")

        models = cfg.get("models") or {}
        groups = cfg.get("groups") or {}

        # group membership (a model may appear in more than one group)
        membership: dict[str, list[str]] = {}
        group_meta: dict[str, dict] = {}
        for gname, g in groups.items():
            if not isinstance(g, dict):
                continue
            group_meta[gname] = g
            for m in g.get("members") or []:
                membership.setdefault(m, []).append(gname)

        for mid, m in models.items():
            if not isinstance(m, dict):
                errors.append(f"[{host}] {mid}: entry is not a mapping")
                continue

            cmd = parse_cmd(m.get("cmd"))
            gguf_raw = cmd.get("--model")
            mmproj_raw = cmd.get("--mmproj")
            gguf = host_path(host, gguf_raw)
            mmproj = host_path(host, mmproj_raw)
            desc = " ".join((m.get("description") or "").split())
            stem = Path(gguf).stem if gguf else mid

            # Directory-backed engines (sushi/MLX pack) are valid: --model may
            # point at a model directory, not just a single GGUF file.
            exists = bool(gguf) and (os.path.isfile(gguf) or os.path.isdir(gguf))
            if not gguf:
                errors.append(f"[{host}] {mid}: no --model in cmd")
            elif not exists:
                # Distinguish "never downloaded" from "symlink points nowhere".
                # These need different fixes and look identical to os.path.isfile.
                if os.path.islink(gguf):
                    tgt = os.readlink(gguf)
                    if "\\" in tgt:
                        errors.append(
                            f"[{host}] {mid}: BROKEN SYMLINK (escaped backslashes in target) "
                            f"-> {tgt}"
                        )
                    else:
                        errors.append(
                            f"[{host}] {mid}: BROKEN SYMLINK -> {tgt} (target absent)"
                        )
                else:
                    errors.append(f"[{host}] {mid}: gguf missing on disk: {gguf}")

            if mmproj and not os.path.isfile(mmproj):
                warnings.append(f"[{host}] {mid}: mmproj missing on disk: {mmproj}")

            gnames = membership.get(mid, [])
            if not gnames:
                warnings.append(
                    f"[{host}] {mid}: in models: but in no group — unreachable, still on disk"
                )
            for g in gnames:
                gm = group_meta.get(g, {})
                if gm.get("members") and mid not in gm["members"]:
                    errors.append(f"[{host}] {mid}: listed in group {g} inconsistently")

            total_b, active_b, arch = infer_params(mid, stem, desc)
            # The header outranks the derivation: expert_count is measured,
            # the id/ARCH_OVERRIDES path is inferred. The derivation stays as
            # the fallback for directory-backed engines and unreadable files.
            hdr_arch = gguf_arch(gguf) if exists else None
            if hdr_arch:
                arch = hdr_arch
            quant_m = QUANT_RE.search(stem)
            tok, tok_src = TOKENIZERS.get(mid, (None, "unmapped"))
            caps = infer_capabilities(mid, bool(mmproj), gnames[0] if gnames else "")

            try:
                ctx = int(cmd.get("--ctx-size") or 0) or None
                par = int(cmd.get("--parallel") or 0) or None
            except ValueError:
                ctx = par = None
            try:
                ttl = int(m.get("ttl")) if m.get("ttl") is not None else None
            except (TypeError, ValueError):
                ttl = None

            persistent = any(
                bool((group_meta.get(g) or {}).get("persistent")) for g in gnames
            )

            _opt_enabled = []
            if cmd.get("--spec-type"):
                _opt_enabled.append("mtp")
            if par and par > 1:
                _opt_enabled.append(f"parallel={par}")
            if ctx:
                _opt_enabled.append(f"ctx={ctx}")
            if quant_m:
                _opt_enabled.append(f"quant={quant_m.group(1)}")

            rows.append({
                "id": mid,
                "host": host,
                "display_name": m.get("name") or mid,
                "groups": sorted(gnames),
                "persistent": persistent,
                "gguf_path": gguf_raw,
                "gguf_resolved": gguf if gguf != gguf_raw else None,
                "gguf_exists": exists,
                "gguf_size_gb": file_size_gb(gguf),
                "mmproj_path": mmproj_raw,
                "mmproj_size_gb": file_size_gb(mmproj),
                "vision": bool(mmproj),
                "ctx_size": ctx,
                "parallel": par,
                "spec_type": cmd.get("--spec-type"),
                "ttl": ttl,
                "quant": quant_m.group(1) if quant_m else None,
                "params_total_b": total_b,
                "params_active_b": active_b,
                "arch": arch,
                "capabilities": caps,
                "capability": caps[0],
                "tokenizer": tok,
                "tokenizer_source": tok_src,
                "bench": bench.get(mid),
                "has_bench": mid in bench,
                "usage": usage.get(mid),
                "has_usage": mid in usage,
                "description": desc,
                "optimizations": compute_optimizations(_text_family(mid), _opt_enabled),
            })

        # Group members that do not exist in models: at — the exact failure
        # mode the studio-* -> ms-* rename produced.
        for mid in membership:
            if mid not in models:
                errors.append(f"[{host}] {mid}: group member with no models: entry (orphan id)")

    rows.sort(
        key=lambda r: (
            HOSTS.index(r["host"]) if r["host"] in HOSTS else 99,
            CAPABILITY_ORDER.index(r["capabilities"][0])
            if r["capabilities"] and r["capabilities"][0] in CAPABILITY_ORDER
            else 99,
            -(r["params_total_b"] or r["params_active_b"] or 0),
            r["id"],
        )
    )
    return rows, errors + warnings


MD_COLUMNS = [
    ("id", "id"),
    ("host", "host"),
    ("cap", "capabilities"),
    ("group", "groups"),
    ("size_gb", "gguf_size_gb"),
    ("total_b", "params_total_b"),
    ("active_b", "params_active_b"),
    ("arch", "arch"),
    ("quant", "quant"),
    ("vision", "vision"),
    ("ctx", "ctx_size"),
    ("mtp", "spec_type"),
    ("tok_s", "bench.tok_s"),
    ("qual", "bench.quality"),
]


def render_md(rows: list[dict], stamp: str, imgs: list[dict] | None = None) -> str:
    def cell(r: dict, key: str) -> str:
        if key == "capabilities":
            return "+".join(r["capabilities"])
        if key == "groups":
            return ",".join(r["groups"]) or "**none**"
        if key == "vision":
            return "yes" if r["vision"] else ""
        if key == "spec_type":
            return "mtp" if r["spec_type"] and "mtp" in r["spec_type"] else ""
        if key.startswith("bench."):
            b = r.get("bench") or {}
            v = b.get(key.split(".", 1)[1])
            return "" if v is None else str(v)
        v = r.get(key)
        if v is None:
            return ""
        if isinstance(v, bool):
            return "yes" if v else ""
        if isinstance(v, float):
            return f"{v:g}"
        return str(v)

    head = "| " + " | ".join(h for h, _ in MD_COLUMNS) + " |"
    rule = "|" + "|".join("---" for _ in MD_COLUMNS) + "|"
    body = [
        "| " + " | ".join(cell(r, k) for _, k in MD_COLUMNS) + " |" for r in rows
    ]

    by_host: dict[str, tuple[int, float]] = {}
    for r in rows:
        n, g = by_host.get(r["host"], (0, 0.0))
        by_host[r["host"]] = (n + 1, g + (r["gguf_size_gb"] or 0))
    total = sum(g for _, g in by_host.values())
    host_line = " \u00b7 ".join(
        f"{h}: {n} models, {g:.1f} GB" for h, (n, g) in by_host.items()
    )

    by_cap: dict[str, int] = {}
    for r in rows:
        for c in r["capabilities"]:
            by_cap[c] = by_cap.get(c, 0) + 1

    foot = [
        "",
        f"**{len(rows)} models, {total:.1f} GB on disk** ({host_line}).",
        "",
        "Capability counts (a model can appear more than once): "
        + ", ".join(f"{k} {v}" for k, v in sorted(by_cap.items()))
        + ".",
        "",
        "`arch` is read from the GGUF header (`expert_count`) whenever the "
        "weights are readable; only then falling back to the A#B/E#B token in "
        "the id and the audited override list.",
        "Blank `total_b` means the parameter count is not stated in the filename "
        "or description — it was not guessed.",
        "Blank `tok_s`/`qual` means no successful benchmark CSV mentions this "
        "model.",
        "`groups` = **none** means the model is in `models:` but unreachable by "
        "llama-swap and still occupying disk.",
        "",
        f"Generated {stamp} from the llama-swap config(s) by the `fleet-catalog` "
        "skill. Do not hand-edit — re-run the generator.",
    ]
    if imgs:
        body.append("")
        body.append("## Image Models")
        body.append(render_image_md(imgs))
        body.append("")
        body.append("## Tuning (fleet-wide)")
        body.append("| model | type | enabled | available | untouched |")
        body.append("|---|---|---|---|---|")
        for r in rows:
            o = r.get("optimizations") or {}
            body.append(
                f"| {r['id']} | text | {', '.join(o.get('enabled') or []) or '—'} | "
                f"{', '.join(o.get('available') or []) or '—'} | "
                f"{', '.join(o.get('untouched') or []) or '—'} |"
            )
        for m in imgs:
            o = m.get("optimizations") or {}
            body.append(
                f"| {m['id']} | image | {', '.join(o.get('enabled') or []) or '—'} | "
                f"{', '.join(o.get('available') or []) or '—'} | "
                f"{', '.join(o.get('untouched') or []) or '—'} |"
            )
    return "\n".join([head, rule, *body, *foot]) + "\n"


def render_widget(rows: list[dict], payload: dict, stamp: str) -> str:
    """Render the catalog as a FRAGMENT for the Hermes ::preview frame.

    The preview frame is a widget context, not a standalone page: it injects
    the app's live theme as CSS vars (--foreground, --muted-foreground,
    --accent, --border, --card) and expects a fragment — no <html>/<head>/<body>
    wrappers, no own background/font/margins. A full standalone document with
    a trailing <script> does not execute in that frame, so the buttons render
    but never attach. This variant uses the theme vars and inline JS that runs
    in the preview context. Same rows as catalog.html — they cannot drift.
    """
    def esc(v) -> str:
        if v is None:
            return ""
        return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def num(v) -> str:
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:g}"
        return str(v)

    def pct(v, maxv) -> int:
        if not v or not maxv:
            return 0
        return max(4, round(v / maxv * 100))

    max_tok = max((r.get("bench") or {}).get("tok_s") or 0 for r in rows) or 1
    cap_counts: dict[str, int] = {}
    for r in rows:
        for c in r.get("capabilities") or []:
            cap_counts[c] = cap_counts.get(c, 0) + 1
    chosen = ["code", "vision", "general", "embedding", "extraction"]

    rows_html = []
    for r in rows:
        b = r.get("bench") or {}
        tok = b.get("tok_s")
        qual = b.get("quality")
        mtp = bool(r.get("spec_type") and "mtp" in r["spec_type"])
        u = r.get("usage") or {}
        reqs = u.get("requests")
        last = u.get("last_used")
        cap_badges = "".join(
            f'<span class="cap cap-{c}">{esc(c)}</span>'
            for c in (_ for _ in chosen if _ in (r.get("capabilities") or []))
        )
        bench_badge = (
            '<span class="b-badge b-yes">bench</span>'
            if r.get("has_bench")
            else '<span class="b-badge b-no">no bench</span>'
        )
        use_badge = (
            '<span class="b-badge b-yes">used</span>'
            if r.get("has_usage")
            else '<span class="b-badge b-no">unused</span>'
        )
        rows_html.append(
            "<tr>"
            f'<td class="mid" data-k="{esc(r.get("id"))}"><span class="host-dot h-{esc(r.get("host", "studio"))}"></span>'
            f'<code>{esc(r.get("id"))}</code></td>'
            f'<td data-k="{esc(r.get("host", "studio"))}"><span class="host-tag">{esc(r.get("host", "studio"))}</span></td>'
            f'<td>{cap_badges}</td>'
            f'<td data-k="{esc(",".join(r.get("groups") or []))}"><code>{esc(",".join(r.get("groups") or []))}</code></td>'
            f'<td class="num" data-k="{num(r.get("gguf_size_gb"))}">{num(r.get("gguf_size_gb"))}</td>'
            f'<td class="num" data-k="{num(r.get("params_total_b"))}">{num(r.get("params_total_b"))}</td>'
            f'<td class="num" data-k="{num(r.get("params_active_b"))}">{num(r.get("params_active_b"))}</td>'
            f'<td data-k="{esc(r.get("arch") or "?")}"><span class="arch {"moe" if r.get("arch") == "moe" else "dense"}">{esc(r.get("arch") or "?")}</span></td>'
            f'<td data-k="{esc(r.get("quant"))}"><code>{esc(r.get("quant"))}</code></td>'
            f'<td class="num" data-k="{1 if r.get("vision") else 0}">{"✓" if r.get("vision") else ""}</td>'
            f'<td class="num" data-k="{esc(r.get("ctx_size"))}">{esc(r.get("ctx_size"))}</td>'
            f'<td class="num" data-k="{1 if mtp else 0}">{"✓" if mtp else ""}</td>'
            f'<td class="num tok" data-k="{num(tok)}"><span class="bar" style="width:{pct(tok, max_tok)}%"></span>{num(tok)}</td>'
            f'<td class="num" data-k="{num(qual)}">{num(qual)}</td>'
            f'<td class="num" data-k="{num(reqs)}">{num(reqs)}</td>'
            f'<td data-k="{esc(last or "")}">{esc(last)}</td>'
            f'<td>{bench_badge}</td>'
            f'<td>{use_badge}</td>'
            "</tr>"
        )

    n_no_bench = sum(1 for r in rows if not r.get("has_bench"))
    n_no_usage = sum(1 for r in rows if not r.get("has_usage"))
    cap_html = "".join(
        f'<button class="chip" data-cap="{esc(c)}">{esc(c)} <span>{n}</span></button>'
        for c, n in sorted(cap_counts.items())
    )

    return f"""<style>
  .fc {{ color: var(--foreground); font-size: 13px; }}
  .fc .stats {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 0 0 12px; }}
  .fc .stat {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
              padding: 8px 12px; min-width: 90px; }}
  .fc .stat-label {{ color: var(--muted-foreground); font-size: 10px; text-transform: uppercase;
                    letter-spacing: 0.05em; }}
  .fc .stat-num {{ font-size: 20px; font-weight: 650; }}
  .fc .stat-sub {{ color: var(--muted-foreground); font-size: 11px; }}
  .fc .stat.warn .stat-num {{ color: var(--accent); }}
  .fc .controls {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 0 0 10px; }}
  .fc input[type=search] {{ background: var(--card); border: 1px solid var(--border);
    color: var(--foreground); border-radius: 8px; padding: 6px 10px; font-size: 12px;
    width: 200px; outline: none; }}
  .fc input[type=search]:focus {{ border-color: var(--accent); }}
  .fc .chips {{ display: flex; gap: 5px; flex-wrap: wrap; }}
  .fc .chip {{ background: var(--card); border: 1px solid var(--border); color: var(--muted-foreground);
    border-radius: 999px; padding: 4px 10px; font-size: 11px; cursor: pointer; }}
  .fc .chip span {{ opacity: .8; }}
  .fc .chip.on {{ background: var(--accent); border-color: var(--accent); color: var(--card); }}
  .fc table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .fc thead th {{ text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--muted-foreground); padding: 6px 8px; border-bottom: 1px solid var(--border);
    cursor: pointer; user-select: none; white-space: nowrap; }}
  .fc thead th:hover {{ color: var(--accent); }}
  .fc tbody td {{ padding: 6px 8px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
  .fc tbody tr:hover {{ background: color-mix(in srgb, var(--accent) 8%, transparent); }}
  .fc code {{ font-family: ui-monospace, SF Mono, Menlo, monospace; font-size: 11px; color: var(--accent); }}
  .fc .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .fc .host-tag {{ font-size: 11px; color: var(--muted-foreground); text-transform: uppercase; }}
  .fc .host-dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px;
    background: var(--accent); }}
  .fc .h-macbook {{ background: color-mix(in srgb, var(--accent) 60%, var(--muted-foreground)); }}
  .fc .arch {{ font-size: 11px; padding: 1px 7px; border-radius: 999px; font-weight: 600; }}
  .fc .arch.moe {{ color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, transparent); }}
  .fc .arch.dense {{ color: var(--muted-foreground); background: color-mix(in srgb, var(--muted-foreground) 14%, transparent); }}
  .fc .cap {{ font-size: 11px; padding: 1px 7px; border-radius: 999px; margin-right: 3px;
    color: var(--muted-foreground); background: color-mix(in srgb, var(--muted-foreground) 12%, transparent); }}
  .fc .b-badge {{ font-size: 11px; padding: 1px 6px; border-radius: 999px; white-space: nowrap; font-weight: 600; }}
  .fc .b-yes {{ color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent); }}
  .fc .b-no {{ color: var(--muted-foreground); background: color-mix(in srgb, var(--muted-foreground) 12%, transparent); }}
  .fc .tok {{ position: relative; min-width: 60px; }}
  .fc .bar {{ position: absolute; inset: auto 0 0 0; height: 2px; background: var(--accent); opacity: .4; }}
  .fc .note {{ color: var(--muted-foreground); font-size: 11px; margin-top: 10px; }}
</style>
<div class="fc">
  <div class="stats">
    <div class="stat"><div class="stat-label">Models</div><div class="stat-num">{len(rows)}</div>
      <div class="stat-sub">{payload.get("total_gguf_gb", 0):g} GB</div></div>
    <div class="stat"><div class="stat-label">No bench</div><div class="stat-num">{n_no_bench}</div>
      <div class="stat-sub">unmeasured</div></div>
    <div class="stat"><div class="stat-label">No usage</div><div class="stat-num">{n_no_usage}</div>
      <div class="stat-sub">no activity</div></div>
    <div class="stat"><div class="stat-label">MoE</div><div class="stat-num">{sum(1 for r in rows if r.get("arch")=="moe")}</div>
      <div class="stat-sub">of {len(rows)}</div></div>
  </div>
  <div class="controls">
    <input type="search" id="fc-search" placeholder="Filter…">
    <div class="chips" id="fc-hosts">
      <button class="chip on" data-host="all">All</button>
      <button class="chip" data-host="studio">Studio</button>
      <button class="chip" data-host="macbook">MacBook</button>
    </div>
    <div class="chips" id="fc-caps">{cap_html}<button class="chip" data-cap="__clear">clear</button></div>
    <div class="chips" id="fc-flags">
      <button class="chip" data-flag="nobench">no bench</button>
      <button class="chip" data-flag="nousage">no usage</button>
    </div>
  </div>
  <table>
    <thead><tr>
      <th data-k="id">ID</th><th data-k="host">Host</th><th>Cap</th><th data-k="groups">Group</th>
      <th data-k="gguf_size_gb" class="num">GB</th><th data-k="params_total_b" class="num">P</th>
      <th data-k="params_active_b" class="num">A</th><th data-k="arch">Arch</th><th data-k="quant">Q</th>
      <th data-k="vision" class="num">V</th><th data-k="ctx_size" class="num">Ctx</th><th data-k="mtp" class="num">M</th>
      <th data-k="tok_s" class="num">tok/s</th><th data-k="quality" class="num">Ql</th>
      <th data-k="reqs" class="num">Reqs</th><th data-k="last">Last</th><th>Bench</th><th>Use</th>
    </tr></thead>
    <tbody id="fc-tbody">{''.join(rows_html)}</tbody>
  </table>
  <div class="note">Generated {esc(stamp)} · sortable, filterable · re-run the generator to refresh</div>
</div>
<script>
(function () {{
  const tbody = document.getElementById("fc-tbody");
  if (!tbody) return;
  const ORIG = Array.from(tbody.querySelectorAll("tr")).map(r => r.cloneNode(true));
  let hostF = "all", capF = null, flagF = null, q = "", sortK = null, sortD = 1;
  const KEYS = [];
  document.querySelectorAll("#fc-tbody").length; // noop
  const ths = tbody.parentElement.querySelectorAll("thead th[data-k]");
  ths.forEach(th => KEYS.push(th.dataset.k));
  const keyOf = (r, k) => {{
    const i = KEYS.indexOf(k);
    if (i < 0) return "";
    const td = r.children[i];
    if (!td) return "";
    const raw = td.dataset.k;
    if (raw !== undefined && raw !== "") {{
      const n = parseFloat(raw);
      return isNaN(n) ? raw : n;
    }}
    const t = td.textContent.trim();
    const n = parseFloat(t);
    return isNaN(n) ? t : n;
  }};
  function render() {{
    let out = ORIG.filter(r => {{
      const host = (r.children[1].textContent || "").trim().toLowerCase();
      const caps = (r.children[2].textContent || "").toLowerCase();
      const benchTxt = (r.children[16].textContent || "").toLowerCase();
      const useTxt = (r.children[17].textContent || "").toLowerCase();
      if (hostF !== "all" && host !== hostF) return false;
      if (capF && !caps.includes(capF)) return false;
      if (flagF === "nobench" && !benchTxt.includes("no bench")) return false;
      if (flagF === "nousage" && !useTxt.includes("unused")) return false;
      if (q && !r.children[0].textContent.toLowerCase().includes(q)
           && !r.textContent.toLowerCase().includes(q)) return false;
      return true;
    }});
    if (sortK) {{
      out.sort((a, b) => {{
        const av = keyOf(a, sortK), bv = keyOf(b, sortK);
        if (typeof av === "string" || typeof bv === "string")
          return String(av).localeCompare(String(bv)) * sortD;
        return ((av || 0) - (bv || 0)) * sortD;
      }});
    }}
    tbody.replaceChildren(...out);
  }}
  const on = (id, fn) => {{
    const el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  }};
  const s = document.getElementById("fc-search");
  if (s) s.addEventListener("input", e => {{ q = e.target.value.toLowerCase(); render(); }});
  on("fc-hosts", e => {{
    const b = e.target.closest(".chip"); if (!b) return;
    document.querySelectorAll("#fc-hosts .chip").forEach(c => c.classList.remove("on"));
    b.classList.add("on"); hostF = b.dataset.host; render();
  }});
  on("fc-caps", e => {{
    const b = e.target.closest(".chip"); if (!b) return;
    if (b.dataset.cap === "__clear") {{
      document.querySelectorAll("#fc-caps .chip").forEach(c => c.classList.remove("on"));
      capF = null; render(); return;
    }}
    document.querySelectorAll("#fc-caps .chip").forEach(c => c.classList.remove("on"));
    b.classList.add("on"); capF = b.dataset.cap; render();
  }});
  on("fc-flags", e => {{
    const b = e.target.closest(".chip"); if (!b) return;
    document.querySelectorAll("#fc-flags .chip").forEach(c => c.classList.remove("on"));
    b.classList.add("on"); flagF = b.dataset.flag; render();
  }});
  ths.forEach(th => {{
    th.addEventListener("click", () => {{
      const k = th.dataset.k;
      if (sortK === k) sortD = -sortD; else {{ sortK = k; sortD = 1; }}
      ths.forEach(t => {{ const a = t.querySelector(".arrow"); if (a) a.textContent = ""; }});
      const a = th.querySelector(".arrow");
      if (a) a.textContent = sortD === 1 ? "▲" : "▼";
      render();
    }});
  }});
}})();
</script>
"""


def _inject_ghosts(html: str) -> str:
    """Server-render ghost section numerals so they survive script-blocked
    preview frames. Deterministic: 01, 02, ... in h2 document order.
    The JS-free fallback keeps the ephemeral in-chat view complete."""
    counter = {"n": 0}

    def _ghost(m):
        counter["n"] += 1
        return f'<h2>{m.group(1)}<span class="row-ghost">{counter["n"]:02d}</span></h2>'

    return re.sub(r"<h2>(.*?)</h2>", _ghost, html, flags=re.S)


def render_html(rows: list[dict], payload: dict, stamp: str) -> str:
    """Render catalog rows as a self-contained modern HTML page.

    No external dependencies: inline CSS + vanilla JS, so the artifact works
    offline and does not rot when a CDN moves. Sorting, filtering and search
    are client-side over the same rows the .json/.md carry. Every sortable
    cell carries a data-k attribute so the JS sorts on the raw value, not the
    rendered text.
    """
    def esc(v) -> str:
        if v is None:
            return ""
        return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def num(v) -> str:
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:g}"
        return str(v)

    def pct(v, maxv) -> int:
        if not v or not maxv:
            return 0
        return max(4, round(v / maxv * 100))

    max_tok = max((r.get("bench") or {}).get("tok_s") or 0 for r in rows) or 1

    cap_counts: dict[str, int] = {}
    for r in rows:
        for c in r.get("capabilities") or []:
            cap_counts[c] = cap_counts.get(c, 0) + 1

    chosen = ["code", "vision", "general", "embedding", "extraction"]

    rows_html = []
    for r in rows:
        b = r.get("bench") or {}
        tok = b.get("tok_s")
        qual = b.get("quality")
        mtp = bool(r.get("spec_type") and "mtp" in r["spec_type"])
        u = r.get("usage") or {}
        reqs = u.get("requests")
        last = u.get("last_used")
        last_epoch = u.get("last_used_epoch")
        cap_badges = "".join(
            f'<span class="cap cap-{c}">{esc(c)}</span>'
            for c in (_ for _ in chosen if _ in (r.get("capabilities") or []))
        )
        # bench presence badge: measured vs never benchmarked
        bench_badge = (
            '<span class="b-badge b-yes" title="has benchmark data">bench</span>'
            if r.get("has_bench")
            else '<span class="b-badge b-no" title="no benchmark data">no bench</span>'
        )
        # usage presence badge
        use_badge = (
            f'<span class="b-badge b-yes" title="{reqs} requests">used</span>'
            if r.get("has_usage")
            else '<span class="b-badge b-no" title="no usage history">unused</span>'
        )
        rows_html.append(
            "<tr>"
            f'<td class="mid" data-k="{esc(r.get("id"))}"><span class="host-dot h-{esc(r.get("host", "studio"))}"></span>'
            f'<code>{esc(r.get("id"))}</code></td>'
            f'<td data-k="{esc(r.get("host", "studio"))}"><span class="host-tag">{esc(r.get("host", "studio"))}</span></td>'
            f'<td>{cap_badges}</td>'
            f'<td data-k="{esc(",".join(r.get("groups") or []))}"><code>{esc(",".join(r.get("groups") or []))}</code></td>'
            f'<td class="num" data-k="{num(r.get("gguf_size_gb"))}">{num(r.get("gguf_size_gb"))}</td>'
            f'<td class="num" data-k="{num(r.get("params_total_b"))}">{num(r.get("params_total_b"))}</td>'
            f'<td class="num" data-k="{num(r.get("params_active_b"))}">{num(r.get("params_active_b"))}</td>'
            f'<td data-k="{esc(r.get("arch") or "?")}"><span class="arch {"moe" if r.get("arch") == "moe" else "dense"}">{esc(r.get("arch") or "?")}</span></td>'
            f'<td data-k="{esc(r.get("quant"))}"><code>{esc(r.get("quant"))}</code></td>'
            f'<td class="num" data-k="{1 if r.get("vision") else 0}">{"✓" if r.get("vision") else ""}</td>'
            f'<td class="num" data-k="{esc(r.get("ctx_size"))}">{esc(r.get("ctx_size"))}</td>'
            f'<td class="num" data-k="{1 if mtp else 0}">{"✓" if mtp else ""}</td>'
            f'<td class="num tok" data-k="{num(tok)}"><span class="bar" style="width:{pct(tok, max_tok)}%"></span>{num(tok)}</td>'
            f'<td class="num" data-k="{num(qual)}">{num(qual)}</td>'
            f'<td class="num" data-k="{num(reqs)}">{num(reqs)}</td>'
            f'<td data-k="{esc(last or "")}">{esc(last)}</td>'
            f'<td>{bench_badge}</td>'
            f'<td>{use_badge}</td>'
            "</tr>"
        )

    hosts = payload.get("hosts") or {}

    def host_card(hkey: str, label: str) -> str:
        h = hosts.get(hkey) or {}
        return (
            f'<div class="stat"><div class="stat-label">{esc(label)}</div>'
            f'<div class="stat-num">{h.get("model_count", 0)}</div>'
            f'<div class="stat-sub">{h.get("total_gguf_gb", 0):g} GB</div></div>'
        )

    n_no_bench = sum(1 for r in rows if not r.get("has_bench"))
    n_no_usage = sum(1 for r in rows if not r.get("has_usage"))

    cap_html = "".join(
        f'<button class="chip" data-cap="{esc(c)}">{esc(c)} <span>{n}</span></button>'
        for c, n in sorted(cap_counts.items())
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Model Fleet Catalog</title>
<style>
  @font-face {{
    font-family: "Space Grotesk";
    font-style: normal; font-weight: 500; font-display: swap;
    src: url(data:font/woff2;base64,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) format("woff2");
  }}
  @font-face {{
    font-family: "Space Grotesk";
    font-style: normal; font-weight: 700; font-display: swap;
    src: url(data:font/woff2;base64,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) format("woff2");
  }}
  :root {{
    --paper: #f7f5f1; --ink: #1a1815; --grey: #6b655c; --line: #d9d3c9;
    --accent: #a33a2a; --accent-soft: rgba(163,58,42,0.08);
    --warn: #a33a2a;
    --mono: ui-monospace, SF Mono, Menlo, Consolas, monospace;
    --display: "Space Grotesk", system-ui, sans-serif;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--paper); color: var(--ink);
    font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
  }}
  ::selection {{ background: var(--ink); color: var(--paper); }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 40px 32px 80px; }}
  header {{ display: flex; align-items: baseline; gap: 20px; flex-wrap: wrap;
            border-bottom: 3px double var(--ink); padding-bottom: 18px; position: relative; }}
  h1 {{ font-family: var(--display); font-size: 44px; font-weight: 700; letter-spacing: -0.03em; }}
  h1 .accent {{ color: var(--ink); }} /* FLEET mark in ink - red reserved strictly for breakage */
  .sub {{ color: var(--grey); font-size: 12.5px; font-family: var(--mono); margin-right: 58px; }}
  .stats {{ display: grid; grid-template-columns: repeat(7, 1fr);
           gap: 0; margin: 0 0 8px; border-bottom: 1px solid var(--line); }}
  @media (max-width: 860px) {{
    .stats {{ grid-template-columns: repeat(3, 1fr); border-bottom: none; }}
    .stat {{ border-right: none; border-bottom: 1px solid var(--line); }}
  }}
  @media (max-width: 480px) {{
    .stats {{ grid-template-columns: repeat(2, 1fr); }}
  }}
  .stat {{ padding: 16px 18px 14px; border-right: 1px solid var(--line); }}
  .stat:last-child {{ border-right: none; }}
  .stat-label {{ color: var(--grey); font-size: 11px; text-transform: uppercase;
                letter-spacing: 0.09em; font-family: var(--mono); }}
  .stat-num {{ font-family: var(--display); font-size: 34px; font-weight: 700; margin-top: 2px; letter-spacing: -0.02em; }}
  .stat-sub {{ color: var(--grey); font-size: 11.5px; font-family: var(--mono); }}
  .stat.warn .stat-num {{ color: var(--warn); }}
  .crest {{ position: absolute; right: 0; top: 2px; width: 42px; height: 42px; }}
  .row-ghost {{ position: absolute; right: 0; top: -14px; font-size: 82px; line-height: 1; color: transparent;
               -webkit-text-stroke: 1.5px var(--line); font-family: var(--display); font-weight: 700; letter-spacing: -0.02em; }}
  body::before {{ content: ""; position: fixed; inset: 0; pointer-events: none; opacity: 0.045; z-index: 999;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E"); }}
  .controls {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
              margin: 22px 0 16px; }}
  input[type=search] {{
    background: transparent; border: 1px solid var(--ink); color: var(--ink);
    border-radius: 0; padding: 8px 12px; font-size: 13px; width: 260px;
    outline: none; font-family: var(--mono);
  }}
  input[type=search]:focus {{ box-shadow: 0 0 0 2px var(--accent-soft); }}
  .chips {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .chip {{ background: transparent; border: 1px solid var(--line); color: var(--grey);
          border-radius: 0; padding: 5px 12px; font-size: 11px; cursor: pointer;
          transition: all .12s; font-family: var(--mono); text-transform: uppercase;
          letter-spacing: 0.05em; }}
  .chip:hover {{ border-color: var(--ink); color: var(--ink); }}
  .chip span {{ opacity: .7; }}
  .chip.on {{ background: var(--ink); border-color: var(--ink); color: var(--paper); }}
  .chip.on span {{ color: var(--paper); opacity: .8; }}
  .chip.warn.on {{ background: var(--accent); border-color: var(--accent); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead th {{
    text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--grey); padding: 8px 10px; border-bottom: 1px solid var(--ink);
    cursor: pointer; user-select: none; white-space: nowrap; font-family: var(--mono);
  }}
  thead th:hover {{ color: var(--ink); }}
  thead th .arrow {{ opacity: .5; font-size: 10px; }}
  tbody td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: middle; }}
  tbody tr:hover td {{ background: var(--accent-soft); }}
  tbody tr:last-child td {{ border-bottom: none; }}
  .mid {{ white-space: nowrap; }}
  code {{ font-family: var(--mono); font-size: 12px; color: var(--ink); }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .host-tag {{ font-size: 11px; color: var(--grey); text-transform: uppercase;
              letter-spacing: 0.05em; font-family: var(--mono); }}
  .host-dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%;
              margin-right: 8px; }}
  .h-studio {{ background: var(--ink); }}
  .h-macbook {{ background: var(--grey); }}
  .arch {{ font-size: 11px; padding: 1px 7px; border: 1px solid var(--line); font-weight: 600;
          font-family: var(--mono); }}
  .arch.moe {{ color: var(--ink); border-color: var(--ink); }}
  .arch.dense {{ color: var(--grey); }}
  .cap {{ font-size: 11px; padding: 1px 7px; border: 1px solid var(--line); margin-right: 4px;
         color: var(--grey); font-family: var(--mono); }}
  .cap-cap-code, .cap-cap-vision, .cap-cap-general, .cap-cap-embedding, .cap-cap-extraction {{
    color: var(--ink); border-color: var(--ink);
  }}
  .b-badge {{ font-size: 11px; padding: 1px 6px; border: 1px solid var(--line); white-space: nowrap;
             font-weight: 600; font-family: var(--mono); }}
  .b-yes {{ color: var(--ink); border-color: var(--ink); }}
  .b-no {{ color: var(--warn); border-color: var(--warn); }}
  .tok {{ position: relative; min-width: 72px; }}
  .bar {{ position: absolute; inset: auto 0 0 0; height: 2px; background: var(--ink);
         opacity: .5; }}
  .note {{ color: var(--grey); font-size: 12px; margin-top: 20px; line-height: 1.7;
          font-family: var(--mono); }}
  .note code {{ color: var(--grey); }}
  h2 {{ font-family: var(--display); font-size: 17px; font-weight: 700; letter-spacing: -0.01em; margin: 44px 0 4px; position: relative; padding-right: 110px; }}
  h2 .count {{ color: var(--grey); font-weight: 500; font-family: var(--mono); font-size: 12px; }}
  .lede {{ color: var(--grey); font-size: 13px; margin-bottom: 18px; }}
  .panel {{ border-top: 1px solid var(--ink); margin-top: 44px; padding-top: 22px; }}
  .panel h2 {{ font-family: var(--display); font-size: 17px; font-weight: 700; letter-spacing: -0.01em;
               margin-bottom: 4px; }}
  .panel h2 .count {{ color: var(--grey); font-weight: 500; font-family: var(--mono); font-size: 12px; }}
  .panel .lede {{ color: var(--grey); font-size: 13px; margin-bottom: 18px; }}
  @media (max-width: 1000px) {{ .wrap {{ padding: 24px 16px 56px; }}
    thead th:nth-child(n+5):nth-child(-n+9), td:nth-child(n+5):nth-child(-n+9) {{ display: none; }} }}
  @media (max-width: 700px) {{
    thead th:nth-child(n+10):nth-child(-n+14), td:nth-child(n+10):nth-child(-n+14) {{ display: none; }}
    .row-ghost {{ display: none; }}
    .crest {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1><span class="accent">FLEET</span> CATALOG</h1>
    <span class="sub">text LLMs · llama-swap configs &nbsp;·&nbsp; image models · disk &nbsp;·&nbsp; {esc(stamp)}</span>
    <div class="crest">
      <svg viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="21" cy="21" r="19.5" stroke="#1a1815" stroke-width="1.5"/>
        <path d="M21 2v5M21 35v5M2 21h5M35 21h5" stroke="#1a1815" stroke-width="1"/>
        <text x="21" y="26" text-anchor="middle" font-family="'Space Grotesk', sans-serif" font-size="14" font-weight="700" fill="#1a1815">F</text>
      </svg>
    </div>
  </header>

  <div class="stats">
    <div class="stat"><div class="stat-label">Models</div><div class="stat-num">{len(rows)}</div>
      <div class="stat-sub">{payload.get("total_gguf_gb", 0):g} GB on disk</div></div>
    {host_card("studio", "Studio")}
    {host_card("macbook", "MacBook")}
    <div class="stat"><div class="stat-label">MoE / dense</div>
      <div class="stat-num">{sum(1 for r in rows if r.get("arch")=="moe")} / {sum(1 for r in rows if r.get("arch")!="moe")}</div>
      <div class="stat-sub">architectures</div></div>
    <div class="stat"><div class="stat-label">Vision</div><div class="stat-num">{sum(1 for r in rows if r.get("vision"))}</div>
      <div class="stat-sub">mmproj equipped</div></div>
    <div class="stat warn"><div class="stat-label">No bench</div><div class="stat-num">{n_no_bench}</div>
      <div class="stat-sub">never measured</div></div>
    <div class="stat warn"><div class="stat-label">No usage</div><div class="stat-num">{n_no_usage}</div>
      <div class="stat-sub">no activity log</div></div>
  </div>

  <h2>Text Models <span class="count">({len(rows)})</span></h2>
  <div class="lede">Llama-swap served LLMs — derived from the Studio and MacBook configs, benchmarked and logged.</div>

  <div class="controls">
    <input type="search" id="search" placeholder="Filter by id or name…">
    <div class="chips" id="hosts">
      <button class="chip on" data-host="all">All</button>
      <button class="chip" data-host="studio">Studio</button>
      <button class="chip" data-host="macbook">MacBook</button>
    </div>
    <div class="chips" id="caps">{cap_html}<button class="chip" data-cap="__clear">clear</button></div>
    <div class="chips" id="flags">
      <button class="chip warn" data-flag="nobench">no bench</button>
    </div>
  </div>

  <table>
    <thead><tr>
      <th data-k="id">ID <span class="arrow"></span></th>
      <th data-k="host">Host</th>
      <th>Capability</th>
      <th data-k="groups">Group</th>
      <th data-k="gguf_size_gb" class="num">GB <span class="arrow"></span></th>
      <th data-k="params_total_b" class="num">Params <span class="arrow"></span></th>
      <th data-k="params_active_b" class="num">Active <span class="arrow"></span></th>
      <th data-k="arch">Arch</th>
      <th data-k="quant">Quant</th>
      <th data-k="vision" class="num">Vis</th>
      <th data-k="ctx_size" class="num">Ctx <span class="arrow"></span></th>
      <th data-k="mtp" class="num">MTP</th>
      <th data-k="tok_s" class="num">tok/s <span class="arrow"></span></th>
      <th data-k="quality" class="num">Qual</th>
      <th data-k="reqs" class="num">Reqs <span class="arrow"></span></th>
      <th data-k="last">Last used</th>
      <th>Bench</th>
      <th>Usage</th>
    </tr></thead>
    <tbody id="tbody">{''.join(rows_html)}</tbody>
  </table>

  <div class="note">
    Capability counts: {", ".join(f"{k} {v}" for k, v in sorted(cap_counts.items()))}.
    Blank cells mean "not stated / not measured" — the catalog never guesses.
    <code>Reqs</code> and <code>Last used</code> come from llama-swap's activity log;
    <code>no usage</code> means the model has no requests on record.
    Arch is <code>moe</code> when the id carries an A#B/E#B token or the audited override list says so.
    Generated {esc(stamp)} by the <code>fleet-catalog</code> skill.
    Do not hand-edit · re-run the generator.
  </div>

  <div class="panel">
  {render_image_html(payload.get("image_models", []))}
  </div>

  <div class="panel">
  {render_tuning_html(rows, payload.get("image_models", []))}
  </div>
</div>

<script>
(function () {{
  const tbody = document.getElementById("tbody");
  const ORIG = Array.from(tbody.querySelectorAll("tr")).map(r => r.cloneNode(true));
  let hostF = "all", capF = null, flagF = null, q = "", sortK = null, sortD = 1;

    // Map column key -> child index, derived from the header row.
  const KEYS = [];
  document.querySelectorAll("thead th[data-k]").forEach(th => KEYS.push(th.dataset.k));
  const keyOf = (r, k) => {{
    const i = KEYS.indexOf(k);
    if (i < 0) return "";
    const td = r.children[i];
    if (!td) return "";
    const raw = td.dataset.k;
    if (raw !== undefined && raw !== "") {{
      const n = parseFloat(raw);
      return isNaN(n) ? raw : n;
    }}
    const t = td.textContent.trim();
    const n = parseFloat(t);
    return isNaN(n) ? t : n;
  }};

  function render() {{
    let out = ORIG.filter(r => {{
      const host = (r.children[1].textContent || "").trim().toLowerCase();
      const caps = (r.children[2].textContent || "").toLowerCase();
      const benchTxt = (r.children[16].textContent || "").toLowerCase();
      const useTxt = (r.children[17].textContent || "").toLowerCase();
      if (hostF !== "all" && host !== hostF) return false;
      if (capF && !caps.includes(capF)) return false;
      if (flagF === "nobench" && !benchTxt.includes("no bench")) return false;
      if (flagF === "nousage" && !useTxt.includes("unused")) return false;
      if (flagF === "cold" && (!benchTxt.includes("no bench") || !useTxt.includes("unused"))) return false;
      if (q && !r.children[0].textContent.toLowerCase().includes(q)
           && !r.textContent.toLowerCase().includes(q)) return false;
      return true;
    }});
    if (sortK) {{
      out.sort((a, b) => {{
        const av = keyOf(a, sortK), bv = keyOf(b, sortK);
        if (typeof av === "string" || typeof bv === "string")
          return String(av).localeCompare(String(bv)) * sortD;
        return ((av || 0) - (bv || 0)) * sortD;
      }});
    }}
    tbody.replaceChildren(...out);
  }}

  document.getElementById("search").addEventListener("input", e => {{ q = e.target.value.toLowerCase(); render(); }});

  document.getElementById("hosts").addEventListener("click", e => {{
    const b = e.target.closest(".chip"); if (!b) return;
    document.querySelectorAll("#hosts .chip").forEach(c => c.classList.remove("on"));
    b.classList.add("on"); hostF = b.dataset.host; render();
  }});

  document.getElementById("caps").addEventListener("click", e => {{
    const b = e.target.closest(".chip"); if (!b) return;
    if (b.dataset.cap === "__clear") {{
      document.querySelectorAll("#caps .chip").forEach(c => c.classList.remove("on"));
      capF = null; render(); return;
    }}
    document.querySelectorAll("#caps .chip").forEach(c => c.classList.remove("on"));
    b.classList.add("on");
    capF = b.dataset.cap;
    render();
  }});

  document.getElementById("flags").addEventListener("click", e => {{
    const b = e.target.closest(".chip"); if (!b) return;
    document.querySelectorAll("#flags .chip").forEach(c => c.classList.remove("on"));
    b.classList.add("on");
    flagF = b.dataset.flag;
    render();
  }});

  document.querySelectorAll("thead th[data-k]").forEach(th => {{
    th.addEventListener("click", () => {{
      const k = th.dataset.k;
      if (sortK === k) sortD = -sortD; else {{ sortK = k; sortD = 1; }}
      document.querySelectorAll("thead th .arrow").forEach(a => a.textContent = "");
      th.querySelector(".arrow").textContent = sortD === 1 ? "▲" : "▼";
      render();
    }});
  }});
}})();
</script>
</body>
</html>
"""



# ---------------------------------------------------------------------------
# Image-generation models (ComfyUI + Unsloth Studio). Offline: scanned from
# the known model directories on disk, never probed over the network. The
# text-LLM catalog above is llama-swap config; image models have no config
# file, so the disk is the source of truth.
# ---------------------------------------------------------------------------

IMAGE_MODEL_DIRS = {
    "studio": [
        Path("/Users/macstudio/models/diffusion/diffusion_models"),
        Path("/Users/macstudio/models/diffusion/text_encoders"),
        Path("/Users/macstudio/models/diffusion/vae"),
        Path("/Users/macstudio/models/diffusion/loras"),
        Path("/Users/macstudio/models/text_encoders"),
    ],
    "macbook": [Path("/Volumes/prasta/.cache/huggingface/hub")],
}

IMAGE_REPO_HINTS = ("z-image", "qwen-image", "image")


def _img_role(p: Path) -> str:
    s = str(p)
    if "diffusion_models" in s or "unet" in s:
        return "DiT"
    if "text_encoders" in s or "clip" in s:
        return "TE"
    if "vae" in s:
        return "VAE"
    if "loras" in s:
        return "LoRA"
    return "?"


def _img_family(name: str) -> str:
    n = name.lower()
    if "z_image" in n or "z-image" in n:
        return "Z-Image"
    if "qwen_image" in n or "qwen-image" in n:
        return "Qwen-Image"
    return "?"


def _img_censored(name: str) -> bool:
    n = name.lower()
    return not any(k in n for k in ("uncensored", "abliterated", "heretic", "nsfw"))


def _img_aesthetic(family: str, name: str) -> str | None:
    if family == "Z-Image":
        return "photoreal"
    if family == "Qwen-Image":
        return "painterly" if not _img_censored(name) else "higher-fidelity"
    return None


def _img_steps(family: str, name: str) -> str:
    if "turbo" in name.lower():
        return "4-8 (turbo)"
    return "20-25 (base)"


def _scan_studio_comfyui() -> list[dict]:
    out = []
    for d in IMAGE_MODEL_DIRS["studio"]:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            try:
                is_file = p.is_file()
            except OSError:
                continue
            if not is_file or p.suffix not in (".safetensors", ".gguf"):
                continue
            family = _img_family(p.name)
            if family == "?":
                continue
            try:
                size = round(p.stat().st_size / 1073741824, 2)
            except OSError:
                size = None
            out.append({
                "id": p.stem, "host": "studio", "backend": "ComfyUI",
                "role": _img_role(p), "family": family, "file": p.name,
                "size_gb": size, "censored": _img_censored(p.name),
                "aesthetic": _img_aesthetic(family, p.name),
                "steps": _img_steps(family, p.name), "notes": "",
                "optimizations": image_optimizations(p.name, _img_role(p)),
            })
    return out


def _sum_size(p: Path) -> int:
    """Recursively sum a path's bytes, resolving symlinks and guarding every
    stat (SMB-mounted HF caches throw EINVAL on broken/odd symlinks)."""
    try:
        if p.is_symlink():
            rp = os.path.realpath(p)
            if os.path.isfile(rp):
                return os.path.getsize(rp)
            if os.path.isdir(rp):
                return _sum_size(Path(rp))
            return 0
        if p.is_file():
            return p.stat().st_size
        if p.is_dir():
            total = 0
            for child in p.iterdir():
                total += _sum_size(child)
            return total
    except OSError:
        return 0
    return 0


def _macbook_size_gb(snapshot: Path) -> float | None:
    """Measure a MacBook HF-cache snapshot's size over ssh. The SMB mount
    cannot read HF-cache symlinks (EINVAL), so sizes come from the MacBook
    itself. None on any failure (share unmounted, ssh down)."""
    local = str(snapshot).replace("/Volumes/prasta", "/Users/prasta")
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "macbook",
             f"du -skL {shlex.quote(local)} 2>/dev/null | cut -f1"],
            capture_output=True, text=True, timeout=25,
        )
        kb = r.stdout.strip()
        if kb.isdigit():
            return int(kb) / 1048576.0
    except Exception:
        pass
    return None


def _scan_macbook_unsloth() -> list[dict]:
    out = []
    hub = IMAGE_MODEL_DIRS["macbook"][0]
    if not hub.is_dir():
        return out
    for repo in sorted(hub.glob("models--*")):
        rname = repo.name.replace("models--", "").replace("--", "/")
        if not any(k in rname.lower() for k in IMAGE_REPO_HINTS):
            continue
        snaps = list(repo.glob("snapshots/*"))
        if not snaps:
            continue
        size_gb = None
        for s in snaps:
            gb = _macbook_size_gb(s)
            if gb is not None:
                size_gb = round(gb, 2)
                break
        censored = _img_censored(rname)
        family = "Z-Image" if "z-image" in rname.lower() else "Qwen-Image"
        ghost = size_gb is not None and size_gb < 0.1
        out.append({
            "id": rname, "host": "macbook", "backend": "Unsloth Studio",
            "role": "DiT+TE+VAE", "family": family, "file": snaps[0].name,
            "size_gb": size_gb, "censored": censored,
            "aesthetic": "photoreal" if family == "Z-Image"
            else ("painterly" if not censored else "higher-fidelity"),
            "steps": "4-8 (turbo)" if family == "Z-Image" else "20-25 (base)",
            "notes": "LFS stubs only, not on disk" if ghost else "",
            "optimizations": image_optimizations(rname, "DiT+TE+VAE"),
        })
    return out


def load_image_models() -> list[dict]:
    """Scan the image-model directories on disk and return a catalog of
    image-generation models (ComfyUI on the Studio, Unsloth on the MacBook
    via the mounted share). Offline — never probes a live backend."""
    out = _scan_studio_comfyui() + _scan_macbook_unsloth()
    out.sort(key=lambda m: (m["host"], m["family"], m["role"], m["id"]))
    return out


def render_image_md(imgs: list[dict]) -> str:
    if not imgs:
        return "No image-generation models found on disk."
    lines = ["| id | host | backend | role | family | size_gb | censored | steps |",
             "|---|---|---|---|---|---|---|---|"]
    for m in imgs:
        lines.append(
            f"| {m['id']} | {m['host']} | {m['backend']} | {m['role']} | "
            f"{m['family']} | {m['size_gb']} | {'no' if not m['censored'] else 'yes'} | "
            f"{m['steps']} |"
        )
    return "\n".join(lines)


def render_image_html(imgs: list[dict]) -> str:
    if not imgs:
        return '<div class="note">No image-generation models found on disk.</div>'
    rows = []
    for m in imgs:
        cens = "no" if not m["censored"] else "yes"
        badge = "b-no" if not m["censored"] else "b-yes"
        size = f"{m['size_gb']:.1f} GB" if m.get("size_gb") is not None else "—"
        rows.append(
            f"<tr><td>{esc(m['id'])}</td><td>{esc(m['host'])}</td>"
            f"<td>{esc(m['backend'])}</td><td>{esc(m['role'])}</td>"
            f"<td>{esc(m['family'])}</td><td>{size}</td>"
            f"<td><span class=\"badge {badge}\">{cens}</span></td>"
            f"<td>{esc(m['steps'])}</td><td>{esc(m['aesthetic'] or '—')}</td>"
            f"<td class=\"muted\">{esc(m['notes'] or '')}</td></tr>"
        )
    return (
        f"<h2>Image Models <span class=\"count\">({len(imgs)})</span></h2>"
        "<div class=\"lede\">ComfyUI on the Mac Studio M3 Ultra, Unsloth Studio on the MacBook Pro M5 — scanned from disk, never probed.</div>"
        "<table><thead><tr><th>ID</th><th>Host</th><th>Backend</th><th>Role</th>"
        "<th>Family</th><th>GB</th><th>Censored</th><th>Steps</th><th>Aesthetic</th>"
        "<th>Notes</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )



# Curated capability map (mirrors references/optimizations.md). Family ->
# optimizations the model/hardware supports. "available" is the full set;
# "untouched" = available minus what's already enabled (ready for tuning).
TEXT_OPT_AVAILABLE = {
    "qwen": ["mtp", "speculative-decoding", "flash-attention", "kv-cache-quant",
             "parallel", "ctx", "quant"],
    "gemma": ["speculative-decoding", "flash-attention", "kv-cache-quant",
              "parallel", "ctx", "quant"],
    "nemotron": ["mtp", "speculative-decoding", "flash-attention",
                 "kv-cache-quant", "parallel", "ctx", "quant"],
    "gpt-oss": ["speculative-decoding", "flash-attention", "kv-cache-quant",
                "parallel", "ctx", "quant"],
    "granite": ["speculative-decoding", "flash-attention", "kv-cache-quant",
                "parallel", "ctx", "quant"],
    "default": ["speculative-decoding", "flash-attention", "kv-cache-quant",
                "parallel", "ctx", "quant"],
}
IMAGE_OPT_AVAILABLE = ["quant", "steps", "resolution", "lora", "upscale", "sampler"]


def _text_family(mid: str) -> str:
    n = mid.lower()
    if "qwen" in n:
        return "qwen"
    if "gemma" in n:
        return "gemma"
    if "nemotron" in n:
        return "nemotron"
    if "gpt-oss" in n or "gptoss" in n:
        return "gpt-oss"
    if "granite" in n:
        return "granite"
    return "default"


def compute_optimizations(family: str, enabled: list[str]) -> dict:
    avail = TEXT_OPT_AVAILABLE.get(family, TEXT_OPT_AVAILABLE["default"])
    untouched = [a for a in avail if a not in enabled]
    return {"enabled": sorted(enabled), "available": sorted(avail),
            "untouched": sorted(untouched)}


def text_enabled_from_row(r: dict) -> list[str]:
    en = []
    if r.get("spec_type"):
        en.append("mtp")
    if r.get("parallel") and r["parallel"] > 1:
        en.append(f"parallel={r['parallel']}")
    if r.get("ctx_size"):
        en.append(f"ctx={r['ctx_size']}")
    if r.get("quant"):
        en.append(f"quant={r['quant']}")
    return en


def image_enabled_from_name(name: str) -> list[str]:
    en = []
    q = QUANT_RE.search(name)
    if q:
        en.append(f"quant={q.group(1)}")
    en.append("steps=turbo(4-8)" if "turbo" in name.lower() else "steps=base(20-25)")
    return en


def image_optimizations(name: str, role: str = "DiT") -> dict:
    enabled = image_enabled_from_name(name) if role == "DiT" else []
    untouched = [a for a in IMAGE_OPT_AVAILABLE if a not in
                 [e.split("=")[0] for e in enabled]]
    return {"enabled": sorted(enabled), "available": sorted(IMAGE_OPT_AVAILABLE),
            "untouched": sorted(untouched)}


def render_tuning_html(rows: list[dict], imgs: list[dict]) -> str:
    """Fleet-wide tuning view: every model (text + image) with its
    enabled / available / untouched optimization buckets."""
    entries = []
    for r in rows:
        o = r.get("optimizations") or {}
        entries.append(("text", r["id"], o))
    for m in imgs:
        o = m.get("optimizations") or {}
        entries.append(("image", m["id"], o))
    if not entries:
        return '<div class="note">No optimization data.</div>'
    rows_html = []
    for typ, mid, o in entries:
        en = ", ".join(o.get("enabled") or []) or "—"
        av = ", ".join(o.get("available") or []) or "—"
        un = ", ".join(o.get("untouched") or []) or "—"
        rows_html.append(
            f"<tr><td>{esc(mid)}</td><td>{typ}</td><td>{esc(en)}</td>"
            f"<td>{esc(av)}</td><td>{esc(un)}</td></tr>"
        )
    return (
        f"<h2>Tuning <span class=\"count\">({len(entries)})</span></h2>"
        "<div class=\"lede\">Every model's optimization buckets — enabled, available, untouched. The untouched column is what's ready for tuning.</div>"
        "<table><thead><tr><th>Model</th><th>Type</th><th>Enabled</th>"
        "<th>Available</th><th>Untouched</th></tr></thead><tbody>"
        + "".join(rows_html) + "</tbody></table>"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path,
                    default=Path("~/.hermes/llama-swap/config.yaml").expanduser())
    ap.add_argument("--results-dir", type=Path,
                    default=Path("~/.hermes/benchmark_results").expanduser())
    ap.add_argument("--out-dir", type=Path,
                    default=Path(OUT_DIR_DEFAULT).expanduser(),
                    help="where the four artifacts land (default: the iCloud "
                         "Hermes infra folder, OUT_DIR_DEFAULT)")
    ap.add_argument("--mb-config", type=Path, default=MB_CONFIG,
                    help="macbook config (skipped when share not mounted)")
    ap.add_argument("--activity", type=Path,
                    default=Path("~/.hermes/llama-swap/activity.sqlite").expanduser(),
                    help="llama-swap activity log for usage history")
    ap.add_argument("--no-mb", action="store_true",
                    help="skip the macbook config even when mounted")
    ap.add_argument("--check", action="store_true",
                    help="validate only, write nothing")
    ap.add_argument("--no-bench", action="store_true", help="skip CSV merge")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as failures")
    ap.add_argument("--open", action="store_true",
                    help="open catalog.html in the default browser after writing")
    args = ap.parse_args()

    if not args.config.is_file():
        sys.exit(f"error: config not found: {args.config}")

    results_dir = Path("/nonexistent") if args.no_bench else args.results_dir
    activity_dbs = [args.activity]
    if not args.no_mb and args.mb_config.is_file():
        activity_dbs.append(args.mb_config.parent / "activity.sqlite")
    rows, problems = build(
        args.config,
        results_dir,
        None if args.no_mb else args.mb_config,
        activity_dbs,
    )

    imgs = load_image_models()

    missing = [r["id"] for r in rows if not r["gguf_exists"]]
    orphans = [r["id"] for r in rows if not r["groups"]]
    total_gb = sum(r["gguf_size_gb"] or 0 for r in rows)

    in_any_group = sum(1 for r in rows if r["groups"])
    print(
        f"{len(rows)} models ({in_any_group} in groups), "
        f"{len(missing)} missing gguf, {len(orphans)} orphans"
    )
    print(f"{len(imgs)} image models on disk")

    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)

    if args.check:
        if problems and (args.strict or missing or orphans):
            print("check FAILED", file=sys.stderr)
            return 1
        print("check OK")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    by_host_count: dict[str, int] = {}
    by_host_gb: dict[str, float] = {}
    for r in rows:
        by_host_count[r["host"]] = by_host_count.get(r["host"], 0) + 1
        by_host_gb[r["host"]] = by_host_gb.get(r["host"], 0.0) + (r["gguf_size_gb"] or 0)

    payload = {
        "generated": stamp,
        "source_configs": {
            "studio": str(args.config),
            "macbook": str(args.mb_config) if not args.no_mb else None,
        },
        "hosts": {
            h: {"model_count": by_host_count.get(h, 0), "total_gguf_gb": round(by_host_gb.get(h, 0.0), 2)}
            for h in HOSTS
        },
        "model_count": len(rows),
        "total_gguf_gb": round(total_gb, 2),
        "problems": problems,
        "models": rows,
        "image_models": imgs,
        "image_model_count": len(imgs),
    }
    (args.out_dir / "catalog.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (args.out_dir / "catalog.md").write_text(render_md(rows, stamp, imgs), encoding="utf-8")
    (args.out_dir / "catalog.html").write_text(
        _inject_ghosts(render_html(rows, payload, stamp)), encoding="utf-8"
    )
    (args.out_dir / "catalog-widget.html").write_text(
        render_widget(rows, payload, stamp), encoding="utf-8"
    )

    print(f"wrote {args.out_dir / 'catalog.json'}")
    print(f"wrote {args.out_dir / 'catalog.md'}")
    print(f"wrote {args.out_dir / 'catalog.html'}")
    print(f"wrote {args.out_dir / 'catalog-widget.html'}")

    if args.open and not args.check:
        html_path = args.out_dir / "catalog.html"
        try:
            subprocess.run(["open", str(html_path)], check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"warning: could not open {html_path}: {exc}")
        else:
            print(f"opened {html_path}")
    return 1 if (missing or orphans) else 0


if __name__ == "__main__":
    sys.exit(main())