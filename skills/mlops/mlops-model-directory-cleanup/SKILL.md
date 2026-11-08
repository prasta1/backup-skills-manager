---
name: mlops-model-directory-cleanup
description: Standardize model names and sync llama-swap config.
---

## 🛠️ Procedure: Model and Config Synchronization

1.  **Audit and Identify Inconsistency:** Use `search_files(target="files", pattern="**/models/gguf")` to locate models. Visually compare directory names against expected conventions (e.g., remove redundant prefixes like `NVIDIA-` to enforce user's preference for clean, upstream-like names).
2.  **Execute Directory Rename:** Perform the rename via SSH, ensuring all contained files are moved with the parent directory.
    *   `ssh macbook 'mv /path/to/old/DirName /path/to/new/DirName'`
3.  **Update `llama-swap` Configuration (Atomic, Style-Aware):**
    *   **Use the tested helper, not a fresh script.** `references/safe_config_edit.py` implements the whole contract below and is verified against both real box layouts. Copy it to the target host and call `add_model()` / `audit()` rather than rewriting the logic each time — hand-rolled versions have repeatedly failed on the same two traps (members-list style, and appending a bracket that already exists).
    *   Read the current `config.yaml` into a memory buffer. **Never use a plain regex/find-and-replace**, and never `yaml.safe_load()` → `yaml.safe_dump()`: the file carries hand-written benchmark and architecture notes that a re-dump silently deletes.
    *   Parse with `yaml.safe_load()` only to read and validate; do all mutation as text surgery on the raw buffer.
    *   Perform the update as one atomic script run that validates before writing, then copies to a dated `.bak`.
    *   **Validate before writing** (the helper asserts all of these): the edited buffer parses; target key exists; model counts and group sizes are as expected; every NON-target model block is byte-identical; the target group keeps its existing member order and its `swap`/`exclusive`/`persistent` flags.
4.  **Rehome Dead/Orphaned Models:** If the model was solely part of a dead service or interpreter group, rehome it into a live service group (like `ondemand`) before reloading the service.
    *   *Pitfall:* A model in `models:` but not assigned to a group will not be served by `llama-swap` and must be placed in a group like `ondemand` to prevent it from becoming an orphaned asset.
5.  **Clean Stale Metadata:** Scan the model descriptions within the config for references to the removed component (e.g., `mrmr-interpreter`) and strip them from the descriptions to maintain configuration purity.
6.  **Verify Service State:**
    *   Run `llama-swap` (hot-reloads are preferred if possible).
    *   Check the service status using `curl http://100.68.81.83:8999/v1/models` to ensure all models are listed and no paths are reported as missing.
    *   **A listing is not proof the model works.** Live-fire each newly wired model with a real `/v1/chat/completions` call and confirm the expected content comes back. A model can appear in `/v1/models` while failing to load.
    *   Confirm no orphans remain: every id in `models:` belongs to at least one group, and no `--model`/`--mmproj` path is missing on disk. `safe_config_edit.audit()` reports both.

## ⚠️ Pitfalls and Rules
*   **Absolute Path Dependency:** Always construct and use absolute file paths for all file system operations within the configuration, never relative paths, to prevent breakage during moves or symlink changes.
*   **Targeted Editing over Re-dump:** The configuration contains hand-written benchmarks and architecture notes. Never use `yaml.safe_load()` followed by `yaml.safe_dump()`. This will silently strip all prose and measured data. Always use targeted string/list manipulation (e.g., regex-based insertion into list bodies) to update values while preserving all existing comments and notes. This is critical for maintaining the integrity of performance benchmarks.
*   **Members-List Style Differs Per Host — Detect, Never Assume:** The Studio uses block style (`members:` then `- id` lines); the MacBook uses flow style (`members: [id, id]`). Both are valid YAML and parse identically, so guessing wrong produces a silent no-match, not an error. Detect the style at edit time.
*   **Regex Group Excludes the Closing Bracket:** In a flow-style match, `members:\[(.*?)\]`, `group(1)` stops *before* the `]`, so `body[end(1):]` already contains it. Appending your own `]` yields `]]` and a parse error. A flow list also may or may not end with a trailing comma before the bracket — handle both.
*   **Never Port Flags Between Hosts:** The Studio recommends `--spec-type draft-mtp,ngram-simple --spec-draft-n-max 1`; the MacBook header records that this exact recipe measured -70%, -36% and -14% there. The prose in each config is the evidence for that box's settings. Read the target host's header before choosing flags, and measure on that host.
*   **Match Anchors Verbatim, and Guard Against Prose:** Assert each anchor string is present exactly before replacing, and abort rather than proceed on a miss. When checking whether a model id already exists, match a real YAML *key* (`^\s{2}<id>\b`) — a bare substring search false-positives when the id appears inside a description.
*   **Case-Sensitive Filesystem Verification:** APFS is case-insensitive by default, so `os.path.exists(".../nemotron-3-nano-omni...")` returns True for a directory actually named `Nemotron-3-Nano-Omni-...`. Stale manifest rows and mis-cased paths hide behind this. Verify by walking the tree and comparing `os.listdir()` entries exactly.
*   **Verify Renames by Hash, Not by Exit Code:** After `mv`, compare inode, size, and SHA256 before/after. Same-volume renames are instant and near-invisibly wrong if they hit the wrong target.
*   **Read GGUF Headers Before Writing Flags (Architecture-Aware):** Do not infer architecture from the filename. Parse the header (e.g., `general.architecture`, `*.context_length`, `*.next n tensors`, and count `next n` tensors). This is critical because Mamba-style hybrids (like Nemotron 3.5) may possess MTP heads even if they aren't plain transformers. The presence of `next n` tensors and specific header flags determines if the MTP speculation is viable/supported by the target `llama-swap` build, overriding simple filename heuristics.
*   **Measure Before Adding Speculation:** Enable `draft-mtp` only on models whose header shows a real MTP head, and only after an A/B on the target host. Acceptance *rate* is a trap metric; compare mean accepted run length and end-to-end tok/s, and confirm the outputs are equivalent between configurations.
*   **Prefer Reversible Cleanup:** When pruning stale backups or dead manifest rows, move them to an `archive/` subdirectory or a dated sidecar rather than deleting. Cleanup should never be the irreversible step.
*   **Model Orphans:** Models are not "safe" if they are not in a service group. Always confirm group membership after path/name changes.
*   **Case-Sensitive Model ID Verification:** Always verify model ID casing against its source (e.g., the raw HF name or directory name). Relying solely on file system presentation can be misleading, especially on case-insensitive file systems like APFS, which can lead to false positives or missed definition errors when matching model blocks.
*   **User Preference Naming Priority:** User-defined naming conventions (e.g., removing proprietary prefixes) take precedence over the upstream repository artifact's name. The automation must programmatically enforce the user's desired standard, even if it deviates slightly from the upstream naming convention.