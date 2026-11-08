"""Grounded vision prompts + deterministic scorers against a KNOWN image.

Replaces the old vision family, which scored nothing: benchmark.py passed
`scorers = None` for vision, every model got the 0.8 unscored default, and the
only real signal was `quality_chars` — a character count of the response. A
model that padded its answer scored higher, so the axis rewarded verbosity and
invention, and the placeholder image made all of it meaningless.

What replaces it: every check compares the response against
`references/vision_ground_truth.json`, which records what is actually in the
image. Counting, object recognition, setting and activity are all scored against
verified facts, and asserting an object that is NOT present subtracts.

Scoring weights (sum to 1.0 before the hallucination penalty):
  people_count        0.35  — can it count? the most discriminating check
  objects_present     0.30  — can it recognise the equipment?
  setting_and_activity 0.20 — does it understand the scene?
  hallucination       -0.15 — SUBTRACTED per absent object confidently claimed

Run with:
    python3 benchmark.py --vision --prompts-file prompts/vision_grounded.py \
        --image-path scripts/test_image_workshop.png --models <id> ...
"""
import json
import os
import re

_GT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references", "vision_ground_truth.json")

with open(_GT_PATH) as _f:
    GT = json.load(_f)

W = GT["scoring"]


PROMPTS = [
    ("count_people",
     "How many people are in this image? Give the number, then explain briefly how you "
     "counted them."),
    ("identify_objects",
     "What tools, machines or equipment can you identify in this image? List each one and "
     "say what it is used for."),
    ("describe_setting",
     "What kind of place is this and what is happening here? State the setting and the "
     "activity, and give the visual evidence that supports your answer."),
    ("count_and_locate",
     "Count the people in this image and say what each one is doing. If you are unsure "
     "about anything you cannot clearly see, say so rather than guessing."),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
_NUM_WORDS = {
    "zero": 0, "no": 0, "none": 0, "one": 1, "a": 1, "single": 1, "two": 2, "three": 3,
    "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
}


def _strip_code_fence(t):
    t = re.sub(r"```(?:json)?", " ", t or "")
    return t.replace("`", " ")


def _mentions(text, words):
    """True if any synonym appears as a whole word/phrase. Case-insensitive."""
    t = text.lower()
    for w in words:
        if re.search(r"\b" + re.escape(w.lower()) + r"\b", t):
            return True
    return False


def _asserts_positively(text, words):
    """Distinguish 'a dog is by the door' from 'there is no dog'.

    The negation window matters: a model that correctly says it sees no dogs must
    not be penalised for the word 'dog'. We look for a negation cue within a
    short window before the keyword and treat that as a NON-assertion.
    """
    t = text.lower()
    neg_cues = ("no ", "not ", "n't", "none", "without", "absent", "cannot", "can't",
                "unclear", "cannot see", "do not", "doesn't", "does not", "zero")
    for w in words:
        for m in re.finditer(r"\b" + re.escape(w.lower()) + r"\b", t):
            start = max(0, m.start() - 60)
            window = t[start:m.start()]
            if any(cue in window for cue in neg_cues):
                continue  # negated mention — not a hallucination
            return True
    return False


def _extract_people_count(text):
    """Best-effort people count. Prefers an explicit answer near the word
    'people'/'person', then any spelled-out or digit count in the first lines."""
    t = _strip_code_fence(text).lower()

    # "there are three people", "3 people", "people: 3"
    m = re.search(r"(?:there\s+(?:are|is)\s+)?(\d{1,2}|" + "|".join(_NUM_WORDS) + r")\s+"
                  r"(?:people|persons?|individuals?|figures?|workers?|men|women|hikers?)", t)
    if m:
        tok = m.group(1)
        return int(tok) if tok.isdigit() else _NUM_WORDS.get(tok, None)
    m = re.search(r"(?:people|persons?)\s*[:=]\s*(\d{1,2})", t)
    if m:
        return int(m.group(1))
    # fall back to the first count token anywhere in the opening
    m = re.search(r"\b(\d{1,2})\b", t[:400])
    if m:
        return int(m.group(1))
    for word, val in _NUM_WORDS.items():
        if re.search(r"\b" + word + r"\b", t[:400]):
            return val
    return None


# ---------------------------------------------------------------------------
# scorers — each returns (score_0_to_1, detail_string)
# ---------------------------------------------------------------------------
def score_count_people(text):
    expected = GT["people_count"]
    said = _extract_people_count(text)
    if said is None:
        return 0.0, "no count found"
    if said == expected:
        return 1.0, f"correct ({said})"
    # partial credit, floored at 0 — being one off is not a total miss
    off = abs(said - expected) / float(expected)
    return max(0.0, 1.0 - off), f"said {said}, expected {expected}"


def score_identify_objects(text):
    present = GT["objects_present"]
    hits = [name for name, syns in present.items() if _mentions(text, syns)]
    frac = len(hits) / float(len(present))
    return frac, f"named {len(hits)}/{len(present)}: {', '.join(hits) or 'none'}"


def score_describe_setting(text):
    setting_ok = _mentions(text, GT["setting_words"])
    activity_ok = _mentions(text, GT["activity_words"])
    frac = (0.5 if setting_ok else 0.0) + (0.5 if activity_ok else 0.0)
    bits = []
    bits.append("setting+" if setting_ok else "setting-")
    bits.append("activity+" if activity_ok else "activity-")
    return frac, " ".join(bits)


def score_count_and_locate(text):
    """Half the count check, half the object check — an integration prompt that
    a model cannot shortcut by answering 'yes, tools'."""
    c, cd = score_count_people(text)
    o, od = score_identify_objects(text)
    return 0.5 * c + 0.5 * o, f"{cd}; {od}"


def _hallucination_penalty(text):
    """Fraction of ABSENT object classes the model positively asserts."""
    absent = GT["objects_absent"]
    hits = [name for name, syns in absent.items() if _asserts_positively(text, syns)]
    frac = len(hits) / float(len(absent))
    return frac, f"claimed absent: {', '.join(hits) or 'none'}"


# ---------------------------------------------------------------------------
# the composite rubric benchmark.py calls per prompt
# ---------------------------------------------------------------------------
# benchmark.py invokes SCORERS[prompt_name](response) and takes [0] as the
# quality score. We route each prompt to its own specific check, then apply the
# hallucination penalty to EVERY response — hallucination is prompt-independent
# and must be punished regardless of which question was asked.
_SPECIFIC = {
    "count_people": score_count_people,
    "identify_objects": score_identify_objects,
    "describe_setting": score_describe_setting,
    "count_and_locate": score_count_and_locate,
}


# Every _SPECIFIC scorer already returns 0.0-1.0, so the composite is just that
# value minus the penalty — no weight rescaling and no normalization step.
#
# An earlier version multiplied by the axis weight AND divided by it, which
# cancelled out and then inflated by 1/W (a perfect answer scored 2.86, and
# 5.00 on describe_setting). The weights in vision_ground_truth.json document
# the rubric's PRIORITY for a human reading it; they are not arithmetic here.
# Keeping the ceiling at 1.0 is what makes the four prompts comparable and stops
# a flawless model from looking mediocre.
def _make(name):
    specific = _SPECIFIC[name]

    def scorer(text):
        base, detail = specific(text)
        h, hdetail = _hallucination_penalty(text)
        penalty = W["hallucination_penalty"] * h
        return max(0.0, base - penalty), (
            f"{detail}; {hdetail}; base={base:.2f} -pen={penalty:.2f}")
    return scorer


SCORERS = {name: _make(name) for name in _SPECIFIC}
