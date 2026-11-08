# Remote Install Cannot Execute — Decision Procedure

Companion to section 2D. Use when the desktop's SSH handshake fails and you must
decide whether the remote is genuinely too old or merely broken.

## The two cases that look identical

The desktop emits one message for both:

```
Desktop boot failed: The remote Hermes install does not support --ssh-session-token-file and --ssh-owner-nonce.
```

| Case | Signal | Fix |
|------|--------|-----|
| **Genuinely old remote** | flags absent from source AND `hermes serve --help` works | update the remote |
| **Broken remote** | flags present in source AND `hermes serve --help` raises | repair the checkout; updating is the wrong move |

Guessing wrong here wastes a cycle and can make things worse — an update against
a dirty tree is a known way to freeze a host.

## The `--version` trap

`hermes --version` reports success on a checkout that cannot execute anything.
It resolves version metadata without walking the module import graph, so a
source file riddled with conflict markers does not stop it.

This matters because the desktop's own probe is a version probe. The version
succeeds, the handshake proceeds, the real invocation dies, and the desktop
concludes "too old." The successful version check is not evidence of health —
it is exactly what makes the misdiagnosis tempting.

Use a subcommand that imports:

```bash
ssh <host> 'hermes serve --help 2>&1 | head -20'
```

## Reading the traceback

A conflict marker in a module imported at startup surfaces as a traceback whose
deepest frame names the *importer*, not the broken file:

```
  File ".../hermes_cli/main.py", line 703, in <module>
    from hermes_cli.config import get_hermes_home
  File ".../hermes_cli/config.py", line 1461
<<<<<<< HEAD
SyntaxError: expected 'except' or 'finally' block
```

The reported location looks like an innocent import. The damage is at the
`<<<<<<<` line in the file named by the *final* frame. Scan for markers
directly rather than trusting the line number the error reports:

```bash
ssh <host> 'cd ~/.hermes/hermes-agent && grep -rlF "<<<<<<<" --include="*.py" . | head'
```

A merge left in progress announces itself:

```bash
ssh <host> 'cd ~/.hermes/hermes-agent && cat .git/MERGE_HEAD .git/MERGE_MSG 2>/dev/null'
```

## Is `git merge --abort` safe?

Abort discards the merge. Count the three categories separately — the counts
answer it without judgment:

```bash
ssh <host> 'cd ~/.hermes/hermes-agent && \
  echo "unstaged: $(git status --porcelain | grep -cE "^.[MDARC]")"; \
  echo "staged:   $(git status --porcelain | grep -cE "^[MARC]")"; \
  echo "untracked:$(git status --porcelain | grep -c "^??")"; \
  git rev-parse --short ORIG_HEAD'
```

- **0 unstaged, 0 untracked, everything staged** → the tree holds only merge
  output. Abort is clean, and `ORIG_HEAD` names the exact pre-merge commit.
  There is no work to lose, because an uncommitted merge was never work.
- **Any unstaged or untracked file** → abort will discard authored changes.
  Stop and surface it; do not force.

## Why this recurs

On a branch carrying local commits, `hermes update` merges the upstream branch
instead of resetting, and says so before doing it. Two outcomes:

- **Backed out cleanly** — reports the conflict, changes nothing, host keeps
  running the old code. Annoying, not dangerous.
- **Left in place** — the tree ends up staged and unparseable. Anything
  long-running survives on code it already imported; every *new* spawn fails.

Read the updater log to see which happened and how often:

```bash
ssh <host> 'tail -40 ~/.hermes/logs/hermes-update.log'
```

Only the second case takes the host down. The durable fix is a policy decision
about whether a production host should self-update a branch with private
commits at all — aborting restores service but does not stop the next attempt
from re-merging and conflicting.

## Quoting pitfall

Passing an unquoted glob through `ssh` hands expansion to the remote shell,
which aborts the command entirely:

```bash
# WRONG — remote zsh: "no matches found", grep never runs
ssh host 'grep -rn "foo" --include=*.py .'

# RIGHT
ssh host 'grep -rlF "foo" --include="*.py" .'
```

A silently skipped grep reads as "the symbol does not exist," which is a
confident wrong answer rather than an obvious failure. Quote every glob you
send over ssh.
