# Inventory Marker Guide

Use `<!-- BEGIN AUTO: <section> -->` and `<!-- END AUTO: <section> -->` to wrap volatile sections in a living inventory document.

## Syntax

```markdown
<!-- BEGIN AUTO: <section> -->
[content that gets regenerated]
<!-- END AUTO: <section> -->
```

- Replace `<section>` with a descriptive name (e.g., `Hardware`, `Listening Ports`, `Model Fleet`).
- The script rewrites only content between the markers.
- Hand-edited content outside the markers survives regeneration.

## Best Practices

- **Use one marker pair per section** — no nesting.
- **Never edit the markers by hand** — use the script to regenerate.
- **Place markers at top-level** — avoid embedding in nested lists or tables.
- **Include a generation note** in the section: `Generated <timestamp> by stack-inventory.py`
- **Verify markers are paired** before committing — use `read_file` to check.

## Common Mistakes

- **Misplaced markers** → script may delete or overwrite non-auto content.
- **Duplicate markers** → script may rewrite the same section multiple times.
- **Missing `END` tag** → script may fail or rewrite too much.

Use this guide whenever creating a new living inventory.

---
*Updated: 2026-10-25*
*Author: Ionga, on behalf of Patrick Ruster*