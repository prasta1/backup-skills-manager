#!/usr/bin/env python3
"""Classify a fleet model two independent ways.

**Model Family** comes from the model id -- the line whoever built it named.
Id-grounded on purpose: an id saying "hermes" or "kat-coder" does not state what
its weights are, and guessing the base is how you end up labelling a Qwen model
as a Llama one. First token match wins, so specific brands precede generic ones.

**Base Architecture** comes from the artifact: the `general.architecture` string
in the model's own GGUF. That is evidence, not inference -- `ms-kat-coder-v2.5`
reports `qwen35moe`, which no amount of reading the id would tell you.

Two machines, one parser. The `gguf` pip package is installed on both Macs at
different versions with different APIs (the MacBook's raises AttributeError where
the Studio's works), so this reads the GGUF header with stdlib instead. Only the
metadata KV section is touched, and it stops as soon as it has what it wants, so
the tokenizer vocabulary is never walked.

The MacBook's weights are not reachable from the Studio -- its llama-swap config
holds `/Users/prasta/Models/...` paths that only resolve on that box -- so its
architectures are read by piping THIS FILE over ssh and running it there. Same
shape as the `--extra-sizes` workaround in build_model_config.py.

Usage (the ssh path relies on this):
    python3 model_family.py --emit-arch-map ~/.hermes/llama-swap/config.yaml
    python3 model_family.py --emit-arch-map <cfg> --only ms-qwen3-14b,ms-gemma-4-e4b
"""
import argparse
import json
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE_PATH = os.path.join(ROOT, "references", "model-arch.json")

STUDIO_CONFIG = os.path.expanduser("~/.hermes/llama-swap/config.yaml")
MBP_CONFIG = "~/.hermes/llama-swap/config.yaml"
MBP_SSH = os.environ.get("BENCH_MBP_SSH", "macbook")

PREFIXES = ("ms-", "mb-")

# (token, family) -- FIRST match wins, so specific brands come before generic
# ones. Id-grounded: qwythos/qwopus/hermes/kat/nuextract/muse/bonsai get their
# own family because that is the line their id names. Their base architecture is
# a separate column, read from the weights.
FAMILY_HINTS = (
    ("qwen", "qwen"),          # qwen3, qwen3.5, qwen3.6, qwen3.8, qwen36
    ("qwopus", "qwopus"),
    ("qwythos", "qwythos"),
    ("gemma", "gemma"),
    ("granite", "granite"),
    ("lfm", "lfm"),
    ("nemotron", "nemotron"),
    ("gpt-oss", "gpt-oss"),
    ("glm", "glm"),
    ("deepseek", "deepseek"),
    ("devstral", "devstral"),
    ("ministral", "ministral"),
    ("hermes", "hermes"),
    ("kat-coder", "kat"),
    ("smollm", "smollm"),
    ("trinity", "trinity"),
    ("nuextract", "nuextract"),
    ("muse", "muse"),
    ("bonsai", "bonsai"),
)


def strip_prefix(model_id, prefixes=PREFIXES):
    """Drop the machine prefix (`ms-`, `mb-`) so both boxes' twins classify the
    same. The prefix is a HOST marker, not part of the model's identity."""
    for p in prefixes:
        if model_id.lower().startswith(p):
            return model_id[len(p):]
    return model_id


def model_family(model_id, prefixes=PREFIXES):
    """Family token for a model id, or None when nothing matches -- `sushi` is a
    llama.cpp fork build, not a model, and gets no family rather than a wrong one."""
    s = strip_prefix(model_id, prefixes).lower()
    for token, fam in FAMILY_HINTS:
        if token in s:
            return fam
    return None


# ---------------------------------------------------------------------------
# GGUF metadata (stdlib)
# ---------------------------------------------------------------------------
_MAGIC = 0x46554747  # "GGUF"
_SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
           6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
_STR, _ARR = 8, 9

DEFAULT_KEYS = ("general.architecture", "general.basename", "general.name",
                "general.size_label", "general.finetune")


class _Reader:
    def __init__(self, f):
        self.f = f

    def scalar(self, t):
        fmt = _SCALAR.get(t)
        if fmt is None:
            raise ValueError(f"unknown GGUF value type {t}")
        return struct.unpack(fmt, self.f.read(struct.calcsize(fmt)))[0]

    def string(self):
        (n,) = struct.unpack("<Q", self.f.read(8))
        return self.f.read(n).decode("utf-8", "replace")

    def value(self, t):
        if t == _STR:
            return self.string()
        if t == _ARR:
            et, = struct.unpack("<I", self.f.read(4))
            (n,) = struct.unpack("<Q", self.f.read(8))
            return [self.value(et) for _ in range(n)]
        return self.scalar(t)


def read_gguf_meta(path, keys=DEFAULT_KEYS, max_kv=None):
    """{key: value} for the requested keys.

    Never raises. Returns whatever it managed to parse, so a truncated file
    yields the keys it got to rather than nothing -- discarding a value already
    read cleanly would be worse than keeping it. A missing file, a non-GGUF file
    or an unreadable one yields {}.
    """
    want = set(keys)
    out = {}
    try:
        with open(path, "rb") as f:
            magic, _v = struct.unpack("<II", f.read(8))
            if magic != _MAGIC:
                return {}
            _tensors, kv_count = struct.unpack("<QQ", f.read(16))
            if max_kv:
                kv_count = min(kv_count, max_kv)
            r = _Reader(f)
            for _ in range(kv_count):
                k = r.string()
                (t,) = struct.unpack("<I", f.read(4))
                if k in want:
                    out[k] = r.value(t)
                    if want <= set(out):
                        break     # general.* leads the file; skip the vocab
                else:
                    r.value(t)
    except (OSError, struct.error, ValueError, MemoryError):
        return out
    return out


def gguf_arch(path):
    """The GGUF's architecture string, or None."""
    v = read_gguf_meta(path).get("general.architecture")
    return v if isinstance(v, str) and v else None


# ---------------------------------------------------------------------------
# config -> paths -> arch
# ---------------------------------------------------------------------------
def config_model_paths(config_path):
    """{model key: main GGUF path} from a llama-swap config.

    The value must look like a path: without that guard a prose comment
    containing the literal `--model` is scraped as a filename (the same bug
    build_model_config.py documents).
    """
    out = {}
    try:
        text = open(os.path.expanduser(config_path)).read()
    except OSError:
        return out
    for block in re.split(r"\n(?=  [a-zA-Z0-9_.-]+:\n)", text):
        m = re.match(r"  ([a-zA-Z0-9_.-]+):", block)
        if not m:
            continue
        paths = [p for p in re.findall(r"(?:-m|--model|--mmproj)\s+(\S+)", block)
                 if "/" in p and "--mmproj" not in p]
        if paths:
            out[m.group(1)] = paths[0]
    return out


def arch_map(config_path, only=None):
    """{model key: architecture} for keys that resolve to a readable GGUF."""
    out = {}
    for key, path in config_model_paths(config_path).items():
        if only is not None and key not in only:
            continue
        a = gguf_arch(path)
        if a:
            out[key] = a
    return out


def remote_arch_map(ids, ssh_host=MBP_SSH, config=MBP_CONFIG, timeout=180):
    """Architectures for another box's models, read by piping THIS FILE over ssh.

    Nothing has to be installed on the far side beyond python3. Returns {} on any
    failure -- a box that is asleep must not break a push.
    """
    ids = [i for i in ids if i]
    if not ids:
        return {}
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", ssh_host,
           "/usr/bin/python3", "-", "--emit-arch-map", config,
           "--only", ",".join(ids)]
    try:
        with open(os.path.abspath(__file__)) as self_src:
            proc = subprocess.run(cmd, stdin=self_src, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=timeout)
        if proc.returncode != 0:
            return {}
        return json.loads(proc.stdout.decode() or "{}")
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}


# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------
def load_cache():
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(dict(sorted(cache.items())), f, indent=2)
        f.write("\n")


def resolve_base_arch(ids, verbose=True, use_ssh=True):
    """{model id: architecture} for as many ids as are verifiable.

    Cached: architectures do not change, and reading them costs I/O over SMB or
    ssh. Only ids that are genuinely not reachable end up absent, and an absent
    value means 'not verified', never 'guessed'.
    """
    cache = load_cache()
    missing = [i for i in ids if i and i not in cache]
    if missing:
        studio = [i for i in missing if i.startswith("ms-")]
        mbp = [i for i in missing if i.startswith("mb-")]
        if studio:
            cache.update(arch_map(STUDIO_CONFIG, only=set(studio)))
        if mbp and use_ssh:
            cache.update(remote_arch_map(mbp))
        # Ids with no machine prefix live in no config (MLX/oMLX runs), so there
        # is nothing to read and no way to verify them.
        save_cache(cache)
    if verbose and missing:
        found = [i for i in missing if i in cache]
        print(f"    base architecture: {len(found)}/{len(missing)} newly resolved "
              f"({len(cache)} cached)")
    return {i: cache[i] for i in ids if i in cache}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit-arch-map", metavar="CONFIG",
                    help="print {model key: architecture} JSON and exit")
    ap.add_argument("--only", help="comma-separated model keys to restrict to")
    ap.add_argument("--families", nargs="*", help="print the family of these ids")
    args = ap.parse_args()

    if args.emit_arch_map:
        only = set(args.only.split(",")) if args.only else None
        print(json.dumps(arch_map(args.emit_arch_map, only=only)))
        return 0
    if args.families is not None:
        for i in args.families:
            print(f"{i}\t{model_family(i) or '—'}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
