---
name: pdw-digi-prospect-outreach
description: Generates outreach email drafts for local businesses.
license: MIT
metadata:
  author: prasta1
  version: "1.0"
  category: lead-generation
---

# PDW Digital Prospect Outreach — Email Draft Generator

## Purpose

Produce ready-to-send outreach email drafts for local Vermont businesses, grounded in actual website research and structured to get replies.

## When to use this skill

- Cold outreach to local businesses (restaurants, lodging, retail, services)
- After prospect research has been gathered (website scrape, contact page, reviews)
- Before writing the email — this produces the full draft including notes
- When you need consistency across multiple outreach attempts

## When not to use this skill

- No research gathered yet — do web_extract first
- Targeting non-local/regional businesses outside Vermont
- When the business has no website and no email found
- For job-search outreach (use different angle)

## Required inputs

- Business name
- Business URL (homepage + contact page)
- Industry / business type
- Verified email address of the contact (or best email found)
- Key observations from site research (mobile issues, booking flow gaps, content problems, etc.)
- Business-specific differentiator (e.g., "dogsled tours," "maple syrup," "trailhead location")

## Universal opener (always used)

> I'm Patrick, I live just around the corner from your shop, off Cady Hill Rd. in Cambridge. I'm currently pivoting away from the Tech/Software world to put my digital skills to use helping local businesses with their marketing & web presence. I was doing some research on prominent businesses in and around Lamoille county and yours hit my radar.

## Rules

1. Use only the supplied research and context.
2. Do not invent facts, quotes, or observations not verified on the live site.
3. Separate evidence from assumptions explicitly in the Notes section.
4. List every claim with a verification source.
5. Never send the email — produce the draft file only.
6. Every observation must be confirmed via web_extract or curl.
7. Keep emails under 250 words (body only).

## Output format

Generate a markdown file at `Digital/outreach-drafts/YYYY-MM-DD-[slug]-draft.md` with the structure:

- Header with To/Subject
- Universal opener (adapted with contact name if known)
- "The gap" paragraph (2-3 sentences on the core observed problem)
- Bullet list of 2-3 specific revenue levers tied to verified site issues
- Additive reframe (acknowledge existing strengths)
- Closing CTA (mockup hook for hospitality/experiences; 15-min call for retail/services)
- Sign-off: Patrick Ruster, Local (Cambridge, VT), patrick@pdwerx.biz
- Notes section documenting tone choice, assumptions, and verification sources

## Process

1. Confirm you have the required inputs (research + verified email).
2. Write the universal opener, addressing the contact by name if known.
3. Identify the core gap from your research (mobile issues, booking flow, content structure).
4. Derive 2-3 specific revenue levers tied to verified site problems.
5. Reframe fixes as additive — acknowledge existing strengths (reviews, location, reputation).
6. Choose the closing:
   - **Hospitality/Lodging/Experiences:** Close with mockup hook ("Want me to send it over?")
   - **Retail/Services:** Close with 15-min call CTA ("Happy to hop on a quick call...")
7. Document every claim with its verification source in the Notes section.
8. Save the draft file to the outreach-drafts folder.

## Verification checklist

- [ ] Business URL is live and accessible
- [ ] Contact email verified on the contact page
- [ ] All technical observations confirmed via curl/web_extract
- [ ] Review scores cited with source link
- [ ] Owner name (if used) verified on the contact/about page
- [ ] Every bullet point ties to a specific, verifiable site issue
