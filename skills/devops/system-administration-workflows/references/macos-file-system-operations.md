---
name: macOS File System Operations
description: Handling macOS-specific file system operations including alias resolution and symlink management for project setup workflows.
---

# macOS File System Operations

Handling macOS-specific file system operations, particularly alias resolution
and symlink management. The alias-resolution technique below is general; the
examples use live symlinks on this box (verified 2026-10-23).

## When to Use This Skill

- When working with Finder aliases (`.alias` files) that need to be resolved or converted to symlinks
- When setting up project directories where aliases are involved
- When encountering filesystem path resolution issues in macOS environments
- When a symlink is broken or points at a stale target

## Key Patterns

### Resolving Finder Aliases
When you encounter a Finder alias file (`.alias`) that points to a directory or file, it may not resolve properly in command-line contexts. Use these approaches:

1. **For direct path resolution**:
   ```bash
   # Use Python to resolve the alias properly (recommended)
   python3 -c "
   import os, subprocess
   path = '/path/to/alias'
   script = f'''
   tell application \"Finder\"
       set origPath to POSIX path of (original item of (alias file \"{path}\"))
       return origPath
   end tell
   '''
   result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
   print(result.stdout.strip())
   "
   ```

2. **For converting aliases to symlinks**:
   ```bash
   # Remove the alias and create a symlink instead
   rm "/path/to/alias"
   ln -s "/resolved/target/path" "/path/to/alias"
   ```

### Verifying a symlink resolves
```bash
# Read the link target
readlink /path/to/link
# Confirm the target actually exists (a broken link resolves to nothing)
[ -e "$(readlink -f /path/to/link)" ] && echo "resolves" || echo "BROKEN"
# For a GGUF or binary, read bytes THROUGH the link, not just resolve it
head -c4 /path/to/link | xxd -p   # GGUF should print 47475546
```

## Live examples on this box (2026-10-23)

These are real symlinks in `~/bin` that follow the "scripts/ owns and versions
it, ~/bin is a thin pointer" pattern:

```bash
# ei-cli -> the real script in ~/.hermes
ls -la ~/bin/ei-cli
#   ei-cli -> /Users/macstudio/.hermes/ei-cli.py

# cruft-check.sh -> the real report script
ls -la ~/bin/cruft-check.sh
#   cruft-check.sh -> /Users/macstudio/.hermes/scripts/cruft-check-report.sh
```

The pattern: the canonical file lives in `~/.hermes/scripts/` (or `~/.hermes/`),
and `~/bin/` holds a symlink so the tool is on PATH without duplicating the
file. When the real file moves, update the symlink — a stale link is the
failure mode to watch for.

## Best Practices
1. When setting up projects or aliases, prefer symlinks over Finder aliases for consistent CLI behavior
2. If an alias is not resolving in command-line tools, convert it to a symlink using the `ln -s` command
3. Always verify that paths resolve correctly in both Finder and terminal contexts
4. Keep the canonical file in one place and point symlinks at it — never copy the file into `~/bin`

## Pitfalls to Avoid
- **Finder aliases don't always resolve**: macOS Finder aliases may not work in shell scripts or command-line tools without proper AppleScript handling
- **Inconsistent behavior**: Finder aliases can behave differently in GUI vs CLI contexts, leading to confusion during project setup
- **Missing tools**: Some alias resolution methods require Python or AppleScript support that may not be available in all environments
- **A broken symlink and a missing file need different fixes and look identical to `os.path.isfile`**: backslash-escaped targets (`/Users/macstudio\.hf\/hub/...`) produce a link that `ls -la` looks fine and `[ -e ]` says is dead. Fix with `ln -sfn` using forward slashes, then confirm by reading bytes *through* the link.
- **APFS is case-insensitive by default**: `os.path.exists(".../Nemotron-3-Nano-Omni...")` returns True for a directory actually named `Nemotron-3-Nano-Omni-...`. Verify by walking the tree and comparing `os.listdir()` entries exactly.
