---
name: email-triage
description: Gmail inbox triage - classify + draft replies, staged for approval, using clef-flash as the gate and classifier.
version: 2.0.0
author: Ionga
tags: [email, gmail, imap, himalaya, triage, draft, automation, clef, decision-model]
metadata:
  hermes:
    tags: [email, gmail, imap, himalaya, triage, draft, automation, clef, decision-model]
---

# Email Triage

Single consolidated skill for Gmail inbox triage: scan, classify, draft replies, stage for
approval. This replaces the former `email-triage-clef`, `email-triage-agent`,
`email-triage-clef-test`, and `email-triage-workflow` skills (consolidated 2026-10-06).

## When to Use

When you want a local decision model to triage the Gmail inbox, classify each thread, and
draft reply emails that Patrick reviews before sending. This path uses **Cloudflare
clef-flash** (9B Qwen3.5-9B backbone + joint schema head) as both the fast gate and the
classifier, served locally on `:8001` via `ai.clef.serve`. Drafting uses BGE-M3 retrieval +
qwen3.6-35b-a3b.

## Why clef-flash (ground-truth bakeoff, 2026-10-03)

On 47 real emails labeled by Patrick (his actual reply decisions), clef-flash beat the
former Laya gate decisively:

| Metric (Patrick's ground truth) | Laya | Clef-flash |
|---|---|---|
| Recall on real replies (4) | 75% (3/4) | **100% (4/4)** |
| False-positive rate (42 he'd skip) | **71% (30/42)** | **17% (7/42)** |

Laya passed 30 of 42 emails Patrick would skip — it was never really gating. Clef-flash
catches all real replies AND filters noise. Cost: ~11x slower per email (median ~1.5s gate
vs Laya's ~130ms) and ~18GB resident footprint vs Laya's ~843MB. The Laya path was deleted
2026-10-04; the plain Devstral path was folded into this skill 2026-10-06.

**Ground-truth rule:** never trust observer-guessed labels for a model verdict. The bakeoff
set + labels live at `~/.hermes/cache/scratch/clef_test_set.json` and
`clef_bakeoff_results.json`. The first (guessed-label) verdict was wrong; the real verdict
came only from Patrick's clicks.

## Prerequisites

- Himalaya v2 installed (`brew install himalaya`)
- Gmail App Password configured in `~/.hermes/.env` as `GMAIL_APP_PASSWORD`
- Himalaya config at `~/.config/himalaya/config.toml` with the Gmail account
- **Clef-flash served on `:8001`** via `ai.clef.serve` (launchd). Model cache at
  `~/.cache/huggingface/hub` (HF_HOME — NOT `~/.hf`; that dir holds only whisper weights).
  API key at `~/.hermes/secrets/clef.key`. Verify:
  `curl -s http://127.0.0.1:8001/health`
- `ms-qwen3.6-35b-a3b` + `ms-bge-m3-1024` via llama-swap `:9292` for drafting

> **⚠️ DO NOT DELETE `ms-bge-m3-1024` from the model fleet.** It is a live dependency of
> the daily Gmail Triage cron (job `69b6e4bf5fbc`, 7:30am). The drafting tier embeds
> Patrick's sent mail with BGE-M3 to retrieve past replies; without it, drafting falls
> back to fresh generation with no retrieval context. It is an embedding model, not a
> chat model — it will not show up as a "drafting LLM" in a fleet review, so it is easy
> to mistake for cruft. Keep it. (Same for `ms-bge-reranker-v2-m3` if it is ever wired
> in.)

## Quick Start

```bash
# Triage unread inbox, classify, draft, stage
hermes chat --toolsets "email,file,terminal,skills" -q "/email-triage run"

# Review staged drafts
hermes chat --toolsets "email,file,terminal,skills" -q "/email-triage review"

# Send approved drafts (this triggers the send-gate)
hermes chat --toolsets "email,file,terminal,skills" -q "/email-triage send"
```

## Configuration

Set the following in the Hermes profile or environment:

- `GMAIL_APP_PASSWORD` — 16-char Gmail App Password (in `~/.hermes/.env`)
- `EMAIL_TRIAGE_MODEL` — fallback model (defaults to `ms-devstral-24b`; not used for
  classify or draft on this path)
- `EMAIL_TRIAGE_LIMIT` — max threads to process per run (default: 20)
- `EMAIL_TRIAGE_FOLDERS` — comma-separated IMAP folders to scan (default: `INBOX`)
- `EMAIL_DRAFT_DIR` — where staged drafts live (default: `~/.hermes/email-drafts`)
- `EMAIL_TRIAGE_STAGE_CLASSES` — classifications that get a draft file (default:
  `action,reply,urgent-reply`). Everything else is logged to `classified.log`.
- `CLEF_URL` — clef-flash endpoint (default: `http://127.0.0.1:8001/v1/systemone`)
- `CLEF_API_KEY` — bearer token; reads from `~/.hermes/secrets/clef.key` if unset
- `CLEF_GATE_THRESHOLD` — probability threshold for `reply_warranted`/`is_alert` to pass
  the gate (default: `0.25`; lower = more recall, less savings)
- `EMAIL_TRIAGE_REVIEW_THRESHOLD` — confidence below which a thread is flagged
  `needs_review` (default: `0.6`). Legacy alias `LAYA_REVIEW_THRESHOLD` still honored.

## Workflow

### 1. Scan (Read)
- Himalaya lists unread envelopes from the configured Gmail account
- For each unread thread, fetches full message content via `himalaya message read`
- Extracts sender, subject, date, body text

### 2. Gate (clef-flash pre-filter)
Before fetching the body or full classify, clef-flash classifies sender + subject on MPS
(~1.5s/thread). If both `reply_warranted` and `is_alert` fall below `CLEF_GATE_THRESHOLD`,
the thread is logged to `classified.log` as `noise`/`reference` and the body-fetch + full
classify is **skipped entirely**. The gate fails open — if clef-flash is unreachable, the
thread proceeds to full classify as before.

### 3. Classify (clef-flash)
For threads that pass the gate, clef-flash classifies the full state (sender + subject +
body) with a 13-question schema in one call (~4-5s on MPS):
- **triage_class** — urgent-reply / reply / action / waiting / reference / noise
- **invoice, brand_deal, scam_phishing, sponsor_fit** — noul flags
- **email_type** — transactional / promotional / personal / notification / other
- **urgency** — low / medium / high
- **spam_likelihood** — no_spam / maybe / spam

### 4. Draft (BGE-M3 retrieval + qwen3.6-35b-a3b)
For threads classified as `urgent-reply` or `reply`:
- BGE-M3 retrieval over Patrick's sent mail → adapt a past reply, or generate fresh with
  qwen3.6-35b-a3b. If drafting fails, the thread is flagged `needs_review` (no silent
  empty draft).
- Draft is saved as a file: `EMAIL_DRAFT_DIR/<timestamp>_<id>.toml`

### 5. Stage (Approval)
- Only `action`, `reply` and `urgent-reply` threads are written as draft files
- `noise`, `reference` and `waiting` are appended to `classified.log` and NOT staged
- Drafts are NOT sent automatically; use `/email-triage review` then `/send`

### 6. Send (Gated)
- A deterministic shell script reads staged drafts; you must explicitly mark each as
  approved in a JSON index; only approved drafts are sent via `himalaya message send`

### 7. Interactive review (chat seat only)
`python3 triage.py review-choices` emits `clarify` question JSON, chunked to <=5 per call,
passed to the `clarify` tool. Act with `triage.py discard` / `triage.py approve`.
`triage.py send` is the sole sender. Cron cannot click buttons.

### Manual sender rules (rules.yaml)
Rules live at `~/.hermes/email-drafts/rules.yaml` (override with `EMAIL_TRIAGE_RULES`).
- `never_draft:` — senders that must never stage a draft (classification `suppressed`)
- `always_action:` — senders whose threads always stage as `action`
Matching is case-insensitive substring against BOTH sender address and display name.
Precedence: `apply_noreply_rule()` first (structural), then `apply_manual_rules()` LAST
and wins outright. Verify with `python3 triage.py rules`.

**`always_action` invariant (fixed 2026-10-04):** a rule that means "never send" must scrub
the send fields (`reply_to`, `reply_subject`, `reply_body`) unconditionally, not only on
the branch where it happens to reclassify. The old code returned the data untouched when
the model had already called the thread a `reply`, letting an alert-robot reply reach the
staging queue. The current code scrubs on every `always_action` match.

### No-reply sender rule (enforced in code)
Senders whose address matches `NOREPLY_RE` (`no-reply`, `noreply`, `donotreply`,
`notification(s)`, `notice`, `alert`, `automated`, `mailer`, `newsletter`, `update(s)` as
a delimited token in the local part):
- `reply`/`urgent-reply` verdicts downgrade to `action` when `ALERT_HINT_RE` finds alert
  language, otherwise to `noise`
- `reply_to`, `reply_subject`, `reply_body` are ALWAYS emptied
- `reasoning` is prefixed with `[no-reply rule]`
Kill switch: `EMAIL_TRIAGE_NOREPLY_RULE=0`.

## Serving (ai.clef.serve)

Clef-flash cannot ride llama-swap (the joint schema head is not in the GGUF quants), so it
runs via the publisher's torch/transformers code on MPS, mirroring the former `ai.laya.serve`
pattern:

- **plist:** `~/Library/LaunchAgents/ai.clef.serve.plist` (launchd, KeepAlive)
- **server:** `~/.venv/clef/serve_clef.py` (stdlib http.server, loads model once, serves
  `/v1/systemone` + `/health`)
- **wrapper:** `~/.venv/clef/serve_clef.sh` (sets HF_HOME=~/.cache/huggingface, HF_HUB_OFFLINE=1, port 8001)
- **venv:** `~/.venv/clef` (torch 2.14.1, transformers 5.18.0, accelerate, torchvision)
- **model cache:** `~/.cache/huggingface/hub/models--Cloudflare--clef-flash` — the repo dir itself is
  only ~196K because its blobs are symlinks into the shared `hub/blobs` store; the weights are ~17.8GB there
- **API key:** `~/.hermes/secrets/clef.key`

Manage with modern launchctl syntax:
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.clef.serve.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.clef.serve.plist
```

## Pitfalls

- **`.processed_ids` must be MERGED, never overwritten.** This is the shared-state
  invariant across all runs.
- **Clef-flash is ~11x slower than the old Laya gate** (median ~1.5s gate, ~4.6s full
  classify on MPS) and ~18GB resident. That is the price of the accuracy.
- **Never run two triage invocations against the same mailbox in one window** — they share
  `.processed_ids` and the draft queue in `~/.hermes/email-drafts`, causing race
  conditions and duplicate processing. Pick one run per window.
- **The draft directory is `~/.hermes/email-drafts`** (`EMAIL_DRAFT_DIR`). Reports must
  copy the `Draft dir: <path>` line the script prints, never restate it from memory.
- **`drafts.json` is a per-run index, not a queue.** The real queue is the `draft_*.toml`
  glob that `review` counts.
- **Never trust a `reply` classification on a no-reply sender.** The no-reply guard strips
  those in code; trust the `[no-reply rule]` prefix in the reasoning.
- **Noise threads still get a draft file written** with empty body; the send-gate skips
  empty bodies.
- **`discard <envelope_id>` removes staged drafts; id stays in `.processed_ids`** — a
  discarded thread is not re-triaged.
- **Gmail throttling:** IMAP LIST over a large mailbox can be slow; the limit flag
  controls batch size.
- **Env var expansion:** Himalaya v2 doesn't expand `${VAR}` in config — use
  `password.command = ["sh", "-c", "echo $GMAIL_APP_PASSWORD"]`.
- **Never auto-send:** the send-gate script must be invoked explicitly.
- **Clef-flash needs `accelerate` and `torchvision`** in the venv (the loader uses a
  device_map and the video processor needs torchvision). Both are installed in
  `~/.venv/clef`.
- **The gate fails open** — if clef-flash is down, threads proceed to full classify. That
  is intended (no mail silently dropped), but a down clef service costs you the
  noise-filtering savings, not correctness.
- **When porting a triage path, grep the new file for the old model's name** before
  trusting any recorded output (the clef path was ported from Laya and once kept a
  hardcoded `"Laya: "` reasoning prefix).

## Verification

```bash
# Clef-flash service healthy
curl -s http://127.0.0.1:8001/health

# Check staged drafts (only actionable threads)
ls -la ~/.hermes/email-drafts/

# Non-actionable threads: logged, not staged
tail -20 ~/.hermes/email-drafts/classified.log

# Check send log
cat ~/.hermes/email-drafts/sent.log

# Verify IMAP still working
GMAIL_APP_PASSWORD="…" himalaya envelope list -a gmail
```

## Commands

- `/email-triage run` — scan inbox, gate, classify, draft, stage
- `/email-triage review` — list pending drafts with classifications
- `python3 triage.py discard <envelope_id> [...]` — delete staged drafts (false positives)
- `python3 triage.py approve <envelope_id> [...]` — mark drafts approved (sends NOTHING)
- `python3 triage.py review-choices` — emit `clarify` question JSON for the staged queue
- `/email-triage send` — send approved drafts via send-gate
- `/email-triage test-model` — verify llama-swap + model are reachable
- `python3 triage.py test-gate '<from_email>' '<from_name>' '<subject>'` — run only the
  clef gate on one email (no body fetch, no full classify); debugs gate calibration
