---
name: llama-swap-model-canonicalization
description: Move GGUF model from HF cache to canonical path.
---
# Llama-Swap Model Canonicalization

Use when a model file is found outside the canonical storage location (`~/models/gguf/`) and must be moved, verified, and reconfigured for correct serving via llama-swap.

This procedure ensures that models are stored as real files within the designated, backed-up directory structure, rather than via transient symlinks pointing to temporary caches.

## Procedure

1.  **Verify and Identify:**
    *   Locate the model file and its source (e.g., cache, external mount).
    *   Determine the canonical filename by cross-referencing upstream documentation (Pitfall: Do not use temporary naming conventions or assume proprietary prefixes like 'UD-' unless explicitly verified by the provider).
    *   Perform a checksum (SHA256) on both the source and the intended destination copy.

2.  **Move and Verify Integrity:**
    *   Execute a secure copy (`cp`) to the canonical path: `~/models/gguf/path/to/model/`.
    *   Verify the copied file's integrity: `shasum -a 256 <destination_path>`.
    *   Verify file size integrity against upstream records.

3.  **Clean Up Links:**
    *   Remove the old symlink pointing to the cache: `rm <symlink_path>`.
    *   Confirm no other system files or snapshot entries still point to the old cache location (e.g., search for `-lname '*old_path*'` in relevant directories).

4.  **Update Configuration:**
    *   Locate the model entry in the `llama-swap` configuration (e.g., `~/.hermes/llama-swap/config.yaml`).
    *   Patch the configuration to point the model identifier to the new canonical path.
    *   Update the model description to reflect the canonical status and record the migration details (SHA256, date).

5.  **Functional Load Test:**
    *   Trigger an on-demand load or a simple inference query using the model's identifier.
    *   Confirm the service responds with an HTTP 200 and the model path resolves to the canonical `~/models/gguf/...` location.

## Pitfalls & Lessons

*   **Symlink Trap:** A symlink pointing to an active, superseded cache directory (`~/.hf/hub/models--.../`) may appear "active" but fails if that cache directory is pruned or moved, leading to silent serving failures. Always treat links in cache directories as potentially volatile.
*   **Naming Conventions:** Rely strictly on upstream naming conventions. Incorrect naming conventions in custom config can cause routing failures even if the file exists.
*   **Spec flags are not copy-paste:** Never add `--spec-type draft-mtp` because a sibling entry has it. Check the GGUF header for nextn/MTP tensors first — quantisation can drop the head, and the flag is silently inert without it. See `references/config-authoring.md`.

## References

*   `references/config-authoring.md` — verifying headers, host-scoped ids, ctx floor, `--jinja`, and load verification when adding a model entry
