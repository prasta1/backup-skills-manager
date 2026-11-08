#!/usr/bin/env python3
"""Generate stakeholder charts from customer index.md files."""

import yaml
from pathlib import Path
import sys

# Use repo-relative paths
REPO_ROOT = Path(__file__).parent.parent
CUSTOMERS_DIR = REPO_ROOT / "customers"
OUTPUT_DIR = REPO_ROOT / "stakeholder_maps"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SLUG_MAP = {
    "motorola": "Motorola Solutions",
    "polar": "Polar Electro",
    "csem": "CSEM",
    "halma": "Halma",
    "university-of-jyvaskyla": "University of Jyväskylä",
    "tridonic": "Tridonic",
    "zwift": "Zwift",
    "poly": "Poly / HP",
    "sofar": "Sofar Ocean",
    "jumo": "JUMO",
    "kuester": "Küster Automotive",
    "getac": "Getac",
    "globalsense": "Globalsense",
    "halo-collar": "Halo Collar",
    "daikin": "Daikin",
    "masco": "Masco",
    "replior": "Replior",
    "nestle-purina": "Nestlé Purina",
}

ACCOUNT_DISPLAY = {
    "Motorola Solutions": "Motorola Solutions",
    "Polar Electro": "Polar Electro",
    "CSEM": "CSEM",
    "Halma": "Halma",
    "University of Jyväskylä": "University of Jyväskylä",
    "Tridonic": "Tridonic",
    "Zwift": "Zwift",
    "Poly / HP": "Poly (fka Plantronics, acquired by HP)",
    "Sofar Ocean": "Sofar Ocean",
    "JUMO": "JUMO",
    "Küster Automotive": "Küster Automotive",
    "Getac": "Getac",
    "Globalsense": "Globalsense",
    "Halo Collar": "Halo Collar",
    "Daikin": "Daikin",
    "Masco": "Masco",
    "Replior": "Replior",
    "Nestlé Purina": "Nestlé Purina Petcare Global Resources Inc",
}

INFLUENCE_COLOR = {"High": "high", "Medium": "medium", "Low": "low"}
RELATIONSHIP_LABEL = {"Ally": "Ally", "Neutral": "Neutral", "Warm": "Warm", "Blocker": "Blocker", "Marketing": "Marketing"}

# HTML template with all CSS braces escaped for Python .format()
HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{account_name} Stakeholder Map</title>
<style>
  :root {{
    --bg: #050b14;
    --card: rgba(15,23,42,0.6);
    --text: #e2e8f0;
    --muted: #94a3b8;
    --border: #1f2937;
    --high: #f59e0b;
    --medium: #34d399;
    --low: #60a5fa;
    --group-fill: rgba(30,41,59,0.5);
  }}
  * {{ box-sizing: border-box; }}
  html,body {{
    margin:0; padding:0;
    background: radial-gradient(1200px 800px at 10% -10%, #0b1d33 0%, transparent 60%),
                radial-gradient(900px 600px at 110% 10%, #0d1f2d 0%, transparent 55%),
                var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    min-height: 100vh;
  }}
  .wrap {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 28px 24px 40px;
  }}
  header {{
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 18px;
  }}
  header .dot {{
    width: 12px; height: 12px;
    border-radius: 50%;
    background: #22d3ee;
    box-shadow: 0 0 12px #22d3aa;
    animation: pulse 2.2s infinite;
  }}
  @keyframes pulse {{
    0%,100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: .75; transform: scale(1.15); }}
  }}
  header h1 {{
    margin: 0;
    font-size: 22px;
    font-weight: 600;
    letter-spacing: 0.2px;
  }}
  header p {{
    margin: 4px 0 0;
    color: var(--muted);
    font-size: 13px;
  }}
  .legend {{
    display: flex;
    gap: 14px;
    margin: 10px 0 18px;
    font-size: 12px;
  }}
  .legend .pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    border-radius: 999px;
    background: var(--card);
    border: 1px solid var(--border);
  }}
  .legend .swatch {{
    width: 10px; height: 10px;
    border-radius: 2px;
  }}
  .stage {{
    background: linear-gradient(180deg, rgba(15,23,42,0.4) 0%, rgba(15,23,42,0.2) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px;
    backdrop-filter: blur(4px);
  }}
  .row {{
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
  }}
  .row + .row {{
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px dashed var(--border);
  }}
  .row .label {{
    width: 100%;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: var(--muted);
    margin-bottom: 6px;
  }}
  .node {{
    flex: 1 1 180px;
    max-width: 260px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    position: relative;
    overflow: hidden;
  }}
  .node::before {{
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
  }}
  .node.high::before {{ background: var(--high); }}
  .node.medium::before {{ background: var(--medium); }}
  .node.low::before {{ background: var(--low); }}
  .node .name {{
    font-size: 14px;
    font-weight: 600;
    color: #f8fafc;
  }}
  .node .role {{
    margin-top: 2px;
    font-size: 12px;
    color: #cbd5e1;
  }}
  .node .meta {{
    margin-top: 8px;
    display: flex;
    gap: 8px;
    font-size: 11px;
    color: var(--muted);
  }}
  .node .badge {{
    padding: 3px 8px;
    border-radius: 999px;
    background: rgba(255,255,255,0.06);
    border: 1px solid var(--border);
  }}
  .group {{
    flex: 1 1 220px;
    background: var(--group-fill);
    border: 1px dashed var(--border);
    border-radius: 14px;
    padding: 12px;
  }}
  .group h4 {{
    margin: 0 0 10px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.1px;
    color: #cbd5e1;
  }}
  .group .row {{ margin-top: 8px; }}
  footer {{
    margin-top: 18px;
    color: var(--muted);
    font-size: 12px;
    display: flex;
    justify-content: space-between;
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="dot" aria-hidden="true"></div>
      <div>
        <h1>{account_name} Stakeholder Map</h1>
        <p>Customer contacts edited over time. Add new contacts in the customer file.</p>
      </div>
    </header>

    <div class="legend">
      <div class="pill"><span class="swatch" style="background:var(--high)"></span>High influence</div>
      <div class="pill"><span class="swatch" style="background:var(--medium)"></span>Medium influence</div>
      <div class="pill"><span class="swatch" style="background:var(--low)"></span>Low influence</div>
    </div>

    <div class="stage">
{rows_html}
    </div>

    <footer>
      <span>{account_display}</span>
      <span>{contact_count} active contacts</span>
    </footer>
  </div>
</body>
</html>"""


def build_node(contact, show_activities=False):
    """Build a single contact node HTML."""
    influence = INFLUENCE_COLOR.get(contact.get("influence", "Low"), "low")
    rel = RELATIONSHIP_LABEL.get(contact.get("relationship_to_us", "Neutral"), "Neutral")
    name = contact.get("name", "")
    role = contact.get("role", "")

    if show_activities:
        notes = contact.get("notes", "")
        activities = "0"
        if "Sales activities:" in notes:
            try:
                activities = notes.split("Sales activities:")[1].split("'")[0].strip()
            except Exception:
                pass
        meta = f'<span class="badge">Active</span><span class="badge">{activities} activities</span>'
    else:
        meta = f'<span class="badge">Contact</span><span class="badge">{rel}</span>'

    return f'''        <div class="node {influence}">
          <div class="name">{name}</div>
          <div class="role">{role}</div>
          <div class="meta">{meta}</div>
        </div>'''


def build_group(contacts, group_name, show_activities=False):
    """Build a grouped section for low-influence contacts."""
    nodes = "\n".join(build_node(c, show_activities) for c in contacts)
    return f'''        <div class="group">
          <h4>{group_name}</h4>
          <div class="row">
{nodes}
          </div>
        </div>'''


def generate_chart(account_slug):
    """Generate stakeholder chart for one account."""
    account_name = SLUG_MAP.get(account_slug, account_slug)
    account_display = ACCOUNT_DISPLAY.get(account_name, account_name)

    path = CUSTOMERS_DIR / account_slug / "index.md"
    if not path.exists():
        return None

    doc = path.read_text()
    if "---" not in doc:
        return None
    front = doc.split("---", 2)[1]
    data = yaml.safe_load(front)
    contacts = data.get("contacts", [])

    if not contacts:
        return None

    # Group contacts by influence
    high = [c for c in contacts if c.get("influence") == "High"]
    medium = [c for c in contacts if c.get("influence") == "Medium"]
    low = [c for c in contacts if c.get("influence") == "Low"]

    rows = []

    # High influence row
    if high:
        nodes = "\n".join(build_node(c) for c in high)
        rows.append(f'''      <div class="row">
        <div class="label">Leadership / High Influence</div>
{nodes}
      </div>''')

    # Medium influence row
    if medium:
        nodes = "\n".join(build_node(c) for c in medium)
        rows.append(f'''      <div class="row">
        <div class="label">Technical / Medium Influence</div>
{nodes}
      </div>''')

    # Low influence - grouped by role category
    if low:
        sw = [c for c in low if any(k in c.get("role", "").lower() for k in ["software", "firmware", "engineer", "system"])]
        eng = [c for c in low if any(k in c.get("role", "").lower() for k in ["quality", "qa", "test", "architect", "technologist", "distinguished"]) and c not in sw]
        biz = [c for c in low if c not in sw and c not in eng]

        low_parts = []
        if sw:
            low_parts.append(build_group(sw, "Software / Firmware", True))
        if eng:
            low_parts.append(build_group(eng, "Engineering / QA", True))
        if biz:
            low_parts.append(build_group(biz, "Business / Admin", True))

        rows.append(f'''      <div class="row">
        <div class="label">Operational / Low Influence</div>
{"".join(low_parts)}
      </div>''')

    rows_html = "\n".join(rows)

    html = HTML_TEMPLATE.format(
        account_name=account_name,
        account_display=account_display,
        contact_count=len(contacts),
        rows_html=rows_html
    )

    output_path = OUTPUT_DIR / f"{account_slug}-stakeholder-map.html"
    output_path.write_text(html)
    return output_path


def main():
    for slug in SLUG_MAP:
        result = generate_chart(slug)
        if result:
            print(f"✓ Generated {result.name}")
        else:
            print(f"✗ Skipped {slug} (no data or missing file)")


if __name__ == "__main__":
    main()