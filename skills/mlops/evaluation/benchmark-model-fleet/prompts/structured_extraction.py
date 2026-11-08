"""Structured extraction prompts — the most objectively scoreable family here.

The output either parses as JSON against the requested schema or it does not, so these
scorers are near-zero-judgement. Models that wrap JSON in prose or markdown fences fail
on strictness, which is the behaviour that actually breaks a pipeline.

Scoring: 5 checks x 0.2 = 1.0 max.
"""
import json
import re

PROMPTS = [
    ("ticket_to_json",
     'Extract structured data from this support ticket and return valid JSON only — no '
     'explanation, no markdown fences, just the JSON object.\n\n'
     'Ticket: "I\'ve been trying to cancel my Pro subscription since Tuesday but clicking '
     '\'Cancel Plan\' on the billing page gives me a white screen. Chrome 124 on Windows 11. '
     'My email is j.smith@example.com, order ORD-88821. This is urgent, my renewal is '
     'tomorrow and I\'ll be charged $149."\n\n'
     'Schema: { customer_email, order_id, plan, issue_type (bug|billing|account|other), '
     'severity (low|medium|high|critical), browser, os, renewal_risk (bool), '
     'summary (one sentence) }'),
    ("nested_schema",
     'Return valid JSON only, no markdown fences.\n\n'
     '"Order 5512 for Acme Corp shipped 2026-03-14 with two line items: 3 widgets at '
     '$12.50 each, and 1 gasket at $4.00. Ship to 42 Mill Lane, Bristol, UK."\n\n'
     'Schema: { order_id (int), customer (string), shipped (YYYY-MM-DD), '
     'items: [ { sku_name, qty (int), unit_price (float) } ], '
     'total (float), address: { street, city, country } }'),
    ("null_handling",
     'Return valid JSON only, no markdown fences. Use null for anything not stated — '
     'do not invent values.\n\n'
     '"Jane Okafor, senior engineer, joined in 2019. Reach her on jane@corp.io."\n\n'
     'Schema: { name, title, start_year (int), email, phone, department, manager }'),
    ("enum_discipline",
     'Return valid JSON only, no markdown fences.\n\n'
     '"The build failed again on the arm64 runner, third time today. Blocking the release."\n\n'
     'Schema: { category (infra|feature|docs|security), priority (p0|p1|p2|p3), '
     'component, recurring (bool), blocking_release (bool) }'),
]


def _parse(text):
    """Accept clean JSON; fall back to the first {...} so we can still score the content
    of a fenced answer, while the strictness check separately penalises the wrapper."""
    t = text.strip()
    try:
        return json.loads(t), True
    except ValueError:
        pass
    m = re.search(r'\{.*\}', t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0)), False
        except ValueError:
            return None, False
    return None, False


def _score(checks):
    score = sum(0.2 for _, passed in checks if passed)
    return min(round(score, 2), 1.0), [f"{'ok' if p else 'no'}: {n}" for n, p in checks]


def score_ticket_to_json(text):
    d, clean = _parse(text)
    if d is None:
        return 0.0, ["no parseable JSON"]
    keys = {"customer_email", "order_id", "plan", "issue_type", "severity",
            "browser", "os", "renewal_risk", "summary"}
    return _score([
        ("bare JSON, no fences", clean),
        ("all 9 keys", keys <= set(d)),
        ("email + order correct", d.get("customer_email") == "j.smith@example.com" and d.get("order_id") == "ORD-88821"),
        ("issue_type=bug", str(d.get("issue_type", "")).lower() == "bug"),
        ("renewal_risk true bool", d.get("renewal_risk") is True),
    ])


def score_nested_schema(text):
    d, clean = _parse(text)
    if d is None:
        return 0.0, ["no parseable JSON"]
    items = d.get("items") or []
    addr = d.get("address") or {}
    return _score([
        ("bare JSON, no fences", clean),
        ("order_id int 5512", d.get("order_id") == 5512),
        ("two line items", isinstance(items, list) and len(items) == 2),
        ("total 41.5", isinstance(d.get("total"), (int, float)) and abs(float(d["total"]) - 41.5) < 0.01),
        ("nested address", isinstance(addr, dict) and str(addr.get("city", "")).lower() == "bristol"),
    ])


def score_null_handling(text):
    d, clean = _parse(text)
    if d is None:
        return 0.0, ["no parseable JSON"]
    absent = ("phone", "department", "manager")
    return _score([
        ("bare JSON, no fences", clean),
        ("all 7 keys present", {"name", "title", "start_year", "email", "phone", "department", "manager"} <= set(d)),
        ("start_year int 2019", d.get("start_year") == 2019),
        ("email correct", d.get("email") == "jane@corp.io"),
        # The real test: did it invent a phone number rather than emit null?
        ("nulls not hallucinated", all(d.get(k) in (None, "", "null") for k in absent)),
    ])


def score_enum_discipline(text):
    d, clean = _parse(text)
    if d is None:
        return 0.0, ["no parseable JSON"]
    return _score([
        ("bare JSON, no fences", clean),
        ("category in enum", str(d.get("category", "")).lower() in ("infra", "feature", "docs", "security")),
        ("priority in enum", str(d.get("priority", "")).lower() in ("p0", "p1", "p2", "p3")),
        ("recurring true", d.get("recurring") is True),
        ("blocking_release true", d.get("blocking_release") is True),
    ])


SCORERS = {
    "ticket_to_json": score_ticket_to_json,
    "nested_schema": score_nested_schema,
    "null_handling": score_null_handling,
    "enum_discipline": score_enum_discipline,
}
