#!/bin/bash
#
# Send-gate for email triage — staged draft approval + send via himalaya.
# This script is the ONLY thing that sends email — deterministic (no LLM).
#
# Usage:
#   ./send-gated.sh              # send all approved drafts
#   ./send-gated.sh approve <file>  # approve a draft then send all
#   ./send-gated.sh status        # show pending/approved counts
#
set -euo pipefail

DRAFT_DIR="${EMAIL_DRAFT_DIR:-$HOME/.hermes/email-drafts}"
SENT_LOG="$DRAFT_DIR/sent.log"

if [ ! -d "$DRAFT_DIR" ]; then
    echo "No draft directory: $DRAFT_DIR"
    exit 0
fi

case "${1:-send}" in
    approve)
        file="$2"
        if [ ! -f "$file" ]; then
            echo "Draft file not found: $file"
            exit 1
        fi
        sed -i '' 's/^approved = false/approved = true/' "$file"
        echo "✅ Approved: $file"
        ;;

    status)
        pending=$(grep -l 'approved = false' "$DRAFT_DIR"/draft_*.toml 2>/dev/null | wc -l || echo 0)
        approved=$(grep -l 'approved = true' "$DRAFT_DIR"/draft_*.toml 2>/dev/null | wc -l || echo 0)
        sent=$(wc -l < "$SENT_LOG" 2>/dev/null || echo 0)
        echo "📊 Draft queue status:"
        echo "  Pending approval: $pending"
        echo "  Approved (ready): $approved"
        echo "  Already sent:     $sent"
        ;;

    send)
        exec python3 "$(dirname "$0")/triage.py" send
        ;;

    *)
        echo "Usage: $0 [send|approve <file>|status]"
        exit 1
        ;;
esac
