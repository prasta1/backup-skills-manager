# Media Download (video and audio files off the web)

Applies to "save this video", "grab that clip", "download this audio". For *text* off a page use `blocked-page-recovery.md` instead.

## Principle

Two needs, two paths: **yt-dlp** when you want the *file*, the site's own **syndication/embed API** when you want the *inventory* (or when the extractor has rotted). Prefer the tool; keep the API route as the fallback that survives extractor breakage.

## Ladder

### 1. yt-dlp (default)

General tool, 500+ sites, playlists, HLS/DASH assembly via ffmpeg, metadata and thumbnail embedding.

```bash
yt-dlp -F "<url>"                     # list formats with IDs
yt-dlp -f "http-2176" "<url>"         # pick one
yt-dlp "<url>"                        # best by default
yt-dlp --playlist-items 2 "<url>"     # a 4-video tweet is a playlist
```

- Installed at `~/.local/bin/yt-dlp` (standalone Mach-O binary, `/opt/homebrew/bin` untouched). Update with `yt-dlp -U`. **Never `brew install yt-dlp`** — the formula drags in python@3.15, deno and ~20 dependencies.
- Public X/Twitter posts resolve anonymously (guest token → GraphQL → m3u8). Cookies are only needed for sensitive-flagged or login-gated posts: `--cookies-from-browser chrome`. Never guess credentials.
- HLS-only renditions need ffmpeg on PATH (present on the Studio, 9.0.x).

### 2. Site syndication/embed endpoint (fallback for extractor rot)

Use when yt-dlp reports `Unsupported URL`, 401, or metadata errors on a site that clearly has the media. For X:

```bash
curl -s -H 'User-Agent: Mozilla/5.0' \
  "https://cdn.syndication.twimg.com/tweet-result?id=<TWEET_ID>&lang=en&token=a"
```

Returns `.video.variants[]` plus `mediaDetails[0].video_info.variants[]` — explicit MP4 URLs with nominal bitrates, and one m3u8. Pick by bitrate and `curl -o`. Zero auth, no dependency. This is the same data path yt-dlp consumes, so it keeps working when the extractor's flags stop mattering.

Limits: one tweet per call, no playlists, cannot assemble HLS-only media without ffmpeg.

### 3. Plain CDN variant URL (last resort)

Only if 1 and 2 both fail and you already hold a direct media URL from a page dump. Same verification discipline as below applies.

## Verify every download (fake-success rule)

A 200 response and a plausible size are not proof. Do all three:

```bash
curl -sIL "<url>" | grep -iE '^(HTTP/|content-length|content-type)'   # before downloading
ls -l "<file>"                                                        # byte count must equal Content-Length
ffprobe -v error -show_entries format=duration,size,bit_rate,format_name \
  -show_entries stream=codec_name,width,height,codec_type \
  -of default=noprint_wrappers=1 "<file>"
```

**Pitfall — estimates masquerading as sizes.** yt-dlp's `≈` file sizes are computed from the *nominal* bitrate, not the real object. Measured 6% low on a 4K rendition (estimated 87.6 MiB, actual 92.6 MiB). The syndication JSON's `bitrate` field is the same trap: a "10368000" bps 1080p variant measured 7.83 Mbps on disk. Trust Content-Length; never report an estimate as the file size.

## Where it lands

- Kept media Patrick asked to save: `~/Downloads/<slug>-<quality>.mp4` (e.g. `nouscon-2026-nousresearch-1080p.mp4`).
- Agent-generated artifacts: `~/.hermes/outputs/` — never the scratch dir, which is pruned at 24h.

## Reporting

Lead with the path and the real byte size, then resolution/codecs/duration and which tier you picked with the other tiers and sizes offered. Show the artifact inline with a `MEDIA:` line.
