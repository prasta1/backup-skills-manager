---
name: hermes-patch-agent
description: Use when source patch is needed but pm repair fails.
---

## Procedure for Source-Based Agent Update

1.  **Backup State.** Capture a pre-state backup of the current `facts.json` to a scratch directory for rollback.
    *   *Command:* `cp ~/.hermes/installs/<ID>/facts.json ~/.hermes/cache/scratch/pminstall-prestate-<TIMESTAMP>/facts.json`
2.  **Invalidate Venv.** Remove the existing `venv` fact from `facts.json`. This forces the system to rebuild the environment from source instead of using the recorded environment.
    *   *Command:* Use a script to load `facts.json` and pop the 'venv' key from the `packages` object before saving.
3.  **Force Reinstall.** Run `hermes pm install`. This forces the system to resolve dependencies and copy the latest code from the project source into a new generation.
    *   *Command:* `hermes pm install`
4.  **Verify.** Check the new generation's mtime against the current source code mtime to ensure the patch has been correctly incorporated.

## Pitfalls and Lessons

**1. Repair is not a source update.** `hermes pm repair` only reconstruct the dependency environment from the previous generation (`replay`), it does not copy the current source code (`source`).
    *   *Why:* The `repair` command's logic is designed to preserve the dependency graph and environment state (`shutil.copytree(replay, root)`), so it clones the old workspace, not the new source.
**2. Invalidate the state to rebuild.** To get the current source into the new venv, the recorded venv fact must be manually removed, forcing `hermes pm install` to fall back to a full source-based resolution.
    *   *Why:* By deleting the `venv` fact, the system determines the environment is "stale" and triggers a full build process instead of a state-preserving rebuild.