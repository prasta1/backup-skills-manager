# LLM Digest Repo Manager

**Absorbed from:** `llm-digest-repo-manager` skill

Manage the list of GitHub repos that the daily Open Source LLM Digest cron job (`~/.hermes/scripts/llm_digest.py`) monitors for releases.

## Purpose

The daily LLM digest cron polls a list of GitHub repos for new releases. This skill provides the procedure for adding, removing, and listing tracked repos.

## Commands

### Add a repo
```bash
python3 ~/.hermes/scripts/llm_digest.py --add-repo org/repo
```

### Remove a repo
```bash
python3 ~/.hermes/scripts/llm_digest.py --remove-repo org/repo
```

### List tracked repos
```bash
python3 ~/.hermes/scripts/llm_digest.py --list-repos
```

### Edit the script directly
```bash
zed ~/.hermes/scripts/llm_digest.py
```

## How it works

The script reads `GH_REPOS` (a Python list at the top of the file) to know which repos to poll on each run. The `--add-repo`, `--remove-repo`, and `--list-repos` subcommands manipulate this list in-place using a lightweight argparse interface.

## Verification

After adding or removing a repo, the command prints the updated list so you can confirm the change landed. The next daily cron run will pick up the new list automatically.

## Caveats

- Repo must be in `org/repo` format (e.g. `huggingface/transformers`)
- Duplicates are silently ignored
- Removing a repo does not affect past digests, only future ones
