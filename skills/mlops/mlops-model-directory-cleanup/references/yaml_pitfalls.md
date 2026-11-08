# YAML Configuration Pitfalls: the user's configuration style

## The problem

`llama-swap/config.yaml` on these boxes has grown to carry **50-95 lines of
hand-written measured research** per file: throughput tables, MTP acceptance
rates, rejected-experiment notes, architecture caveats. That prose is the
record of *why* the flags are what they are, and it has already prevented real
mistakes:

- The **Studio** header recommends `--spec-type draft-mtp,ngram-simple --spec-draft-n-max 1`.
- The **MacBook** header records that this exact recipe measured **-70%, -36% and -14%** on its own models, and warns explicitly against porting it.

A `yaml.safe_load()` -> `yaml.safe_dump()` round-trip deletes every one of those
lines, silently. There is no error and no diff warning — the file still parses and
still serves models. You just lose the knowledge.

## The solution: use the tested helper

`safe_config_edit.py` (next to this file) implements the whole contract. Copy it to
the target host and call it rather than rewriting the logic:

```python
import sys; sys.path.insert(0, "/tmp")
import safe_config_edit as sce

sce.add_model(path, mid, name, description, cmd, group="ondemand", ttl=900)
sce.audit(path)          # read-only: orphans + missing paths
```

It parses only to read and validate, mutates the raw text, and refuses to write
unless every invariant holds.

## Why not hand-roll it each time

Every trap below was hit in a single session, each one costing a failed run:

| Trap | Consequence if you get it wrong |
|---|---|
| Members-list style differs per host (block vs flow) | Silent no-match; the regex "succeeds" and edits nothing |
| `re.search(r"members:\[(.*?)\]")` — `group(1)` excludes the `]` | Appending your own `]` gives `]]` and a parse error |
| Flow list may not end with a trailing comma | Malformed YAML, or a lost member |
| Matching a model id as bare substring | False positive when the id appears inside a description |
| `os.path.exists()` on APFS | Case-mismatched paths report as existing |
| Reading a model id from the filename | Wrong flags for Mamba hybrids and MTP-less quants | The Mamba-2 Hybrid MoE architecture (like Nemotron 3.5) requires parsing GGUF headers (`next n tensors` count, specific architecture flags) before enabling `draft-mtp`. Filename-based heuristics fail to detect if the model carries an MTP head, which is critical for viability. |

The first three are pure YAML mechanics and have nothing to do with judgment —
which is exactly why they belong in tested code rather than in the head of
whoever runs the next edit.

## Invariants the helper enforces before writing

1. The edited buffer parses.
2. The target key exists in `models:`; counts are exactly `before + 1`.
3. The target group grew by exactly one member, **last**, and its existing member
   order is unchanged.
4. `swap` / `exclusive` / `persistent` on the target group are unchanged.
5. Every **non-target** model block is byte-identical to the original.
6. Every other group is byte-identical.
7. No top-level key other than `models` / `groups` changed.
8. `--model` and `--mmproj` paths exist on disk.
9. The id is not already present as a real key (catches a partial prior write).
10. Comment count did not decrease.
11. A dated `.bak` is written first.

Any failure aborts with the file untouched. Verified against both real box
layouts: a block-style add and a flow-style add both succeed, and six negative
cases (missing model path, missing mmproj, duplicate id, unknown group,
corrupted source, bad prose match) each abort leaving the file byte-identical.