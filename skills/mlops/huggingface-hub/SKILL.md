---
name: huggingface-hub
description: "HuggingFace hf CLI: search/download/upload models, datasets."
version: 1.0.1
author: Hugging Face
license: MIT
tags: [huggingface, hf, models, datasets, hub, mlops]
platforms: [linux, macos, windows]
---

# Hugging Face CLI (`hf`) Reference Guide

The `hf` command is the modern command-line interface for interacting with the Hugging Face Hub, providing tools to manage repositories, models, datasets, and Spaces.

> **IMPORTANT:** The `hf` command replaces the now deprecated `huggingface-cli` command.

## Quick Start
*   **Installation:** `curl -LsSf https://hf.co/cli/install.sh | bash -s`
*   **Help:** Use `hf --help` to view all available functions and real-world examples.
*   **Authentication:** Recommended via `HF_TOKEN` environment variable or the `--token` flag.

## Pitfall: verifying a completed `hf download`

Verify against the etag **hf itself recorded locally**, not against a Hub API lookup.
`hf download --local-dir DIR` writes `DIR/.cache/huggingface/download/<repo_path>.metadata`
whose lines are: (1) commit sha, (2) expected sha256 (the LFS oid), (3) a timestamp.
Comparing each file's computed sha256 to line 2 is authoritative and needs no network.

Do **not** verify with `GET /api/models/<repo>/tree/main/<dir>?expand[]=lfs` — that call
can return a listing in which no entry matches the requested path, so the lookup yields
`None`, and a naive `expected is None or expected == actual` check reports a **pass while
comparing nothing**. (Hit 2026-10-28: 9/9 files reported OK with zero verification done.)
When an expected value cannot be retrieved, print `UNVERIFIED` and fail the check rather
than defaulting to success. `GET /api/models/<repo>?blobs=true` returns `siblings[]` with
`rfilename`/`size`/`lfs.oid` and is the reliable source for expected sizes.

The `.metadata` line 3 is a **timestamp**, not a size — casting it to int raises.

## Pitfall: gated repos

`gated: "auto"` in the model API does **not** mean your token can download it. It means
the user must accept the terms once on the model page ("Agree and access repository",
instant grant); until then every download fails with `Access denied. Model '<repo>'
requires approval.` There is no CLI accept, and accepting a license is the user's act,
not the agent's. Probe with a 100-byte ranged `curl` before launching a large pull so the
gate surfaces immediately instead of after three retry cycles.

## Pitfall: `HF_HOME` must be set or auth silently fails

`huggingface_hub` resolves BOTH the cache root and the saved token through `HF_HOME`
(token lives at `$HF_HOME/token`, cache at `$HF_HOME/hub`). If `HF_HOME` is unset it
silently falls back to `~/.cache/huggingface`, so a login made under one value is
invisible under the other.

**On the Studio the agreed HF_HOME is `~/.cache/huggingface`** — `.zshenv` deliberately
leaves HF_HOME unset so that default is used everywhere (shells, launchd, Unsloth.app).
The token files live at `~/.cache/huggingface/token` and `~/.cache/huggingface/stored_tokens`.
Do NOT force `HF_HOME="$HOME/.hf"` — `~/.hf` is a real dir with no token in it, and a
script that points there gets `hf auth token` → "Not logged in" even though the login
is healthy. This exact bug broke `hf-mcp-token-sync.sh` (fixed 2026-10-08: it forced
`HF_HOME=$HOME/.hf`; corrected to `$HOME/.cache/huggingface`).

**Rule:** before trusting any `hf` auth result, check what the shell resolved:
`hf env | grep -E 'Token path|Has saved token'`. "Not logged in" usually means a split
HF_HOME, not a missing login. Confirm with `ls -la $HF_HOME/token`. When a script must
pin the home explicitly, use `HF_HOME="$HOME/.cache/huggingface"`, never `~/.hf`.

---

## Core Commands

### General Operations
*   `hf download REPO_ID`: Download files from the Hub.
*   `hf upload REPO_ID`: Upload files/folders (recommended for single-commit; also handles resumable uploads of large directories).
*   `hf upload-large-folder REPO_ID LOCAL_PATH`: **[Deprecated]** — use `hf upload` instead.
*   `hf sync`: Sync files between a local directory and a bucket.
*   `hf env` / `hf version`: View environment and version details.

### Authentication (`hf auth`)
* `login` / `logout`: Manage sessions using tokens from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
* `list` / `switch`: Manage and toggle between multiple stored access tokens.
* `whoami`: Identify the currently logged-in account.
* `token`: Print the current access token to stdout (useful for piping into other configs).

**Multiple stored tokens.** `hf auth list` shows every token with its name, masked value and
expiry. A token produced by an OAuth login is a long (~825 char) access token; a classic
PAT is 37 chars and has no expiry. Which one is live matters, because they are not
interchangeable - a PAT can 401 against the MCP endpoint even while the Hub API accepts
it. `hf auth switch` changes the active token; `~/.cache/huggingface/token` always
mirrors the active one.

**Never bake an expiring token into a static config header.** An MCP server block that
authenticates with a literal `Authorization: Bearer hf_...` cannot refresh: the CLI
refreshes transparently (a `refresh_token` lives beside the access token in
`~/.cache/huggingface/stored_tokens`), but a static header silently 401s the moment the
access token expires. Check `hf auth list` for an `expires` date and re-sync the header
after any `hf auth login` or `hf auth switch`. On this machine
`~/.hermes/scripts/hf-mcp-token-sync.sh` does exactly that: it reads `hf auth token`,
rewrites the `hugging_face` block in `~/.hermes/config.yaml` file-to-file (token never
echoed), and keeps a `config.yaml.bak-pre-hfsync` backup. It is croned weekly (Mon 05:30,
`deliver: local`) so the header never goes stale again.

### Repository Management (`hf repos`)
*   `create` / `delete`: Create or permanently remove repositories.
*   `duplicate`: Clone a model, dataset, or Space to a new ID.
*   `move`: Transfer a repository between namespaces.
*   `branch` / `tag`: Manage Git-like references.
*   `delete-files`: Remove specific files using patterns.

---

## Specialized Hub Interactions

### Datasets & Models
*   **Datasets:** `hf datasets list`, `info`, and `parquet` (list parquet URLs).
*   **SQL Queries:** `hf datasets sql SQL` — Execute raw SQL via DuckDB against dataset parquet URLs.
*   **Models:** `hf models list` and `info`.
*   **Papers:** `hf papers ls` — View daily papers.

### Discussions & Pull Requests (`hf discussions`)
*   Manage the lifecycle of Hub contributions: `list`, `create`, `info`, `comment`, `close`, `reopen`, and `rename`.
*   `diff`: View changes in a PR.
*   `merge`: Finalize pull requests.

### Infrastructure & Compute
*   **Endpoints:** Deploy and manage Inference Endpoints (`deploy`, `pause`, `resume`, `scale-to-zero`, `catalog`).
*   **Jobs:** Run compute tasks on HF infrastructure. Includes `hf jobs uv` for running Python scripts with inline dependencies and `stats` for resource monitoring.
*   **Spaces:** Manage interactive apps. Includes `dev-mode` and `hot-reload` for Python files without full restarts.

### Storage & Automation
*   **Buckets:** Full S3-like bucket management (`create`, `cp`, `mv`, `rm`, `sync`).
*   **Cache:** Manage local storage with `list`, `prune` (remove detached revisions), and `verify` (checksum checks).
*   **Webhooks:** Automate workflows by managing Hub webhooks (`create`, `watch`, `enable`/`disable`).
*   **Collections:** Organize Hub items into collections (`add-item`, `update`, `list`).

---

## Advanced Usage & Tips

### Global Flags
*   `--format json`: Produces machine-readable output for automation.
*   `-q` / `--quiet`: Limits output to IDs only.

### Extensions & Skills
*   **Extensions:** Extend CLI functionality via GitHub repositories using `hf extensions install REPO_ID`.
*   **Skills:** Manage AI assistant skills with `hf skills add`.
