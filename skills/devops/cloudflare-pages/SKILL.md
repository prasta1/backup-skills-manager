---
name: cloudflare-pages
description: Deploy static sites to Cloudflare Pages.
---

# Cloudflare Pages Deployment

## Trigger

Use when deploying static sites to Cloudflare Pages, extracting Claude Design artifacts, fixing misconfigured Pages projects, or setting up GitHub continuous deployment.

## Prerequisites

- `wrangler` CLI installed and authenticated
- Cloudflare account with domain added
- GitHub repo with site files

## Workflow

### 1. Check project type

```bash
wrangler pages project list
```

If build logs show `npx wrangler deploy`, the project is configured as a Worker. Fix in Cloudflare dashboard:
- **Build command**: blank or `echo "no build"`
- **Deploy command**: `npx wrangler pages deploy . --project-name <name>`

Or add `wrangler.toml` to repo root:
```toml
name = "<project-name>"
compatibility_date = "2026-08-01"

[site]
bucket = "./"
```

### 2. Deploy static assets

```bash
wrangler pages deploy <directory> --project-name <name>
```

For Claude Design bundled HTML, extract first. See `references/extracting-claude-design-artifacts.md`.

### 3. Connect custom domain

In Cloudflare dashboard:
- Workers & Pages > Pages > `<project>` > Custom domains
- Add custom domain

If domain is attached to another project, remove it from the old project first.

### 4. Verify

```bash
curl -sI https://<domain> | grep -E 'content-type|cf-cache-status'
```

Expect `content-type: text/html`. If still serving old content, purge cache:

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/<zone-id>/purge_cache" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

## Common Pitfalls

- **Non-interactive auth**: CI/agent terminals can't complete OAuth. Use API token or run `wrangler` interactively.
- **Worker vs Pages**: Projects with `npx wrangler deploy` build command are Workers. Static sites need `pages deploy` or `[site] bucket`.
- **Case-sensitive filenames**: Pages expects lowercase `index.html`.
- **GitHub email privacy**: Push may fail with GH007. Use `git config user.email "<username>@users.noreply.github.com"`.
- **Cache staleness**: Purge after domain routing changes.

## Continuous Deployment

Once GitHub integration is active, every push auto-deploys. No further wrangler commands needed for content updates.
