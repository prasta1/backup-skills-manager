# Content Monitoring: Reddit and RSS Feeds

**Consolidated from:** `social-media-content-reading` (which absorbed `reddit-reading` and `rss-feeds`)

## Overview

Monitoring Reddit and RSS/Atom feeds is a core research technique for tracking public sentiment, product issues, competitor activity, and emerging topics. These are used within competitive analysis, blogwatcher workflows, and market intelligence gathering.

## Reddit Monitoring

Reddit's `.json` endpoints return 403 for server/DC IPs. Two viable backends:

1. **OAuth app-only** (`client_credentials` grant): register a "script" app at `reddit.com/prefs/apps`, set `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET`. No user login. ~100 req/min, full JSON with scores and nested comments.
2. **Anonymous Atom feeds** (`/r/NAME/.rss`): no setup needed but ~1 req/min/IP.

### Common Reddit Research Tasks

| Need | Command |
|---|---|  
| Subreddit front page | `python3 scripts/reddit.py sub NAME --sort hot --limit 15` |
| Search all of Reddit | `python3 scripts/reddit.py search "query" --limit 15` |
| Search one subreddit | `python3 scripts/reddit.py search "query" --sub NAME` |
| Thread + comments | `python3 scripts/reddit.py thread URL` |
| User posts/comments | `python3 scripts/reddit.py user NAME` |
| Backend check | `python3 scripts/reddit.py doctor` |

### Pitfalls

- `www.reddit.com/.json`, `api.reddit.com`, `old.reddit.com` return 403 for datacenter IPs.
- Anonymous thread feeds: top-level comments only, no scores.
- Reddit anonymous feeds share a ~1 req/min/IP throttle with RSS feed reads.
- Never paste `REDDIT_CLIENT_SECRET` into chat.

## RSS/Atom/JSON Feed Reading

### Common Feed Patterns

| Source | Feed URL pattern |
|---|---|  
| GitHub releases | `https://github.com/USER/REPO/releases.atom` |
| Subreddit / search | `https://reddit.com/r/NAME/.rss` |
| YouTube channel | `https://www.youtube.com/feeds/videos.xml?channel_id=UC...` |
| Hacker News | `https://hnrss.org/frontpage` |
| arXiv category | `https://rss.arxiv.org/rss/cs.CL` |
| Substack / Medium / WordPress | `SITE/feed` or `medium.com/feed/@user` |

### Usage

```bash
python3 scripts/feed.py read https://hnrss.org/frontpage --limit 10
python3 scripts/feed.py discover https://example.com/  # finds feed behind a page URL
python3 scripts/feed.py read https://example.com/      # auto-discovers then reads
```

Output fields: `title`, `link`, `published` (UTC ISO 8601), `author`, `summary`. Newest-first.

## Integration with Research Workflows

1. **Blogwatcher**: use `feed.py` to monitor company blogs, competitor news, and industry publications.
2. **Competitive analysis**: use `reddit.py` to track sentiment and issues in relevant subreddits.
3. **Blocked page recovery**: if a feed or linked article returns 403, use `recover_page.py` to find an archive copy.
