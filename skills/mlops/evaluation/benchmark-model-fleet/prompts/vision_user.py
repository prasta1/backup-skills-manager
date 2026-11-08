"""Grounded vision rubric #2 — the discriminating one.

Built against a user-supplied photograph (references/vision_ground_truth_user.json)
that was verified by two independent vision reads which DISAGREED on four points.
Those disagreements are the questions. Where the first synthetic rubric gave every
model 1.00, this one is built so that only genuinely careful models score well.

What makes it discriminate:

  negative_existence (0.30) — "how many people are wearing a RED top?" The answer
      is ZERO. Her top is light, so a model pattern-matching light->a-colour
      answers 1 and is wrong. A model that treats the question as presupposing
      existence also answers 1. Only a model that actually checks each colour
      says 0.

  spatial_trap (0.25) — "the person on the FAR LEFT". There is no person on the
      left; the horse is. The only person stands on the right. Answering about
      the woman is ignoring the spatial qualifier, which is a specific and very
      common failure.

  small_object (0.20) — the cat is bottom-corner, small, and occluded by the
      fence. Detection here is capability, not a giveaway.

  calibration (0.25) — two background elements are GENUINELY ambiguous (a white
      structure, a dark vertical shape). Correct behaviour is to hedge, list
      plausible readings, or say it cannot be determined. Confident fabrication
      is scored as a failure. This is the check the old char-count rubric was
      structurally unable to express: it rewarded longer answers, so hedging and
      invention both scored well.

Negation is handled throughout with a windowed cue check, so "there is no person
on the left" scores as correct rather than as a failed mention.

Run with:
    python3 benchmark.py --vision --image-path scripts/test_image_user.png \
        --prompts-file prompts/vision_user.py --models <id> ...
"""
import json
import os
import re

_GT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references", "vision_ground_truth_user.json")

with open(_GT_PATH) as _f:
    GT = json.load(_f)

W = GT["scoring"]
C = GT["colors"]
SP = GT["spatial"]


PROMPTS = [
    ("color_counts",
     "How many people in this image are wearing a red top? How many are wearing a "
     "blue top? Give a number for each. If there are none, say none."),
    ("spatial_left",
     "Describe the person on the far left of the image — what are they wearing and "
     "what are they doing?"),
    ("find_small",
     "Look carefully at the edges and foreground of this image. Is there any animal "
     "other than the horse? Name it and say where it is."),
    ("background_ambiguity",
     "In the far background, what is the white structure, and is there another person "
     "near the dark horse? If something is too far away or unclear to identify "
     "confidently, say so rather than guessing."),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
_NEG_CUES = ("no ", "not ", "n't", "none", "zero", "without", "absent", "cannot",
             "can't", "unclear", "do not", "doesn't", "does not", "never",
             "there is no", "there are no", "nobody", "no one", "isn't", "aren't")


def _mentions(text, words):
    t = (text or "").lower()
    return any(re.search(r"\b" + re.escape(w.lower()) + r"\b", t) for w in words)


def _negated_mention(text, words, window=70):
    """True if any synonym appears WITHOUT a negation cue in the preceding window.

    This is what lets "there is no person on the far left" score as correct: the
    words match, but the mention is negated, so it is not an assertion.
    """
    t = (text or "").lower()
    for w in words:
        for m in re.finditer(r"\b" + re.escape(w.lower()) + r"\b", t):
            pre = t[max(0, m.start() - window):m.start()]
            if not any(cue in pre for cue in _NEG_CUES):
                return True
    return False


_COUNT_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "none": 0, "nobody": 0, "no one": 0, "neither": 0,
                "no": 0, "0": 0}
# 'no' must be listed BEFORE the digit alternation or 'no' in "no red" is not
# recognised as a zero count at all. Longer tokens come first for the same
# reason: 'no one' must win over 'no'.
_NUM = ("(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|none|nobody|"
        "no one|neither|no|\\d{1,2})")
# The colours the colour_counts prompt asks about. _count_for_color compares a
# number against EVERY colour in the text, not just the one being asked about,
# so this list must cover all of them.
_COLOR_ORDER = ("red", "blue")
# Tokens that assert a count of zero. They pair with the nearest FOLLOWING
# colour, because English puts the colour after the count in both the common
# phrasings ('nobody in red', 'zero in blue').
_NEGATIVE_TOKENS = ("zero", "none", "nobody", "no one", "neither", "0")


def _as_count(tok):
    return int(tok) if tok.isdigit() else _COUNT_WORDS.get(tok, None)


def _count_for_color(text, color):
    """The number a model gave for one colour.

    Three earlier attempts at this were wrong, all for the same underlying
    reason: they tried to decide (number, colour) pairings by DISTANCE across
    the whole answer, and in natural phrasing distance lies.

      - nearest-number-in-a-window reads '1 person in a red top and 0 wearing
        blue' as red=0, because that 0 is 14 chars from 'red' while red's own 1
        is 18 away.
      - nearest-overall sends BOTH halves of 'nobody in red and nobody in blue'
        to red, leaving blue unclaimed.
      - making negatives pair forward-only fixes that case but breaks 'Zero
        people in red, zero in blue', where the first zero is then stranded.

    The actual structure is CLAUSAL: an answer to 'how many in red, how many in
    blue' gives one count per colour, and the colour words are the anchors. So
    find every colour mention, cut the text at those anchors, and bind each
    number to the colour of the region it falls in. A number before the first
    colour belongs to that first colour; a number after the last belongs to the
    last. Within a region, one colour, so a nearest-number rule is safe again.

    Headcounts ('only one person in the image') are dropped first: a number
    immediately followed by person/people is describing the scene, not a colour.
    """
    t = (text or "").lower()

    anchors = sorted((m.start(), c) for c in _COLOR_ORDER
                     for m in re.finditer(r"\b" + re.escape(c) + r"\b", t))
    if not anchors:
        # BARE-ANSWER FALLBACK. The prompt asks for "a number for each" and
        # explicitly invites "if there are none, say none", so a compliant model
        # answers '0, 0' or 'none / none' -- numbers with NO colour words at all.
        # Returning None here scored those perfect answers 0.0 and made the
        # rubric measure verbosity instead of accuracy: the models that spelled
        # out 'Red: 0 / Blue: 0' scored 1.00 while glm-4.6v and gemma-4-12b,
        # which answered '0, 0' and 'none/none', scored 0.00 on the SAME fact.
        #
        # Positional reading: with no anchors, the answers can only be in the
        # order the colours were asked (red first, blue second), so bind the
        # numbers in sequence. Guarded to exactly one number per colour -- if the
        # count differs the mapping is ambiguous and we still return None rather
        # than guess.
        if len(_COLOR_ORDER) != 2:
            return None
        bare = []
        for nm in re.finditer(r"\b(" + _NUM + r")\b", t):
            val = _as_count(nm.group(1))
            if val is None:
                continue
            after = t[nm.end():nm.end() + 12]
            if re.match(r"\s+(person|people|individual|man|woman|girl|boy)\b", after):
                continue  # headcount, e.g. 'only 1 person'
            bare.append(val)
        if len(bare) != len(_COLOR_ORDER):
            return None
        return bare[_COLOR_ORDER.index(color)]

    # number -> value. A number immediately followed by person/people is a
    # HEADCOUNT ("there is only one person in the image"), not a colour count.
    # But 'zero people in red' IS a colour count, so the headcount reading only
    # applies when no colour word follows within the same breath — otherwise the
    # filter eats the answer ('zero people in red' scored as no answer at all).
    numbers = []
    for nm in re.finditer(r"\b(" + _NUM + r")\b", t):
        val = _as_count(nm.group(1))
        if val is None:
            continue
        after = t[nm.end():nm.end() + 12]
        is_headcount = bool(re.match(r"\s+(person|people|individual|man|woman|girl|boy)\b", after))
        # Look ahead far enough to contain a WHOLE colour word. At 24 chars,
        # "one person is wearing a blue top" clipped 'blue' to 'blu', the
        # \bblue\b guard missed it, and a genuine blue count was discarded as a
        # headcount. 40 covers the phrasing comfortably.
        if is_headcount and not re.search(r"\b(" + "|".join(_COLOR_ORDER) + r")\b",
                                          t[nm.end():nm.end() + 40]):
            continue
        numbers.append(((nm.start() + nm.end()) // 2, val))

    if not numbers:
        return None

    # Boundaries midway between consecutive colour anchors.
    bounds = []
    for i, (pos, c) in enumerate(anchors):
        if i == 0:
            lo = 0
        else:
            prev = anchors[i - 1][0]
            lo = (prev + pos) // 2
        if i == len(anchors) - 1:
            hi = len(t)
        else:
            nxt = anchors[i + 1][0]
            hi = (pos + nxt) // 2
        bounds.append((lo, hi, c))

    for lo, hi, c in bounds:
        if c != color:
            continue
        in_region = [v for pos, v in numbers if lo <= pos < hi]
        if in_region:
            return in_region[0]

    # This colour was named but no number landed in its region.
    #
    # The midpoint boundary can strand a number on the wrong side when the two
    # colours are far apart and a number sits just past the midpoint: in
    # 'nobody in red AND nobody in blue' the second 'nobody' (mid 28) falls in
    # red's region [0,29) because the boundary is the midpoint 29, leaving blue
    # unclaimed. So before giving up, take the nearest number in the text — the
    # region result above is preferred precisely because it is usually right,
    # and this only runs when it found nothing.
    own_positions = [p for p, c2 in anchors if c2 == color]
    if not own_positions:
        return None
    best = min(numbers, key=lambda nv: min(abs(nv[0] - p) for p in own_positions))
    return best[1]


# ---------------------------------------------------------------------------
# specific scorers — each returns (0.0-1.0, detail)
# ---------------------------------------------------------------------------
def score_color_counts(text):
    """Both counts must be zero. Partial credit if exactly one is right."""
    red = _count_for_color(text, "red")
    blue = _count_for_color(text, "blue")
    exp_r, exp_b = C["red_top"], C["blue_top"]
    ok = sum(1 for got, exp in ((red, exp_r), (blue, exp_b)) if got == exp)
    detail = f"red={red} (exp {exp_r}), blue={blue} (exp {exp_b})"
    if red is None and blue is None:
        return 0.0, detail + " — no counts found"
    return ok / 2.0, detail


def score_spatial_left(text):
    """Correct = acknowledges there is no person on the far left.

    Answering about the woman on the right, with no acknowledgement of the
    spatial mismatch, scores 0. That is the trap.
    """
    t = (text or "").lower()
    # An EXPLICIT denial only. An earlier version accepted any answer that
    # mentioned the left side and contained a negation cue within 70 chars,
    # which let "the person on the far left is wearing pink and standing BY THE
    # FENCE" pass — 'no' inside 'standing' is not a denial of a person.
    denies = bool(
        re.search(r"(no|not|isn'?t|aren'?t|doesn'?t)\s+"
                  r"(person|people|one|anyone|somebody|someone|man|woman|girl)\b", t)
        or re.search(r"\b(nobody|no one|there (?:is|are) no one)\b", t)
        or re.search(r"\bonly (?:one|1) person\b", t)
        or re.search(r"\bjust (?:one|1) person\b", t)
    )
    # ...and it must be attached to the left side, or be a global "only one person"
    left_anchored = bool(re.search(r"\b(left|leftmost|far left|left side|left-hand)\b", t))
    global_only = bool(re.search(r"\b(only|just) (?:one|1) person\b", t))

    if denies and (left_anchored or global_only):
        return 1.0, "correctly denied a person on the left"

    # the trap: answered about a person without noticing the mismatch
    if re.search(r"\b(the|that)\s+(person|woman|girl|man|individual)\b[^.]{0,50}"
                 r"\b(left|far left|left side|leftmost)\b", t):
        return 0.0, "FELL FOR IT — answered about a person 'on the left'"
    if left_anchored and re.search(r"\b(she|he|they|woman|man|girl|person)\b", t):
        return 0.0, "FELL FOR IT — described a person for a left-side question"
    if denies:
        return 0.5, "denied a person but never anchored it to the left side"
    return 0.0, "did not identify a left-side person or deny one"


def score_find_small(text):
    """The cat is small, bottom-corner, and occluded. Partial for a dog/other."""
    t = (text or "").lower()
    if _mentions(t, ["cat", "kitten", "kitty"]):
        loc_bonus = 0.0
        if re.search(r"\b(bottom|lower|corner|foreground|right|edge|behind)\b", t):
            loc_bonus = 0.1
        return min(1.0, 0.9 + loc_bonus), "detected the cat" + (" + location" if loc_bonus else "")
    if _mentions(t, ["dog", "puppy", "fox", "animal", "pet"]):
        return 0.3, "found an animal but misidentified it"
    return 0.0, "missed the cat entirely"


def score_background_ambiguity(text):
    """Two parts: the white structure, and the second-person question.

    Both are genuinely ambiguous, so hedging or listing plausible readings is
    CORRECT and confident fabrication is WRONG. Half credit each.
    """
    t = (text or "").lower()
    hedges = _mentions(t, ["cannot tell", "can't tell", "unclear", "not sure",
                           "hard to tell", "difficult to tell", "ambiguous",
                           "too far", "too small", "can't determine",
                           "cannot determine", "not certain", "uncertain",
                           "appears to be", "seems to be", "possibly",
                           "could be", "might be", "resembles"])
    struct_ok = _mentions(t, ["trailer", "rv", "camper", "shed", "outbuilding",
                              "building", "tent", "barn", "structure", "roof"])
    # a hedge anywhere in the answer counts toward calibration
    struct_score = 1.0 if (hedges or struct_ok) else 0.0
    if struct_ok and not hedges:
        struct_score = 0.7          # plausible reading, stated too confidently
    if not struct_ok and not hedges:
        struct_score = 0.0

    # second person: denial OR hedge is correct; a definite 'yes' is a hallucination
    denies = re.search(r"(no|not|isn'?t)\s+(second|another|other|second)\b", t) \
        or re.search(r"(only|just)\s+one\s+person", t) \
        or re.search(r"no\s+(one\s+)?(other|second|another)\s+people?", t)
    hedges_person = re.search(r"(possibly|maybe|might be|could be|unclear|not sure|"
                              r"hard to tell|cannot tell|can'?t tell|there might be|"
                              r"appears to be|seems to be)\b[^.]{0,60}"
                              r"\b(person|figure|someone|somebody)\b", t)
    asserts_person = re.search(r"\byes\b[^.]{0,40}\b(person|figure|someone)\b", t) \
        or re.search(r"\b(another|second|other)\s+person\b", t)
    if asserts_person and not denies and not hedges_person:
        person_score = 0.0          # confident hallucination
    elif denies or hedges_person:
        person_score = 1.0
    else:
        person_score = 0.3

    total = 0.5 * struct_score + 0.5 * person_score
    return total, (f"structure={struct_score:.1f} (hedge={hedges}, named={struct_ok}); "
                   f"second_person={person_score:.1f} (denied={bool(denies)}, "
                   f"hedged={bool(hedges_person)})")


_SPECIFIC = {
    "color_counts": score_color_counts,
    "spatial_left": score_spatial_left,
    "find_small": score_find_small,
    "background_ambiguity": score_background_ambiguity,
}

# How much of the 0-1 each prompt's specific score is worth. The composite is
# normalized by this ceiling so a perfect answer is 1.0 on every prompt — without
# it, the same flawless response scores 0.25 on one prompt and 0.30 on another and
# the four become incomparable.
_CEIL = {
    "color_counts": W["negative_existence"],
    "spatial_left": W["spatial_trap"],
    "find_small": W["small_object"],
    "background_ambiguity": W["calibration"],
}


def _make(name):
    """Wrap a specific scorer.

    Each _SPECIFIC already returns 0.0-1.0, so the composite is that value
    directly — no weight multiplication and no division. (An earlier revision
    computed `(ceil * raw) / ceil`, which is just `raw`; and a still earlier one
    divided by the weight without multiplying first, inflating a perfect answer
    to 2.86. Every specific scorer here is already normalized, so the correct
    expression is the simplest one.)
    """
    specific = _SPECIFIC[name]

    def scorer(text):
        return specific(text)
    return scorer


SCORERS = {name: _make(name) for name in _SPECIFIC}
