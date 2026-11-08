---
name: model-cold-archive
description: Use when cold-archiving models to NAS.
---
# Model Cold Archive Workflow

This skill encapsulates the procedure and pitfalls for performing a verified, weights-only archival of LLM models to the NAS, prioritizing cold storage over local inference readiness.

## Procedure

1.  **Identify Source:** Determine if the model source is Hugging Face (HF) or ModelScope (MS).
    *   *HF:* The primary mechanism is the `nas-archive.sh add hf:[owner]/model [filename]` command.
    *   *MS:* Requires an isolated `uv` environment (`uv run --with gguf python -c ...`) and the use of the `modelscope-hub` CLI entrypoint for discovery/download, then queueing via the archive script.
2.  **Determine Target Artifact:** Specify the exact quantization/version (e.g., `MTP-v2`, `Q4_K_M`).
    *   **Pitfall:** Model MTP status is a *quant property*, not a base model feature. Upstream vendors may list "MTP" in the name, but the head must be grafted onto a non-MTP base (e.g., Qwen3.6-35B-A3B) and then re-quantized. Verify MTP presence by checking for specific tensor names (e.g., `blk.40.nextn.*`) within the GGUF file structure.
3.  **Verify Upstream Availability (The Gating Check):** Before queuing, verify the model's existence and LFS status against the source API, as repository file lists are often misleading.
    *   **Pitfall:** The HF API's `tree` endpoint frequently returns a 200 OK even for gated/private models because the request is authenticated. Always verify gate status via an *unauthenticated* sweep or a direct resource check before trusting the listing.
4.  **Enforce Weights-Only Extraction:** To prevent archival of configuration and tokenizer bloat, the download mechanism must be configured to strip non-weight files.
    *   **Pitfall:** Even a "weights-only" download will leave substantial bookkeeping in the local HF cache (`.cache`). Ensure the archive script's verification phase validates against the SHA256 hash of *only* the weight file, ignoring cache bloat.
5.  **Enqueue and Monitor:** Use the archive script to add the model to the queue and monitor the `queue.tsv` manifest. The verification phase (SHA256 validation against upstream) runs in the background.

## Source-Specific Quirks

*   **ModelScope (MS):** Requires an isolated `uv` environment (`uv run --with gguf python -c ...`) because the CLI entrypoint is often external to the main package. The archive script's ModelScope implementation must use the MS `files` positional argument syntax (`modelscope-hub files [model] [file]`).
*   **Hugging Face (HF):** The archive script uses a wrapper around `huggingface-cli`. Ensure the CLI is configured to use the correct `cache_dir` path for the archive process to prevent it from cluttering the primary `~/models/.hf` folder.

## Pitfalls Summary

*   **Pitfall: APFS snapshots pin deleted blocks — `df` will lie to you.** Deleting 46.7 GiB of model files changed `df` by ZERO. The files were gone, `hf cache rm` reported `freed=25.1G`, and the cache `du` dropped 214G -> 191G — but the volume stayed at 19Gi free. Two purgeable local Time Machine snapshots (2026-10-27, 2026-10-28) still referenced the deleted blocks. Purging them (`tmutil deletelocalsnapshots <date>`) released **61 GiB** in one step: 19Gi -> 80Gi free. On APFS, deleting a file that a snapshot references frees nothing until the snapshot goes. **Always run `tmutil listlocalsnapshots /` before concluding a deletion reclaimed no space.**
*   **Pitfall: Retiring a model from llama-swap needs TWO edits.** Removing the `models:` block entry alone makes the daemon's hot-reload fail with `no model config for "ms-<name>"` — because the model is still listed in a `groups.<group>.members` list. Remove it from every group too. Verify with `llama-swap --config <path> --validate` before reloading; the daemon runs with `--watch-config` (via `~/.hermes/llama-swap/run.sh`) so the change hot-reloads without a restart.
*   **Pitfall: Benchmarking NAS throughput with zeros.** `dd if=/dev/zero` to the SMB mount measured 77 MB/s, but real (incompressible) model weights move at **~5 MiB/s** — 15x slower. SSH and SMB measure the same, so it is the link, not the protocol. The zeros result compresses or dedupes somewhere in the path and is meaningless for capacity planning. Always benchmark with `/dev/urandom` before quoting a transfer time.
*   **Pitfall: The Studio-NAS link is not LAN-local.** The Studio sits on 192.168.4.x and reaches the NAS at 192.168.5.60 via the 192.168.4.1 gateway with 52-83 ms RTT. The tailnet IP (100.102.22.38) shows the SAME latency — it is not a shortcut to a local path. Do not assume bulk archives are fast because the NAS is in the house.
*   **Pitfall: `nas-archive.sh` copies, it does not move.** The local file is never deleted by `run`; removing the local copy is a separate, explicit step. That is deliberate — cold-archiving is backup-first, prune-second. See the script's own comment block.
*   **Pitfall: A cold-archived model may still be referenced by a live serving config.** Before removing the local copy, grep every serving config for the path. `llama-swap` entries point at absolute paths under `~/models/gguf/`; leaving one pointing at a deleted file makes the model fail to load at request time, not at config time. Also check Unsloth Studio's `~/.unsloth/studio/cache/hub-state/manifests/` — those point at the HF **cache** path, not `~/models`, so removing the cache copy makes Studio re-download.
*   **Pitfall: "Registered" is not "used."** A model can have a llama-swap entry, pass health checks, and still have served zero real sessions. Check `session_model_usage` in `~/.hermes/state.db` for actual call volume, and distinguish health-check hits from real request traffic.
*   **Pitfall: Relying on filename suffixes.** The 'MTP' suffix in a filename is a *label* of the quantizer, not a guarantee of the underlying model architecture. Verify the presence of `nextn` tensors to confirm the MTP graft.
*   **Pitfall: Misidentifying the core problem.** A '401 Unauthorized' during an initial sweep may be a transient API issue, not a hard gate. Perform a targeted, unauthenticated check to resolve the actual gating status before concluding the artifact is unavailable.
*   **Pitfall: Ignoring bookkeeping.** A file's hash integrity is only as good as the extraction process. Ensure the workflow validates the file's SHA256 against the source before the file is considered "archived," not just before it's copied to the NAS.

## Tooling and Scripts
The primary entry point for this workflow is the `nas-archive.sh` script in `~/scripts/`.

```bash
# Add a model to the queue
~/.hermes/scripts/nas-archive.sh add hf:[owner]/model [filename]
# Check queue status
~/.hermes/scripts/nas-archive.sh status
```
