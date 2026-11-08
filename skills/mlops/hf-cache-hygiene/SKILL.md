---
name: hf-cache-hygiene
description: "Audit and prune HF cache to reclaim disk space."
version: 0.1.0
author: Hermes
license: MIT
tags: [huggingface, cache, disk, maintenance, mlops]
platforms: [macos]
metadata:
  hermes:
    tags: [HuggingFace, Cache, Disk, Maintenance]
---

# Hugging Face Cache Hygiene

Audit and prune the Hugging Face cache store to reclaim disk space from orphaned blobs, incomplete downloads, and detached revisions. Does NOT touch the curated model tree at `~/models` — `hf cache` commands never modify it.

**Resolve the store path per host; never assume it.** On the Studio `HF_HOME` is *deliberately unset* (`~/.zshenv` line 1: "HF_HOME deliberately unset: ~/.cache/huggingface"), so the real store is `~/.cache/huggingface/hub`. `~/.hf` exists but is an 8 KB stub holding only marker files — auditing there finds nothing and reports the cache as empty. On the MacBook `HF_HOME=/Users/prasta/.hf`.

**Cache hygiene is not a disk-pressure lever when the cache is clean.** A fully-referenced 230 GB cache prunes to zero. `hf cache prune` reporting "Nothing to prune" is a real, common result — not a broken check.

## When to Use

- Disk is tight and you need to reclaim space
- After a failed or interrupted `hf download`
- As part of any disk-pressure investigation
- When `du -sh <store>` is much larger than `hf cache list` reports
- Studio's Data volume has run 92-96% full — check the Studio store there too

## Prerequisites

- `hf` CLI installed (`curl -LsSf https://hf.co/cli/install.sh | bash -s`)
- On Studio: the store is `~/.cache/huggingface/hub` (HF_HOME deliberately unset in `~/.zshenv`; the unsloth plist may still set it). Check which host you're on before acting.
- On MacBook: `HF_HOME=/Users/prasta/.hf`

## How to Run

Invoke all commands through the `terminal` tool. Always run `--dry-run` first, report what will be deleted, and get explicit confirmation before running `-y`.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `hf cache list` | List repos, sizes, last_accessed |
| `hf cache list --show-warnings` | Also show inconsistencies (missing blobs, missing snapshots) |
| `hf cache prune --dry-run` | Preview what prune will delete |
| `hf cache prune -y` | Delete detached revisions, incomplete downloads, unreferenced blobs |
| `hf cache rm <repo>` | Remove a specific repo |
| `hf cache verify` | Checksum a repo revision |

## Procedure

0. **Decide which lever applies.** If `hf cache prune --dry-run` says "Nothing to prune", the cache is STALE (referenced but unwanted), not dirty. Go straight to per-repo `hf cache rm --dry-run` on the candidates. Do not waste time trying to make prune work.

1. **Check which host you're on and resolve the store path.** Run `echo $HF_HOME` and size the candidates (`du -sh ~/.cache/huggingface/hub ~/.hf`) through `terminal`, then trust whichever is real. An empty `~/.hf` on the Studio is expected, not a broken install.

2. **Compare total size vs listed size.** Run `du -sh <store>` and `hf cache list` through `terminal`. A large gap means orphaned blobs.

3. **Run dry-run prune.** `hf cache prune --dry-run` through `terminal`. Report the count and total size of what will be deleted to the user. Get explicit OK before proceeding.

4. **Execute prune.** `hf cache prune -y` through `terminal`. This removes detached revisions, incomplete downloads, AND unreferenced shared blobs.

5. **Check for broken shells.** `hf cache list --show-warnings` through `terminal`. Repos with broken symlinks or no snapshots dir are skipped ("Repo ignored"). List them and ask before deleting the folders manually.

6. **Verify.** Re-run `hf cache list --show-warnings` and confirm the repo list and sizes are unchanged. Confirm `~/models` is untouched.

### Per-repo reclaim (the stale-cache path)

When prune finds nothing:

7. **Pick candidates from real evidence, not from "looks big".** Grep for each candidate across: llama-swap `config.yaml`, the activity DB, every skill script, every ComfyUI workflow JSON, Unsloth Studio's `~/.unsloth/studio/cache/hub-state/manifests/`, and PNG metadata in `~/.hermes/outputs/`. A repo named by a manifest is LIVE for that tool even if the tool is currently down.

8. **Dry-run the removal.** `hf cache rm --dry-run model/<org>/<repo>` (with the `model/` prefix) per candidate. Report nominal totals.

9. **Compute the REAL reclaim** before promising numbers — see the Pitfalls section for the inode method. Quote the real figure, and state the nominal one alongside it.

10. **Get explicit sign-off, then remove.** `hf cache rm -y model/<org>/<repo> ...`. Re-check `df -h /System/Volumes/Data` and `du -sh <store>` after.

11. **Re-verify with `hf cache list --show-warnings`** that no live repo was collaterally damaged, and that `~/models` is untouched.

## Pitfalls

- `hf cache scan` NO LONGER EXISTS. Do not use it.
- **`hf cache prune` finds NOTHING in a stale-but-referenced cache.** Prune only removes detached revisions, incomplete downloads, and unreferenced blobs. If every repo still has a valid `snapshots/` dir pointing at its blobs, prune reports "Nothing to prune" — even when 100+ GB of upstream source weights are dead weight. That is not a broken check; it is the signal that the reclaim lever is `hf cache rm <repo>` per repo, not a global prune. Verified 2026-10-29 on the Studio: a 214G cache pruned to zero while 136G of it was removable source weights.
- **`hf cache rm` needs the `model/` prefix.** `hf cache rm Qwen/Qwen-Image-2.1-Turbo` fails with "Could not find in cache"; `hf cache rm model/Qwen/Qwen-Image-2.1-Turbo` works. The prefix selects the cache type.
- **`du -sh <repo-dir>` UNDERCOUNTS badly.** Repo payload lives in a SHARED blob store (`hub/blobs/<xx>/<hash>`); the repo dir holds symlinks. A repo whose `du` reads 4K can hold 30 GB. Count real payload by resolving symlinks with `os.path.realpath()` and de-duplicating by `(st_dev, st_ino)`. Authoritative per-repo numbers come from `hf cache rm --dry-run`.
- **Matching name + size is NOT evidence of duplication.** HF hardlinks some blobs to `~/models` instead of copying them on the same filesystem. An apparent "17 GB duplicate" can be ONE inode with `nlink=2`, and deleting either path frees nothing. Compare inodes (`stat -f "inode=%i links=%l"`) before claiming a reclaim. Matching `sha256` proves identical content, never independent storage.
- **`hf cache rm` on a hardlinked repo reclaims only the non-linked extras.** The weights stay on disk via the `~/models` link; only files that were copied rather than linked (e.g. an `mmproj`) actually free space.
- **`hf cache rm --dry-run` nominal size OVERSTATES real reclaim** — it counts a hardlinked weight as if deleting it freed the bytes. Build the real number yourself: for each repo, sum unique `(dev, inode)` payload sizes, then subtract any file whose inode also appears outside the cache. Verified 2026-10-29: nominal 136.1G vs 127.4 GiB real across 11 repos.
- **Unsloth Studio's hub-state is a registration, not evidence of use.** `~/.unsloth/studio/cache/hub-state/` holds both `manifests/` (live registrations) and `cancelled/` (abandoned download attempts), and the SAME repo can appear under both — so presence is not proof the weights are wanted or even loadable. Rule a candidate out on capability instead: an `unsloth/*-FP8` image repo cannot load on Apple Silicon at all (MPS rejects fp8 dtypes), which made it the one clean deletion on 2026-11-01 (25.9G nominal -> 24 GiB freed, 103 -> 127 GiB free).
- **A byte-identical STANDALONE copy is different from a hardlink.** `unsloth/flint-GGUF` had the same GGUF at both the cache path and `~/models/gguf/unsloth/flint-GGUF/` as two separate inodes — deleting the cache copy freed the full 23.3 GB with no effect on the serving copy. Check `nlink` AND inode equality before calling a pair a "duplicate that frees nothing".
- **A deleted file on APFS frees NOTHING until local snapshots are purged.** Deleting 46.7 GB of models moved `df` by zero. The bytes were pinned by two purgeable local Time Machine snapshots (2026-10-27, 2026-10-28) that still referenced the deleted blocks. `tmutil deletelocalsnapshots <date>` released **61 GB** instantly — 19Gi -> 80Gi free, 98% -> 91%. This is the single biggest lever on this box and it is invisible until a deletion actually happens. **Always run `tmutil listlocalsnapshots /` before concluding a deletion freed nothing.**
- **A cache repo dir can be 16K while holding 23 GB.** Payload lives in the shared store `hub/blobs/<xx>/<hash>`; the repo holds symlinks. `du -sh <repo-dir>` measures the symlink, not the target. To find the real bytes, resolve the snapshot symlink with `realpath` and stat THAT. To check whether a blob is shared, use `find <hub> -samefile <blob>` — if the only hit is the blob itself, removing the repo frees the full payload.
- **`find ... -exec du -h {} \;` on a `.gguf` in a snapshot reports 0B and means NOTHING.** The file is a symlink, and `du` does not follow symlinks. So do not conclude "LFS pointer stub, weights absent" from a 0B reading — that reading is the link's own inode. Cross-check against `hf cache list`, which reports the real repo size (it read 4.2G while the finder said 0B). Confirm with `stat -f "size=%z inode=%i links=%l" $(realpath <snapshot-file>)` before writing "weights absent" into a config, a report, or a skill. Done once and it cost a reverted commit.
- **When a clean cache prunes to zero, the lever is model curation, not hygiene.** See `fleet-catalog` (what is served) and `model-cold-archive` (move, don't delete). The real reclaim in a clean cache is redundant format variants of one model family — on the Studio, four `Qwen-Image-2.1` variants totalled 91 GB.
- The plain `list` output only mentions incomplete downloads. The real prune also deletes unreferenced shared blobs — the summary understates what prune will do.
- Repos with broken symlinks or no snapshots dir are skipped by both `list` and `prune`. They are empty shells that must be removed manually.
- If `hf download` stalls on Studio, use `HF_HUB_DISABLE_XET=1`. Stalled downloads are one source of incomplete blobs.
- `hf cache` commands NEVER touch `~/models`. Do not "clean" the curated model tree as part of cache hygiene.

## Verification

After pruning, run `hf cache list --show-warnings` through `terminal` and confirm:
- The repo list and sizes match the pre-prune state
- No new warnings appear
- `~/models` is untouched
