---
name: software-development-workflows
description: "Comprehensive software development workflows and debugging practices"
version: 1.0.0
author: Hermes Agent + Teknium
license: MIT
tags: [development, debugging, testing, tdd, ci/cd]
---

# Software Development Workflows - Hermes Guide

This skill provides comprehensive guidance for software development workflows including debugging, testing, and development practices.

## Overview

Hermes supports a wide range of software development workflows and debugging practices that can be automated or orchestrated.

## Debugging Tools

### Python Debugging
```
# Using debugpy for remote debugging
python -m debugpy --listen 5678 --wait-for-client script.py

# In Hermes session:
terminal(command="python -m debugpy --listen 5678 --wait-for-client myapp.py", workdir="~/project")
```

### Node.js Debugging
```
# Using --inspect for Node.js debugging
node --inspect=9229 app.js

# In Hermes session:
terminal(command="node --inspect=9229 app.js", workdir="~/project")
```

### Hermes TUI Debugging
```
# Debug Hermes TUI slash commands
debug --command python
debug --command gateway
debug --command ink-ui
```

## Testing and Quality Assurance

### Test-Driven Development (TDD)
```
# Enforce RED-GREEN-REFACTOR cycle
terminal(command="pytest --tb=short", workdir="~/project")
```

### Code Review Automation
```
# Pre-commit security scan and quality gates
terminal(command="pre-commit run --all-files", workdir="~/project")
```

### Automated Testing
```
# Run tests in parallel with pytest-xdist
terminal(command="pytest -n 4 --tb=short", workdir="~/project")
```

## Development Patterns

### Spike Development
```
# Throwaway experiments to validate an idea before build
spike --name "new-feature-research" --description "Research for new feature implementation"
```

### Systematic Debugging
```
# 4-phase root cause debugging approach
debug --phase understand --phase analyze --phase fix --phase verify
```

### Code Simplification
```
# Parallel 3-agent cleanup of recent code changes
simplify --target "src/app.py" --agent-count 3
```

## Planning and Development

### Writing Implementation Plans
```
# Create actionable implementation plans with exact paths and code examples
plan --task "implement user authentication" --output "docs/implementation-plan.md"
```

### Subagent-Driven Development
```
# Execute plans via delegate_task subagents (2-stage review)
delegate --task "build api endpoints" --reviewer-count 2
```

### Commit hygiene: staged-pile sweep
`git commit` commits the ENTIRE staging area, not just the files you added this turn. If the working tree already had staged/untracked changes (a skills sync, plugin install, snapshot snapshot) and you run `git add myfile && git commit`, you sweep hundreds of unrelated files into your commit. Before committing, run `git diff --cached --name-only` and confirm the list is exactly what you intend. If you already made the mess: `git reset --soft <parent>` (keeps everything), then `git reset` (unstages all, working tree intact), then `git add <your files>` and commit again — clean. The swept files return to their prior unstaged/untracked state, nothing is lost.



### Configuration and Setup
1. **Use proper toolsets**: Enable `terminal`, `file`, and `web` toolsets for development workflows
2. **Version control integration**: Always work within git repositories for proper tracking
3. **Environment consistency**: Use virtual environments or containers to ensure consistent development environments

### Code Quality
1. **Pre-commit hooks**: Run security scans and quality checks before committing
2. **Automated testing**: Ensure all code changes pass tests before merging
3. **Documentation**: Maintain up-to-date documentation for development practices
## User Preference Alignment

The user prefers direct, concise responses with minimal fluff. They are frustrated by verbosity and want to see the final result quickly.

When applying development workflows:
- If a task can be solved with a simple command or one-liner, use that instead of generating extensive documentation
- Avoid lengthy process descriptions when the user just wants to know what to do next
- Focus on actionable steps rather than general workflow descriptions
- When using tools like `plan`, `delegate_task`, or `spike`, prioritize the immediate output over process context
- **Do NOT provide meta-commentary or "I'm doing this because..." rationale unless explicitly requested**
- **Do NOT describe the process steps when the user wants just the result**

When applying development workflows:
1. **Prioritize output over process**: The user prefers final results to process documentation.
2. **Trim excess explanation**: If a skill would normally generate 3+ paragraphs of process context, only provide the core output.
3. **Apply the "just give me the answer" principle**: When a user says "just do X", execute it without commentary.
- When using tools like `plan`, `delegate_task`, or `spike`, prioritize the immediate output over process context

## Development Workflow Examples

### CI/CD Integration
```
# Example CI workflow for software development
terminal(command="pytest --tb=short && flake8 && mypy", workdir="~/project")
```

### Automated Refactoring
```
# Use code review tools for automated refactoring
terminal(command="refactor --rules all --target src/", workdir="~/project")
```

### Development Environment Setup
```
# Example development environment configuration
development:
  tools:
    - python-debugpy
    - pytest
    - flake8
    - mypy
  testing:
    parallel: true
    coverage: 80%
```

## Skill Inventory

The following archived subskills have been fully absorbed into this umbrella:

| Skill | Absorbed Into |
|---|---|
| software-development-spike | Spike development methodology (`references/spike.md`) |
| software-development-systematic-debugging | 4-phase debugging methodology (`references/systematic-debugging.md`) |
| software-development-python-debugpy | Python debugging guide (`references/python-debugpy.md`) |
| software-development-node-inspect-debugger | Node.js debugging guide (`references/node-inspect-debugger.md`) |
| software-development-inspecting-hermes-desktop-dom | Hermes DOM inspection guide (`references/inspecting-hermes-desktop-dom.md`) |
| software-development-code-audit-patterns | Code audit methodology (`references/code-audit-patterns.md`) |
| software-development-issue-taxonomy | Issue classification (`references/issue-taxonomy.md`) |
| software-development-test-driven-development | TDD workflow (`references/test-driven-development.md`) |
| software-development-requesting-code-review | Pre-commit review workflow (`references/requesting-code-review.md`) |
| software-development-simplify-code | Code cleanup workflow (`references/simplify-code.md`) |
| software-development-writing-plans | Plan authoring (`references/writing-plans.md`) |
| software-development-subagent-driven-development | Parallel subagent orchestration (`references/subagent-driven-development.md`) |
| software-development-dogfood | Exploratory QA methodology (`references/dogfood.md`, `templates/dogfood-report-template.md`) |

## References

- `references/user-preference-concise-response.md` - User preference for concise, direct responses with minimal fluff
- `references/test-driven-development.md` - Absorbed TDD workflow from software-development-test-driven-development
- `references/writing-plans.md` - Absorbed plan authoring from software-development-writing-plans
- `references/code-audit-patterns.md` - Absorbed code audit methodology
- `references/issue-taxonomy.md` - Absorbed issue classification from software-development-code-audit-patterns
- `references/subagent-driven-development.md` - Absorbed parallel subagent orchestration
- `references/simplify-code.md` - Absorbed code cleanup workflow
- `references/requesting-code-review.md` - Absorbed pre-commit review workflow
- `references/spike.md` - Absorbed spike development methodology
- `references/systematic-debugging.md` - Absorbed 4-phase debugging methodology
- `references/python-debugpy.md` - Absorbed Python debugging guide
- `references/node-inspect-debugger.md` - Absorbed Node.js debugging guide
- `references/inspecting-hermes-desktop-dom.md` - Absorbed Hermes DOM inspection guide
- `references/dogfood.md` - Absorbed exploratory QA methodology
- `templates/dogfood-report-template.md` - Absorbed QA report template (YAML)
- `references/inspecting-hermes-desktop-dom.md` - Absorbed Hermes DOM inspection
- `templates/development-workflow.yaml` - Example development workflow configurations