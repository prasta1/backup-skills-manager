---
name: pdw-preview-sites
description: Build and ship a single-page preview website for a local-business prospect — research, bespoke build, deploy to previews.pdwerx.dev, screenshots, HubSpot logging, and outreach drafts. Use when Patrick says "build a preview for <business>" or wants to work the prospect pipeline.
---

# PDW Preview Sites

Repo: `~/Projects/business/pdw/Digital/Examples` on the MacBook, mounted on the
Studio at `/Volumes/prasta/Projects/business/pdw/Digital/Examples` (git remote:
`prasta1/pdw-previews`). Live at `https://previews.pdwerx.dev/<slug>/`. Deploys
mirror pdwerx-site: push to main → GitHub Actions → wrangler → Cloudflare Pages
project `pdw-previews`; only `sites/` is published.

Read `prospects.md` first, always. Statuses:
todo → researched → built → live → sent → replied | parked.

Hard rules:
- Never contact a prospect, send email, or enroll anyone in a sequence.
- Every page: `<meta name="robots" content="noindex, nofollow">`.
- Self-contained site folder — no shared assets, no CDN except Google Fonts.
- `git add` explicit paths only.
- Slug: kebab-case business name without legal suffix or town (e.g. `burger-barn`, `ace-glass`).
- If research contradicts the lead list (closed, renamed, already has a real
  site), STOP and tell Patrick; update `prospects.md` and the lead report note.

## 1. Pick prospect

Patrick names one, or suggest the next `todo` from Tier 1 → 2 → 3 of `prospects.md`
with a one-line why. Confirm before starting.

## 2. Research → brief

Sources, in order: their row in `prospects.md`; Facebook/Instagram pages; Google Maps
listing. Fill `briefs/<slug>.md` from `references/brief-template.md`.

Photo rule: shortlist 4–8 photos from THEIR public posts (log post URLs in
the brief). Download picks to `sites/<slug>/images/` with curl. Flag if
nothing usable — Patrick chooses fallback (authentic-generic VT imagery or
photo-light design); never silently use bad stock.

**GATE: Patrick skims the brief (~5 min) before any building.**

## 3. Build

Read `references/art-directions.md`; state which direction and why in one
line. Build `sites/<slug>/index.html` (+ `style.css` if cleaner) bespoke —
the direction is a starting recipe, not a template.

Non-negotiables: their photos; copy in their voice with local references;
mobile-first; click-to-call `tel:` link; hours; embedded Google Map;
paraphrased real reviews; footer line
"Website preview by Peregrine Design Werx · 585-414-2907"; contact form
via Formsubmit to ruster.patrick@gmail.com (AJAX, honeypot — copy the
pattern from the demo-website scaffold in Dropbox if needed).

Generic-smell self-check before showing Patrick:
- Hero could belong to any business in this category → redo it.
- At least one detail only THIS business could claim (year founded,
  signature item, landmark, review quote)?
- Colors from their branding/photos, not a default palette?
- Reads like the owner talking, not an agency?

## 4. Live review with Patrick

```bash
cd ~/Projects/business/pdw/Digital/Examples/sites/<slug>   # or /Volumes/prasta/... on the Studio
python3 -m http.server 8787
# → Patrick reviews at http://localhost:8787, iterate on feedback
# when done:
pkill -f "http.server 8787"
```

## 5. Deploy

```bash
cd ~/Projects/business/pdw/Digital/Examples   # or /Volumes/prasta/... on the Studio
git add sites/<slug> briefs/<slug>.md prospects.md
git commit -m "Add preview: <Business Name>"
git push
gh run watch --repo prasta1/pdw-previews
```

Verify live (CDN can lag a green check):
```bash
curl -s https://previews.pdwerx.dev/<slug>/ | grep "<business name>"
```

## 6. Screenshots → `shots/<slug>/`

With browser tools (Hermes `browser_*` / Playwright) on the LIVE URL:
1. Resize window to 1440 wide → full-page screenshot → `desktop.png`.
2. Resize to 390×844 → full-page screenshot → `mobile.png`.
3. Open `file:///Users/prasta/Projects/business/pdw/Digital/Examples/tools/phone-frame.html?img=../shots/<slug>/mobile.png`
   (on the Studio: `/Volumes/prasta/...`) → screenshot the phone element → `phone-framed.png`.
4. `git add shots/<slug> && git commit -m "Shots: <Business Name>" && git push`

## 7. HubSpot + outreach drafts

Follow `references/hubspot-outreach.md` exactly:
1. Create/update company (+ contact if owner known) via HubSpot. **Hermes has no
   HubSpot connector** — on this seat, HubSpot writes are a manual/UI step for
   Patrick (or via the HubSpot API if a token is ever added). Draft the record
   fields and note text so he can paste them in.
2. Log a note with the preview URL + research summary.
3. Write `outreach/<slug>.md` — sequence-step emails or DM/talking points.
4. No-email prospects: also create a HubSpot follow-up task.
5. `git add outreach/<slug>.md && git commit -m "Outreach: <Business Name>" && git push`

## 8. Close the loop

Update the prospect's row in `prospects.md`: status `live`, Preview URL filled. Report to
Patrick: live URL, screenshot paths, HubSpot record link, outreach file —
and remind him: enroll/personalize in HubSpot, attach `phone-framed.png`.
