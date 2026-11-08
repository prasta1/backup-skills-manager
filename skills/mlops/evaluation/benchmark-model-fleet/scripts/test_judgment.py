"""Unit tests for the judgment prompts family (prompts/judgment.py).

Each scorer must discriminate: a crafted GOOD answer (matches the source
rubric's correct answer) must score substantially above a plausible-but-wrong
answer. Run after ANY change to prompts/judgment.py:

    python3 scripts/test_judgment.py

Prints PASS/FAIL per scorer and exits non-zero on any failure.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts"))
from judgment import SCORERS  # noqa: E402

GOOD = {
    "agentic_coding": (
        "The root cause is that JWTs are stateless — nothing revokes them. "
        "The fix is to add a token_version column to the user table in "
        "db.py, include it in the JWT at issuance, and bump it on password "
        "reset; auth.py then checks the version on every request before "
        "accepting the token. Tradeoff: adds a DB hit per request, but "
        "that's the cost of reliable invalidation. Test: issue a token, "
        "reset the password, assert the old token is rejected with 401 while "
        "a fresh token is accepted."
    ),
    "math_trains": (
        "Train A: leaves at 6:00, covers 90 km/h. By 8:00 it has gone "
        "180 km. Remaining distance is 600-180 = 420 km, closing speed "
        "90+120 = 210 km/h, so 420/210 = 2 hours. They meet at 10:00 AM, "
        "and train A has traveled 180 + 90*2 = 360 km from city A. "
        "Verify: train B travels 120*2 = 240 km, and 360 + 240 = 600. "
        "Correct."
    ),
    "logic_assignment": (
        "Constraint reasoning: Falcon needs 3, Griffin needs 2. Alice and "
        "Bob cannot be together. If Carol is on Falcon then Dan must be too. "
        "Eve refuses Bob. Valid assignments: 1) Falcon: Alice, Dan, Eve — "
        "Griffin: Bob, Carol. 2) Falcon: Bob, Carol, Dan — Griffin: Alice, "
        "Eve. These are the only two valid assignments. Best: Alice, Dan, "
        "and Eve on Falcon because Dan and Alice prefer to be paired and "
        "work well together, and it keeps Bob off Eve's team."
    ),
    "debugging_duplicates": (
        "The crash is a TypeError: lists are unhashable, so they can't go in "
        "a set or be used as dict keys. The fix converts each item to a "
        "hashable form before checking — tuple(item) when it's a list — and "
        "returns the deduplicated results. Edge case: booleans collide with "
        "ints, so [1, True, 1] — True hashes the same as 1 — must be "
        "handled by keeping seen in original order and returning a list "
        "instead of list(set(...)), which would itself crash on nested "
        "unhashables."
    ),
    "password_validator": (
        "```python\n"
        "from dataclasses import dataclass\n"
        "from typing import List\n"
        "import bcrypt\n"
        "import re\n"
        "\n"
        "@dataclass\n"
        "class ValidationResult:\n"
        "    valid: bool\n"
        "    failure_reasons: List[str]\n"
        "\n"
        "def validate_password(password: str, username: str, last_hashes: List[str]) -> ValidationResult:\n"
        "    reasons = []\n"
        "    if len(password) < 12: reasons.append('too short')\n"
        "    if not re.search(r'[A-Z]', password): reasons.append('no uppercase')\n"
        "    if not re.search(r'[a-z]', password): reasons.append('no lowercase')\n"
        "    if not re.search(r'\\d', password): reasons.append('no digit')\n"
        "    if not re.search(r'[!@#$%^&*]', password): reasons.append('no special')\n"
        "    if username.lower() in password.lower(): reasons.append('contains username')\n"
        "    if any(bcrypt.checkpw(password.encode(), h.encode()) for h in last_hashes):\n"
        "        reasons.append('recently used')\n"
        "    return ValidationResult(valid=not reasons, failure_reasons=reasons)\n"
        "```"
    ),
    "support_ticket_json": (
        '{"customer_email": "j.smith@example.com", "order_id": "ORD-88821", '
        '"plan": "pro", "issue_type": "billing", "severity": "critical", '
        '"browser": "chrome", "os": "windows", "affected_page": "billing", '
        '"renewal_risk": true, "summary": "Cannot cancel plan; renewal due '
        'tomorrow."}'
    ),
    "practical_reasoning": (
        "Go with Option B: add Redis and optimize the three slowest queries "
        "in about three weeks. Option A burns four months with a rewrite the "
        "team has no production Go experience for. The biggest risk is "
        "strategic: if the bottleneck isn't I/O-bound, caching won't get "
        "p95 under 500ms — so profile first to validate the hypothesis "
        "before committing. Option C just papers over latency with monthly "
        "cost against a 14-month runway."
    ),
}

BAD = {
    "agentic_coding": (
        "The bug is probably in the frontend. I would log in again and see "
        "if it works. Maybe clear the localStorage token."
    ),
    "math_trains": (
        "They meet at 11:30 AM, about 300 km from city A. Close enough."
    ),
    "logic_assignment": (
        "Put Alice and Bob on Falcon because they are the best engineers. "
        "Then everyone else on Griffin. Done."
    ),
    "debugging_duplicates": (
        "The function is slow. Wrap it in try/except and return []. That "
        "fixes everything."
    ),
    "password_validator": (
        "```python\n"
        "import requests, os, sys, json, hashlib, bcrypt\n"
        "\n"
        "def check_password(pwd, user, old):\n"
        "    \"\"\"Validates a password thoroughly with best practices, "
        "logging every attempt and telling the user exactly what to fix, "
        "plus an example usage block and a main() for CLI testing.\"\"\"\n"
        "    ok = len(pwd) >= 12\n"
        "    return ok\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    print(check_password('test', 'u', []))\n"
        "```"
    ),
    "support_ticket_json": (
        '```json\n{"customer_email": "j.smith@example.com", "order_id": '
        '"ORD-88821", "plan": "pro", "issue_type": "bug", "severity": '
        '"high", "browser": "chrome", "os": "windows", "affected_page": '
        '"billing", "renewal_risk": false, "summary": "White screen on '
        'billing page."}\n```\n'
        "Here is the data you asked for. Let me know if you need anything "
        "else!"
    ),
    "practical_reasoning": (
        "Definitely Option A, rewrite in Go — performance is the only thing "
        "that matters and Rust developers will love it. Risks: maybe a bit "
        "of cache invalidation."
    ),
}


def main():
    failures = 0
    for name in sorted(SCORERS):
        scorer = SCORERS[name]
        good_score, _ = scorer(GOOD[name])
        bad_score, _ = scorer(BAD[name])
        ok = good_score >= 0.6 and bad_score < good_score
        status = "PASS" if ok else "FAIL"
        print(f"{status} {name:<22} good={good_score:.2f} bad={bad_score:.2f}")
        if not ok:
            failures += 1
    if failures:
        print(f"\n{failures} FAILED")
        sys.exit(1)
    print("\nall judgment scorers pass")


if __name__ == "__main__":
    main()
