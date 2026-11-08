# Reading the account's brand access list

Goal: export every brand the signed-in account can shop (pro-deal access) without
scraping and without handling credentials — attach to the user's own browser
session and read the site's own API.

## Attach to a signed-in session (macOS)

- `browser.backend` must not be `off` (`hermes config set browser.backend local`).
  Set `browser.use_real_profile false` when attaching over CDP instead of
  snapshotting the profile. The config file itself is agent-blocked; use
  `hermes config set`.
- **Chrome >= 136 ignores `--remote-debugging-port` on the default profile** and
  reports nothing — no listener, no error. Always pass a non-default
  `--user-data-dir`, or the flag is silently a no-op.
- Working recipe: rely on the built-in real-profile support. `browser.use_real_profile`
  is `true` in config.yaml, so Hermes snapshots the active Chrome profile into
  `~/.hermes/browser-profile/chrome` (caches, extensions, and service workers
  skipped) and launches it with a CDP port itself. Do NOT rsync the profile by
  hand into a scratch dir; that produced a redundant 10 GB copy
  (`~/.hermes/chrome-cdp-real`, removed 2026-09-21).
- Always verify the CDP endpoint answers before driving it; a dead port surfaces
  as a confusing "Chrome fallback failed: could not determine current URL".
- Cookies carry over and stay decryptable because it is the same Chrome binary
  hitting the same Keychain item. The user's normal browser can run at the same
  time, but it must be closed while the snapshot is taken or the cookie DB is
  locked.

## Tab targeting

Launching Chrome opens a New Tab page alongside your target, and
`browser_console` may evaluate in the wrong target. Verify with a
`location.href` probe first, or list `Target.getTargets` and evaluate against the
page target explicitly:
`browser_cdp(method='Runtime.evaluate', params={expression, returnByValue:true}, target_id=<page>)`.

## Endpoints (same-origin, cookie-authenticated)

Fetch from inside the page with `credentials:'include'`.

- `/xapi/campaign/ext/v1/targetedContent/access` — **the access truth.** Array of
  `{orgId, accessLevel, shop, learn, orgClientStatus, targeted}`. `shop: true` is
  shopping/pro-deal access; `learn: true` is learning access.
- `/xapi/organization/ext/1.0/brand-list/all?orgClientStatus=-1&size=-1&includeCategories=true`
  — the whole catalog (4000+ orgs) with `name`, `orgKey`, `categories[]`,
  `isLiked` (following), `storePageUrl`. Contains no per-user access flag.
- `/xapi/profile/ext/1.0/affiliations` — the verified groups that grant access
  (org/team name, status, expiration date).
- `/xapi/user-affiliations/ext/1.0/relationship/myTeams` — team memberships,
  including INACTIVE and EXPIRED ones.
- `/xapi/organization/ext/1.0/brand/associated` — only `{blocked, followed}`
  org-id lists. Follows are not access.
- UI cross-check: `/home/brands?access=qualified` renders "Your access" counts
  (Shopping / Learning / Pending verification / Not available, plus Following).

## Output and verification

- Join access flags to the brand list by `orgId`; emit CSV columns
  `orgId, brand, accessLevel, following, categories, storePageUrl`, sorted by name.
- Move the file out of the browser with `Browser.setDownloadBehavior` plus a Blob
  download from the page, or `Storage.getCookies` and `curl` the endpoint. Do not
  hand-retype hundreds of rows from a tool result.
- Verify before handing over: row count equals the `shop: true` tally, zero
  duplicate orgIds, and the following count equals the site's own Following count.
- Access is affiliation-driven and expires: check
  `/xapi/profile/ext/1.0/affiliations` for `expiringSoon` before treating the list
  as durable.
