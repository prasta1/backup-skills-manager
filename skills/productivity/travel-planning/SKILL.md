---
name: travel-planning
description: Use when planning a trip — research, itinerary, one-pager.
version: 1.0.0
author: Ionga (Hermes Agent)
license: MIT
metadata:
  hermes:
    tags: [travel, itinerary, trip, logistics]
---

# Travel Planning

## When to use
Planning ANY trip: conference/event attendance, flights + hotels, road trips, weekend getaways. Run the full workflow, update it as the trip firms up (flight changes, venue address, hotel decisions), and land the finished deliverables in the travel directory.

## Output convention — one folder per trip, date-prefixed

Every trip gets ONE folder in the travel directory, named `<YYYY-MM-DD>-<trip-slug>/` (date = event/arrival date). From the Studio the directory is:

    /Volumes/prasta/Library/Mobile Documents/com~apple~CloudDocs/Hermes/travel/<YYYY-MM-DD>-<slug>/

(the underlying MacBook path is `/Users/prasta/Library/Mobile Documents/com~apple~CloudDocs/Hermes/travel`; the Studio reaches it via the mounted `prasta` share).

Folder contents:
- `plan.md` — the master plan: goal, event facts, itinerary, budget, risks, verification checklist, open questions. Keep updating it through the trip.
- `itinerary.html` — the styled one-pager (see One-pager below).
- `assets/` — boarding passes, booking confirmations, venue docs. Copy them from Hermes attachments when the user shares them.

Seed the folder as soon as the trip is defined; copy finished artifacts in as they land. Never store the same trip in two folders.

## Intake — suss out the intent first

Before researching, pin down the trip's shape with ONE short round of questions (chat or the clarify tool). If the user's request already makes purpose/date/companions obvious, skip the questions and note the inferred profile as an assumption.

Ask (recommended option first, 2–4 questions max):
1. **Purpose/scope**: Work / Personal / Family visit / Adventure-outdoor / Mixed / **Just researching** — the fork that shapes the whole plan.
2. **Dates**: fixed (event dates) or flexible (leisure).
3. **Companions**: solo / partner / family / group.
4. **Budget posture**: value / mid-range / no constraint.

**Purpose fork — what changes per intent:**
- **Work** (conference, interviews, meetings): research the event itself — registration/approval, venue disclosure, capacity notes, over-subscription warnings. Prioritize logistics + prep: event agenda alignment, materials to carry, attire, and expense receipts (reimbursement-friendly: itemized receipts, business purpose noted).
- **Personal** (vacation, weekend): lodging comfort and location, activities/food, light packing, dog care if overnight (Cora → Lyndsey), budget flexibility.
- **Family visit**: dates around holidays, gifts, car vs fly, longer stays, household logistics.
- **Adventure/outdoor** (overlanding, biking, skiing): vehicle/gear readiness, weather windows, permits, backup plans (Land Cruiser, ski season, etc).
- **Mixed** (e.g., work event + weekend): plan the work spine hard, layer the personal time after, split accommodations accordingly.
- **Just researching** (no trip planned yet): deliver a research brief ONLY — event/destination facts, transport options with rough costs, lodging market, seasonal windows, recommendations. No bookings, no itinerary one-pager unless asked. Output in chat, or as `research.md` in `travel/<slug>/` when worth keeping; convert to full planning later on request.

The folder/plan/one-pager structure stays identical; the content emphasis shifts. Record the purpose in the plan header and reflect it in the one-pager Mission card.

## Workflow

1. **Research the trip.** Event, destination, or visit — whatever the intake fork landed on. For events: Luma/page + web search; capture dates, times (doors vs main event vs afterparty), exact venue once disclosed, registration/approval status, capacity notes (over-subscribed events matter — the host may ask non-attendees to cancel). For non-event trips: destination logistics, seasonal windows, lodging market.
2. **Assess travel options from Cambridge, VT.**
   - Drive: OSRM routing via `curl` (NOT python urllib — SSL handshake fails against router.project-osrm.org). Route home ↔ destination. Add ~15% for traffic fudge.
   - Fly: flight aggregators. Google Flights renders results only in a browser; static extraction may show round-trip-influenced prices — verify one-way pricing by toggling one-way or checking the airline directly.
   - Train: Amtrak schedules (Vermonter from Waterbury-Stowe / Essex Junction; arrivals can land at doors-open — check slack).
   - In-city transit: NYC PATH runs 24/7 with 20–35 min overnight headways; 9th St & 23rd St stations close overnight; AirTrain + PATH is the airport (EWR) play.
   - Walking distances: OSRM's `foot` profile returns garbage (nonsense durations). Use haversine straight-line × ~1.3 for a realistic walk.
3. **Build the plan** as markdown with: Goal, Event facts (verified), Status, Current context/assumptions, step-by-step itinerary (Day-by-day), Money table, Key dates, Alternatives, Risks/tradeoffs, Verification checklist, Open questions.
4. **Refine with the user.** Flight changes: check the fare class — Basic Economy = no changes/refunds, no full-size carry-on (personal item only), free seat only at 24h check-in. Hotels: pull the LIVE all-in rate for the exact night (Booking.com/agoda static extraction shows only reference/average rates; exact-date rates need live entry). Lounge passes: United Club one-time pass is $59, entry ONLY within 3h of departure (since May 2025); showers at EWR only at C123 (6 suites, first-come) — NOT C74 or Terminal A.
5. **Produce the one-pager** (`itinerary.html`) — standalone dark-themed HTML, print-clean, with the event's own visual language (Nous-flavored: monospace headers, tagline, status badges). Optional animated dither-globe hero (see references/dither-globe-port.md).
6. **Save.** Create the trip folder, write `plan.md` + `itinerary.html`, copy `assets/` docs. Confirm the folder listing back to the user.

**Research-only scope ends the workflow after step 2** — deliver the brief in chat (or `research.md`) instead of building a plan/one-pager, and offer the step-up to full planning.

## Pitfalls (learned the hard way)

- **python urllib SSL fails** vs router.project-osrm.org → always `curl`.
- **OSRM foot profile is broken** for pedestrian routing → haversine × 1.3 for walks.
- **Hotel averages lie on peak dates.** Halloween/NYC holiday weekends run 2–3× average. Always pull the live all-in for the exact night (resort fees + taxes excluded from shown rate are common — e.g. Booking.com shows rate + "$25 resort fee included, 14.75% tax + $4 city tax excluded").
- **Google Flights** may keep showing RT-influenced prices even in one-way mode — confirm before quoting.
- **Verify the actual date** before saying "X days out" — sessions span days; a stale "15 days" was wrong when the event was 4 days out. Run `date`.
- **United Club pass**: 3h entry window kills the "sleep in the lounge at 5am" idea unless the flight is early enough; trip passes (~$40, sold at booking) beat one-time ($59).
- **Basic Economy** fare rules decide whether "move to an earlier flight" is a free swap or a new purchase — check the fare class first.
- **Refundable-hotel insurance pattern**: book refundable early, cancel by ITS deadline (often the day before check-in) if the plan firms up differently. Costs nothing held.
- **All-nighter pattern** (no hotel): airport lounge as recovery hub can beat hotel+late-flight on both cost and endurance — but only if the lounge 3h-entry window aligns with the chosen flight. Otherwise the 4–9am dead zone eats the savings.
- **Over-subscribed events**: if the user can't make it, cancel the RSVP early so others get the slot.

## One-pager structure

Header (logo/tagline + status list) → hero (optional globe) → title/subtitle → grid: Mission, Venue, Timeline, Loadout, Transit, Status badges, Contingency → footer (confirmation refs). Dark terminal aesthetic; the frame's CSS vars (--foreground, --accent, --border...) themed in the Hermes desktop preview. Print media query keeps it clean on paper.
