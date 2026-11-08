# Merge Conflict Reconciliation

**Absorbed from:** `autonomous-ai-agents` → `merge-reconciler` skill.

## When to Use

- Two agent branches/worktrees collide during a parallel campaign
- `git merge` or `git rebase` halts on conflicts between two agents' work
- Do NOT use for conflicts within a single agent's own work, or trivial lockfile conflicts

## Hunk Classification

Agents resolving conflicts against a peer's work reliably overwrite the peer or abandon their own change — they lack the peer's context and are biased. This procedure is the impartial third-party fix.

| Hunk class | Definition | Resolution |
|---|---|---|
| disjoint-intent | Different goals, can coexist | Combine both |
| same-question-different-answer | Both sides answered one design question differently | Pick ONE per stated intents |
| superseded | One side's premise no longer holds after the other's change | Keep the surviving side; note why |

## Procedure

1. **Gather both sides** — `git status`, `git merge-base`, `git diff` for each side. Collect intent from PR bodies, commit messages, or kanban summaries.
2. **Classify every conflicted hunk** — assign each `<<<<<<<` block one class from the table.
3. **Resolve under the impartiality contract** — disjoint-intent: merge both; same-question: pick per stated intents; superseded: keep surviving side. Touch ONLY conflicted regions. `git add` each resolved file.
4. **Verify** — Run build/tests; both intents must be demonstrably present.
5. **Hand back** — Produce a completion summary naming every hunk decision.

## Full Reference

`references/merge-reconciler.md` in the archived `autonomous-ai-agents` skill directory (under `.archive/`).
