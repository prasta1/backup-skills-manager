---
name: code-audit-patterns
description: "Systematic code audit methodology (Ponytail-style): find duplicate patterns, classify by tag, rank by impact, prioritize safe cuts."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-audit, refactoring, ponytail, technical-debt, cleanup, prioritization]
    related_skills: [simplify-code, requesting-code-review, software-development-workflows]
---

# Code Audit Patterns — Ponytail Methodology

Systematic approach to finding and prioritizing safe code deletions in a codebase. Based on the "Ponytail" philosophy: lazy senior dev who deletes more than writes.

## Core Philosophy

> **Delete first, ask questions later.** Most codebases carry 10-30% dead weight — duplicate registries, unused abstractions, backup files, over-engineered interfaces. The goal is to find the *safe* cuts that reduce cognitive load without changing behavior.

## Audit Workflow

### Phase 1 — Pattern Discovery

Scan the codebase for recurring structural patterns. Use these queries:

```bash
# Find duplicate ABCs with single implementations
grep -r "class.*ABC" --include="*.py" | sort | uniq -c | sort -rn

# Find identical boilerplate across files
# Look for: register/lookup/get_active, is_available/display_name/list_* defaults

# Find backup files accumulating on disk
find . -name "*.bak*" -o -name "*.backup*" -o -name "*~"

# Find proxy/wrapper classes with no behavior
grep -r "class.*Proxy" --include="*.py"
```

### Phase 2 — Classification Tags

Every finding gets a tag. These are the canonical tags:

| Tag | Meaning | Action |
|-----|---------|--------|
| `delete` | Trash — backup files, dead code, config debris | Remove immediately |
| `yagni` | "You Aren't Gonna Need It" — unused abstraction, duplicate pattern | Collapse to generic |
| `stdlib` | Reimplements stdlib/stdlib-adjacent functionality | Use stdlib |
| `native` | Can be replaced by native language feature | Use native |
| `shrink` | Two files doing overlapping work — merge them | Merge to one |

### Phase 3 — Impact Ranking

Rank by **net lines deleted** (biggest cut first). Always estimate:
- Lines deleted if consolidated
- Lines of replacement code needed
- Risk of behavior change (0-10)

### Phase 4 — Priority Order

Execute in this order:

1. **Registries / identical boilerplate** — self-contained, obvious diff, low risk
2. **Provider ABCs** — same shape as registries, shared defaults
3. **Tool merges** — two files → one, no behavior change
4. **Catalog merges** — overlapping logic, clear consolidation
5. **Everything else** — as bandwidth allows

### Phase 5 — Out of Scope (Correctness/Security)

Route to normal review, do NOT auto-cut:
- Error classification by fragile string-matching (may be load-bearing)
- Complex fallback chains (complexity is intentional)
- Exact-pinned dependencies (pins are post-incident decisions)

## Pattern Recognition Heuristics

### Duplicate Registry Pattern
```
Symptom: 5+ files with identical structure:
  _providers: Dict[str, T] = {}
  _lock = threading.Lock()
  def register_provider(...)
  def list_providers(...)
  def get_provider(...)
  def _reset_for_tests(...)
  # Only resolution logic differs
```
**Action:** Extract `Registry[T]` generic. Keep resolution in subclasses.

### Single-Implementation ABC Pattern
```
Symptom: ABC with exactly one concrete subclass
  class FileOperations(ABC): ...
  class FilesystemOps(FileOperations): ...
```
**Action:** Delete ABC. Use concrete class directly.

### Backup File Accumulation
```
Symptom: config.yaml.bak.*, .env.bak-*, auth.json.bak.* in home dir
```
**Action:** `git` is the backup. Delete all.

### Proxy-for-Import Pattern
```
Symptom: class _OpenAIProxy defers 240ms import
  _OPENAI_CLS_CACHE = None
  class _OpenAIProxy: __call__ -> _load_openai_cls()(...)
```
**Action:** KEEP if import cost is real and module is hot-path. This is a valid lazy-import pattern.

### Durable-Target Infrastructure
```
Symptom: Complex install-target logic for sealed venvs
  HERMES_LAZY_INSTALL_TARGET, .python-abi stamp, sys.path append
```
**Action:** KEEP if used by Docker/CI. This is load-bearing infra.

## Verification Checklist

Before committing any audit-driven deletion:

- [ ] Run full test suite (not just affected module)
- [ ] Verify no behavior change in integration paths
- [ ] Check plugin/extension points still work
- [ ] Confirm no downstream consumers broken (grep for imports)
- [ ] Update any documentation referencing removed code

## Reference: Real Audit Example

See `references/ponytail-audit-2026-06-25.md` for the full audit that inspired this skill — 11 findings, ~2,400 safe lines cut (not the claimed 9,000), with detailed per-finding verdicts.