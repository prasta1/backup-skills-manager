#!/usr/bin/env python3
"""Mechanical cap checker for Flotsam & Jetsom drafts (Substack + X + LinkedIn).

The body of a draft is everything after the first line that is exactly `---`
(per the skill's draft file shape), so a body containing its own `---` rule
still counts correctly. A file with a metadata block but no `---` rule is
counted whole and flagged, because the header would inflate the count. A file
with no metadata block at all (a headerless legacy draft, say) is counted whole
and silent, because there is nothing to separate.

Usage:
    python3 count.py note     <draft.md>    # Substack Note    cap 200 chars
    python3 count.py article  <draft.md>    # Substack article cap 800 words
    python3 count.py post     <draft.md>    # single X post    cap 280 chars
    python3 count.py thread   <draft.md>    # X thread         cap 280 per post
    python3 count.py linkedin <draft.md>    # LinkedIn post    cap 3000 chars

Threads separate their posts with a line containing only `===`.

X counts every URL as 23 characters no matter its real length, so `post` and
`thread` enforce the X-weighted count (URLs collapsed to 23) and also print the
raw character count. Substack `note` and `linkedin` enforce the literal
character count — LinkedIn does not collapse URLs, so a link costs its real
length there.

`linkedin` also reports, WITHOUT failing the draft: the mobile and desktop fold
positions (~140 / ~210 characters — third-party consensus, not LinkedIn
documentation), the first-paragraph length, the external links in the body, and
the hashtag count. The 3,000-character cap is LinkedIn's own limit and is the
only cap in this tool that comes from a platform rather than from Patrick's
taste; no editorial length target is enforced.

Exit status: 0 when every unit is within cap, 1 when any unit is over, 2 on a
usage error. Never exits 0 on an over-cap draft.
"""

from __future__ import annotations

import pathlib
import re
import sys

CAPS = {"note": 200, "article": 800, "post": 280, "thread": 280, "linkedin": 3000}
SEPARATOR = "\n---\n"
POST_SEP = re.compile(r"(?m)^\s*===\s*$")
URL = re.compile(r"https?://\S+")
HASHTAG = re.compile(r"(?<!\w)#\w+")
X_URL_COST = 23

# Third-party consensus only — LinkedIn documents neither fold nor hashtag count.
LINKEDIN_FOLD_MOBILE = 140
LINKEDIN_FOLD_DESKTOP = 210
LINKEDIN_HASHTAG_GUIDE = 5


def body_of(text: str) -> tuple[str, str]:
    """Return (body, state).

    state is 'separated'   — the normal case: body follows the first `---` rule
             'unseparated' — a metadata block exists but no rule does, so the
                             header would be counted as body: warn
             'bare'        — no metadata block at all, so the whole file is the
                             body and there is nothing to warn about
    """
    if SEPARATOR in text:
        return text.split(SEPARATOR, 1)[-1].strip(), "separated"
    head = [l for l in text.splitlines()[:10] if l.strip()]
    has_metadata = any(l.lstrip().startswith(">") for l in head)
    return text.strip(), "unseparated" if has_metadata else "bare"


def x_count(s: str) -> int:
    """X wraps every URL in t.co and counts it as exactly 23 characters."""
    return len(URL.sub("x" * X_URL_COST, s))


def units(fmt: str, body: str) -> list[str]:
    if fmt == "thread":
        return [p.strip() for p in POST_SEP.split(body) if p.strip()]
    return [body] if body else []


def measure(fmt: str, unit: str) -> tuple[int, int]:
    """Return (enforced_value, raw_value)."""
    if fmt == "article":
        words = len(unit.split())
        return words, words
    if fmt in ("post", "thread"):
        return x_count(unit), len(unit)
    return len(unit), len(unit)


def linkedin_notes(body: str) -> list[str]:
    """Advisory lines for a LinkedIn draft. These never fail the draft."""
    notes: list[str] = []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    first = paragraphs[0] if paragraphs else ""
    if first and len(first) > LINKEDIN_FOLD_MOBILE:
        notes.append(
            f"first paragraph is {len(first)} chars, past the ~{LINKEDIN_FOLD_MOBILE}-char "
            'mobile fold — the hook gets cut before "...see more"'
        )

    links = URL.findall(body)
    if links:
        notes.append(
            f"{len(links)} external link(s) in the body — contested: LinkedIn's public line is "
            "that in-post links are fine, while an independent ~300k-post study (2026) measured "
            "~16-19% lower median reach for one caption link. Putting it in the first comment "
            "is worse, not better: LinkedIn filters link-bearing comments"
        )

    tags = HASHTAG.findall(body)
    if len(tags) > LINKEDIN_HASHTAG_GUIDE:
        notes.append(
            f"{len(tags)} hashtags — LinkedIn documents 3-5 for company Pages only; there is "
            "no official figure for personal profiles"
        )

    return notes


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in CAPS:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    fmt, path = argv[1], pathlib.Path(argv[2])
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2

    body, state = body_of(path.read_text())
    if state == "unseparated":
        print(
            f"WARNING: {path.name} has a metadata block but no '---' rule, so the "
            "header is being counted as body. Insert a '---' line after the block.",
            file=sys.stderr,
        )

    us = units(fmt, body)
    if not us:
        print(f"{path.name}: empty body", file=sys.stderr)
        return 2

    cap = CAPS[fmt]
    unit_name = "words" if fmt == "article" else "chars"
    cap_label = f"{cap} {unit_name}"
    over = False

    print(f"{fmt} — {path.name} (cap {cap_label})")
    for index, unit in enumerate(us, 1):
        value, raw = measure(fmt, unit)
        flag = "OVER" if value > cap else "ok"
        over = over or value > cap
        label = f"post {index}" if fmt == "thread" else "body"
        detail = f"  (raw {raw})" if fmt in ("post", "thread") else ""
        print(f"  {label}: {value} / {cap} {flag}{detail}")

    if fmt == "thread":
        print(f"  {len(us)} posts total — {'OVER CAP' if over else 'all within cap'}")

    if fmt == "linkedin":
        text = us[0]
        words = len(text.split())
        paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        print(f"  words: {words}   paragraphs: {len(paragraphs)}")
        print(f"  fold ~{LINKEDIN_FOLD_MOBILE} (mobile): {text[:LINKEDIN_FOLD_MOBILE]!r}")
        print(f"  fold ~{LINKEDIN_FOLD_DESKTOP} (desktop): {text[:LINKEDIN_FOLD_DESKTOP]!r}")
        for note in linkedin_notes(text):
            print(f"  NOTE: {note}")

    first_line = us[0].splitlines()[0] if us[0].splitlines() else ""
    print(f"  first line: {first_line[:60]}")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
