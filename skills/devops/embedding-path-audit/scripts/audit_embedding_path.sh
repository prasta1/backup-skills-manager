#!/usr/bin/env bash
# One-shot audit of the macOS embedding inference path (llama-swap + llama-server).
#
# Checks ports, makes a real /v1/embeddings call against the canonical proxy using
# the model id the SERVER advertises, runs the watchdog, and sweeps every known
# consumer for stale model ids. Prints a PASS/FAIL report; exit 1 if anything fails.
#
# Usage: audit_embedding_path.sh [--quiet]
set -uo pipefail

QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1
FAIL=0
ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$*"; }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$*"; FAIL=1; }
warn() { printf '  \033[33mWARN\033[0m  %s\n' "$*"; }
say()  { [[ $QUIET -eq 1 ]] || printf '%s\n' "$*"; }

SWAP_URL="${EMBEDDING_URL_BASE:-http://127.0.0.1:9292}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

say "=== embedding path audit ($(date '+%Y-%m-%d %H:%M %Z')) ==="

# --- 1. ports ---------------------------------------------------------------
if lsof -iTCP:9292 -sTCP:LISTEN >/dev/null 2>&1; then
  ok "llama-swap listening on :9292"
else
  bad "llama-swap NOT listening on :9292"
fi
# :5800 is lazy-loaded; absence only matters if the embedding call below fails.
if lsof -iTCP:5800 -sTCP:LISTEN >/dev/null 2>&1; then
  ok "llama-server backend up on :5800"
else
  warn "llama-server not bound on :5800 (lazy: expected until first embed request)"
fi

# --- 2. discover the real model ids (never trust a hardcoded id) -------------
MODELS=$(curl -sf -m 10 "${SWAP_URL}/v1/models" 2>/dev/null | jq -r '.data[].id' 2>/dev/null)
if [[ -z "$MODELS" ]]; then
  bad "could not list models from ${SWAP_URL}/v1/models"
  EMB_ID=""; RERANK_ID=""
else
  ok "model list retrieved ($(printf '%s\n' "$MODELS" | grep -c .) ids)"
  EMB_ID=$(printf '%s\n' "$MODELS" | grep -E 'bge-m3' | grep -v reranker | head -1)
  RERANK_ID=$(printf '%s\n' "$MODELS" | grep -E 'reranker' | head -1)
  if [[ -n "$EMB_ID" ]]; then ok "embedding id advertised: ${EMB_ID}"; else
    # ms-bge-m3-1024 is `unlisted: true` in llama-swap's config: it serves
    # embeddings but never appears in /v1/models, so the list above cannot find
    # it. Read the id from the config's embeddings group instead and let the real
    # POST in step 3 prove whether it actually works. (Found 2026-11-04 — this
    # check was reporting FAIL on a healthy embedding path.)
    CFG="${HERMES_HOME}/llama-swap/config.yaml"
    EMB_ID=$(sed -n '/^  embeddings:/,/^  [a-z]/p' "$CFG" 2>/dev/null \
      | grep -E '^[[:space:]]+- ' | head -1 | sed 's/^[[:space:]]*-[[:space:]]*//')
    if [[ -n "$EMB_ID" ]]; then
      ok "embedding id from config (unlisted): ${EMB_ID}"
    else
      bad "no embedding id in /v1/models or the config embeddings group"
    fi
  fi
  [[ -n "$RERANK_ID" ]] && say "        reranker id advertised: ${RERANK_ID}"
fi

# --- 3. real embedding call -------------------------------------------------
if [[ -n "$EMB_ID" ]]; then
  DIMS=$(curl -sf -m 60 "${SWAP_URL}/v1/embeddings" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${EMB_ID}\",\"input\":\"ping\"}" 2>/dev/null \
    | jq -r '.data[0].embedding | length' 2>/dev/null)
  if [[ "${DIMS:-0}" -ge 1 ]] 2>/dev/null; then
    ok "embeddings OK via ${EMB_ID} (${DIMS} dims)"
  else
    bad "embeddings FAILED for ${EMB_ID} on ${SWAP_URL}"
  fi
fi

# --- 4. tailnet path (the watchdog requires both) ---------------------------
TAILNET="${EMBEDDING_URL_MB:-https://studio.taile85139.ts.net:9292}"
if [[ -n "$EMB_ID" ]]; then
  TN=$(curl -sf -k -m 30 "${TAILNET}/v1/embeddings" -H 'Content-Type: application/json' \
    -d "{\"model\":\"${EMB_ID}\",\"input\":\"ping\"}" 2>/dev/null \
    | jq -r '.data[0].embedding | length' 2>/dev/null)
  if [[ "${TN:-0}" -ge 1 ]] 2>/dev/null; then ok "tailnet embeddings OK (${TAILNET})"; else bad "tailnet embeddings FAILED (${TAILNET})"; fi
fi

# --- 5. watchdog ------------------------------------------------------------
# The embeddings probe now lives in the consolidated llama-swap sentinel, which
# owns the whole :9292 surface (watchdog_embedding.sh was retired Oct 2026 when
# the sentinel was finally scheduled). Two things changed with it:
#   * it always exits 0, even while alerting, so SILENCE is the healthy signal
#     here, not the exit code (running it by hand only prints; the cron job is
#     what posts to Discord);
#   * its output covers models and the MacBook too, so this audit fails only on
#     the embedding lines and merely warns about the rest.
SENTINEL="${HERMES_HOME}/scripts/watchdog_llama_swap_sentinel.sh"
if [[ -x "$SENTINEL" ]]; then
  OUT=$("$SENTINEL" 2>&1)
  if printf '%s' "$OUT" | grep -q 'embeddings'; then
    bad "sentinel reports embedding failures: $(printf '%s' "$OUT" | grep 'embeddings' | head -2 | tr '\n' ' ')"
  elif [[ -n "$OUT" ]]; then
    warn "sentinel alerting (not embedding-related): $(printf '%s' "$OUT" | head -2 | tr '\n' ' ')"
  else
    ok "sentinel silent/green (:9292 surface)"
  fi
  for k in embed_local embed_tailnet; do
    COUNT_FILE="${HERMES_HOME}/state/sentinel_${k}_fails"
    [[ -f "$COUNT_FILE" ]] && warn "consecutive-failure counter still present (${k}): $(cat "$COUNT_FILE")"
  done
else
  bad "watchdog_llama_swap_sentinel.sh missing or not executable"
fi

# --- 6. stale-id sweep across every known consumer --------------------------
# Match stale MODEL ids only (studio-<model-family>), not endpoint/file names
# like "llama-swap-studio-tailnet" or "studio-config.json".
STALE=$(grep -rn 'studio-\(devstral\|qwen\|glm\|gemma\|bge\|granite\|gpt\|kat\|laguna\|nuextract\)' --include='*.sh' --include='*.env' --include='*.yaml' \
  --include='*.yml' --include='*.json' --include='*.py' \
  "${HERMES_HOME}/scripts" "${HERMES_HOME}/hindsight" \
  "${HERMES_HOME}/skills" \
  "${HERMES_HOME}/config.yaml" "$HOME/Library/LaunchAgents" 2>/dev/null \
  | grep -v '\.bak' \
  | grep -v '/\.archive/' | grep -v 'embedding-path-audit')
if [[ -z "$STALE" ]]; then
  ok "no stale studio-* ids in live config/scripts"
else
  bad "stale studio-* ids found:"; printf '%s\n' "$STALE" | sed 's/^/        /'
fi

# --- 7. cron model pins (live fields only; last_error text is historical) ---
if [[ -f "${HERMES_HOME}/cron/jobs.json" ]]; then
  PINS=$(grep -o '"model": "[^"]*"' "${HERMES_HOME}/cron/jobs.json" | sort -u)
  STALE_PINS=$(printf '%s\n' "$PINS" | grep -E 'studio-|bge-m3' || true)
  if [[ -z "$STALE_PINS" ]]; then
    ok "cron model pins look current ($(printf '%s\n' "$PINS" | grep -c .) distinct)"
  else
    bad "cron jobs still pinning stale ids:"; printf '%s\n' "$STALE_PINS" | sed 's/^/        /'
  fi
fi

# --- 8. Docker consumers' live env -----------------------------------------
for c in Hindsight open-webui; do
  docker inspect "$c" >/dev/null 2>&1 || continue
  ENVS=$(docker inspect "$c" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null \
    | grep -E 'HINDSIGHT_API_(LLM|EMBEDDINGS|REFLECT|CONSOLIDATION)[A-Z_]*MODEL=|RAG_EMBEDDING_MODEL=')
  if printf '%s' "$ENVS" | grep -q 'studio-'; then
    bad "${c} running with stale ids: $(printf '%s' "$ENVS" | tr '\n' ' ')"
  else
    ok "${c} env current ($(printf '%s\n' "$ENVS" | grep -c . ) model vars)"
  fi
done

say ''
if [[ $FAIL -eq 0 ]]; then
  say "RESULT: all checks passed."
else
  say "RESULT: FAILURES present — see FAIL lines above."
fi
exit $FAIL
