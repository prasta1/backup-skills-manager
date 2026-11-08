# Phase 2 — Memory, Skills, and Clutter Cleanup

Source: Patrick's pasted master prompt (2026-10-13). "This one specifically targets Hermes'
learning system." Verbatim:

> "Perform an exhaustive memory, skills, and knowledge-base optimization audit.
>
> Inspect persistent memory, USER.md, MEMORY.md, SOUL.md, AGENTS.md, available skills, skill references, and session-retrieval mechanisms.
>
> Identify:
>
> - Duplicate, conflicting, outdated, or low-value memories
> - Redundant instructions repeated in multiple locations
> - Overlapping or obsolete skills
> - Skills containing excessive explanations instead of reusable procedures
> - Valuable knowledge buried in old conversations that should become durable memory or a skill
> - Repeated mistakes that should have produced a documented lesson
> - Unnecessary context consuming tokens on every request
> - Unused or stale supporting files and recoverable archives
>
> Run the built-in Hermes Curator in dry-run mode when available. Compare its findings against your independent inspection.
>
> Develop a consolidation strategy that preserves all useful capabilities while reducing unnecessary complexity.
>
> Create a before-and-after inventory. Estimate token savings where measurable, and test whether important information remains retrievable.
>
> Back up all affected data. Do not permanently delete or overwrite anything important without approval. Prefer reversible archiving and staged changes.
>
> Report exactly what should be merged, shortened, archived, retained, or improved, along with the reasoning for each recommendation."

## Local execution notes

- Curator dry-run: invoke dry mode when it exists on this install; treat its output as one
  input, never the verdict.
- Memory work must respect the MEMORY.md format and cap (see `hermes-infrastructure`):
  canonical `\n§\n` separators, 12,000-char cap, entry-granular edits only.
- Prefer archiving to deletion; `~/.hermes` is a git backup repo and everything skills-related
  is recoverable from its history, but never run recursive `-x` cleans.
- Agent-self-error lessons belong in skills, not memory.
