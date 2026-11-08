# HubSpot + Outreach Conventions

Local repo: `~/Projects/business/pdw/Digital/Examples` on the MacBook, mounted on
the Studio at `/Volumes/prasta/Projects/business/pdw/Digital/Examples` (git remote:
`prasta1/pdw-previews`).
**HubSpot Portal:** accountId `5879337` · Owner Patrick Ruster (ruster.patrick@gmail.com, ownerId `36752648`) · ~258 existing companies (tech-skewed, local SMBs are safe/proportional).

**Tools:** Hermes has **no HubSpot connector** — HubSpot writes are a manual/UI
step for Patrick. Draft the record fields and note text so he can paste them in.
Patrick reviews and sends everything — Hermes only logs data and drafts copy.

**⚠️ HubSpot not reachable from Hermes.** Since there's no HubSpot connector on
this seat, Patrick must enter company records + sequence manually via the HubSpot
UI. See [[Portal: accountId 5879337, owner Patrick Ruster, ownerId 36752648]].

## CRM logging (per preview)

1. Search first (avoid duplicates): company by name, contact by name/email.
2. Company: name (exact), phone, address, city, state="Vermont", industry/category,
   website = the CURRENT one if any (not the preview). **⚠️ Always set `domain`** —
   if the real domain is unknown, leave a placeholder (e.g. `burgerbarnvt.com`);
   without domain, auto-enrichment creates duplicate records.
3. Contact (only if owner/decision-maker known): name, phone, email if any.
4. Description field: `PDW-3 pipeline lead — score X/100 (tier, rank). Category… GAP(n):… PAY(n):… VALUE(n):… Play:…`
5. Note on the company record:
   "Website preview built <YYYY-MM-DD>: https://previews.pdwerx.dev/<slug>/
    — Channel: <channel>. Hooks: <the 2–3 observations from the brief>."
6. No-email prospects: create a follow-up task on the record —
   "Deliver preview to <name> via <channel>", due in 2 business days.

**Write requirements:** (HubSpot API / UI) `manage_crm_objects` needs `confirmationStatus` = `CONFIRMED` or `CONFIRMATION_WAIVED_FOR_SESSION`. Creating pipeline company records is within standing mandate — use `CONFIRMATION_WAIVED_FOR_SESSION`. **Max 10 objects per batch** (20 → error).

**Limitation:** HubSpot API/UI only creates/updates — **no delete, no merge**. Bad bulk loads can't be cleaned up from here. Verify on a small batch first.

## Sequence creation (HubSpot UI — required, not API-creatable)

Sequences need Sales Hub Pro+ and aren't creatable via MCP tools. Patrick creates once:

1. HubSpot → **Automations → Sequences → Create sequence**
2. Name: **"PDW Local Biz Outreach"**
3. 4 manual-email steps with delays:
   - Step 2: 3 business days after Step 1
   - Step 3: 5 business days after Step 2
   - Step 4: 15 business days after Step 3
4. Leave email bodies as skeleton — personalization happens at enrollment from `outreach/<slug>.md`.

> The sequence is the **email cadence**. For no-email prospects (FB-only, phone-first),
> skip sequence enrollment — use a follow-up task instead (see CRM logging step 6).

## Deal pipeline reference (for associating deals with companies)

- Pipeline: `default` (labeled "Pipe")
- Stage map: `appointmentscheduled`=Opportunity Identified → `outreachinitiated`=Outreach Initiated → `10837142`=Scoping → `1106837025`=Negotiating → `closedwon`=Closed Won / `closedlost`=Closed Lost
- PDW mapping: Opportunity Identified = pre-touch ready → Outreach Initiated = contacted → Scoping = discovery call → Negotiating = proposal → Closed Won/Lost

## outreach/<slug>.md format

Header: business, slug, channel, preview URL, which shots to attach
(phone-framed.png for email/DM; desktop.png optional for email).

### Email channel → HubSpot sequence steps

Use the templates in the `pdw-digi-prospect-outreach` skill as skeletons;
personalize with brief hooks. Golden rule: if it doesn't prove Patrick
looked at THEIR business, rewrite it.

- Step 1 (day 0): subject "Quick thought about \<Business\>'s website" —
  2–3 specific observations, preview link, 10-minute ask.
- Step 2 (+3–4 days): short circle-back, offer phone walkthrough.
- Step 3 (+5–7 days after step 2): "one last try", warm close, park promise.
- Step 4 (+2–3 weeks): new-angle touch (recent post/review/competitor).

Each step: subject line + full body, ready to paste into the sequence at
enrollment. End the file with: "Patrick: enroll in the PDW outreach sequence
in HubSpot and personalize each step from the above."

### DM channel (FB/IG)

One opener (their template style: fan-of + observation + "mind if I send the
mockup?") + a follow-up nudge for +4 days. Short — 5 sentences max.
No sequence enrollment — use a HubSpot follow-up task instead.

### In-person/phone channel

Talking points card: opener, the one observation, show phone-framed.png or
live URL on phone, leave-behind line. Plus the voicemail variant.
Create a HubSpot task: "Deliver preview to \<name\> via in-person at \<address\>".
