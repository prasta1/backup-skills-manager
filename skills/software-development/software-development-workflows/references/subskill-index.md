# Software Development Workflows - Subskill Index

This skill serves as the umbrella for the software development workflow cluster.
The following subskills were consolidated into this umbrella:

## Planning & Execution
- writing-plans — Implementation plan authoring (bite-sized tasks, TDD, exact paths)
- subagent-driven-development — Parallel subagent orchestration with 2-stage review
- plan — Implementation plan writer (protected built-in, not modified)
- spike — Throwaway experiments to validate ideas before building

## Debugging
- systematic-debugging — 4-phase root cause: understand, analyze, fix, verify
- python-debugpy — Python debugging via pdb + debugpy remote
- node-inspect-debugger — Node.js debugging via --inspect + Chrome DevTools Protocol
- debugging-hermes-tui-commands — Debugging Hermes TUI slash commands across Python/gateway/Ink layers
- inspecting-hermes-desktop-dom — Reading live Hermes desktop DOM/CSS over CDP

## Code Quality
- code-audit-patterns — Systematic code audit methodology (Ponytail-style)
- requesting-code-review — Pre-commit review: security scan, quality gates, auto-fix
- simplify-code — Parallel multi-agent cleanup of recent code changes
- sdlc-review — Software development lifecycle review

## Testing
- test-driven-development — RED-GREEN-REFACTOR cycle enforcement

## GitHub Integration
- github-issue-to-pr — End-to-end: issue → duplicate sweep → reproduce → fix → PR → CI honesty (absorbed into autonomous-ai-agents instead — workflow is about orchestrating Claude Code/Codex/OpenCode agents)
- github-workflows — GitHub Actions workflow management
- codebase-inspection — LOC, language, ratio analysis with pygount

## QA
- dogfood — Exploratory QA: systematic web app testing with evidence collection

## Key Principles
- Bite-sized tasks (2-5 min each)
- Exact file paths, complete code, exact commands with expected output
- DRY, YAGNI, TDD
- Frequent commits
- Verify before declaring done
