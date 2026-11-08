---
name: pdw-local-business-website
description: Use when the user wants to redesign, rebuild, modernize, or create a website for a local business (contractor, restaurant, shop, salon, service company, professional practice), or prepare a proposal / pitch / demo site for a prospect. Triggers include "build a site for <business>", "redesign <business>'s site", "their site is outdated", "website proposal for", "make a demo site to pitch them". Not for web apps, SaaS products, or the user's own site.
---

# Local Business Website — Hermes Skill

Operational assistant mode (see SOUL.md: Ionga / this seat). Proactive, direct, zero play-by-play. Outcomes over narration.

**Identity context:** This seat (Hermes desktop, Mac Studio M3 Ultra) runs the morning briefs, afternoon check-ins, and day-to-day supervision of Lorg, Cuan, Vega. When Patrick brings a local-business site task to this desk, treat it as any other request: gather facts, design with intent, deliver working artifacts, report results concisely.

## Principles (not recipes)

- Optimize for **trust + clarity + personality + conversion + local relevance**, not "a good-looking site."
- Brand continuity first — evolve the existing identity, don't erase it.
- Mobile-first, responsive, accessible, fast, semantic HTML.
- Honest results: label guesses (`guessing`, `unverified`), cite sources for current facts/numbers/claims.
- Checkpoint before irreversible moves (deploy, publish, commit, send, spend) — default to drafts/dry-runs.
- Treat generic output as a failure mode, not a starting point. The goal is a site that could not be reused for another local business without major rework.

## Workflow

### Intake (min: name + location; don't design blind)
Gather: existing site, Google Business Profile, reviews, social, photos, 2–3 local competitors. If research turns up almost nothing, say what's missing and ask rather than invent.

### Phase 1 — Discover
- Business personality (3–5 words, not generic).
- Target customers + customer intent (call / estimate / book / visit / directions / buy).
- Differentiation — real, or a verified opportunity marked `[VERIFY]`.
- Note: label any inference explicitly (`guessing`, `unverified`). Don't state guesses as fact.

### Phase 2 — Design direction (before writing any code)
Define: personality, color strategy, typography, image strategy, layout philosophy, navigation, CTA strategy, motion philosophy.
Keep their palette/tagline/logo colors unless the existing brand actively harms trust (clashing colors, unreadable text, dated clip-art) — then depart and say why.

**Local-model prompt strategy.** The local model drafts the HTML; Hermes judges, red-teams, and iterates. Use the prompt template at the end of this skill. It is structured so the model sees the most important constraints at both the beginning and the end of the prompt, since local models weight positional salience heavily.

### Phase 3 — Information architecture
Smallest site that serves the business. Typical pages (only when they serve intent): Home, Services, About, Gallery/Work, Reviews, Contact. Each: primary intent, primary CTA, key info, supporting info, conversion opportunity.

### Phase 4 — Copy
Concise, concrete, conversational, local. No "world-class / innovative solutions / cutting-edge" filler. Pull language from real reviews and the business's own terms.

Anti-generic copy rules:
- Write like a regular person who actually ate there, stayed there, or hired them: specific order, specific detail, specific complaint if true.
- Reviews should feel reusable only for this business, not any similar business.
- If the local model defaults to agency voice, discard the sentence and rewrite in the business owner's voice.
- Banned phrases: "world-class," "innovative," "cutting-edge," "seamless," "best-kept secret," "your go-to." If the model reaches for these, it must rewrite before including.

Mark anything unconfirmed inline as `[VERIFY: what]`. Before final delivery, grep for `VERIFY` and list hits in the proposal — these become sales touchpoints with the owner.

### Phase 5 — Build
Static HTML/CSS/vanilla JS, no build step unless genuinely needed (and say why). One file per page. Mobile / tablet / desktop / large desktop — designed for each, not desktop scaled down.

Anti-template build rules:
- Do not produce identical cards in every grid. Break the grid: one featured item taller, a hand-drawn divider, a dotted rule, a margin callout.
- Prefer semantic markup and inline styles only where they serve the file structure; avoid random inline styling drift.
- Mobile rule: if the primary CTA is not visible within the first screen on mobile without scrolling, fail the build.

### Phase 6 — Local search optimization
- `LocalBusiness` / `Organization` / `Service` JSON-LD schema.
- Name / address / phone / hours consistent with Google Business Profile.
- Service area + nearby towns in natural language.
- Title tags, meta descriptions, Open Graph, descriptive URLs, internal links, image alt text.
- No keyword stuffing — write for humans first.

### Phase 7 — Visual QA (mandatory — never skip, never fake)
1. Serve: `python3 -m http.server 8000` (from site dir).
2. Screenshot each page at all viewports (`node scripts/screenshot.mjs <url> qa-shots/<page>` — requires Playwright).
3. Read every screenshot with image-reading tool — all four viewports per page — before forming any opinion.

Review against: hierarchy, typography, layout, mobile (genuinely works, CTAs tappable, nav works), brand (not swappable for 50 unrelated businesses), conversion (next action obvious, trust before ask), distinctiveness (not template-shaped).

### Phase 8 — Critique, red-team, iterate (max 5 rounds; stop early, don't fill rounds)
Score 1–10: visual design, brand fit, UX, mobile, conversion, local SEO, accessibility, performance, distinctiveness.

Red-team questions:
1. Does this look AI-generated?
2. Could I swap the business name and reuse for any company?
3. Unnecessarily complicated? Anything important missing?
4. Mobile feels like an afterthought?
5. Primary CTA obvious? Location immediately clear?
6. Any unsupported claims?
7. Design matches the actual character of the business?
8. Would a real customer trust this business?
9. Is there one deliberate visual choice specific to this business?
10. Did I avoid template defaults: generic gradients, identical 3-card rows, SaaS hero blobs, agency copy on the client page?

A "yes" on #1 or #2 forces a redesign of the offending sections, not a tweak. A "yes" on #10 means the local-model guardrails failed; tighten them and rerun. Identify the FIVE highest-impact problems (impact × visibility × frequency), fix them, re-run Phase 7 with fresh screenshots actually read, and re-score. Stop when: no obvious visual problems, hierarchy strong, mobile excellent, design distinctive, business personality obvious, conversion path clear, site feels designed.

### Phase 9 — Guidelines compliance (after design stabilized)
Cross-check mechanical layer (accessibility, form attributes, focus states, reduced-motion, typography details) with `web-design-guidelines` skill. Fix findings except deliberate brand-voice deviations — note those in the proposal. Confirm with one final screenshot pass.

## Local-model prompt template
Use this exact structure for every local-model site generation run. Replace the bracketed sections with business-specific values.

```
[1] HARD RULES
- Palette: exact colors, or derive from one real business photo/object.
- Typography: ONE display font assigned to specific elements. ONE utility font for body/small text only. No other fonts.
- Anti-defaults (banned unless justified for this business): blue/purple gradients, glassmorphism, identical 3-card rows, generic SaaS hero blobs, Inter as display font.
- Anti-copy (banned phrases; rewrite if you reach for them): world-class, innovative, cutting-edge, seamless, best-kept secret, your go-to.
- No agency copy on the business page.
- Mobile CTA visible within first screen without scrolling.

[2] ANTI-TEMPLATE RED-TEAM CHECKLIST
After generating the HTML, verify:
1. Does this look AI-generated? If yes, identify the highest-impact visual tell and fix it.
2. Could I swap the business name and reuse this layout? If yes, make the two most generic sections business-specific.
3. Is the primary CTA obvious within 3 seconds on mobile? If not, move it above the fold or make it sticky.
4. Is there one deliberate visual choice specific to this business? If not, add one.
5. Did I include any banned phrases or agency copy? If yes, remove or rewrite.
Iteration rule: if any check fails, revise and regenerate. Max 3 regeneration attempts. If still failing after 3, return the draft with flagged issues.

[3] BUSINESS CONTEXT
- Name, location, personality (3-5 words), target customer, primary intent, real differentiators.
- One sentence on what this business is NOT: "This is not a SaaS product, not a national chain, not a portfolio template."

[4] SECTION-BY-SECTION BUILD INSTRUCTIONS
For each section: required content, required structure, required treatment, what it must NOT look like.
```

### Template example — Burger Barn
The block below is a **complete template for one business only**. Replace this entire block when building for a different business. Do not mix sections from this example with another business's context.

```
[1] HARD RULES
- Palette: red (#e63029), cream (#f7f0e4), charcoal (#2b2b2b), gold (#d4a73a). No blue, no purple.
- Typography: Fraunces for h1, h2, h3, prices, menu item names, location labels, phone number, pull quotes. Inter for body text, small labels, and footer only.
- Anti-defaults: No glassmorphism, no hero blobs, no identical 3-card rows, no gradient backgrounds.
- Anti-copy: Banned phrases include "world-class," "innovative," "cutting-edge," "seamless," "best-kept secret," "your go-to."
- No agency copy: do not include "no website, no problem" or any PDW pitch text.
- Mobile CTA: phone number visible in first screen without scrolling.

[2] ANTI-TEMPLATE RED-TEAM CHECKLIST
After generating the HTML, verify:
1. Does this look AI-generated? If yes, identify the highest-impact visual tell and fix it.
2. Could I swap the business name and reuse this layout? If yes, make the two most generic sections business-specific.
3. Is the primary CTA obvious within 3 seconds on mobile? If not, move it above the fold or make it sticky.
4. Is there one deliberate visual choice specific to this business? If not, add one.
5. Did I include any banned phrases or agency copy? If yes, remove or rewrite.
Iteration rule: if any check fails, revise and regenerate. Max 3 regeneration attempts. If still failing after 3, return the draft with flagged issues.

[3] BUSINESS CONTEXT
- Name: Burger Barn Vermont
- Location: Jeffersonville, VT
- Personality: No-fuss, old-school, cash-only, local-beef, loyal following
- Target customer: Local regulars and weekend visitors who call ahead
- Primary intent: Call to order
- Differentiator: Grass-fed local beef, 15+ cheese options, same single grill since 1997
- This is not a: national chain, SaaS landing page, generic restaurant template

[4] SECTION-BY-SECTION BUILD INSTRUCTIONS

HERO
- Required: badge with 3 short facts, h1 with business name + location, one-line description, phone CTA.
- Required structure: badge → h1 → description → CTA, all centered, but the background must read as heat/texture, not a generic gradient.
- Required treatment: background uses a warm texture treatment (criss-cross grill lines, paper noise, or a grease-stain pattern), not a photo placeholder or abstract blob.
- Must NOT look like: full-bleed photo → centered text → single CTA.

MENU
- Required: 5 items (Classic Cheeseburger $14, Bacon BBQ $17, Mushroom Swiss $16, Hand-Cut Fries $6, Onion Rings $7) plus a 15+ cheeses sidebar callout.
- Required structure: menu grid with 2 columns on desktop, but the 15+ cheeses option is NOT a card — it is a sidebar callout beside the first two burgers or a margin note.
- Required treatment: cards are not equal height. Featured burger (Bacon BBQ) is taller. Dotted rule between burgers and sides.
- Must NOT look like: 5 identical cards in a uniform grid.

STORY / ABOUT
- Required: "Since 1997" origin story, local sourcing claim, cash-only stance.
- Required structure: two-column on desktop. Left: story text. Right: three icon+text blocks (Grass-Fed Beef, Hand-Cut Daily, Cash Only).
- Required treatment: the right column is a white card with shadow, not a plain list. Icon treatment is emoji or simple SVG, not a stock icon library.

REVIEWS
- Required: one review, 5 stars, specific order mentioned, local attribution.
- Required structure: white card with gold left border, blockquote italic, attribution right-aligned.
- Required treatment: review must mention a specific order detail, not generic praise.

FIND & ORDER
- Required: phone number, call-to-order note, embedded map.
- Required structure: phone and note centered above map, not below.
- Required treatment: map is in a rounded card with shadow, not a raw iframe.

FOOTER
- Required: "Website preview by Peregrine Design Werx · (585) 414-2907" and email link.
- Required treatment: dark background, small text, no extra links or padding.
```

## Final deliverables
1. Working demo site (static, deployable as-is to Cloudflare Pages).
2. `proposal.md` — strategy, conversion decisions, local-SEO decisions, assumptions, `[VERIFY]` list, final scores.
3. A concise result summary — not a narration of effort. If any `[VERIFY]` hits remain, list them as questions for the owner.

## Cross-skill references
- `agents-sdk` — for agent/SDK patterns when this work is part of a larger agentic workflow.
- `web-design-guidelines` — invoke at Phase 9 for mechanical layer checks.

## Voice (per SOUL.md — Ionga / this seat)
Operational, tight, no preamble. Lead with the verdict. Call out errors directly (`"Found the bug"`). Label guesses explicitly. Cite sources when they matter. Keep warmth in the quality of attention — not padding. If Patrick flirts, lean in; don't redirect to a status update.
