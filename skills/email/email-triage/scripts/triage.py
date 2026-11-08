#!/usr/bin/env python3
"""
Email Triage Agent — scan Gmail inbox, classify threads, draft replies, stage for approval.

Usage:
    triage.py run       — scan + classify + draft + stage
    triage.py review    — list pending drafts
    triage.py send      — send approved drafts (requires send-gate approval)
    triage.py test-model — verify the local model is reachable

Uses Himalaya v2 (Homebrew) for IMAP, clef-flash (9B) for classification,
BGE-M3 retrieval + ministral-3-3b for drafting. No Devstral fallback.
"""
import json
import os
import re
import sys
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──
DRAFT_DIR = Path(os.environ.get("EMAIL_DRAFT_DIR", "~/.hermes/email-drafts")).expanduser()
MODEL = os.environ.get("EMAIL_TRIAGE_MODEL", "ms-devstral-24b")
LIMIT = int(os.environ.get("EMAIL_TRIAGE_LIMIT", "20"))
ACCOUNT = "gmail"
LLAMA_SWAP_URL = "http://127.0.0.1:9292/v1/chat/completions"
# Key resolver lives in clef_client (reads HERMES_CUSTOM_LLAMA_SWAP_API_KEY from env,
# falling through to ~/.hermes/.env; sentinel env values are treated as unset).

# ── clef-flash (9B decision model) + BGE-M3 retrieval drafting ────────────────
# Classification: Cloudflare clef-flash on :8001 (~3.4s/email, MPS, local, $0).
# Drafting tier: BGE-M3 retrieval over past replies + ministral-3-3b (3B).
# Per Patrick's direction: Devstral is NOT used for classify or draft.
# LAYA_REVIEW_THRESHOLD is the legacy name for this knob (this path was ported
# from the Laya triage); still honored so existing env setups keep working.
REVIEW_THRESHOLD = float(os.environ.get(
    "EMAIL_TRIAGE_REVIEW_THRESHOLD",
    os.environ.get("LAYA_REVIEW_THRESHOLD", "0.6"),
))
sys.path.insert(0, str(Path.home() / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clef_client import classify_email, retrieve_and_draft, LLAMA_SWAP_KEY

# Only these classifications get a staged draft file. Everything else (noise,
# reference, waiting) is recorded as a log line instead, so the review queue
# holds only threads worth a human look. Override with EMAIL_TRIAGE_STAGE_CLASSES.
STAGE_CLASSES = {
    c.strip() for c in os.environ.get(
        "EMAIL_TRIAGE_STAGE_CLASSES", "action,reply,urgent-reply"
    ).split(",") if c.strip()
}

# Use Homebrew himalaya (v2.1.0), not the broken nix one
HIMALAYA_BIN = "/opt/homebrew/bin/himalaya"

DRAFT_DIR.mkdir(parents=True, exist_ok=True)
SENT_LOG = DRAFT_DIR / "sent.log"
DISCARD_LOG = DRAFT_DIR / "discarded.log"
APPROVED_LOG = DRAFT_DIR / "approved.log"
CLASSIFIED_LOG = DRAFT_DIR / "classified.log"
INDEX_FILE = DRAFT_DIR / "drafts.json"
RULES_FILE = Path(
    os.environ.get("EMAIL_TRIAGE_RULES", "~/.hermes/email-drafts/rules.yaml")
).expanduser()

# Manual per-sender rules. Patrick's explicit intent beats both the model and the
# no-reply guard, so these are applied LAST and win outright. See rules.yaml.
#   never_draft: senders that should never produce a staged draft
#   always_action: senders whose threads should always stage as `action`
# Matching is case-insensitive substring against the sender address OR display
# name, so `patreon` catches 9holereviews@creator.patreon.com. Keep patterns
# specific — `gmail.com` would match everything.
RULES_DEFAULTS = {"never_draft": [], "always_draft": [], "always_action": []}
_rules_cache = {}


def load_rules(refresh=False):
    """Load manual sender rules from the rules file. Missing/broken file = no rules.

    Parsed WITHOUT pyyaml: the cron runs under /opt/homebrew/bin/python3 which
    has no yaml module, so a pyyaml import silently disabled all rules on every
    scheduled run. The rules file is a simple two-list structure; parse it
    directly so rules enforcement never depends on the interpreter's packages.
    """
    if _rules_cache and not refresh:
        return _rules_cache
    rules = dict(RULES_DEFAULTS)
    if RULES_FILE.exists():
        parsed = _parse_rules_file(RULES_FILE.read_text(errors="ignore"))
        for key in RULES_DEFAULTS:
            val = parsed.get(key) or []
            if isinstance(val, str):
                val = [val]
            rules[key] = [str(x).strip().lower().lstrip("@") for x in val if str(x).strip()]
    _rules_cache.clear()
    _rules_cache.update(rules)
    return _rules_cache


def _parse_rules_file(text):
    """Minimal YAML-subset parser for the rules file's two-list shape.

    Handles:
        never_draft:
          - item
          - item
        always_action:
          - item
    Also tolerates trailing comments and blank lines. Anything else (e.g. a
    mapping value) is ignored rather than crashed on, mirroring the old
    yaml.safe_load fallback.
    """
    result = {}
    current = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith("-"):
            key = stripped[:-1].strip().strip('"').strip("'")
            current = key
            result.setdefault(current, [])
        elif stripped.startswith("-") and current is not None:
            item = stripped[1:].strip().strip('"').strip("'")
            if item:
                result[current].append(item)
    return result


def _rule_match(pattern, from_email, from_name):
    if not pattern:
        return False
    p = pattern.lower().lstrip("@")
    hay_email = (from_email or "").lower()
    hay_name = (from_name or "").lower()
    return p in hay_email or p in hay_name


def _sender_email(from_email):
    """Return the raw sender address without display-name decorations."""
    if not from_email:
        return ""
    m = re.search(r"([^ <\t]+@[^ >\t]+)", from_email)
    if m:
        return m.group(1)
    return from_email.strip()


def _match_rule_category(category, from_email, from_name):
    """Return the first rules.yaml pattern matching this sender in the category, or None."""
    if not (from_email or from_name):
        return None
    rules = load_rules()
    for pattern in rules.get(category, []):
        if _rule_match(pattern, from_email, from_name):
            return pattern
    return None


def apply_manual_rules(data, from_email, from_name):
    """Enforce Patrick's explicit per-sender rules. Runs last; overrides everything else."""
    if not (from_email or from_name):
        return data
    rules = load_rules()

    for pattern in rules["never_draft"]:
        if _rule_match(pattern, from_email, from_name):
            return {
                **data,
                "classification": "suppressed",
                "reply_to": "",
                "reply_subject": "",
                "reply_body": "",
                "reasoning": (
                    f"[manual rule] never_draft matched '{pattern}' "
                    f"(sender {from_email or from_name}); no draft staged."
                ),
            }

    for pattern in rules["always_draft"]:
        if _rule_match(pattern, from_email, from_name):
            if data.get("classification") not in ("reply", "urgent-reply"):
                return {
                    **data,
                    "classification": "reply",
                    "reply_to": data.get("reply_to") or _sender_email(from_email),
                    "reply_subject": data.get("reply_subject") or f"Re: {data.get('subject', '')}",
                    "reasoning": (
                        f"[manual rule] always_draft matched '{pattern}' "
                        f"(sender {from_email or from_name}); forced to reply for drafting."
                    ),
                }
            return data

    for pattern in rules["always_action"]:
        if _rule_match(pattern, from_email, from_name):
            if data.get("classification") in ("noise", "reference", "waiting", "suppressed"):
                return {
                    **data,
                    "classification": "action",
                    "reply_to": "",
                    "reply_subject": "",
                    "reply_body": "",
                    "reasoning": (
                        f"[manual rule] always_action matched '{pattern}' "
                        f"(sender {from_email or from_name}); promoted to action."
                    ),
                }
            # An always_action sender is never sendable, even when the model
            # called it a reply. These stage as action items for Patrick's eyes,
            # not as drafts -- so scrub the reply fields here too. Previously this
            # fell through with reply_to/reply_body intact, which let a drafted
            # reply to an alert robot reach the staging queue.
            return {
                **data,
                "classification": "action",
                "reply_to": "",
                "reply_subject": "",
                "reply_body": "",
                "reasoning": (
                    f"[manual rule] always_action matched '{pattern}' "
                    f"(sender {from_email or from_name}); staged as action, reply suppressed."
                ),
            }
    return data


def himalaya_json(args, timeout_s=60, retries=1):
    """Run himalaya CLI with --json output. Returns parsed JSON.

    Gmail IMAP hiccups are common (2026-10-13: a single 60s stall on the first
    envelope fetch killed the whole 7:30 run with a traceback). Retry transient
    failures once before letting the run die. Safe here because every
    himalaya_json call is read-only; write paths use himalaya_text and must
    NOT be blindly retried.
    """
    last_err = None
    for attempt in range(retries + 1):
        try:
            env = dict(os.environ)
            result = subprocess.run(
                [HIMALAYA_BIN, "--json", *args],
                capture_output=True, text=True, env=env, timeout=timeout_s
            )
            if result.returncode != 0:
                raise RuntimeError(f"Himalaya error: {result.stderr or result.stdout}")
            return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as e:
            last_err = e
            if attempt < retries:
                print(f"⚠️ himalaya {' '.join(args[:2])} hiccup ({type(e).__name__}); retrying once...", file=sys.stderr)
                time.sleep(3)
    raise RuntimeError(f"Himalaya failed after {retries + 1} attempts: {last_err}")


def himalaya_text(args, timeout_s=60):
    """Run himalaya CLI without JSON output."""
    env = dict(os.environ)
    result = subprocess.run(
        [HIMALAYA_BIN, *args],
        capture_output=True, text=True, env=env, timeout=timeout_s
    )
    if result.returncode != 0:
        raise RuntimeError(f"Himalaya error: {result.stderr or result.stdout}")
    return result.stdout


def llm_request(prompt, max_tokens=2048, temp=0.7):
    """Call the local model via llama-swap."""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temp,
    }
    curl_headers = ["-H", "Content-Type: application/json"]
    if LLAMA_SWAP_KEY:
        curl_headers += ["-H", "Authorization: Bearer " + LLAMA_SWAP_KEY]
    result = subprocess.run(
        ["curl", "-s", "--max-time", "120", "-X", "POST",
         LLAMA_SWAP_URL, *curl_headers,
         "-d", json.dumps(payload)],
        capture_output=True, text=True, timeout=130
    )
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError(f"LLM call failed: {result.stderr}")
    data = json.loads(result.stdout)
    return data["choices"][0]["message"]["content"].strip()


# ── Clef-flash fast gate (local decision model: Cloudflare/clef-flash, 9B) ──
# Pre-filter: classify sender+subject to decide if an email is worth the full
# classify+body-fetch. Clef-flash is a 9B Qwen3.5-9B backbone + joint schema head
# served on :8001 via ai.clef.serve (torch/MPS, /v1/systemone). It cannot ride
# llama-swap (the joint head is not in the GGUF quants).
# Fail OPEN: if clef is down, the gate passes and the existing flow handles it.
CLEF_URL = os.environ.get("CLEF_URL", "http://127.0.0.1:8001/v1/systemone")
_clef_key_file = Path(os.path.expanduser("~/.hermes/secrets/clef.key"))
CLEF_API_KEY = os.environ.get("CLEF_API_KEY") or (
    _clef_key_file.read_text().strip() if _clef_key_file.exists() else ""
)
CLEF_GATE_THRESHOLD = float(os.environ.get("CLEF_GATE_THRESHOLD", "0.25"))

CLEF_GATE_QUESTIONS = {
    "reply_warranted": {"type": "noul", "instructions": "Does this email warrant a reply from Patrick?"},
    "is_alert": {"type": "noul", "instructions": "Is this an alert or notice requiring action (billing, credits, expiration, failure, verification)?"},
    "priority": {"type": "score", "instructions": "How urgent is attention to this email?",
                 "criteria": ["low", "medium", "high"]},
}


def clef_gate(from_email, from_name, subject):
    """Fast clef-flash pre-classification on sender+subject only.

    Returns dict:
      pass            — bool; True means proceed to full classify+body-fetch
      reply_warranted — P(email needs a reply)
      is_alert        — P(alert/notice needing action)
      priority        — choice: low | medium | high
      reason          — human-readable for logging
      fallback        — True if clef was unreachable (fail-open)

    Fails OPEN: on any error returns pass=True so the existing flow runs.
    """
    state = f"From: {from_name} <{from_email}>\nSubject: {subject}"
    headers = ["-H", "Content-Type: application/json"]
    if CLEF_API_KEY:
        headers += ["-H", "Authorization: Bearer " + CLEF_API_KEY]
    payload = json.dumps({"state": state, "questions": CLEF_GATE_QUESTIONS, "model": "clef-flash"})
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "30", "-X", "POST", CLEF_URL, *headers, "-d", payload],
            capture_output=True, text=True, timeout=35,
        )
        if result.returncode != 0 or not result.stdout:
            raise RuntimeError("clef did not respond")
        data = json.loads(result.stdout)
        a = data["answers"]
        reply_w = float(a["reply_warranted"]["noul"])
        alert = float(a["is_alert"]["noul"])
        _p = a["priority"]
        if "choice" in _p:
            prio = _p["choice"]
        else:
            probs = _p.get("probabilities", {})
            legend = _p.get("legend", {})
            best = max(probs, key=probs.get) if probs else ""
            prio = legend.get(best, best) if best else "unknown"
        should_pass = reply_w >= CLEF_GATE_THRESHOLD or alert >= CLEF_GATE_THRESHOLD
        return {
            "pass": should_pass,
            "reply_warranted": round(reply_w, 3),
            "is_alert": round(alert, 3),
            "priority": prio,
            "reason": f"reply={reply_w:.2f} alert={alert:.2f} prio={prio} (threshold={CLEF_GATE_THRESHOLD})",
        }
    except Exception as e:
        return {"pass": True, "reply_warranted": 0.0, "is_alert": 0.0, "priority": "unknown",
                "reason": f"clef-unreachable ({e}); falling through", "fallback": True}


PROCESSED_FILE = DRAFT_DIR / ".processed_ids"
MAX_TRACKED_IDS = 2000


def load_processed_ids():
    """Load set of envelope IDs we've already triaged."""
    if PROCESSED_FILE.exists():
        return set(PROCESSED_FILE.read_text().strip().splitlines())
    return set()


def save_processed_ids(ids):
    """Persist processed envelope IDs by MERGING with those already tracked.

    Do not overwrite. A run only ever sees its own batch, so overwriting makes
    the next run forget every thread triaged earlier; those threads are still
    unread in Gmail, so they get re-fetched, re-classified and re-staged as
    duplicate drafts — the feedback loop that made the queue grow without bound.
    """
    tracked = load_processed_ids() | {str(i) for i in ids if i}
    ordered = sorted(tracked, key=lambda x: (int(x) if x.isdigit() else 0, x))
    PROCESSED_FILE.write_text("\n".join(ordered[-MAX_TRACKED_IDS:]) + "\n")


def fetch_new_envelopes():
    """Get recent email envelopes from Gmail INBOX, skipping already-processed ones."""
    print("📥 Fetching recent envelopes from Gmail...")
    data = himalaya_json([
        "envelope", "list", "-a", ACCOUNT,
        "--page-size", str(LIMIT * 3)
    ], timeout_s=180)

    if isinstance(data, dict) and "envelopes" in data:
        envelopes = data["envelopes"]
    elif isinstance(data, dict) and "data" in data:
        envelopes = data["data"]
    elif isinstance(data, list):
        envelopes = data
    else:
        envelopes = []

    processed = load_processed_ids()
    # Himalaya v2: flags is [{"raw": "\\Seen"}, {"raw": "\\Answered"}, ...]
    def is_unseen(env):
        flags = env.get("flags", [])
        for f in flags:
            if isinstance(f, dict):
                raw = f.get("raw", "").lower()
                if "unseen" in raw:
                    return True
            elif isinstance(f, str) and "unseen" in f.lower():
                return True
        return False

    # Prefer truly unseen, but Gmail IMAP sometimes doesn't expose \Unseen reliably.
    # Fall back to "not flagged as Seen" for robustness.
    unseen = [e for e in envelopes if is_unseen(e)]
    if len(unseen) < len(envelopes):
        # Include ones without flags (often unseen on Gmail IMAP)
        noflag = [e for e in envelopes if is_unseen(e) or not e.get("flags")]
        print(f"  Found {len(envelopes)} envelopes — {len(unseen)} unseen, {len(noflag)} without \\Seen flag")
        candidates = noflag
    else:
        print(f"  Found {len(unseen)} unseen envelopes out of {len(envelopes)} total")
        candidates = unseen

    # Filter out already-processed IDs
    new = [e for e in candidates if e.get("id") not in processed]
    print(f"  New (unprocessed): {len(new)} — skipping {len(candidates) - len(new)} already processed")
    return new[:LIMIT]


def fetch_message_body(message_id):
    """Fetch full message body by envelope ID."""
    try:
        return himalaya_text(["message", "read", "-a", ACCOUNT, message_id], timeout_s=60)
    except Exception as e:
        return f"[Could not fetch full message: {e}]"


# A sender whose local part says "no reply" can never get a drafted reply. The model
# got this wrong repeatedly — Wyze, HubSpot, ecobee, Clarify, UnitedHealthcare and
# Synchrony all produced fake "reply" drafts, and a reply to notice@eml.ecobee.com
# goes nowhere. The address itself is the evidence, so we enforce it in code rather
# than hoping the prompt holds. Set EMAIL_TRIAGE_NOREPLY_RULE=0 to disable.
NOREPLY_RULE_ON = os.environ.get("EMAIL_TRIAGE_NOREPLY_RULE", "1") != "0"
NOREPLY_RE = re.compile(
    r"(^|[.@_+-])(no[-_.]?reply|donotreply|do[-_.]?not[-_.]?reply|"
    r"notifications?|notices?|alerts?|automated|mailer|newsletter|updates?)([@_+-]|$)",
    re.I,
)
# No-reply senders split into two groups: real alerts (worth staging as `action`)
# and marketing blasts (noise). Without this, demoting to noise would bury the
# Clarify credits warning and the ecobee temperature alert.
ALERT_HINT_RE = re.compile(
    r"(action required|out of credits?|no credits?|running low|expire|expiring|"
    r"deadline|past due|overdue|balance due|payment (due|required)|invoice|"
    r"statement|alert|warning|limit reached|suspend|low temperature|"
    r"unusually (low|high)|detected|failed|issue with|verify your)",
    re.I,
)


def apply_noreply_rule(data, from_email, subject, body_text=""):
    """Strip the reply from a no-reply sender; keep real alerts as `action`.

    Never returns a `reply`/`urgent-reply` classification and never leaves a
    reply_body or reply_to behind, so the send-gate has nothing to send.
    """
    if not NOREPLY_RULE_ON or not from_email:
        return data
    if not NOREPLY_RE.search(from_email):
        return data
    # Already noise/reference/waiting: leave it alone, but still scrub any body the
    # model invented — the send-gate must never see a reply target for a no-reply
    # sender regardless of what class the model picked.
    if data.get("classification") not in ("reply", "urgent-reply"):
        if data.get("reply_body") or data.get("reply_to"):
            return {
                **data,
                "reply_to": "",
                "reply_subject": "",
                "reply_body": "",
                "reasoning": (
                    f"[no-reply rule] {from_email} is a no-reply sender; reply body discarded. "
                    + (f" Model said: {data.get('reasoning', '')}" if data.get("reasoning") else "")
                ),
            }
        return data

    haystack = f"{subject}\n{body_text[:2000]}"
    is_alert = bool(ALERT_HINT_RE.search(haystack))
    return {
        **data,
        "classification": "action" if is_alert else "noise",
        "reply_to": "",
        "reply_subject": "",
        "reply_body": "",
        "reasoning": (
            f"[no-reply rule] {from_email} is a no-reply sender; reply suppressed. "
            + ("Alert language detected, kept as action."
               if is_alert else "No alert language, logged as noise.")
            + (f" Model said: {data.get('reasoning', '')}" if data.get("reasoning") else "")
        ),
    }


def classify_and_draft(envelope):
    """Use local LLM to classify + draft reply."""
    msg_id = envelope.get("id", "")
    subject = envelope.get("subject", "(no subject)")

    from_list = envelope.get("from", [])
    if isinstance(from_list, list) and from_list:
        from_obj = from_list[0]
        if isinstance(from_obj, dict):
            from_name = from_obj.get("name", "") or ""
            from_email = from_obj.get("email", "") or ""
        else:
            from_name = str(from_list)
            from_email = ""
    else:
        from_name = str(from_list)
        from_email = ""

    date_str = envelope.get("date", "")
    sender_display = f"{from_name} <{from_email}>" if from_email else from_name

    # ── clef-flash full classification (sender + subject, all questions in one ~3.4s call) ──
    state = f"From: {from_name} <{from_email}>\nSubject: {subject}"
    body_text = ""
    try:
        t0 = time.time()
        l = classify_email(state)
        classification = l.get("triage_class") or "noise"
        confidence = float(l.get("_confidence", 0) or 0)
        print(f"  🧠 Clef: {classification} (conf={confidence:.3f}, {time.time()-t0:.3f}s)")
    except Exception as e:
        print(f"  ⚠️  Clef classify failed: {e}")
        return {"classification": "reference", "confidence": 0.0,
                "reply_to": "", "reply_subject": "", "reply_body": "",
                "reasoning": f"Clef-flash unreachable: {e}", "needs_review": True}

    needs_review = confidence < REVIEW_THRESHOLD

    # ── always_draft manual rule: force the reply-drafting path ──
    forced_draft = _match_rule_category("always_draft", from_email, from_name)
    if forced_draft:
        classification = "reply"
        print(f"  📌 always_draft rule '{forced_draft}' — forced reply path for {sender_display}")

    # ── If reply-worthy: fetch body + draft via BGE retrieval + ministral-3-3b ──
    reply_body = ""
    if classification in ("reply", "urgent-reply"):
        body_text = fetch_message_body(msg_id)
        if len(body_text) > 2000:
            body_text = body_text[:2000] + "\n...[truncated]"
        full_state = f"From: {from_name} <{from_email}>\nSubject: {subject}\n\n{body_text}"
        print(f"  📝 Draft: BGE-M3 retrieval + ministral-3-3b")
        dt0 = time.time()
        reply_body = retrieve_and_draft(full_state, l) or ""
        if reply_body:
            print(f"  ✅ Drafted ({time.time()-dt0:.1f}s)")
        else:
            needs_review = True
            print(f"  ⚠️  Draft generation failed — flagged for review")
    else:
        print(f"  -> {classification} (no draft)")

    # ── Build result; noreply guard (alert promotion) + manual rules applied after ──
    data = {
        "classification": classification,
        "confidence": round(confidence, 3),
        "reply_to": from_email if classification in ("reply", "urgent-reply") else "",
        "reply_subject": f"Re: {subject}" if classification in ("reply", "urgent-reply") else "",
        "reply_body": reply_body,
        "reasoning": f"Clef-flash: {classification} (conf={confidence:.3f}). rules: "
                     f"invoice={l.get('invoice')} scam={l.get('scam_phishing')} "
                     f"type={l.get('email_type')} urgency={l.get('urgency')} "
                     f"sponsor={l.get('sponsor_fit')}",
        "needs_review": needs_review,
    }
    data = apply_noreply_rule(data, from_email, subject, body_text)
    return apply_manual_rules(data, from_email, from_name)


def save_draft(envelope, result):
    """Save a classified/drafted email as a staged TOML file."""
    msg_id = envelope.get("id", "unknown")
    now = datetime.now(timezone.utc).isoformat()
    from_list = envelope.get("from", [])
    sender_str = json.dumps(from_list) if from_list else ""

    draft = {
        "id": msg_id,
        "classification": result.get("classification", "reference"),
        "confidence": result.get("confidence", 0.0),
        "sender": sender_str,
        "subject": envelope.get("subject", ""),
        "date": envelope.get("date", ""),
        "reply_to": result.get("reply_to", ""),
        "reply_subject": result.get("reply_subject", ""),
        "reply_body": result.get("reply_body", ""),
        "reasoning": result.get("reasoning", ""),
        "draft_created_at": now,
        "approved": False,
        "needs_review": result.get("needs_review", False),
    }

    filename = DRAFT_DIR / f"draft_{msg_id}_{int(datetime.now().timestamp())}.toml"
    with open(filename, "w") as f:
        f.write(f'# Staged email draft — not yet approved for sending\n')
        f.write(f'# Created: {now}\n')
        f.write(f'# Classification: {draft["classification"]} ({draft["confidence"] * 100:.0f}% confident)\n')
        f.write(f'# Reason: {draft["reasoning"]}\n\n')
        f.write(f'id = "{draft["id"]}"\n')
        f.write(f'classification = "{draft["classification"]}"\n')
        f.write(f'classification_confidence = {draft["confidence"]}\n')
        f.write(f'sender = {draft["sender"]}\n')
        f.write(f'subject = "{draft["subject"]}"\n')
        f.write(f'date = "{draft["date"]}"\n')
        f.write(f'draft_to = "{draft["reply_to"]}"\n')
        f.write(f'draft_subject = "{draft["reply_subject"]}"\n')
        f.write(f'draft_body = """\n{draft["reply_body"]}\n"""\n')
        f.write(f'draft_created_at = "{draft["draft_created_at"]}"\n')
        f.write(f'approved = false\n')
        f.write(f'needs_review = {str(draft["needs_review"]).lower()}\n')

    status = draft["reply_body"][:0] if not draft["reply_body"] else "📝"
    print(f"  {status} Staged: {draft['classification']} | {draft['subject'][:50]}")
    return filename


def log_classification(env, result):
    """Record a non-actionable thread as a log line instead of a staged draft."""
    from_list = env.get("from", [])
    sender = ""
    if from_list:
        first = from_list[0] if isinstance(from_list, list) else from_list
        sender = first.get("email", "") if isinstance(first, dict) else str(first)
    subject = env.get("subject", "").replace("\n", " ")
    with open(CLASSIFIED_LOG, "a") as log:
        log.write(
            f"{datetime.now(timezone.utc).isoformat()} | {result.get('classification', 'reference')} "
            f"| {env.get('id', '')} | {sender} | {subject}\n"
        )
    print(f"  ·  Logged ({result.get('classification', 'reference')}): {subject[:60]}")
    return None


def cmd_run():
    """Main: scan, classify, draft, stage."""
    print("=" * 60)
    print(f"📧 Email Triage Agent — run @ {datetime.now().isoformat()}")
    print(f"   Model: {MODEL} | Draft dir: {DRAFT_DIR}")
    print(f"   Staging: {','.join(sorted(STAGE_CLASSES))} (others logged, not staged)")
    print("=" * 60)

    envelopes = fetch_new_envelopes()
    if not envelopes:
        print("📭 No new emails to triage. Nothing to do.")
        return

    results = []
    processed_ids = set()
    for env in envelopes:
        result = classify_and_draft(env)
        processed_ids.add(env.get("id"))
        if result["classification"] in STAGE_CLASSES:
            draft_file = save_draft(env, result)
            staged = True
        else:
            draft_file = log_classification(env, result)
            staged = False
        results.append({
            "envelope_id": env.get("id"),
            "subject": env.get("subject", ""),
            "classification": result["classification"],
            "confidence": result.get("confidence", 0.0),
            "has_reply": bool(result.get("reply_body", "")),
            "needs_review": result.get("needs_review", False),
            "staged": staged,
            "draft_file": str(draft_file) if draft_file else None,
            "reasoning": result.get("reasoning", ""),
        })

    with open(INDEX_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    by_class = {}
    for r in results:
        c = r["classification"]
        by_class[c] = by_class.get(c, 0) + 1
    for cls, count in sorted(by_class.items(), key=lambda x: -x[1]):
        print(f"  {cls}: {count}")
    reply_count = sum(1 for r in results if r["has_reply"])
    staged_count = sum(1 for r in results if r["staged"])
    print(f"\n  Total threads: {len(results)}")
    print(f"  Drafts with replies: {reply_count}")
    print(f"  Staged drafts: {staged_count}  (logged, not staged: {len(results) - staged_count})")
    review_count = sum(1 for r in results if r.get("needs_review", False))
    print(f"  Classified by Clef-flash: {len(results)}  (zero-cost, no Devstral)")
    print(f"  Low-confidence / needs review: {review_count}")
    on_disk = len(list(DRAFT_DIR.glob("draft_*.toml")))
    print(f"  Review queue on disk: {on_disk} draft(s)")
    print(f"  Draft dir: {DRAFT_DIR}")
    print(f"  Classified log: {CLASSIFIED_LOG}")
    print(f"  Index: {INDEX_FILE}")
    print(f"\n  Review: python3 {__file__} review")
    print(f"  Send:   python3 {__file__} send  (only approved drafts)")

    # Persist processed IDs to avoid re-triaging
    save_processed_ids(processed_ids)


def cmd_review():
    """List all staged drafts."""
    drafts = sorted(DRAFT_DIR.glob("draft_*.toml"))
    if not drafts:
        print("📭 No staged drafts found.")
        return

    print(f"📋 {len(drafts)} staged drafts in {DRAFT_DIR}:\n")
    for f in drafts:
        content = f.read_text()
        approved = "approved = true" in content
        status = "✅ APPROVED" if approved else "⏳ PENDING"
        subject = re.search(r'subject = "(.*)"', content)
        cls = re.search(r'classification = "(.*)"', content)
        conf = re.search(r'classification_confidence = (.*)', content)
        sender = re.search(r'sender = (\[.*?\])', content, re.DOTALL)

        subj = (subject.group(1)[:60] if subject else "(no subject)")
        c = cls.group(1) if cls else "?"
        c2 = conf.group(1) if conf else "?"
        s = (sender.group(1)[:50] if sender else "?")

        print(f"  [{status}] {c} ({c2})")
        print(f"    From: {s}")
        print(f"    Subj: {subj}")
        print(f"    File: {f.name}")
        print()

    print(f"Draft dir: {DRAFT_DIR}")
    print(f"Discard:   python3 {__file__} discard <envelope_id> [...]")


def cmd_discard(ids):
    """Delete staged drafts for the given envelope ids and drop them from the index.

    The envelope id stays in .processed_ids so the thread is NOT re-triaged and the
    false positive cannot come back on the next run.
    """
    if not ids:
        print("Usage: triage.py discard <envelope_id> [...]")
        return 1

    dropped, missing = [], []
    for env_id in ids:
        matches = sorted(DRAFT_DIR.glob(f"draft_{env_id}_*.toml"))
        if not matches:
            missing.append(env_id)
            continue
        for f in matches:
            f.unlink()
            dropped.append(f.name)
        with open(DISCARD_LOG, "a") as log:
            log.write(f"{datetime.now(timezone.utc).isoformat()} | DISCARDED | {env_id} | {','.join(m.name for m in matches)}\n")

    if INDEX_FILE.exists():
        try:
            index = json.loads(INDEX_FILE.read_text())
            kept = [e for e in index if str(e.get("envelope_id")) not in set(ids)]
            INDEX_FILE.write_text(json.dumps(kept, indent=2) + "\n")
            print(f"  Index: {len(index)} → {len(kept)} entries")
        except Exception as e:
            print(f"  ⚠️  Index not updated: {e}")

    for n in dropped:
        print(f"  🗑️  Deleted: {n}")
    for m in missing:
        print(f"  ⚠️  No draft found for envelope {m}")

    print(f"\n📊 Discarded {len(dropped)} draft file(s) for {len(ids) - len(missing)} envelope(s)")
    print(f"   Log: {DISCARD_LOG}")
    print(f"   Note: envelope ids remain in .processed_ids — these threads will not be re-triaged.")
    return 0


def cmd_approve(ids):
    """Mark staged drafts as approved (gated send: does NOT send anything).

    Approval is a reversible local flag. Actual sending stays behind `triage.py send`,
    so a misclick can never put mail on the wire.
    """
    if not ids:
        print("Usage: triage.py approve <envelope_id> [...]")
        return 1

    approved, missing = [], []
    for env_id in ids:
        matches = sorted(DRAFT_DIR.glob(f"draft_{env_id}_*.toml"))
        if not matches:
            missing.append(env_id)
            continue
        for f in matches:
            content = f.read_text()
            if "approved = true" in content:
                print(f"  ↺  Already approved: {f.name}")
                approved.append(f.name)
                continue
            f.write_text(content.replace("approved = false", "approved = true", 1))
            with open(APPROVED_LOG, "a") as log:
                log.write(f"{datetime.now(timezone.utc).isoformat()} | APPROVED | {env_id} | {f.name}\n")
            approved.append(f.name)
            print(f"  👍 Approved: {f.name}")

    for m in missing:
        print(f"  ⚠️  No draft found for envelope {m}")

    print(f"\n📊 Approved {len(approved)} draft(s). Nothing was sent.")
    print(f"   Log: {APPROVED_LOG}")
    print(f"   Send: python3 {__file__} send  (only approved drafts)")
    return 0


def cmd_rules():
    """Show the manual sender rules currently in effect, and verify the file parses."""
    rules = load_rules(refresh=True)
    print(f"📋 Rules file: {RULES_FILE}")
    if not RULES_FILE.exists():
        print("   (does not exist yet — no manual rules active)")
    print()
    never = rules["never_draft"]
    always = rules["always_action"]
    draft_always = rules["always_draft"]
    print(f"🚫 never_draft ({len(never)}):")
    for p in never or ["   (none)"]:
        print(f"   - {p}")
    print()
    print(f"📌 always_draft ({len(draft_always)}):")
    for p in draft_always or ["   (none)"]:
        print(f"   - {p}")
    print()
    print(f"⚡ always_action ({len(always)}):")
    for p in always or ["   (none)"]:
        print(f"   - {p}")
    print()
    staged = [c for c in STAGE_CLASSES]
    print(f"Staging classes: {', '.join(sorted(staged))}")
    print("`suppressed` is NOT a staging class, so never_draft threads are logged, not staged.")
    return 0


def cmd_review_choices(limit=5):
    """Emit clarify-tool questions for the staged queue, ready to pass straight to `clarify`.

    The interactive review runs on the chat seat, not in cron: `clarify` needs a live user
    to click. One question per draft, three choices each, batched into calls of <=5
    questions (clarify's per-call cap). Output is JSON: a list of calls, each a list of
    question objects.
    """
    drafts = sorted(DRAFT_DIR.glob("draft_*.toml"))
    if not drafts:
        print("[]")
        return 0

    questions = []
    for f in drafts:
        content = f.read_text()
        env_id = f.name.split("_")[1]
        subj = (re.search(r'^subject = "(.*)"', content, re.M) or [None, "(no subject)"])[1]
        cls = (re.search(r'^classification = "(.*)"', content, re.M) or [None, "?"])[1]
        to = (re.search(r'^draft_to = "(.*)"', content, re.M) or [None, ""])[1]
        target = f" to {to}" if to else ""
        questions.append({
            "question": (
                f"[{env_id}] {cls}: {subj[:70]}{target}. What should I do with this draft?"
            ),
            # First choice is labelled "(Recommended)" by the clarify tool. Order it per
            # batch: mostly-noise queues lead with Discard, a real reply leads with Approve.
            "choices": ["Discard draft", "Approve and send", "Leave staged"],
        })

    calls = [questions[i:i + limit] for i in range(0, len(questions), limit)]
    print(json.dumps(calls, indent=2))
    print(f"\n# {len(drafts)} staged draft(s) in {DRAFT_DIR}", file=sys.stderr)
    print(f"# {len(calls)} clarify call(s), max {limit} questions each", file=sys.stderr)
    return 0


def cmd_send():
    """Send approved drafts via himalaya."""
    drafts = sorted(DRAFT_DIR.glob("draft_*.toml"))
    if not drafts:
        print("📭 No drafts found.")
        return

    sent = 0
    skipped = 0
    for f in drafts:
        content = f.read_text()
        if "approved = true" not in content:
            print(f"  ⏸️  Skipped (not approved): {f.name}")
            skipped += 1
            continue

        to_match = re.search(r'draft_to = "(.*)"', content)
        subj_match = re.search(r'draft_subject = "(.*)"', content)
        body_match = re.search(r'draft_body = """\n(.*)\n"""', content, re.DOTALL)

        to_addr = to_match.group(1) if to_match else ""
        subject = subj_match.group(1) if subj_match else ""
        body = body_match.group(1) if body_match else ""

        if not to_addr or not body:
            print(f"  ❌ Missing fields in {f.name}")
            skipped += 1
            continue

        print(f"  📤 Sending: {subject[:50]} → {to_addr}")
        try:
            result = subprocess.run(
                [HIMALAYA_BIN, "message", "send", "-a", "gmail",
                 "--from", "Patrick Ruster <ruster.patrick@gmail.com>",
                 "--to", to_addr,
                 "--subject", subject],
                input=body, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"  ✅ Sent: {subject[:50]}")
                with open(SENT_LOG, "a") as log:
                    log.write(f"{datetime.now(timezone.utc).isoformat()} | SENT | {subject} | {to_addr} | {f.name}\n")
                f.unlink()
                sent += 1
            else:
                print(f"  ❌ Failed: {result.stderr[:200]}")
                skipped += 1
        except Exception as e:
            print(f"  ❌ Error: {e}")
            skipped += 1

    print(f"\n📊 Send results: {sent} sent, {skipped} skipped")
    if sent:
        print(f"   Log: {SENT_LOG}")


def cmd_test_model():
    """Verify the local model is reachable."""
    print(f"Testing model: {MODEL}")
    try:
        result = llm_request(
            "Reply with exactly: DEVSTRAL_EMAIL_TEST_OK",
            max_tokens=8, temp=0.1
        )
        print(f"✅ Response: {result}")
        if "DEVSTRAL_EMAIL_TEST_OK" in result:
            print(f"✅ Model {MODEL} is reachable and responsive.")
            return True
        else:
            print(f"⚠️ Model responded but content unexpected.")
            return False
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False


def cmd_report():
    """Emit the full Discord report deterministically — no model formatting.

    Reads the last run's index (drafts.json) for counts, and the on-disk
    draft queue for the 'Needs you' items. The cron relays this verbatim, so
    the report shape can never drift.

    Delta behavior: drafts staged since the last report are listed in full;
    older drafts collapse to a 'Still pending' line so the report shows what's
    new, not the whole ledger.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    report_state = DRAFT_DIR / ".report_state.json"
    last_reported = ""
    if report_state.exists():
        try:
            last_reported = json.loads(report_state.read_text()).get("last_at", "")
        except Exception:
            pass

    # ── counts from the last run's index ──
    processed = 0
    staged_run = 0
    errors = 0
    results = []
    if INDEX_FILE.exists():
        try:
            results = json.loads(INDEX_FILE.read_text())
            processed = len(results)
            staged_run = sum(1 for r in results if r.get("staged"))
            errors = sum(1 for r in results
                         if (not r.get("staged"))
                         and ("failed" in r.get("reasoning", "").lower()
                              or "unreachable" in r.get("reasoning", "").lower()))
        except Exception:
            pass

    # ── the real queue: on-disk drafts ──
    drafts = []
    for f in sorted(DRAFT_DIR.glob("draft_*.toml")):
        content = f.read_text(errors="ignore")
        subj = re.search(r'^subject = "(.*)"', content, re.M)
        cls = re.search(r'^classification = "(.*)"', content, re.M)
        sender = re.search(r'^sender = (\[.*?\])', content, re.M | re.S)
        body = re.search(r'^draft_body = """\n(.*?)\n"""', content, re.M | re.S)
        rev = re.search(r'^needs_review = (.*)', content, re.M)
        to = re.search(r'^draft_to = "(.*)"', content, re.M)
        env = re.search(r'^id = "(.*)"', content, re.M)
        created = re.search(r'^draft_created_at = "(.*)"', content, re.M)
        name = ""
        if sender:
            try:
                for s in json.loads(sender.group(1)):
                    name = s.get("name", "")
                    if name:
                        break
            except Exception:
                name = sender.group(1)[:40]
        drafts.append({
            "id": env.group(1) if env else f.name,
            "subject": (subj.group(1) if subj else "(no subject)")[:55],
            "classification": cls.group(1) if cls else "?",
            "sender": name or "?",
            "body": (body.group(1).strip() if body else ""),
            "needs_review": (rev.group(1).strip() == "true" if rev else False),
            "to": to.group(1) if to else "",
            "created_at": created.group(1) if created else "",
            "file": f.name,
        })

    on_disk = len(drafts)

    # The report must be honest about the on-disk queue, not just the last run.
    actual = on_disk if on_disk else 0

    # ── friendly date, e.g. "Tue, Oct 27" ──
    friendly = datetime.now().strftime("%a, %b %-d")

    lines = []
    lines.append(f"📬 **Email Triage** — {friendly}")
    lines.append("")
    lines.append(f"📊 **{processed}** processed · **{actual}** staged · **{errors}** errors")

    # Split the queue: sendable vs empty/needs-review.
    needs = [d for d in drafts if d["body"] and d["classification"] != "noise"]
    review = [d for d in drafts if d["needs_review"] or not d["body"]]

    # Delta: what's new since the last report vs still pending.
    seen_before = set()
    if last_reported:
        try:
            seen_before = set(json.loads(report_state.read_text()).get("drafts_seen", []))
        except Exception:
            pass
    new_ids = set(d["id"] for d in drafts) - seen_before

    def fmt(d):
        marker = "🔴" if d["needs_review"] else "🟡"
        out = [f"{marker} **{d['id']}** · {d['sender']} — {d['subject']}"]
        if d["body"]:
            preview = d["body"].replace("\n", " ")[:160]
            out.append(f"  > {preview}")
        return out

    pending_count = sum(1 for d in drafts if d["id"] not in new_ids) if last_reported else 0

    if needs:
        new_needs = [d for d in needs if d["id"] in new_ids]
        old_needs = [d for d in needs if d["id"] not in new_ids]
        lines.append("")
        lines.append("📥 **Needs you**:")
        if new_needs:
            for d in new_needs:
                lines.extend(fmt(d))
        elif last_reported:
            lines.append(f"  (+{len(old_needs)} from earlier — see *Still pending* below)")
        else:
            for d in needs:
                lines.extend(fmt(d))
    if review:
        new_review = [d for d in review if d["id"] in new_ids]
        old_review = [d for d in review if d["id"] not in new_ids]
        lines.append("")
        lines.append("⚠️ **Needs attention** (no sendable body):")
        if new_review:
            for d in new_review:
                lines.extend(fmt(d))
        elif last_reported:
            lines.append(f"  (+{len(old_review)} from earlier — see *Still pending* below)")
        else:
            for d in review:
                lines.extend(fmt(d))
    if not drafts:
        lines.append("")
        lines.append("✅ All clear — nothing new since yesterday.")

    if pending_count:
        lines.append("")
        lines.append(f"⏳ *Still pending: {pending_count} older draft(s) not yet sent/discarded.*")

    lines.append("")
    lines.append("📭 Nothing sent · queue: `~/.hermes/email-drafts`")
    print("\n".join(lines))

    # Persist the report time so the next run shows only what's new.
    try:
        report_state.write_text(json.dumps({
            "last_at": datetime.now(timezone.utc).isoformat(),
            "drafts_seen": sorted(d["id"] for d in drafts),
        }))
    except Exception:
        pass
    return 0


def cmd_test_gate(args):
    """Run the clef gate on a single email for calibration debugging."""
    if len(args) < 3:
        print("Usage: triage.py test-gate '<from_email>' '<from_name>' '<subject>'")
        return 1
    from_email, from_name, subject = args[0], args[1], args[2]
    gate = clef_gate(from_email, from_name, subject)
    print(f"Clef gate: {from_name} <{from_email}> — {subject}")
    print(f"  pass:            {gate['pass']}")
    print(f"  reply_warranted: {gate['reply_warranted']}")
    print(f"  is_alert:        {gate['is_alert']}")
    print(f"  priority:        {gate['priority']}")
    print(f"  threshold:       {CLEF_GATE_THRESHOLD}")
    print(f"  reason:          {gate['reason']}")
    verdict = "-> proceeds to full classify" if gate["pass"] else "-> SKIPPED (classify saved)"
    print(f"  verdict:         {verdict}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: triage.py [run|review|report|rules|review-choices|approve <envelope_id> [...]|discard <envelope_id> [...]|send|test-model|test-gate <email> <name> <subject>]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "run":
        cmd_run()
    elif cmd == "review":
        cmd_review()
    elif cmd == "discard":
        sys.exit(cmd_discard(sys.argv[2:]))
    elif cmd == "approve":
        sys.exit(cmd_approve(sys.argv[2:]))
    elif cmd == "review-choices":
        cmd_review_choices()
    elif cmd == "report":
        sys.exit(cmd_report())
    elif cmd == "rules":
        sys.exit(cmd_rules())
    elif cmd == "send":
        cmd_send()
    elif cmd == "test-model":
        ok = cmd_test_model()
        sys.exit(0 if ok else 1)
    elif cmd == "test-gate":
        sys.exit(cmd_test_gate(sys.argv[2:]))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
