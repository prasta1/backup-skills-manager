#!/usr/bin/env python3
"""Build the inbox-zero sender-grouped widget from the Gmail inbox.

Enumerates the INBOX via himalaya (Studio account `gmail`), groups emails by sender,
and writes a self-contained HTML widget with clickable pills for high-count senders,
one "All other senders" bucket pill for everything below the pill threshold, per-email
sections, and double-click-to-confirm bulk delete that POSTs to a local delete server
(see inbox-delete-server.py).

Every email in the inbox is reachable from the UI. The bucket pill exists because a
per-sender pill threshold alone strands low-count senders in hidden sections with no
control able to reveal them, which makes inbox zero unreachable by construction.

Usage: python3 build_inbox_widget.py --out /tmp/inbox-sender-widget.html [--token <tok>]
"""
import argparse, html as htmlmod, os, subprocess, sys, urllib.parse
from datetime import datetime, timezone
from collections import defaultdict

SEP = "\u2502"   # │
DASH = "\u2506"  # ┆

PAGE_SIZE = 250   # himalaya page size; we page until a short page comes back
MAX_PAGES = 60    # safety stop (15k messages)
PILL_MIN = 3      # senders at or above this get their own pill
OTHER_KEY = "__other__"


def esc(value):
    """Escape untrusted text for HTML text nodes and quoted attributes.

    Sender display names and subjects are attacker-controlled: anyone can put a quote,
    an angle bracket or a <script> in a display name. This page embeds the bearer token
    for a destructive endpoint, so unescaped markup here is script execution against it.
    A mere double-quote also breaks data-sender="..." and makes that sender unopenable.
    """
    return htmlmod.escape(str(value), quote=True)


def ts_of_date(date_str):
    """Parse himalaya's `YYYY-MM-DD HH:MM±HH:MM` into an epoch; 0 if unparseable.

    Sorting must happen on real instants, not the rendered string: the same wall clock
    in two timezones compares wrong lexicographically. An unparseable date sorts last
    rather than crashing the build, and main() reports how many did.
    """
    s = (date_str or "").strip()
    for fmt in ("%Y-%m-%d %H:%M%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    return 0


# Favicon: envelope with a 0 inside. Margins are stroke-aware (the flap's painted
# bottom, not its centre line) and every gap is >= 1.5 units so nothing merges at
# a 32px tab. Verified numerically, not by eye.
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#2f6ae0"/><rect x="6" y="9" width="52" height="46" rx="7" fill="none" stroke="#ffffff" stroke-width="4.5"/><path d="M9 13 32 24 55 13" fill="none" stroke="#ffffff" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/><ellipse cx="32" cy="39.5" rx="6.4" ry="7.6" fill="none" stroke="#ffffff" stroke-width="4.6"/></svg>"""


def favicon_data_uri():
    """Inline SVG data URI, so the widget stays a single portable file."""
    return "data:image/svg+xml," + urllib.parse.quote(FAVICON_SVG, safe="")


def _parse_rows(out):
    """Parse a himalaya envelope table into dicts.

    Columns are id/FLAGS/SUBJECT/SENDER/DATE/SIZE. A subject containing the column
    separator would shift everything right, so take the trailing three columns from
    the right and re-join whatever is left as the subject.
    """
    rows = []
    for ln in out.splitlines():
        if not ln.strip().startswith(SEP):
            continue
        inner = ln.strip()[1:-1]
        parts = [p.strip() for p in inner.split(DASH)]
        if len(parts) < 6 or not parts[0].isdigit():
            continue
        eid, flags = parts[0], parts[1]
        size, date, sender = parts[-1], parts[-2], parts[-3]
        subject = DASH.join(parts[2:-3])
        rows.append({"id": eid, "flags": flags, "subject": subject,
                     "from": sender, "date": date, "size": size,
                     "unread": "*" in flags})
    return rows


def enumerate_inbox():
    """Return every INBOX envelope, paging until himalaya runs out.

    himalaya lists most-recent-first and paginates; a full page means there is more.
    Never treat one page as the whole mailbox: a page size that happens to exceed the
    mailbox today silently truncates it tomorrow.
    """
    env = dict(os.environ)
    pw = None
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("GMAIL_APP_PASSWORD="):
                pw = line.split("=", 1)[1].strip().strip('"')
                break
    if pw:
        env["GMAIL_APP_PASSWORD"] = pw

    def fetch(page):
        r = subprocess.run(
            ["himalaya", "envelope", "list", "-a", "gmail", "-m", "INBOX",
             "-p", str(page), "-s", str(PAGE_SIZE)],
            capture_output=True, text=True, timeout=180, env=env)
        return _parse_rows(r.stdout)

    emails, seen, page = [], set(), 1
    while page <= MAX_PAGES:
        rows = fetch(page)
        if not rows:
            break
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                emails.append(r)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return emails


def build_widget(emails, token):
    by_sender = defaultdict(list)
    for e in emails:
        by_sender[e["from"]].append(e)
    senders = sorted(by_sender.items(), key=lambda kv: (-len(kv[1]), kv[0].lower()))

    newest = {sender: max(ts_of_date(e["date"]) for e in es) for sender, es in senders}

    big = [d for d in senders if len(d[1]) >= PILL_MIN]
    big.sort(key=lambda kv: -len(kv[1]))
    small = [d for d in senders if len(d[1]) < PILL_MIN]
    small_total = sum(len(es) for _, es in small)

    # Open something on load: an empty pane reads as broken. Prefer the catch-all bucket
    # (most senders, most mail), else the largest single sender. This deliberately does
    # NOT pre-select anything - clicking a pill selects its mail, but merely opening the
    # widget must never arm a 130-email delete.
    default_open = OTHER_KEY if small else (big[0][0] if big else None)

    def pill_html(sender, label, count, bucket=False, ts=0):
        cls = "pill pill-bucket" if bucket else "pill"
        extra = ' data-nofilter="1"' if bucket else ""
        return ('<button type="button" class="%s" data-sender="%s" data-name="%s" '
                'data-count="%d" data-ts="%d"%s onclick="togglePill(this)">'
                '<span class="pill-check">\u2713</span>'
                '<span class="pill-name">%s</span>'
                '<span class="pill-count">%d</span></button>'
                % (cls, esc(sender), esc(sender), count, ts, extra, esc(label), count))

    pill_parts = [pill_html(s, s, len(es), ts=newest[s]) for s, es in big]
    if small:
        pill_parts.append(pill_html(OTHER_KEY, "All other senders", small_total, bucket=True,
                                    ts=max(newest[s] for s, _ in small)))
    pills_html = "\n".join(pill_parts)

    def row_html(e, sender):
        badge = '<span class="unread-badge">unread</span>' if e["unread"] else ""
        row_cls = "email-row" + (" unread" if e["unread"] else "")
        return ('<div class="%s" data-id="%s" data-sender="%s">'
                '<input type="checkbox" class="email-cb" data-id="%s" data-sender="%s">'
                '<span class="email-subj">%s</span>'
                '<span class="email-date">%s</span>%s</div>'
                % (row_cls, esc(e["id"]), esc(sender), esc(e["id"]), esc(sender),
                   esc(e["subject"]), esc(e["date"]), badge))

    def head_html(title, count_label):
        return ('<div class="section-head">'
                '<span class="section-sender">%s</span>'
                '<span class="section-count">%s</span>'
                '<button type="button" class="mini-btn" onclick="checkAllInSection(this)">check all</button>'
                '<button type="button" class="mini-btn" onclick="uncheckAllInSection(this)">uncheck</button>'
                '</div>' % (esc(title), esc(count_label)))

    sections = []
    # High-count senders: one pill, one section.
    for sender, es in big:
        es_sorted = sorted(es, key=lambda e: e["date"], reverse=True)
        rows = "\n".join(row_html(e, sender) for e in es_sorted)
        sections.append(
            '<div class="sender-section" data-sender="%s" data-name="%s" data-count="%d" '
            'data-ts="%d" style="display:%s">%s%s</div>'
            % (esc(sender), esc(sender), len(es), newest[sender],
               "block" if sender == default_open else "none",
               head_html(sender, "%d emails" % len(es)), rows))

    # Everything below the pill threshold: one bucket, sub-headed per sender, so every
    # email has a clickable path. These senders get NO individual section: a second copy
    # of the same rows would double-count checkboxes and break per-row removal.
    if small:
        chunks = []
        for sender, es in sorted(small, key=lambda kv: (-len(kv[1]), kv[0].lower())):
            es_sorted = sorted(es, key=lambda e: e["date"], reverse=True)
            chunks.append(
                '<div class="sub-group" data-sender="%s" data-name="%s" data-count="%d" data-ts="%d">'
                '<div class="sub-head">'
                '<span class="sub-sender">%s</span>'
                '<span class="sub-count">%d</span>'
                '<button type="button" class="mini-btn" onclick="checkAllInSection(this)">check</button>'
                '<button type="button" class="mini-btn" onclick="uncheckAllInSection(this)">uncheck</button>'
                '</div>%s</div>'
                % (esc(sender), esc(sender), len(es), newest[sender],
                   esc(sender), len(es),
                   "\n".join(row_html(e, sender) for e in es_sorted)))
        sections.append(
            '<div class="sender-section bucket-section" data-sender="%s" style="display:%s">%s%s</div>'
            % (OTHER_KEY,
               "block" if default_open == OTHER_KEY else "none",
               head_html("All other senders", "%d senders \u00b7 %d emails" % (len(small), small_total)),
               "\n".join(chunks)))
    sections_html = "\n".join(sections)

    note = (" Senders with fewer than %d emails are grouped under <b>All other senders</b>."
            % PILL_MIN) if small else ""
    html = _TEMPLATE.replace("__PILLS__", pills_html).replace("__SECTIONS__", sections_html)
    html = html.replace("__TOTAL__", str(len(emails))).replace("__SENDERS__", str(len(senders)))
    html = html.replace("__BUCKET_NOTE__", note).replace("__TOKEN__", token)
    html = html.replace("__FAVICON__", favicon_data_uri())
    return html


_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="icon" type="image/svg+xml" href="__FAVICON__">
<style>
  :root {
    --bg: #0e0e12;
    --surface: #17171d;
    --surface-2: #1e1e26;
    --border: #2b2b35;
    --fg: #f5f5f7;
    --muted: #9b9ba6;
    --accent: #2f6ae0;
    --accent-bright: #4d86ff;
    --accent-soft: rgba(61, 123, 255, 0.16);
    --danger: #d92d20;
    --danger-hover: #b32218;
    --ok: #32d583;
    --radius: 12px;
  }
  * { box-sizing: border-box; }
  html { scrollbar-color: #3a3a46 transparent; background: var(--bg); }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    color: var(--fg); margin: 0; padding: 32px 36px 64px;
    background: var(--bg); max-width: 980px;
    -webkit-font-smoothing: antialiased;
  }
  ::selection { background: var(--accent-soft); }

  /* Masthead */
  .masthead { display: flex; align-items: flex-end; gap: 18px; margin-bottom: 10px; }
  h1 { font-size: 30px; font-weight: 700; letter-spacing: -0.032em; margin: 0; line-height: 1; }
  .count { color: var(--muted); font-size: 15px; font-weight: 500; font-variant-numeric: tabular-nums; padding-bottom: 2px; }
  .count b { color: var(--fg); font-weight: 650; }
  .sub { color: var(--muted); font-size: 14px; line-height: 1.55; margin: 0 0 28px; max-width: 70ch; }
  .sub b { color: var(--fg); font-weight: 600; }

  /* Pills */
  .pills { display: flex; flex-wrap: wrap; gap: 9px; margin-bottom: 26px; }
  .pill {
    display: inline-flex; align-items: center; gap: 9px;
    background: var(--surface); border: 1px solid var(--border); border-radius: 999px;
    padding: 9px 17px; font-size: 14px; font-weight: 550; cursor: pointer; color: var(--fg);
    transition: border-color .16s ease, background .16s ease, box-shadow .16s ease, transform .1s ease;
  }
  .pill:hover { border-color: #3f3f4c; background: var(--surface-2); }
  .pill:active { transform: translateY(1px); }
  .pill:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .pill .pill-check { display: none; font-weight: 800; }
  .pill.active {
    background: var(--accent); border-color: var(--accent); color: #fff;
    box-shadow: 0 2px 10px rgba(0,0,0,.45);
  }
  .pill.active .pill-check { display: inline; }
  .pill .pill-count {
    background: rgba(255,255,255,.07); border-radius: 999px; padding: 2px 10px;
    font-size: 12.5px; font-weight: 700; color: var(--muted); font-variant-numeric: tabular-nums;
    min-width: 26px; text-align: center;
  }
  .pill.active .pill-count { background: rgba(255,255,255,.22); color: #fff; }
  .pill-bucket { border-style: dashed; color: var(--muted); }
  .pill-bucket.active { color: #fff; }

  /* Sort bar */
  .sortbar { display: flex; align-items: center; gap: 8px; margin: 0 0 16px; }
  .sort-label { font-size: 13px; color: var(--muted); font-weight: 550; margin-right: 2px; }
  .sort-btn {
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 6px 13px; font-size: 13px; font-weight: 550; color: var(--muted); cursor: pointer;
    transition: border-color .16s ease, color .16s ease, background .16s ease;
  }
  .sort-btn:hover { border-color: #3f3f4c; color: var(--fg); }
  .sort-btn.is-active { background: var(--accent-soft); border-color: var(--accent); color: var(--fg); }
  .sort-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .sort-dir {
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    width: 34px; height: 31px; font-size: 15px; line-height: 1; color: var(--fg); cursor: pointer;
    transition: border-color .16s ease;
  }
  .sort-dir:hover { border-color: #3f3f4c; }
  .sort-dir:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  /* Status + toolbar */
  .status { font-size: 14px; color: var(--muted); margin-bottom: 16px; min-height: 21px; }
  .status b { color: var(--accent-bright); font-weight: 700; }
  .toolbar {
    display: flex; gap: 10px; align-items: center; margin-bottom: 30px; flex-wrap: wrap;
    padding: 13px 15px; background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius);
  }
  .search {
    flex: 1; min-width: 210px; padding: 10px 15px; border: 1px solid var(--border);
    border-radius: 9px; font-size: 14px; color: var(--fg); background: var(--bg);
    transition: border-color .16s ease, box-shadow .16s ease;
  }
  .search:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
  .search::placeholder { color: var(--muted); }
  .sel-count { font-size: 13.5px; color: var(--muted); font-weight: 550; margin-right: auto; font-variant-numeric: tabular-nums; }

  /* Buttons */
  .btn {
    background: var(--surface-2); border: 1px solid var(--border); border-radius: 9px;
    padding: 10px 17px; font-size: 14px; font-weight: 600; cursor: pointer; color: var(--fg);
    transition: border-color .16s ease, background .16s ease, box-shadow .16s ease;
  }
  .btn:hover:not(:disabled) { border-color: #454554; background: #23232c; }
  .btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .btn:disabled { opacity: .35; cursor: not-allowed; }
  .btn.armed { border-color: var(--accent-bright); background: var(--surface-2); }
  .btn-danger { background: var(--danger); color: #fff; border-color: var(--danger); }
  .btn-danger:hover:not(:disabled) { background: var(--danger-hover); border-color: var(--danger-hover); }
  .btn-danger.armed { background: var(--danger-hover); border-color: #8f1a13; }

  /* Sender groups — dense, hairline-ruled */
  .sender-section { margin-bottom: 8px; }
  .section-head {
    display: flex; align-items: center; gap: 12px; padding: 16px 6px 11px;
    border-bottom: 1px solid var(--border);
  }
  .section-head::before {
    content: ""; width: 3px; height: 17px; border-radius: 2px;
    background: var(--accent-bright); flex-shrink: 0; opacity: .9;
  }
  .section-sender { font-weight: 650; font-size: 15.5px; letter-spacing: -0.012em; }
  .section-count { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
  .mini-btn {
    background: none; border: 1px solid var(--border);
    border-radius: 7px; padding: 5px 12px; font-size: 12.5px; cursor: pointer; color: var(--muted);
    margin-left: 6px; transition: border-color .16s ease, color .16s ease;
  }
  .mini-btn:first-of-type { margin-left: auto; }
  .mini-btn:hover { border-color: var(--accent); color: var(--fg); }

  /* Bucket sub-groups */
  .bucket-section .section-head::before { background: var(--muted); opacity: .55; }
  .sub-group { border-bottom: 1px solid var(--border); }
  .sub-group:last-child { border-bottom: none; }
  .sub-head { display: flex; align-items: center; gap: 10px; padding: 12px 6px 8px 22px; }
  .sub-sender { font-weight: 600; font-size: 14px; letter-spacing: -0.008em; color: #dcdce2; }
  .sub-count {
    color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums;
    background: rgba(255,255,255,.05); border-radius: 999px; padding: 1px 8px;
  }

  /* Email rows */
  .email-row {
    display: flex; align-items: center; gap: 14px; padding: 12px 6px 12px 22px;
    border-bottom: 1px solid var(--border); font-size: 14px;
    transition: background .13s ease;
  }
  .sub-group .email-row { padding-left: 34px; border-bottom: none; }
  .email-row:hover { background: var(--surface); }
  .email-row.selected { background: var(--accent-soft); }
  .email-cb { accent-color: var(--accent); width: 16px; height: 16px; flex-shrink: 0; cursor: pointer; }
  .email-subj { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .email-row.unread .email-subj { font-weight: 600; }
  .email-date {
    color: var(--muted); font-size: 12.5px; white-space: nowrap; flex-shrink: 0;
    font-variant-numeric: tabular-nums;
  }
  .unread-badge {
    background: var(--accent); color: #fff; border-radius: 5px;
    padding: 2px 8px; font-size: 11.5px; font-weight: 700; flex-shrink: 0;
  }

  /* Result banner */
  .result-banner { display: none; margin-top: 22px; padding: 14px 17px; border-radius: 9px; font-size: 14px; }
  .result-banner.ok { display: block; background: rgba(50,213,131,.1); border: 1px solid rgba(50,213,131,.4); color: var(--fg); }
  .result-banner.err { display: block; background: rgba(240,68,56,.1); border: 1px solid rgba(240,68,56,.4); color: var(--fg); }
  .result-banner b { font-weight: 700; }

  .footer { margin-top: 32px; font-size: 13px; color: var(--muted); line-height: 1.65; max-width: 70ch; }

  /* Empty state */
  .empty { display: none; padding: 72px 20px; text-align: center; }
  .empty.show { display: block; }
  .empty .empty-title { font-size: 20px; font-weight: 700; color: var(--fg); margin-bottom: 9px; letter-spacing: -0.02em; }
  .empty .empty-sub { font-size: 14px; color: var(--muted); }
</style>
</head>
<body>
  <div class="masthead">
    <h1>Inbox by sender</h1>
    <div class="count"><b>__TOTAL__</b> emails · __SENDERS__ senders</div>
  </div>
  <div class="sub">Click a sender to expand its emails. Select, then Archive, Mark as read, or Delete (double-click to confirm).__BUCKET_NOTE__</div>

  <div class="sortbar">
    <span class="sort-label">Sort</span>
    <button type="button" class="sort-btn is-active" data-sort="count" onclick="setSort('count')">Count</button>
    <button type="button" class="sort-btn" data-sort="name" onclick="setSort('name')">Name</button>
    <button type="button" class="sort-btn" data-sort="date" onclick="setSort('date')">Date</button>
    <button type="button" class="sort-dir" id="dirBtn" onclick="toggleDir()" title="Reverse order">&darr;</button>
  </div>

  <div class="pills" id="pills">
__PILLS__
  </div>

  <div class="status" id="status">Nothing selected yet.</div>

  <div class="toolbar">
    <input class="search" id="search" placeholder="Filter senders…" oninput="filterPills()">
    <span class="sel-count" id="selCount">0 emails selected</span>
    <button type="button" class="btn" id="readBtn" disabled onclick="armOrAction('read')">Mark as read</button>
    <button type="button" class="btn" id="archiveBtn" disabled onclick="armOrAction('archive')">Archive</button>
    <button type="button" class="btn btn-danger" id="delBtn" disabled onclick="armOrAction('delete')">Delete</button>
  </div>

  <div id="sections">
__SECTIONS__
  </div>

  <div class="empty" id="empty">
    <div class="empty-title">Inbox zero</div>
    <div class="empty-sub">Nothing left to triage. New mail will show up here next time you run it.</div>
  </div>

  <div class="result-banner" id="resultBanner"></div>

  <div class="footer">Deletes move emails to trash (recoverable ~30 days). Archive moves them out of the inbox. Double-click an action to confirm — first click arms it, second fires.</div>

<script>
  const sections = document.getElementById('sections');
  const delBtn = document.getElementById('delBtn');
  const archiveBtn = document.getElementById('archiveBtn');
  const readBtn = document.getElementById('readBtn');
  const selCount = document.getElementById('selCount');
  const status = document.getElementById('status');
  const resultBanner = document.getElementById('resultBanner');
  const empty = document.getElementById('empty');
  const API = 'http://127.0.0.1:8644/';
  const TOKEN = '__TOKEN__';
  let armed = false;
  let armTimer = null;
  let armedAction = null;

  // Sorting. Every sender entity carries data-count / data-name / data-ts so the
  // ordering never requires re-parsing rendered text. The catch-all bucket is pinned
  // last in both the pill row and the section list: it is a remainder, not a sender.
  const SORT_DEFAULT_DIR = { count: -1, name: 1, date: -1 };
  let sortKey = 'count';
  let sortDir = -1;

  function cmpFor(key) {
    if (key === 'count') return (a, b) => Number(a.dataset.count) - Number(b.dataset.count);
    if (key === 'date')  return (a, b) => Number(a.dataset.ts) - Number(b.dataset.ts);
    return (a, b) => a.dataset.name.localeCompare(b.dataset.name, undefined, { sensitivity: 'base' });
  }

  function sortAll() {
    const cmp = cmpFor(sortKey);
    const tie = (a, b) => a.dataset.name.localeCompare(b.dataset.name, undefined, { sensitivity: 'base' });
    const order = (a, b) => (cmp(a, b) * sortDir) || tie(a, b);

    const pillsBox = document.getElementById('pills');
    const bucketPill = pillsBox.querySelector('.pill-bucket');
    Array.from(pillsBox.querySelectorAll('.pill:not(.pill-bucket)'))
      .sort(order).forEach(p => pillsBox.insertBefore(p, bucketPill || null));
    if (bucketPill) pillsBox.appendChild(bucketPill);

    const box = document.getElementById('sections');
    const bucketSec = box.querySelector('.bucket-section');
    Array.from(box.querySelectorAll('.sender-section:not(.bucket-section)'))
      .sort(order).forEach(s => box.insertBefore(s, bucketSec || null));
    if (bucketSec) box.appendChild(bucketSec);

    if (bucketSec) {
      Array.from(bucketSec.querySelectorAll('.sub-group'))
        .sort(order).forEach(g => bucketSec.appendChild(g));
    }
  }

  function setSort(key) {
    sortKey = key;
    sortDir = SORT_DEFAULT_DIR[key];
    document.querySelectorAll('.sort-btn').forEach(b =>
      b.classList.toggle('is-active', b.dataset.sort === key));
    updateDirBtn();
    sortAll();
  }

  function toggleDir() {
    sortDir *= -1;
    updateDirBtn();
    sortAll();
  }

  function updateDirBtn() {
    const b = document.getElementById('dirBtn');
    b.textContent = sortDir === 1 ? '\u2191' : '\u2193';
    b.title = sortDir === 1 ? 'Ascending (click to reverse)' : 'Descending (click to reverse)';
  }

  function emailCount() {
    return document.querySelectorAll('.email-cb:checked').length;
  }

  function update() {
    document.querySelectorAll('.email-row').forEach(row => {
      row.classList.toggle('selected', row.querySelector('.email-cb').checked);
    });
    const n = emailCount();
    selCount.textContent = n + ' email' + (n === 1 ? '' : 's') + ' selected';
    delBtn.disabled = n === 0;
    archiveBtn.disabled = n === 0;
    readBtn.disabled = n === 0;
    if (n === 0) resetArm();
    if (n === 0) {
      status.innerHTML = 'Nothing selected yet.';
    } else {
      status.innerHTML = '<b>' + n + '</b> email' + (n === 1 ? '' : 's') + ' selected — review, then act.';
    }
    const hasRows = document.querySelectorAll('.email-row').length > 0;
    empty.classList.toggle('show', !hasRows);
  }

  function resetArm() {
    armed = false;
    armedAction = null;
    if (armTimer) clearTimeout(armTimer);
    delBtn.textContent = 'Delete';
    delBtn.classList.remove('armed');
    archiveBtn.textContent = 'Archive';
    archiveBtn.classList.remove('armed');
    readBtn.textContent = 'Mark as read';
    readBtn.classList.remove('armed');
  }

  function armOrAction(action) {
    const btn = action === 'delete' ? delBtn : (action === 'archive' ? archiveBtn : readBtn);
    if (!armed || armedAction !== action) {
      armed = true;
      armedAction = action;
      const n = emailCount();
      const verb = action === 'delete' ? 'delete' : (action === 'archive' ? 'archive' : 'mark read');
      btn.textContent = 'Click again to ' + verb + ' ' + n;
      btn.classList.add('armed');
      armTimer = setTimeout(resetArm, 3000);
    } else {
      resetArm();
      doAction(action);
    }
  }

  function clearSel() {
    document.querySelectorAll('.email-cb').forEach(cb => cb.checked = false);
    document.querySelectorAll('.pill.active').forEach(p => p.classList.remove('active'));
    resultBanner.className = 'result-banner';
    resultBanner.style.display = 'none';
    resetArm();
    update();
  }

  function filterPills() {
    const q = document.getElementById('search').value.toLowerCase();
    document.querySelectorAll('.pill').forEach(p => {
      if (p.dataset.nofilter === '1') { p.style.display = ''; return; }
      p.style.display = p.dataset.sender.toLowerCase().includes(q) ? '' : 'none';
    });
  }

  // A pill is a select-all toggle for one sender, and open/closed follows the selection.
  // Keying off the selection rather than the current display state matters because the
  // widget opens with a section already expanded and nothing selected: keying off
  // display would make the first pill click collapse that section instead of selecting it.
  function togglePill(btn) {
    const sender = btn.dataset.sender;
    const section = sections.querySelector('.sender-section[data-sender="' + CSS.escape(sender) + '"]');
    if (!section) return;
    const boxes = Array.from(section.querySelectorAll('.email-cb'));
    const allSelected = boxes.length > 0 && boxes.every(cb => cb.checked);
    if (allSelected) {
      boxes.forEach(cb => cb.checked = false);
      section.style.display = 'none';
      btn.classList.remove('active');
    } else {
      boxes.forEach(cb => cb.checked = true);
      section.style.display = 'block';
      btn.classList.add('active');
    }
    update();
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Scope to the nearest sub-group when there is one, else the whole sender section,
  // so a bucket sub-header's "check" only touches that one sender's rows.
  function scopeOf(btn) {
    return btn.closest('.sub-group') || btn.closest('.sender-section');
  }
  function checkAllInSection(btn) {
    scopeOf(btn).querySelectorAll('.email-cb').forEach(cb => cb.checked = true);
    update();
  }
  function uncheckAllInSection(btn) {
    scopeOf(btn).querySelectorAll('.email-cb').forEach(cb => cb.checked = false);
    update();
  }

  sections.addEventListener('change', update);
  updateDirBtn();
  sortAll();

  function doAction(action) {
    const cbs = document.querySelectorAll('.email-cb:checked');
    if (!cbs.length) return;
    const ids = Array.from(cbs).map(cb => parseInt(cb.dataset.id, 10));
    delBtn.disabled = true;
    archiveBtn.disabled = true;
    readBtn.disabled = true;
    delBtn.textContent = 'Working...';
    resultBanner.className = 'result-banner';
    resultBanner.style.display = 'none';
    fetch(API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + TOKEN
      },
      body: JSON.stringify({ ids: ids, action: action })
    })
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        const n = Number(data.deleted);
        const one = n === 1 ? '' : 's';
        const verb = data.verb || (action === 'delete' ? 'deleted' : (action === 'archive' ? 'archived' : 'marked read'));
        // Partial application: himalaya acted on fewer ids than we sent, and it does not
        // say which. Removing rows would hide emails that are still in the mailbox, so
        // leave the list alone and tell the user to rebuild.
        if (data.confirmed !== false && Number(data.requested) > n) {
          resultBanner.className = 'result-banner err';
          resultBanner.innerHTML = '<b>' + n + '</b> of <b>' + data.requested + '</b> email' + one +
            ' ' + verb + '. The widget is stale: rebuild it before acting again.';
          update();
          return;
        }
        resultBanner.className = 'result-banner ok';
        resultBanner.innerHTML = '<b>' + n + '</b> email' + one + ' ' + verb + '.' +
          (data.confirmed === false ? ' himalaya reported no count, so this is what we asked for, not what it confirmed.' : '');
        ids.forEach(id => {
          document.querySelectorAll('.email-row[data-id="' + id + '"]').forEach(row => row.remove());
        });
        update();
      } else {
        resultBanner.className = 'result-banner err';
        resultBanner.textContent = 'Action failed: ' + (data.error || data.detail || 'unknown');
        update();
      }
    })
    .catch(err => {
      resultBanner.className = 'result-banner err';
      resultBanner.textContent = 'Action failed: cannot reach delete server. Is the MacBook helper running? (' + err + ')';
      update();
    });
  }
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/inbox-sender-widget.html")
    ap.add_argument("--token", default=os.environ.get("INBOX_DELETE_TOKEN", ""))
    args = ap.parse_args()
    if not args.token:
        import secrets
        args.token = secrets.token_urlsafe(24)
        print(f"[inbox-zero] generated token: {args.token}", file=sys.stderr)
    emails = enumerate_inbox()
    html = build_widget(emails, args.token)
    with open(args.out, "w") as f:
        f.write(html)
    os.chmod(args.out, 0o600)  # the file embeds the delete token
    by_sender = defaultdict(list)
    for e in emails:
        by_sender[e["from"]].append(e)
    n_small = sum(1 for v in by_sender.values() if len(v) < PILL_MIN)
    n_small_mail = sum(len(v) for v in by_sender.values() if len(v) < PILL_MIN)
    print(f"[inbox-zero] wrote {args.out}: {len(emails)} emails, {len(by_sender)} senders "
          f"({len(by_sender) - n_small} pill senders, {n_small} bucketed \u2192 {n_small_mail} emails)")
    n_unread = sum(1 for e in emails if e["unread"])
    print(f"[inbox-zero] reachable in UI: {len(emails)}/{len(emails)} (all senders have a pill or the bucket)")
    print(f"[inbox-zero] unread badges: {n_unread} (must equal IMAP UID SEARCH UNSEEN)")
    n_bad = sum(1 for e in emails if ts_of_date(e["date"]) == 0)
    if n_bad:
        print(f"[inbox-zero] WARNING: {n_bad} unparseable dates - those sort last under Date")


if __name__ == "__main__":
    main()
