---
name: social-media-content-reading
description: "Read Reddit, RSS, Atom, and JSON feeds without a browser."
version: 1.0.0
author: Hermes Curator
license: MIT
platforms: [linux, macos, windows]
tags: [reddit, rss, atom, json-feed, social-media, content-reading, monitoring, research]
metadata:
  hermes:
    tags: [reddit, rss, atom, json-feed, social-media, content-reading, monitoring, research]
---

# Social Media Content Reading

Read Reddit posts and comments, or RSS/Atom/JSON Feed entries, from headless/server environments where normal browser routes are blocked (403, humanity walls). No browser required. Standard library Python only — nothing to install.

This umbrella consolidates two former skills:

| Former Skill | Purpose | Script |
|---|---|---|
| `reddit-reading` (absorbed) | Reddit listings, search, threads with comments, user pages | `scripts/reddit.py` |
| `rss-feeds` (absorbed) | RSS/Atom/JSON Feed reading + feed discovery behind page URLs | `scripts/feed.py` |

## When to Use

- "What is r/NAME saying about X" → **Reddit Reading**
- "Find Reddit threads on Y" → **Reddit Reading**
- "Summarise this Reddit thread" → **Reddit Reading**
- "What's new on <blog/site>" → **RSS Feeds**
- "Latest releases of <GitHub repo>" → **RSS Feeds**
- "Does this site have an RSS feed" → **RSS Feeds**
- Passing entry links to `web_extract` for full-body content

## Common Setup

No prerequisites for either reader. Both scripts are zero-install (Python 3.10+ standard library).

### Reddit optional upgrade (app credentials, no user login)

Anonymous Atom feeds (`.rss` endpoints) work with no setup but are throttled to ~1 request/minute per IP. For sustained use or full data (scores, nested comments), register a free "script" app at https://www.reddit.com/prefs/apps and set in `.env`:

```
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
```

This is an application registration, not a login: the script uses the app-only `client_credentials` grant, never a username, password, or browser cookie. With both values set, the script switches to the OAuth API automatically (~100 requests/minute). If missing or rejected, it falls back to anonymous feeds and says so.

| | Anonymous feeds | OAuth app credentials |
|---|---|---|
| Setup | nothing | 1-minute app registration, two `.env` values |
| Rate limit | ~1 request / minute / IP | ~100 requests / minute |
| Thread data | post + top-level comments, no scores | nested comments, scores |
| Acts as a user | no | no |

### RSS Feeds

No credentials needed. Python 3.10+, network access to the feed host.

## Reddit Reading (absorbed from `reddit-reading`)

### How to Run

```bash
python3 scripts/reddit.py doctor
python3 scripts/reddit.py sub LocalLLaMA --sort hot --limit 15
python3 scripts/reddit.py search "hermes agent" --sub LocalLLaMA --sort new
python3 scripts/reddit.py thread https://www.reddit.com/r/x/comments/abc123/slug/ --limit 40
python3 scripts/reddit.py user spez --limit 10
python3 scripts/reddit.py --json search "topic"
```

### Quick Reference

| Need | Command | Anonymous | OAuth |
|---|---|---|---|
| Subreddit front page | `sub NAME --sort hot\|new\|top\|rising [--time week]` | ✔ | ✔ |
| Search all of Reddit | `search "q" --sort relevance\|new\|top\|comments` | ✔ | ✔ |
| Search one subreddit | `search "q" --sub NAME` | ✔ | ✔ |
| Thread + comments | `thread URL --limit N` | ✔ top-level only, no scores | ✔ nested, scores |
| User posts/comments | `user NAME` | ✔ | ✔ |
| Backend + rate limit | `doctor` | ✔ | ✔ |

### Procedure

1. `doctor` once per task if you haven't called it this session.
2. Plan your calls before making them. Anonymous Reddit allows ~1 request/minute/IP.
3. Read thread bodies, not just titles.
4. Cite the permalink (`url` field), not the listing page.
5. For sustained access, ask the user to register app credentials.

### Pitfalls

- `www.reddit.com/.json`, `api.reddit.com`, `old.reddit.com` return 403 for datacenter IPs.
- `r.jina.ai` and `browser_navigate` hit the same block.
- Anonymous thread feeds: top-level comments only, no scores.
- Never paste `REDDIT_CLIENT_SECRET` into chat or log.
- Do not fix 429 by retrying in a loop.

### Verification

`python3 scripts/reddit.py doctor` prints `anonymous_feed: ok` and rate-limit info. With credentials, prints `active_backend: oauth` and numeric scores.

## RSS/Atom/JSON Feed Reading (absorbed from `rss-feeds`)

### How to Run

```bash
python3 scripts/feed.py read https://hnrss.org/frontpage --limit 10
python3 scripts/feed.py read https://example.com/            # page URL → discovers the feed
python3 scripts/feed.py read URL --since 2026-09-01 --json
python3 scripts/feed.py discover https://example.com/
```

### Quick Reference — Feed URL patterns

| Source | Feed URL pattern |
|---|---|
| GitHub releases / commits / tags | `…releases.atom`, `…/commits/BRANCH.atom`, `…/tags.atom` |
| Subreddit / Reddit search | `…r/NAME/.rss`, `…/search.rss?q=…` |
| YouTube channel | `…/feeds/videos.xml?channel_id=UC…` |
| Hacker News | `https://hnrss.org/frontpage` |
| arXiv category | `https://rss.arxiv.org/rss/cs.CL` |
| Substack / Medium / WordPress / Ghost | `SITE/feed`, `medium.com/feed/@user`, `SITE/rss/` |
| Podcasts | RSS URL from hosting page (`discover` finds it) |

Output fields: `title`, `link`, `published` (UTC ISO 8601), `author`, `summary` (HTML stripped, ≤ 2000 chars). Newest-first.

### Procedure

1. Run `read` on a site URL directly for auto-discovery.
2. Bound with `--limit N` or `--since YYYY-MM-DD`.
3. For full text, pass entry `link` to `web_extract`.
4. Cite the entry `link`, not the feed URL.

### Pitfalls

- 200 response with HTML = page, not feed; script auto-discovers.
- Reddit feeds share anonymous throttle; use `scripts/reddit.py` for Reddit calls.
- Dates normalised to UTC; dateless entries sort to bottom.
- Cloudflare-fronted feeds 403 non-browser clients; `blocked-page-recovery` handles that.

### Verification

`python3 scripts/feed.py read https://github.com/NousResearch/hermes-agent/releases.atom --limit 1` prints one entry with a `releases/tag/` link.

## Cross-References

- `blocked-page-recovery` (in `research-toolkit`) — recovers WAF/paywalled pages.
- `web_extract` — for fetching full article bodies from feed entry links.
