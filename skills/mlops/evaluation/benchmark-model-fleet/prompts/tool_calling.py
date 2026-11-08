"""Tool / function-calling prompts.

Tests the behaviour that actually breaks agents: emitting a well-formed call, NOT
inventing arguments the user never supplied, and NOT reaching for a tool when plain
knowledge answers the question. Two of the four prompts are traps where the correct
move is to not call a tool.

These use prompt-level tool definitions rather than the OpenAI `tools` parameter, so the
family works across every runtime in the registry regardless of native tool support.

Scoring: 5 checks x 0.2 = 1.0 max.
"""
import json
import re

TOOLS = '''You have these tools:

get_weather(city: string, unit: "c"|"f") -> current conditions
send_email(to: string, subject: string, body: string) -> sends mail
search_flights(origin: string, destination: string, date: "YYYY-MM-DD") -> flight list

To call a tool, respond with ONLY a JSON object: {"tool": "<name>", "arguments": {...}}
If no tool is needed, answer in plain text with no JSON.'''

PROMPTS = [
    ("well_formed_call",
     TOOLS + "\n\nUser: What's the weather in Reykjavik right now, in celsius?"),
    ("missing_argument",
     TOOLS + "\n\nUser: Book me a flight to Lisbon next Tuesday."),
    ("no_tool_needed",
     TOOLS + "\n\nUser: What's the capital of Portugal?"),
    ("correct_tool_choice",
     TOOLS + "\n\nUser: Email dana@corp.io to let her know the Q3 report is ready."),
]


def _parse(text):
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


def score_well_formed_call(text):
    d, clean = _parse(text)
    if d is None:
        return 0.0, ["no JSON tool call emitted"]
    args = d.get("arguments") or {}
    return _score([
        ("bare JSON", clean),
        ("tool=get_weather", d.get("tool") == "get_weather"),
        ("city=Reykjavik", "reykjavik" in str(args.get("city", "")).lower()),
        ("unit=c", str(args.get("unit", "")).lower() == "c"),
        # only meaningful if a call with args was actually made
        ("no extra args", bool(args) and set(args) <= {"city", "unit"}),
    ])


def score_missing_argument(text):
    """'next Tuesday' has no absolute date and no origin was given. Correct behaviour is
    EITHER a clarifying question with no tool call, OR a call that leaves the unknown
    fields null — never an invented JFK and a guessed date.

    Prose must be measured OUTSIDE the JSON: the payload itself contains the words
    'origin' and 'date', which would otherwise self-satisfy a naive keyword check.
    """
    d, _ = _parse(text)
    prose = re.sub(r'\{.*\}', ' ', text, flags=re.DOTALL).lower()
    asked = "?" in prose or any(t in prose for t in (
        "what date", "which date", "where are you", "flying from", "what city",
        "need to know", "please specify", "clarify", "could you tell"))

    origin = date = ""
    if d and isinstance(d.get("arguments"), dict):
        origin = str(d["arguments"].get("origin") or "").strip().lower()
        date = str(d["arguments"].get("date") or "").strip().lower()
    invented_origin = origin not in ("", "none", "null", "unknown", "?")
    invented_date = bool(re.match(r'20\d{2}-\d{2}-\d{2}', date))

    return _score([
        ("did not invent an origin", not invented_origin),
        ("did not fabricate a date", not invented_date),
        ("asked for the missing detail", asked),
        ("recognised Lisbon", "lisbon" in text.lower()),
        ("no blind tool call", d is None or not (invented_origin or invented_date)),
    ])


def score_no_tool_needed(text):
    d, _ = _parse(text)
    called = d is not None and "tool" in d
    low = text.lower()
    return _score([
        ("no tool call", not called),
        # a tool call mentioning Lisbon is not an answer
        ("answered Lisbon", "lisbon" in low and not called),
        ("plain text", "```" not in text),
        ("concise", len(text.split()) < 60),
        ("no invented JSON", not text.strip().startswith("{")),
    ])


def score_correct_tool_choice(text):
    d, clean = _parse(text)
    if d is None:
        return 0.0, ["no JSON tool call emitted"]
    args = d.get("arguments") or {}
    return _score([
        ("bare JSON", clean),
        ("tool=send_email", d.get("tool") == "send_email"),
        ("to=dana@corp.io", str(args.get("to", "")).lower() == "dana@corp.io"),
        ("subject present", bool(str(args.get("subject", "")).strip())),
        ("body mentions Q3", "q3" in str(args.get("body", "")).lower()),
    ])


SCORERS = {
    "well_formed_call": score_well_formed_call,
    "missing_argument": score_missing_argument,
    "no_tool_needed": score_no_tool_needed,
    "correct_tool_choice": score_correct_tool_choice,
}
