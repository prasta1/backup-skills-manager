#!/usr/bin/env python3
"""Customer dashboard — urgency, touch, and health snapshot."""

import os
import sys
import yaml
from pathlib import Path
from datetime import date, datetime

CUSTOMERS_DIR = Path(__file__).resolve().parent.parent / "customers"
TODAY = date.today()


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    return yaml.safe_load(text[text.find("\n") + 1 : end]) or {}


def days_until(d):
    if d is None:
        return None
    if isinstance(d, date):
        return (d - TODAY).days
    dt = datetime.strptime(str(d), "%Y-%m-%d").date()
    return (dt - TODAY).days


def score(fm: dict) -> int:
    s = 0
    r = days_until(fm.get("renewal"))
    if r is not None and r <= 30:
        s += 20
    elif r is not None and r <= 90:
        s += 10

    t = days_until(fm.get("next_touch_due"))
    if t is not None and t < 0:
        s += 30
    elif t is not None and t <= 7:
        s += 15

    if fm.get("health") == "red":
        s += 40
    elif fm.get("health") == "yellow":
        s += 20
    return s


def build() -> dict:
    accounts = []
    for sub in sorted(CUSTOMERS_DIR.iterdir()):
        if not sub.is_dir():
            continue
        idx = sub / "index.md"
        if not idx.exists():
            continue
        fm = parse_frontmatter(idx)
        if "name" not in fm:
            continue
        accounts.append(
            {
                "id": sub.name,
                "name": fm.get("name", sub.name),
                "health": fm.get("health", "unknown"),
                "renewal": fm.get("renewal"),
                "next_touch_due": fm.get("next_touch_due"),
                "arr": fm.get("arr"),
                "score": score(fm),
                "contacts": [
                    {
                        "name": c.get("name"),
                        "role": c.get("role"),
                        "influence": c.get("influence"),
                        "relationship_to_us": c.get("relationship_to_us"),
                    }
                    for c in (fm.get("contacts") or [])
                ],
            }
        )

    accounts.sort(key=lambda a: a["score"], reverse=True)

    return {
        "generated_at": TODAY.isoformat(),
        "total": len(accounts),
        "by_health": {
            h: sum(1 for a in accounts if a["health"] == h)
            for h in ["green", "yellow", "red", "unknown"]
        },
        "renewal_next_30d": [
            {
                "id": a["id"],
                "name": a["name"],
                "days": days_until(a["renewal"]),
            }
            for a in accounts
            if days_until(a["renewal"]) is not None and 0 <= days_until(a["renewal"]) <= 30
        ],
        "overdue_touch": [
            {
                "id": a["id"],
                "name": a["name"],
                "days_overdue": -days_until(a["next_touch_due"]),
            }
            for a in accounts
            if days_until(a["next_touch_due"]) is not None and days_until(a["next_touch_due"]) < 0
        ],
        "top_priority": [
            {k: v for k, v in a.items() if k != "score"} for a in accounts[:5]
        ],
        "all_contacts": [
            {
                "account_id": a["id"],
                "account_name": a["name"],
                "contacts": a["contacts"],
            }
            for a in accounts
            if a["contacts"]
        ],
    }


def render(data: dict) -> str:
    lines = [
        f"# Customer Dashboard — {data['generated_at']}",
        f"Total accounts: {data['total']}",
        f"Health: {data['by_health']}",
        "",
    ]

    if data["renewal_next_30d"]:
        lines.append("## Renewals in next 30 days")
        for r in data["renewal_next_30d"]:
            lines.append(f"- {r['name']} ({r['id']}) — {r['days']} days")
    else:
        lines.append("No renewals in the next 30 days.")

    lines.append("")

    if data["overdue_touch"]:
        lines.append("## Overdue next touch")
        for o in data["overdue_touch"]:
            lines.append(f"- {o['name']} ({o['id']}) — {o['days_overdue']} days overdue")
    else:
        lines.append("No overdue touches.")

    lines.append("")
    lines.append("## Top priority")
    for a in data["top_priority"]:
        lines.append(
            f"- {a['name']} [{a['health']}] renewal={'soon' if days_until(a['renewal']) is not None and days_until(a['renewal']) <= 90 else a['renewal']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        import yaml  # noqa: F401
    except ImportError:
        # minimal fallback: no PyYAML
        data = build()
        print(render(data))
        sys.exit(0)
    print(render(build()))
