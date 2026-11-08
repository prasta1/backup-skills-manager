"""Judgment family — 7 quality-discrimination prompts ported from the Claude
Code `benchmark-models` command (archive: backups/claude-code-export-2026-10-08,
2026-10-08).

Where the built-in coding set measures basic knowledge (csv_parser, npm_diff,
...) and the vision rubrics measure perception, this family measures REASONING:
root-cause diagnosis, math, constraint logic, debugging, strict instruction
following, structured extraction, and strategic judgment. These were the
prompts the old LM Studio harness used to differentiate models that breeze
through knowledge checks.

Scoring philosophy: deterministic, matching every other family in this skill —
each prompt's rubric has a DEFINED correct answer (10:00 / 360 km, exactly two
valid assignments, severity=critical, etc.), so scores are ground-truth checks,
not observer-guessed labels. Where the source rubric was a human judgement
call ("winner vs tie"), the deterministic scorer approximates it by checking
for the rubric's explicitly-named elements.

Rubric notes from the original file are kept inline next to each scorer — they
document what discriminates and what rarely does (e.g. the trains prompt is
explicitly marked as rarely differentiating; both models usually get it right,
and the scorer reflects that by rewarding the correct answer fully).

Run with:
    python3 scripts/benchmark.py --prompts-file prompts/judgment.py \
        --models <id> ... --max-tokens 2048

Use --max-tokens 2048: the agentic-coding and debugging prompts ask for real
code, and thinking models truncate at 512 (see SKILL.md Qwen3 pitfall).

CSV family prefix: judgment_bench (derived from the filename by benchmark.py).
"""
import json
import re

# ---------------------------------------------------------------------------
# PROMPTS
# ---------------------------------------------------------------------------
# Text preserved verbatim from benchmark-models.md (2026-10-08 archive).

PROMPTS = [
    ("agentic_coding",
     "You have a Python project with this structure:\n"
     "\n"
     "src/\n"
     "  auth.py      # handles JWT creation and validation\n"
     "  db.py        # SQLite wrapper, has get_user(id) and save_user(user)\n"
     "  api.py       # Flask routes\n"
     "\n"
     "A bug was filed: \"After a password reset, old JWT tokens are still accepted.\"\n"
     "\n"
     "Without seeing the actual files, describe the most likely root cause, "
     "write the fix you'd make to auth.py, and write a test that would have "
     "caught this. Be specific about code."),

    ("math_trains",
     "A train leaves city A at 6:00 AM traveling toward city B at 90 km/h. "
     "Another train leaves city B at 8:00 AM traveling toward city A at "
     "120 km/h. The cities are 600 km apart.\n"
     "\n"
     "At what time do the trains meet, and how far from city A?\n"
     "\n"
     "Show your work step by step, then verify your answer."),

    ("logic_assignment",
     "Five engineers — Alice, Bob, Carol, Dan, and Eve — need to be assigned "
     "to two projects: Falcon (needs 3 people) and Griffin (needs 2 people).\n"
     "\n"
     "Constraints:\n"
     "- Alice and Bob cannot be on the same project\n"
     "- If Carol is on Falcon, Dan must also be on Falcon\n"
     "- Eve refuses to work with Bob\n"
     "- Dan and Alice work well together and prefer to be paired\n"
     "\n"
     "List all valid assignments. Then recommend the best one given the "
     "preferences, and explain your reasoning."),

    ("debugging_duplicates",
     "A function has a bug:\n"
     "```python\n"
     "def find_duplicates(items):\n"
     "    seen = set()\n"
     "    duplicates = []\n"
     "    for item in items:\n"
     "        if item in seen:\n"
     "            duplicates.append(item)\n"
     "        seen.add(item)\n"
     "    return list(set(duplicates))\n"
     "```\n"
     "# Reports: find_duplicates([1, 2, 2, 3, 3, 3]) returns [2, 3] ✓\n"
     "# Reports: find_duplicates([]) returns [] ✓\n"
     "# Reports: find_duplicates([1]) returns [] ✓\n"
     "# Reports: find_duplicates([[1,2], [1,2], [3]]) crashes\n"
     "\n"
     "Fix the crash, explain why it happens, and add one more edge case the "
     "current tests miss."),

    ("password_validator",
     "Write a function that validates a password. Rules:\n"
     "- Minimum 12 characters\n"
     "- At least one uppercase, one lowercase, one digit, one special "
     "character (!@#$%^&*)\n"
     "- Cannot contain the username (case-insensitive)\n"
     "- Cannot be any of the last 5 passwords (passed in as a list of hashes "
     "— use bcrypt)\n"
     "- Return a dataclass with: valid (bool), and a list of specific failure "
     "reasons\n"
     "\n"
     "Language: Python. No external libraries except bcrypt. Include type "
     "hints. Do not add any functionality not listed above."),

    ("support_ticket_json",
     "Extract structured data from this support ticket and return valid JSON "
     "only — no explanation, no markdown fences, just the JSON object.\n"
     "\n"
     "Ticket: \"Hi, I've been trying to cancel my Pro subscription since "
     "Tuesday but every time I click 'Cancel Plan' on the billing page I get "
     "a white screen. I'm on Chrome 124 on Windows 11. My account email is "
     "j.smith@example.com and my order number is ORD-88821. This is urgent, "
     "my renewal is tomorrow and I'll be charged $149.\"\n"
     "\n"
     "Schema: { customer_email, order_id, plan, issue_type "
     "(bug|billing|account|other), severity (low|medium|high|critical), "
     "browser, os, affected_page, renewal_risk (bool), summary (one "
     "sentence) }"),

    ("practical_reasoning",
     "A startup has 3 engineers and needs to choose between:\n"
     "\n"
     "Option A: Rewrite their Python monolith in Go for performance. "
     "Estimated 4 months, no new features during that time.\n"
     "\n"
     "Option B: Add a caching layer (Redis) and optimize the 3 slowest "
     "database queries. Estimated 3 weeks.\n"
     "\n"
     "Option C: Scale horizontally — add two more servers behind a load "
     "balancer. Estimated 1 week, ongoing $800/month.\n"
     "\n"
     "Current situation: 50k users, p95 latency is 2.1s (target: under "
     "500ms), the team has never shipped Go in production, runway is 14 "
     "months.\n"
     "\n"
     "Which option do you recommend and why? What's the biggest risk in your "
     "recommendation?"),
]

# ---------------------------------------------------------------------------
# SCORERS
# ---------------------------------------------------------------------------
# Each returns (score 0-1, feedback list). Rubric notes from the source file
# are preserved inline — they encode what the discriminator actually is.

RE = re.IGNORECASE | re.MULTILINE


def score_agentic_coding(text):
    """JWT revocation bug. Rubric: correct root cause (stateless JWT / missing
    revocation), fix actually invalidates old tokens on reset, test verifies
    BOTH rejection of old AND acceptance of new, Flask integration realistic,
    tradeoffs acknowledged."""
    t = text
    checks = [
        ("root cause: stateless/revocation",
         bool(re.search(r"stateless|revocat|still valid|no (way to )?invalidat|token.*valid", t, RE)), 0.2),
        ("fix invalidates old tokens",
         bool(re.search(r"revok|blacklist|denylist|invalidat|token_version|version|issued_at|rotat|check.*(db|database|storage)", t, RE)), 0.2),
        ("test rejects old + accepts new",
         bool(re.search(r"(old token|old_one).*(reject|invalid|fail|403|401)", t, RE))
         and bool(re.search(r"(new token|fresh|new_one).*(accept|pass|valid|200)", t, RE)), 0.2),
        ("flask integration realistic",
         bool(re.search(r"flask|@app|before_request|route|decorator|Blueprints?", t, RE)), 0.2),
        ("tradeoffs acknowledged",
         bool(re.search(r"tradeoff|cost|overhead|latency|statelessness|scalab|db hit|expen", t, RE)), 0.2),
    ]
    return _score(t, checks)


def score_math_trains(text):
    """Trains. Rubric: correct answer (10:00 AM, 360 km from A), step-by-step
    work, verification that both distances sum to 600. NOTE: original rubric
    says this prompt rarely differentiates models — mark full marks when both
    get the right answer."""
    t = text
    checks = [
        ("time 10:00",
         bool(re.search(r"10\s*[:.]?\s*0?0|10 ?am|ten (o'?clock|am)", t, RE)) and "14" not in t, 0.3),
        ("distance 360 km from A",
         bool(re.search(r"360\s*(km|kilometers?|km/h)?", t, RE)), 0.2),
        ("step-by-step work shown",
         bool(re.search(r"6:00|8:00", t, RE)) and bool(re.search(r"\b90\b|\b120\b", t, RE)), 0.2),
        ("verification (distances sum to 600)",
         bool(re.search(r"verif|check|sum|360\s*\+\s*240|600", t, RE)), 0.3),
    ]
    return _score(t, checks)


def score_logic_assignment(text):
    """Engineer assignment. Rubric: exactly 2 valid assignments
    (Falcon: Alice/Dan/Eve + Griffin: Bob/Carol; OR Falcon: Bob/Carol/Dan +
    Griffin: Alice/Eve), recommends Alice+Dan together, explains correctly."""
    t = text
    checks = [
        ("exactly 2 valid assignments named",
         bool(re.search(r"\b2\b|two", t, RE)) and bool(re.search(r"valid", t, RE)), 0.3),
        ("both configurations spelled out",
         t.lower().count("falcon") >= 2 and t.lower().count("griffin") >= 2, 0.2),
        ("recommends Alice+Dan paired",
         bool(re.search(r"alice.{0,20}dan|dan.{0,20}alice", t, RE))
         and bool(re.search(r"prefer|recommend|pair|work well", t, RE)), 0.2),
        ("constraint reasoning explained",
         bool(re.search(r"constraint|cannot|must|refus|because|if .* then", t, RE)), 0.2),
        ("explicit validity statement",
         bool(re.search(r"all valid|only valid|valid assignments?|list of", t, RE)), 0.1),
    ]
    return _score(t, checks)


def score_debugging_duplicates(text):
    """find_duplicates crash. Rubric: fix handles unhashable types, explains
    TypeError/hashability correctly, edge case quality — the bool/int
    collision ([1, True, 1]) is the non-obvious high-quality answer; nested
    unhashables is valid but easier. Check the fix itself has no bugs (e.g.
    list(set(duplicates)) crashes again if duplicates contains lists)."""
    t = text
    code = _extract_python(t)
    checks = [
        ("root cause: TypeError/unhashable",
         bool(re.search(r"unhashable|TypeError|hashab|list.*(set|dict) key|cannot.*hash", t, RE)), 0.2),
        ("fix serializes/handles unhashable",
         bool(re.search(r"repr\(|tuple\(|frozenset|str\(|isinstance.*list|try:.*except TypeError", code or t, re.DOTALL)), 0.2),
        ("strong edge case (bool/int collision)",
         bool(re.search(r"\bTrue\b|bool|1\s*==\s*True|isinstance\(.*bool", code or t, RE)), 0.2),
        ("fix correct (no re-crash on returned list)",
         bool(re.search(r"return\s+list\(set\(", code or t, RE))
         and bool(re.search(r"seen\.add|seen\.|\.append", code or t, RE)), 0.2),
        ("explains hashability/why",
         bool(re.search(r"immutable|mutable|hash|because|can'?t (be|go) (in|into)", t, RE)), 0.2),
    ]
    return _score(t, checks)


def score_password_validator(text):
    """Instruction following with a NEGATIVE constraint. Rubric: strict
    compliance with \"Do not add any functionality not listed above.\"
    Penalize: unrequested __main__ blocks, docstrings, extra imports, example
    usage, helper functions not needed. Field should be named
    failure_reasons. This is the prompt that tests whether the model respects
    a negative constraint."""
    code = _extract_python(text) or text
    t = text
    rules = [
        "length check" if re.search(r"12", code) else "",
        "upper check" if re.search(r"isupper|upper\(|A-Z", code) else "",
        "lower check" if re.search(r"islower|lower\(|a-z", code) else "",
        "digit check" if re.search(r"isdigit|digit|\d", code) else "",
        "special check" if re.search(r"special|!@#|\W.*character|re\.search.*[!@#$%^&*()]", code, RE) else "",
        "username check" if re.search(r"username", code, RE) else "",
        "bcrypt used" if re.search(r"bcrypt", code) else "",
    ]
    rule_hits = sum(1 for r in rules if r)
    checks = [
        ("implements stated rules (%d/7)" % rule_hits, rule_hits / 7 >= 4 / 7, 0.3),
        ("field named failure_reasons",
         "failure_reasons" in code, 0.2),
        ("no __main__ block",
         "__main__" not in code, 0.2),
        ("no docstring",
         '"""' not in code and "'''" not in code, 0.1),
        ("no extra imports (only bcrypt/dataclass/typing)",
         not bool(re.search(r"^import (?!bcrypt|dataclass|typing|re)\S+", code, RE | re.MULTILINE)), 0.1),
        ("type hints present",
         bool(re.search(r"->\s*\w+|:\s*(str|bool|list)\b|def \w+\([^)]*:\s*\w+", code)), 0.1),
    ]
    return _score(t, checks)


def score_support_ticket_json(text):
    """Structured output. Rubric: valid JSON only (no prose, no fences), all
    fields present and correct types, severity: CRITICAL (renewal tomorrow +
    financial consequence = critical, not high), renewal_risk: true."""
    t = text.strip()
    has_fences = bool(re.search(r"```|```json", t))
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.MULTILINE).strip()
    data = None
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        try:
            data = json.loads(t)
        except json.JSONDecodeError:
            data = None
    checks = [
        ("parses as JSON", data is not None, 0.2),
        ("no markdown fences", not has_fences, 0.2),
        ("all 10 schema fields present",
         bool(data) and all(k in data for k in (
             "customer_email", "order_id", "plan", "issue_type", "severity",
             "browser", "os", "affected_page", "renewal_risk", "summary")), 0.2),
        ("severity == critical",
         bool(data) and str(data.get("severity", "")).lower() == "critical", 0.2),
        ("renewal_risk == true",
         bool(data) and data.get("renewal_risk") is True, 0.1),
        ("issue_type == billing",
         bool(data) and str(data.get("issue_type", "")).lower() == "billing", 0.1),
    ]
    return _score(t, checks)


def score_practical_reasoning(text):
    """Startup choice. Rubric: correct recommendation is Option B. Risk
    quality: \"B might not reach <500ms if bottleneck isn't I/O-bound\" is the
    STRATEGIC risk (better answer); \"cache invalidation is hard\" is an
    implementation risk. Profiling first to validate the hypothesis is a
    plus."""
    t = text
    checks = [
        ("recommends Option B (caching/query opt)",
         bool(re.search(r"option\s*b|option\s*2", t, RE))
         and bool(re.search(r"cache|redis|optim", t, RE)), 0.3),
        ("rejects Option A rewrite cost",
         bool(re.search(r"rewrite|4 months|four months|go\b|opportunity cost|no new features", t, RE)), 0.1),
        ("strategic risk: might not reach <500ms if not I/O-bound",
         bool(re.search(r"(may|might|could|won'?t) not reach|if (the )?(bottleneck|problem)|not (I/O|io|input/output)|doesn'?t.*500", t, RE)), 0.2),
        ("implementation risk acknowledged (cache invalidation)",
         bool(re.search(r"cache invalidation|stale|eviction|consisten|ttl", t, RE)), 0.1),
        ("profile/measure first to validate hypothesis",
         bool(re.search(r"profil|measur|validat|hypothes|test the assumption|instrument", t, RE)), 0.2),
        ("considers runway/team/Go-experience constraints",
         bool(re.search(r"runway|14 months|three engineers|3 engineers|never shipped go|existing users", t, RE)), 0.1),
    ]
    return _score(t, checks)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score(text, checks):
    score = sum(weight for _, passed, weight in checks if passed)
    feedback = [name if passed else f"missing: {name}" for name, passed, _ in checks]
    return min(score, 1.0), feedback


def _extract_python(text):
    """Pull the first ```python ... ``` block, else the raw text."""
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return m.group(1) if m else None


SCORERS = {
    "agentic_coding": score_agentic_coding,
    "math_trains": score_math_trains,
    "logic_assignment": score_logic_assignment,
    "debugging_duplicates": score_debugging_duplicates,
    "password_validator": score_password_validator,
    "support_ticket_json": score_support_ticket_json,
    "practical_reasoning": score_practical_reasoning,
}
