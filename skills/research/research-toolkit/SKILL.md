---
name: research-toolkit
description: "Research toolkit: arxiv, scraping, media download, monitoring."
version: 1.2.0
license: MIT
author: Hermes Curator
tags: [research, arxiv, scraping, competitive, monitoring, publications]
metadata:
  hermes:
    tags: [research, arxiv, scraping, competitive-analysis, monitoring, publications]
---

# Research Toolkit

## Overview
This umbrella consolidates research-oriented skills: academic paper discovery (arXiv), web content extraction and recovery, competitive monitoring, blog/RSS feed monitoring, and research gap analysis.

## When to Use
- "Find academic papers on [topic]"
- "Search arXiv for [keyword]"
- "Recover blocked/paywalled pages"
- "Monitor competitors for news"
- "Analyze research gaps in our dataset"
- "Track blog and RSS feed updates"
- "Save this video / grab that clip" (YouTube, X/Twitter, 500+ sites — see references/media-download.md)

## Skill Inventory

| Skill | Purpose | Status |
|---|---|---|
| arxiv | Search arXiv papers by keyword, author, category, ID | absorbed |
| blocked-page-recovery | Recover blocked/paywalled/WAF'd pages via fallbacks | absorbed |
| competitive-analysis | Structured competitive analysis for products/companies | absorbed |
| competitor-news-monitor | Watch named companies for material news | absorbed |
| research-gap-analysis | Identify missing information for qualification | absorbed |
| blogwatcher | Monitor blogs and RSS/Atom feeds via blogwatcher-cli | absorbed |
| research-arxiv | Archive of arxiv search script and methodology | absorbed |
| research-blocked-page-recovery | Archive of page recovery script | absorbed |
| research-competitor-news-monitor | Archive of competitor monitoring | absorbed |
| research-gap-analysis | Archive of gap analysis methodology | absorbed |

## Workflows

### Academic Paper Research
Use arxiv to search by keyword, author, category, or ID. Fetch abstracts and metadata, identify relevant papers for literature reviews or domain research.

### Web Content Recovery
When a page is blocked, paywalled, or behind a WAF:
1. Try cached versions (Wayback Machine, Google Cache)
2. Use Firecrawl for scraping with bypass
3. Check alternative sources (Semantic Scholar, PubMed, etc.)

### Media Capture (video and audio files)
1. Default to `yt-dlp` (`~/.local/bin/yt-dlp`): `-F` to list formats, `-f` to pick, plain URL for best. Multi-video tweets are playlists.
2. If the extractor rots (`Unsupported URL`/401), fall back to the site's own syndication/embed endpoint — zero auth, version-free. For X: `cdn.syndication.twimg.com/tweet-result?id=<id>&lang=en&token=a`.
3. Verify for real: Content-Length from a HEAD request, byte count on disk, then ffprobe. yt-dlp's `"≈"` sizes are bitrate estimates and run ~6% low.
4. Save kept media to `~/Downloads/<slug>-<quality>.mp4`, report the chosen tier plus the alternatives. Full detail: references/media-download.md

### Competitive Intelligence
1. Define scope — what competitors, what dimensions
2. Gather data — competitor websites, pricing sheets, press releases
3. Organize — comparison matrix with scoring/weighting
4. Analyze — identify patterns, gaps, differentiation
5. Monitor — set up recurring alerts for material news

### Blog/RSS Monitoring (absorbed from blogwatcher)
Track blog and RSS/Atom feed updates with the blogwatcher-cli tool. Supports automatic feed discovery, HTML scraping fallback, OPML import, and read/unread article management. Install via Go, Docker, or binary download from the GitHub releases page. See references/blogwatcher.md for full command reference.

### Research Gap Analysis
Identify missing information required for QA or qualification:
1. Map required information items
2. Cross-reference against available sources
3. Flag gaps with priority
4. Generate research plan to fill gaps

## References
- references/competitive-analysis.md
- references/research-gap-analysis.md
- references/blogwatcher.md
- references/arxiv.md (absorbed from research-arxiv)
- references/blocked-page-recovery.md (absorbed from research-blocked-page-recovery)
- references/media-download.md (yt-dlp + syndication-endpoint fallback, verification discipline)
- references/competitor-news-monitor.md (absorbed from research-competitor-news-monitor)

## Scripts
- scripts/search_arxiv.py (absorbed from research-arxiv)
- scripts/recover_page.py (absorbed from research-blocked-page-recovery)
