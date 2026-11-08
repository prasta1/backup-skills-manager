---
name: macOS File System Operations
description: Handling macOS-specific file system operations including alias resolution and symlink management for project setup workflows.
---

# macOS File System Operations

This skill covers handling macOS-specific file system operations, particularly alias resolution and symlink management for project setup workflows.

## When to Use This Skill

- When working with Finder aliases (`.alias` files) that need to be resolved or converted to symlinks
- When setting up project directories where aliases are involved
- When encountering filesystem path resolution issues in macOS environments

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
   rm "/path/to/Edge Impulse alias"
   ln -s "/resolved/target/path" "/path/to/Edge Impulse alias"
   ```

### Handling macOS Path Issues
- Finder aliases may not resolve in shell scripts or terminal tools without proper AppleScript handling
- When a path exists as a Finder alias but should be a symlink, convert it for consistent behavior

## Best Practices
1. When setting up projects or aliases, prefer symlinks over Finder aliases for consistent CLI behavior
2. If an alias is not resolving in command-line tools, convert it to a symlink using the `ln -s` command
3. Always verify that paths resolve correctly in both Finder and terminal contexts

## Pitfalls to Avoid
- **Finder aliases don't always resolve**: macOS Finder aliases may not work in shell scripts or command-line tools without proper AppleScript handling
- **Inconsistent behavior**: Finder aliases can behave differently in GUI vs CLI contexts, leading to confusion during project setup
- **Missing tools**: Some alias resolution methods require Python or AppleScript support that may not be available in all environments

## Examples
### Converting a Finder Alias to Symlink
```bash
# Remove the alias file
rm "/Users/macstudio/.hermes/projects/Edge Impulse/Edge Impulse alias"

# Create a symlink to the actual directory
ln -s "/Users/macstudio/Dropbox (Maestral)/claude-cowork-maestral/Edge Impulse" "/Users/macstudio/.hermes/projects/Edge Impulse/Edge Impulse alias"
```

### Verifying Path Resolution
```bash
# Check what a path resolves to in various contexts
ls -la "/Users/macstudio/.hermes/projects/Edge Impulse/Edge Impulse alias"
readlink "/Users/macstudio/.hermes/projects/Edge Impulse/Edge Impulse alias" 2>/dev/null || echo "Not a symlink"
```