# Issue-to-PR Workflow

**Absorbed from:** `autonomous-ai-agents` → `github-issue-to_pr` skill.

**Companion to:** `github/references/issue-to-pr.md` (PR mechanics) — this reference focuses on the agent orchestration angle.

## When to Use

- "Fix issue #123 and open a PR"
- "Implement this GitHub feature request"
- "Take this bug from issue to green CI"

## Procedure

1. Read the live issue body AND full thread (comments carry live state)
2. Sweep for existing/duplicate PRs with keyword variants
3. Validate premise against current code + design intent (git log -p -S)
4. Define acceptance criteria and risk
5. Implement the smallest complete change — fix the class, not just one call site
6. Prove the regression test bites (sabotage run: revert fix, test fails, restore fix)
7. Run quality gates, open PR immediately (PR dispatches CI)
8. Shepherd CI honestly — report from live evidence only

## Prequel Dependencies

This workflow assumes the developer tools from `software-development-workflows`:
- `systematic-debugging` — for root cause analysis when reproduction fails
- `test-driven-development` — for writing regression tests first
- `requesting-code-review` — for pre-commit review

## Key Agent-Specific Steps

- **Premise validation**: Use `search_files` and `read_file` to trace the reported path. Check git log for design intent.
- **Sabotage run**: Temporarily restore old behavior, run the new test, confirm it FAILS; then restore fix and confirm it passes.
- **Sibling call sites**: After the fix, search for the same bug shape at sibling call sites and fix the whole class.
- **CI shepherding**: Inspect live checks via `gh pr checks` / `gh run view --log-failed`. Distinguish failures introduced by your diff from pre-existing baseline failures.

Full reference: `references/github-issue-to-pr.md` in the archived `autonomous-ai-agents` skill directory.