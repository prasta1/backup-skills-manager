"""Coding benchmark prompts and deterministic quality scorers.

Each prompt has a 0-1 quality scorer that checks for key elements in the
model's response. These are deterministic pattern-matchers, not LLM judges —
they're fast, repeatable, and don't require a separate model call.

Scoring: each check is worth 0.2 points (5 checks = 1.0 max).
"""
import re

CODING_PROMPTS = [
    ("csv_parser",
     "Write a Python function that parses a CSV file and returns rows where the 'status' column equals 'active'. Handle edge cases like missing columns, empty files, or malformed rows."),
    ("go_json_tags",
     "Given a Go struct, explain how you'd serialize it to JSON with custom field mappings using struct tags. Show an example struct with snake_case JSON output."),
    ("rust_closure_borrow",
     "Debug this Rust code: a closure that tries to borrow `mut self` — what's wrong and how to fix it? Show a minimal example."),
    ("npm_diff",
     "Describe the difference between `npm install` and `npm ci`. When would you use each, and what are the performance implications?"),
]

VISION_PROMPTS = [
    ("describe_scene",
     "Describe what you see in this image in detail."),
    ("count_objects",
     "How many people are in this image? Count carefully and explain your reasoning."),
    ("technical_detail",
     "What technical equipment or tools can you identify? List each one and its likely purpose."),
    ("contextual_reasoning",
     "If this scene represents a real situation, what activity or event is taking place? What evidence supports your conclusion?"),
]


def score_csv_parser(text):
    score = 0.0
    feedback = []
    code_match = re.search(r'```python\n(.*?)```', text, re.DOTALL)
    if not code_match:
        code_match = re.search(r'(def .*?)(?=\n\n|\nclass |\Z)', text, re.DOTALL)
    if not code_match:
        return 0.0, ["no code found"]
    code = code_match.group(1)
    checks = [
        ("csv module used", "import csv" in code or "csv.reader" in code or "DictReader" in code),
        ("reads file", "open(" in code),
        ("filters by status", "active" in code),
        ("handles empty/missing", "empty" in code.lower() or "if not" in code.lower() or "try" in code.lower()),
        ("returns rows", "return" in code),
    ]
    for name, passed in checks:
        if passed:
            score += 0.2
            feedback.append(f"ok: {name}")
    if "csv.DictReader" in code or "csv.reader" in code:
        if "active" in code and "return" in code:
            score += 0.2
    return min(score, 1.0), feedback


def score_go_json_tags(text):
    score = 0.0
    feedback = []
    checks = [
        ("json tag", "json:" in text),
        ("snake_case", "snake" in text.lower()),
        ("tag example", "omitempty" in text.lower()),
        ("skip field", "json:\"-\"" in text),
        ("serialization", "Marshal" in text or "serialize" in text.lower()),
    ]
    for name, passed in checks:
        if passed:
            score += 0.2
    return min(score, 1.0), feedback


def score_rust_closure(text):
    score = 0.0
    checks = [
        ("FnOnce", "FnOnce" in text),
        ("move keyword", "move" in text.lower()),
        ("borrow concept", "borrow" in text.lower()),
        ("mut self", "mut" in text.lower() and "self" in text.lower()),
        ("solution pattern", "RefCell" in text or "Box" in text or "Arc" in text),
    ]
    for name, passed in checks:
        if passed:
            score += 0.2
    return min(score, 1.0), checks


def score_npm_diff(text):
    score = 0.0
    checks = [
        ("lockfile", "package-lock.json" in text or "lockfile" in text.lower()),
        ("both commands", "ci" in text.lower() and "install" in text.lower()),
        ("determinism", "deterministic" in text.lower()),
        ("CI/CD context", "CI" in text.upper()),
        ("clean install", "clean" in text.lower()),
    ]
    for name, passed in checks:
        if passed:
            score += 0.2
    return min(score, 1.0), checks


SCORERS = {
    "csv_parser": score_csv_parser,
    "go_json_tags": score_go_json_tags,
    "rust_closure_borrow": score_rust_closure,
    "npm_diff": score_npm_diff,
}
