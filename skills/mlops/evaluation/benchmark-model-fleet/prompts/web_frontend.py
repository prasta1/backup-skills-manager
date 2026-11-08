"""Frontend/website generation prompts and scorers.

Structure is what we can check deterministically: does the markup parse as a real
document, is it semantic, is it accessible, is it responsive. We cannot score whether
it looks good — read the output for that.

Scoring: 5 checks x 0.2 = 1.0 max.
"""
import re

PROMPTS = [
    ("landing_page",
     "Write a complete single-file HTML landing page for a local bakery. It needs a hero "
     "section, three product cards, and a contact form. Do not use any external CSS or "
     "JavaScript libraries — everything inline in the one file."),
    ("responsive_nav",
     "Write HTML and CSS for a site navigation bar that collapses to a hamburger menu "
     "below 768px wide. No JavaScript frameworks."),
    ("accessible_form",
     "Write an accessible HTML signup form with fields for email, password, and password "
     "confirmation, plus a submit button. Follow WCAG basics."),
    ("css_grid_cards",
     "Write the CSS for a three-column card grid that collapses to a single column on "
     "mobile. Use CSS Grid, not flexbox."),
]


def _code(text):
    """Prefer fenced blocks; fall back to the raw response so unfenced answers still score."""
    blocks = re.findall(r'```(?:html|css|\w*)\n(.*?)```', text, re.DOTALL)
    return "\n".join(blocks) if blocks else text


def _score(checks, code, need=("<", "{")):
    """Guard first: a response with no markup or CSS at all scores 0, so that a refusal
    cannot collect points from negative checks ('no external deps') passing vacuously."""
    if not any(t in code for t in need):
        return 0.0, ["no markup/css in response"]
    score = sum(0.2 for _, passed in checks if passed)
    return min(round(score, 2), 1.0), [f"{'ok' if p else 'no'}: {n}" for n, p in checks]


def score_landing_page(text):
    c = _code(text).lower()
    return _score([
        ("doctype", "<!doctype html" in c),
        ("viewport meta", "viewport" in c and "width=device-width" in c),
        ("semantic sections", sum(t in c for t in ("<header", "<main", "<footer", "<section", "<nav")) >= 3),
        ("form with inputs", "<form" in c and "<input" in c),
        # The prompt said no external libraries — penalise CDN links.
        ("no external deps", not re.search(r'(src|href)\s*=\s*["\']https?://', c)),
    ], c)


def score_responsive_nav(text):
    c = _code(text).lower()
    return _score([
        ("nav element", "<nav" in c),
        ("media query", "@media" in c),
        ("768px breakpoint", "768" in c),
        ("hamburger control", any(t in c for t in ("hamburger", "menu-toggle", "☰", "checkbox", "aria-expanded"))),
        ("real css", "{" in c and ":" in c and "}" in c),
    ], c)


def score_accessible_form(text):
    c = _code(text).lower()
    return _score([
        ("label for=", re.search(r'<label[^>]*\bfor\s*=', c) is not None),
        ("typed inputs", 'type="email"' in c or "type='email'" in c),
        ("password fields", c.count("password") >= 2),
        ("aria or required", "aria-" in c or "required" in c),
        ("submit button", "<button" in c or 'type="submit"' in c),
    ], c)


def score_css_grid_cards(text):
    c = _code(text).lower()
    return _score([
        ("display grid", "display" in c and "grid" in c),
        ("grid-template-columns", "grid-template-columns" in c),
        ("repeat/minmax/auto-fit", any(t in c for t in ("repeat(", "minmax(", "auto-fit", "auto-fill"))),
        ("collapses on mobile", "@media" in c or "auto-fit" in c or "auto-fill" in c),
        ("gap", "gap" in c or "grid-gap" in c),
    ], c)


SCORERS = {
    "landing_page": score_landing_page,
    "responsive_nav": score_responsive_nav,
    "accessible_form": score_accessible_form,
    "css_grid_cards": score_css_grid_cards,
}
