#!/usr/bin/env python3
"""Tests for model_family.py -- the id classifier and the stdlib GGUF reader.

Run after ANY change to FAMILY_HINTS or to the GGUF parser:
    python3 test_model_family.py
"""
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import model_family as F  # noqa: E402

FAILS = []


def eq(got, want, label):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


# ---------------------------------------------------------------------------
# family classification
# ---------------------------------------------------------------------------
# The machine prefix is a HOST marker, so the same model on either box has to
# classify identically.
eq(F.model_family("ms-qwen3.6-35b-a3b"), "qwen", "ms qwen")
eq(F.model_family("mb-qwen3.6-35b-a3b"), "qwen", "mb qwen (same family)")
eq(F.model_family("ms-qwen36-35b-a3b"), "qwen", "qwen36 no-dot spelling")
eq(F.model_family("Qwen3.8-27B-MLX-4bit"), "qwen", "bare unprefixed id")
eq(F.model_family("Swift-Qwen3.8-27b-oQ4e-mtp"), "qwen", "variant prefix still qwen")

# Id-grounded policy: a distinct line in the id gets a distinct family, even
# where the base architecture (a separate column) says otherwise.
for mid, fam in [("ms-qwythos-9b-v2", "qwythos"),
                 ("ms-qwopus3.8-27b-flash", "qwopus"),
                 ("ms-hermes-4.3-36b", "hermes"),
                 ("ms-kat-coder-v2.5", "kat"),
                 ("ms-nuextract3", "nuextract"),
                 ("ms-muse-glimmer-30b", "muse"),
                 ("ms-trinity-26b-a3b", "trinity")]:
    eq(F.model_family(mid), fam, f"standalone {fam}")

eq(F.model_family("ms-devstral-24b"), "devstral", "devstral is its own line")
eq(F.model_family("ms-ministral-3-3b"), "ministral", "ministral is its own line")
eq(F.model_family("ms-gpt-oss-20b"), "gpt-oss", "hyphenated family")
eq(F.model_family("mb-smollm3-3b"), "smollm", "no separator before version")

# Honest blanks: nothing matched means no label, never a guess.
eq(F.model_family("sushi"), None, "sushi is a runtime build, not a model")
eq(F.model_family(""), None, "empty id")


# ---------------------------------------------------------------------------
# GGUF reader (synthetic files -- no model weights needed)
# ---------------------------------------------------------------------------
def build_gguf(entries, magic=0x46554747, version=3, tensors=0, count=None):
    """Minimal GGUF header: magic, version, tensor count, kv count, then pairs."""
    out = struct.pack("<II", magic, version)
    out += struct.pack("<QQ", tensors, len(entries) if count is None else count)
    for key, vtype, payload in entries:
        kb = key.encode()
        out += struct.pack("<Q", len(kb)) + kb + struct.pack("<I", vtype)
        if vtype == 8:                       # string
            pb = payload.encode()
            out += struct.pack("<Q", len(pb)) + pb
        else:
            out += payload
    return out


def write(tmp, name, data):
    p = os.path.join(tmp, name)
    with open(p, "wb") as f:
        f.write(data.encode() if isinstance(data, str) else data)
    return p


with tempfile.TemporaryDirectory() as tmp:
    # architecture + basename, then a large array the reader should never reach
    big = struct.pack("<I", 8) + struct.pack("<Q", 4000) + b"".join(
        struct.pack("<Q", 3) + b"tok" for _ in range(4000))
    good = build_gguf([
        ("general.architecture", 8, "qwen35moe"),
        ("general.basename", 8, "Qwen3.6-35B-A3B"),
        ("tokenizer.ggml.tokens", 9, big),
        ("general.file_type", 4, struct.pack("<I", 15)),
    ])
    p = write(tmp, "good.gguf", good)
    m = F.read_gguf_meta(p)
    eq(m.get("general.architecture"), "qwen35moe", "arch parsed")
    eq(m.get("general.basename"), "Qwen3.6-35B-A3B", "basename parsed")
    eq(F.gguf_arch(p), "qwen35moe", "gguf_arch")

    # Native ints/floats/bools interleaved must not desync the reader.
    mixed = build_gguf([
        ("general.architecture", 8, "llama"),
        ("x.i", 5, struct.pack("<i", -7)),
        ("x.f", 6, struct.pack("<f", 0.5)),
        ("x.b", 7, struct.pack("<?", True)),
        ("x.u64", 10, struct.pack("<Q", 123456789)),
    ])
    eq(F.gguf_arch(write(tmp, "mixed.gguf", mixed)), "llama", "scalar types skipped cleanly")

    # Failure modes must return a value, not raise: a missing file is normal
    # for a retired model.
    eq(F.read_gguf_meta(os.path.join(tmp, "nope.gguf")), {}, "missing file -> {}")
    eq(F.gguf_arch(write(tmp, "notgguf.bin", b"hello world not a gguf")), None,
       "bad magic -> None")
    trunc = write(tmp, "trunc.gguf", good[:24])
    eq(F.gguf_arch(trunc), None, "truncated -> None")
    eq(F.gguf_arch(write(tmp, "empty.gguf", b"")), None, "empty file -> None")

    # A file whose declared KV count overruns the data must not raise. It
    # returns whatever it managed to parse -- discarding a value it already read
    # cleanly would be worse than keeping it.
    over = write(tmp, "over.gguf", build_gguf(
        [("general.architecture", 8, "gemma4")], count=99))
    eq(F.gguf_arch(over), "gemma4", "kv count overruns -> partial result, no raise")


# ---------------------------------------------------------------------------
# config scraping
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    cfg = write(tmp, "config.yaml", """models:
  ms-alpha:
    cmd: |
      llama-server -m /models/alpha.gguf --mmproj /models/alpha-mmproj.gguf
  ms-nopath:
    cmd: |
      llama-server --host 0.0.0.0
  ms-comment:
    cmd: |
      llama-server -m /models/beta.gguf
    note: this is --model wired to a prose comment
""")
    paths = F.config_model_paths(cfg)
    eq(paths.get("ms-alpha"), "/models/alpha.gguf", "main gguf, not mmproj")
    eq("ms-nopath" in paths, False, "model with no -m excluded")
    eq(paths.get("ms-comment"), "/models/beta.gguf", "prose --model not scraped")

if FAILS:
    print(f"FAIL ({len(FAILS)})")
    for f in FAILS:
        print("  " + f)
    sys.exit(1)
print("all model_family tests passed")
