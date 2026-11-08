#!/usr/bin/env bash
# Read-only health probe for a remote Hermes install reached over SSH.
# Usage: probe-remote-install.sh <ssh-host>
#
# Answers: is the remote genuinely too old for Desktop SSH mode, or is its
# checkout simply broken? Makes no changes to the remote.

set -uo pipefail

HOST="${1:-studio}"
REPO="$HOME/.hermes/hermes-agent"

echo "== 1. version probe (NOT a health check - it skips the import graph) =="
ssh -o ConnectTimeout=10 "$HOST" 'hermes --version 2>&1 | head -3'

echo
echo "== 2. flag support present in remote source? =="
ssh -o ConnectTimeout=10 "$HOST" \
  "grep -rlF 'ssh_session_token_file' --include='*.py' '$REPO' 2>/dev/null | head -5"
echo "   (empty above => remote is genuinely old; the desktop's message is then accurate)"

echo
echo "== 3. real executability probe - this is the honest test =="
ssh -o ConnectTimeout=10 "$HOST" \
  'hermes serve --help >/dev/null 2>&1 && echo "   OK: serve subcommand imports cleanly" \
   || echo "   FAIL: serve subcommand cannot load (broken checkout - see step 4)"'

echo
echo "== 4. merge state / conflict markers =="
ssh -o ConnectTimeout=10 "$HOST" \
  "cd '$REPO' 2>/dev/null && { \
     [ -f .git/MERGE_HEAD ] && echo \"   MERGE IN PROGRESS: \$(cat .git/MERGE_HEAD)\" \
       || echo '   no MERGE_HEAD'; \
     n=\$(grep -rlF '<<<<<<<' --include='*.py' . 2>/dev/null | wc -l | tr -d ' '); \
     echo \"   files with conflict markers: \$n\"; \
     grep -rlF '<<<<<<<' --include='*.py' . 2>/dev/null | head -5; \
   } || echo '   repo path not found on remote'"

echo
echo "== 5. abort safety (0 unstaged + 0 untracked => git merge --abort is clean) =="
ssh -o ConnectTimeout=10 "$HOST" \
  "cd '$REPO' 2>/dev/null && { \
     echo \"   unstaged:  \$(git status --porcelain | grep -cE '^.[MDARC]')\"; \
     echo \"   staged:    \$(git status --porcelain | grep -cE '^[MARC]')\"; \
     echo \"   untracked: \$(git status --porcelain | grep -c '^??')\"; \
     echo \"   ORIG_HEAD: \$(git rev-parse --short ORIG_HEAD 2>/dev/null)\"; \
     echo \"   branch:    \$(git rev-parse --abbrev-ref HEAD) - \$(git rev-list --count HEAD..origin/main 2>/dev/null) behind origin/main\"; \
   }"

echo
echo "== 6. service liveness (up != healthy; a process can serve pre-breakage code) =="
ssh -o ConnectTimeout=10 "$HOST" \
  "launchctl list 2>/dev/null | grep -i hermes | head -10 || ps aux | grep -i '[h]ermes' | head -5"

echo
echo "== verdict =="
echo "  step 2 empty + step 3 OK   -> remote is genuinely old; update it"
echo "  step 3 FAIL               -> checkout is broken; do NOT update, repair the tree"
echo "  step 4 markers + step 5 clean -> 'git merge --abort' is a safe one-command fix"
