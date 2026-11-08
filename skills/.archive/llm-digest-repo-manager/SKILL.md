---
name: llm-digest-repo-manager
description: Manage GitHub repos tracked by the LLM digest cron.
version: 1.0.0
author: Ionga
tags: [productivity, cron, github, automation]
---

# LLM Digest Repo Manager

## Purpose

Manage the list of GitHub repos that the daily Open Source LLM Digest cron job
(`~/.hermes/scripts/llm_digest.py`) monitors for releases. Add a repo to
tracking, remove one, list all tracked repos, or open the script for editing.

## When to Use

Use this skill when the user wants to adjust which GitHub repos the daily LLM
digest monitors for new releases.

## Trigger

Use when the user wants to adjust which GitHub repos the daily LLM digest
monitors for new releases.

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

The script reads `GH_REPOS` (a Python list at the top of the file) to know
which repos to poll on each run. The `--add-repo`, `--remove-repo`, and
`--list-repos` subcommands manipulate this list in-place using a lightweight
argparse interface — no manual editing required.

## Verification

After adding or removing a repo, the command prints the updated list so you
can confirm the change landed. The next daily cron run will pick up the new
list automatically.

## Caveats

- Repo must be in `org/repo` format (e.g. `huggingface/transformers`)
- Duplicates are silently ignored
- Removing a repo does not affect past digests, only future ones
