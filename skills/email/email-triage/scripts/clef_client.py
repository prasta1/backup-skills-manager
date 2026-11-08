#!/usr/bin/env python3
"""
laya_client.py — Local-first email triage: Laya classification + BGE-M3 retrieval drafting.

Architecture (informed by the Jev email-triage pattern):
  1. LAYA (421M, MPS, ~86ms): classify sender+subject+body with ALL questions in ONE call
     (6-class taxonomy + 7 routing rules = 13 questions; extra signals cost no extra round-trip,
      per the TypeSafe question-multiplexing pattern).
  2. BATCH: classify_batch() runs N emails concurrently via ThreadPoolExecutor.
  3. DRAFTING tier: BGE-M3 retrieval over Patrick's sent mail → if hit, adapt the template.
     If miss, generate with ministral-3-3b (3B, ~8x faster than Devstral-24b on MPS).
  4. FALLBACK: Devstral-24b only if retrieval + ministral both fail.

All inference is local (Laya :8000, llama-swap :9292). Zero per-token cost.
Env: LAYA_URL, LAYA_API_KEY, LLAMA_SWAP_URL, DRAFT_MODEL, EMAIL_TRIAGE_MODEL.
"""
import json, os, time, numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

# ── Endpoints ─────────────────────────────────────────────────────────────────
CLEF_URL      = os.environ.get("CLEF_URL", "http://127.0.0.1:8001/v1/systemone")
LLAMACPP_URL  = os.environ.get("LLAMA_SWAP_URL", "http://127.0.0.1:9292/v1")
_clef_key_file = Path(os.path.expanduser("~/.hermes/secrets/clef.key"))
CLEF_KEY = os.environ.get("CLEF_API_KEY") or (_clef_key_file.read_text().strip() if _clef_key_file.exists() else "")
# llama-swap enforces an apiKey (2026-10-14). The key lives in ~/.hermes/.env as
# HERMES_CUSTOM_LLAMA_SWAP_API_KEY (the same file Hermes loads at startup); read it
# directly so this script works standalone too, not only under a hermes cron env.
def _llama_swap_key() -> str:
    k = os.environ.get("HERMES_CUSTOM_LLAMA_SWAP_API_KEY", "").strip()
    if k and k not in ("no-key-required", "no-key", "none"):
        return k
    try:
        for _ln in Path(os.path.expanduser("~/.hermes/.env")).read_text().splitlines():
            if _ln.startswith("HERMES_CUSTOM_LLAMA_SWAP_API_KEY="):
                v = _ln.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    except OSError:
        pass
    return ""
LLAMA_SWAP_KEY = _llama_swap_key()
DRAFT_MODEL    = os.environ.get("DRAFT_MODEL", "ms-devstral-24b")
DEVSTRAL_MODEL = os.environ.get("EMAIL_TRIAGE_MODEL", "ms-devstral-24b")

# ── Classification questions: 6-class taxonomy + 7 routing rules (one call) ──
CLASSIFY_QUESTIONS = {
    "triage_class": {"type": "choice", "instructions": "How should Patrick handle this email?",
        "criteria": {"urgent-reply": "real person, needs a reply within 24h",
                     "reply": "real person, needs a reply but not urgent",
                     "action": "needs action (review a doc, click, follow up) but no reply",
                     "waiting": "awaiting Patrick's or a third party's response",
                     "reference": "keep for info, no action needed",
                     "noise": "newsletter, promo, automated alert, no action"}},
    "invoice":        {"type": "noul", "instructions": "Is this an invoice, receipt, bill, or payment notification?"},
    "brand_deal":     {"type": "noul", "instructions": "Is this a brand, partnership, or sponsorship deal offer?"},
    "scam_phishing":  {"type": "noul", "instructions": "Does this look like a scam or phishing attempt?"},
    "email_type":     {"type": "choice", "instructions": "What type of email is this?",
        "criteria": {"transactional": "order confirmations, receipts, shipping",
                     "promotional": "newsletters, ads, marketing",
                     "personal": "from a known individual",
                     "notification": "alerts, status updates, system notices",
                     "other": "none of the above"}},
    "urgency":        {"type": "score", "instructions": "How urgent is a response or action?",
                       "criteria": ["low", "medium", "high"]},
    "sponsor_fit":    {"type": "noul", "instructions": "Would Patrick's audience or business benefit from a sponsored mention?"},
    "spam_likelihood":{"type": "score", "instructions": "How likely is this to be spam or unwanted?",
                       "criteria": ["no_spam", "maybe", "spam"]},
}

# ── Low-level HTTP ─────────────────────────────────────────────────────────────
def _post(url, payload, timeout=15, auth_key=None):
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if auth_key:
        headers["Authorization"] = "Bearer " + auth_key
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def _answer(ans):
    """Extract a normalized value from a Laya/Score answer, handling all three types."""
    t = ans.get("type")
    if t == "choice":
        return ans.get("choice")
    if t == "noul":
        return float(ans.get("noul", 0))
    if t == "score":
        probs = ans.get("probabilities", {})
        legend = ans.get("legend", {})
        best = max(probs, key=probs.get) if probs else ""
        return legend.get(best, best) if best else None
    return None

# ── Laya classification ────────────────────────────────────────────────────────
def classify_email(state, questions=None):
    """Classify one email: sender + subject + body → all answers in a single Laya call (~86ms).

    Returns a flat dict: {triage_class, invoice, brand_deal, scam_phishing,
    email_type, urgency, sponsor_fit, spam_likelihood, _confidence: max}.
    """
    data = _post(CLEF_URL, {"state": state, "questions": questions or CLASSIFY_QUESTIONS, "model": "clef-flash"}, auth_key=CLEF_KEY)
    answers = data["answers"]
    result = {}
    best_conf = 0.0
    for key, ans in answers.items():
        result[key] = _answer(ans)
        best_conf = max(best_conf, float(ans.get("answer_confidence", ans.get("confidence", 0))))
    result["_confidence"] = round(best_conf, 3)
    return result

def classify_batch(emails, max_workers=None, timeout=30):
    """Classify multiple emails concurrently. Returns list of result dicts.

    emails: list of (state_str,) or list of state_str.
    Uses ThreadPoolExecutor — tests Laya server concurrency on MPS.
    """
    states = [e[0] if isinstance(e, tuple) else e for e in emails]
    max_workers = max_workers or min(8, len(states)) or 1
    results = [None] * len(states)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_idx = {ex.submit(classify_email, s): i for i, s in enumerate(states)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result(timeout=timeout)
            except Exception as e:
                results[idx] = {"triage_class": "reference", "_error": str(e), "_confidence": 0.0}
    return results

# ── Retrieval-augmented drafting ───────────────────────────────────────────────
def _embed(text, model="ms-bge-m3-1024", dims=1024):
    """Embed text via llama-swap BGE-M3 endpoint."""
    payload = {"model": model, "input": text}
    data = _post(LLAMACPP_URL + "/embeddings", payload, timeout=30, auth_key=LLAMA_SWAP_KEY)
    return np.array(data["data"][0]["embedding"], dtype=np.float32)

def load_index(path=None):
    """Load the sent-mail embedding index (built by sent_index.py)."""
    p = Path(path or os.path.expanduser("~/.hermes/email-drafts/sent_index.npz"))
    if not p.exists():
        return None
    return np.load(p, allow_pickle=True)

def retrieve_and_draft(state, classification, index_path=None, top_k=3, score_threshold=0.75):
    """Draft a reply using retrieval + ministral generation. Returns draft text or None.

    Tier 1: Retrieve Patrick's 3 most similar past replies (BGE-M3 cosine) and adapt.
    Tier 2: If no strong match, generate with ministral-3-3b using retrieved context.
    Tier 3: If both fail, return None (caller falls back to Devstral).
    """
    index = load_index(index_path)
    if index is None:
        return None  # no sent index → skip straight to Devstral

    # Embed the new email
    query_emb = _embed(state)
    db_embs = index["embeddings"]
    sims = (db_embs @ query_emb) / (np.linalg.norm(db_embs, axis=1) * np.linalg.norm(query_emb) + 1e-9)
    order = np.argsort(sims)[::-1][:top_k]
    best_score = float(sims[order[0]])

    past_replies = []
    for i in order:
        if sims[i] < 0.3:
            break
        past_replies.append({
            "from": str(index["froms"][i]), "to": str(index["tos"][i]),
            "subject": str(index["subjects"][i]), "date": str(index["dates"][i]),
            "reply_body": str(index["replies"][i]), "score": round(float(sims[i]), 3),
        })

    if best_score >= score_threshold and past_replies:
        # Strong match: adapt the retrieved reply to the new context
        return _adapt_past_reply(state, classification, past_replies)
    elif past_replies:
        # Weak match: use past replies as few-shot context for ministral generation
        return _generate_with_context(state, classification, past_replies)
    else:
        # No retrieval context: fresh generation with ministral
        return _generate_fresh(state, classification)

def _adapt_past_reply(state, classification, past_replies):
    """Adapt a retrieved past reply to the new email context (ministral, ~1.5s)."""
    retrieved = "\n---\n".join(
        f"[score={r['score']}] Reply to \"{r['subject']}\":\n{r['reply_body']}"
        for r in past_replies[:2]
    )
    prompt = f"""You are drafting an email reply for Patrick. Adapt the most relevant past reply below
to the new email, preserving Patrick's voice (concise, dry, half-a-step-ahead wit). Update any
specific facts (dates, names, amounts) to match the new context. Keep it short.

New email:
---
{state}
---

Patrick's past similar reply (adapt, don't copy verbatim):
---
{retrieved}
---

Respond with ONLY the adapted reply body. No preamble."""
    return _post(LLAMACPP_URL + "/chat/completions",
                 {"model": DRAFT_MODEL, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 512, "temperature": 0.3}, timeout=30, auth_key=LLAMA_SWAP_KEY)["choices"][0]["message"]["content"].strip()

def _generate_with_context(state, classification, past_replies):
    """Generate a draft using past replies as few-shot context (ministral)."""
    context = "\n---\n".join(r["reply_body"] for r in past_replies[:2])
    prompt = f"""You are Patrick's email assistant. Draft a concise reply in Patrick's voice
(dry, precise, half-a-step-ahead wit; no fluff). Below are examples of Patrick's
reply style. Adapt to the new email.

Writing style examples from Patrick's past replies:
---
{context}
---

New email:
---
{state}
---

Classification: {classification.get('triage_class', 'reply')}. Urgency: {classification.get('urgency', 'medium')}.

Reply with ONLY the draft body. No preamble, no placeholders."""
    try:
        return _post(LLAMACPP_URL + "/chat/completions",
                     {"model": DRAFT_MODEL, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 512, "temperature": 0.3}, timeout=30, auth_key=LLAMA_SWAP_KEY)["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

def _generate_fresh(state, classification):
    """No retrieval context found. Generate a fresh draft (ministral)."""
    return _generate_with_context(state, classification, [])

# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"

    if cmd == "test":
        # Smoke test: classify a sample email against local Laya
        state = "From: Rachel Provan <rachel@provan.dev>\nSubject: Quick Q on the Vermont site-build timeline\n\nHey Patrick — circling back on the timeline for the Cambridge shop CNC enclosure. Are we still on for next week?"
        t0 = time.time()
        r = classify_email(state)
        elapsed = time.time() - t0
        print(json.dumps(r, indent=2))
        print(f"Latency: {elapsed:.3f}s")
    elif cmd == "batch-bench":
        # Benchmark: classify N copies concurrently to test Laya throughput
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        state = "From: test@example.com\nSubject: Invoice #12345 for September hosting\n\nPlease review and confirm payment of $450."
        states = [state] * n
        t0 = time.time()
        results = classify_batch(states, max_workers=8)
        elapsed = time.time() - t0
        per_email = elapsed / n
        print(f"Batch classified {n} emails in {elapsed:.1f}s ({per_email*1000:.0f}ms/email)")
        print(f"Extrapolated: 1000 emails in {per_email * 1000:.0f}s with batch=8")
        print(f"Results: {len(results)} classified, {sum(1 for r in results if r.get('invoice') and r['invoice'] > 0.5)} detected as invoices")
