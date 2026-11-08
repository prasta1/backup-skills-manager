---
name: shit-posting
description: "Use when drafting Substack/X/LinkedIn posts in his voice."
version: 0.6.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Writing, Substack, X, LinkedIn, Voice, Drafting]
---

# Drafting in Patrick's Voice

Drafts Substack **Notes** (hard cap 200 characters), Substack **Articles** (hard cap 800 words), **X posts** (hard cap 280 characters each, single or threaded), and **LinkedIn posts** (cap 3,000 characters, LinkedIn's own) that sound like Patrick: conversational first-person narrative that opens on a specific moment or a concrete ask, blends technical depth with dry wit, and lands on something the reader can act on. Not a replacement for research — the agent gathers sources with `web_extract`/`web_search`, then this skill shapes the prose. It publishes nothing: it produces a draft you paste and post yourself. X *mechanics* — `xurl`, auth, media upload, API cost — live in the `xurl` skill; LinkedIn is manual end to end (the composer, the Open to Work setting, per-post analytics). This skill owns voice, caps, and the draft files.

## Four formats, four mediums

A Note is not a short article, and an X post is neither. They differ in medium, not just length: a Note lives in a subscriber feed and never reaches an inbox; an X post lives on a public timeline among strangers, carried by replies and quote-posts; a LinkedIn post lands in front of first-degree connections, past colleagues and recruiters, under his real name and his actual employer history; only the article is emailed, and only the article can hold a technical argument.

| | Note | Article | Post (X) | LinkedIn |
|---|---|---|---|---|
| Hard cap | **200 characters** | **800 words** | **280 characters**, per post | **3,000 characters** (LinkedIn's, not ours) |
| Title / subtitle | none | both required | none | none |
| Landing | one idea, hook in the first line | 2-3 paragraphs of mechanism, sourced | hook has to land early — quote-post previews truncate before the cap | hook has to land inside ~140 characters; the feed folds to "...see more" there |
| Tags | none — the Notes composer has no tag field | `#Tag1 #Tag2 #Tag3` at the bottom | hashtags optional, 0-2 max, inline; never a tag block | 0-3, at the very bottom on their own line; the documented 3-5 figure is for company Pages |
| Audience | subscribers: home feed + profile, **never emailed** | subscribers: email + publication home | strangers on a public timeline, plus replies and quote-posts | first-degree connections, past colleagues, recruiters — a high-trust, low-anonymity graph |
| Links | counted literally — a pasted Substack URL eats 50-60 characters | inline | counted at **23 characters** whatever their real length (t.co) | counted literally — no collapsing; external links carry a contested reach cost |
| Formatting | rich text on web: bold, italic, strikethrough, quotes, bullets; up to 6 images/GIFs, video | full editor | plain text; one image or video | plain text, no markdown — line breaks *are* the formatting; one image, video, or document (PDF carousel) |
| Scheduling | yes (calendar icon in the composer) | yes | yes, in the X composer | yes, native — clock icon in the create-post window, 10 minutes to 3 months out, times pinned to UTC |
| Publish path | Create → Note, or https://substack.com/notes | https://prasta.substack.com/publish/home | manual paste into https://x.com/compose/post — **this skill never posts** | manual paste into the LinkedIn composer, or schedule it there — **this skill never posts** |
| Safety net | `View stats` per note: new subs, followers, clicks, shares | standard post stats | per-post analytics in the X app | per-post analytics: impressions, members reached, the in-network vs out-of-network split |

Sourced from Substack's own docs (support.substack.com Notes section; on.substack.com/p/notes-faq) — including the detail that Notes have **no published character limit**, which is a trap rather than a permission slip: the 200-character cap below is Patrick's, not Substack's.

The X column comes from X's own counting rules: 280 characters per post on a standard account, and every URL counted as **23 characters** regardless of real length because X wraps all links in t.co ([docs.x.com/fundamentals/counting-characters](https://docs.x.com/fundamentals/counting-characters)). That rule, not the URL's actual size, is the budget a linked post works against.

The LinkedIn column comes from LinkedIn's own Help pages where it can: the 3,000-character post limit ("Post and share updates", a528176) and native scheduling ("Schedule posts", a1347212 — 10 minutes to three months out, and not offered for Events, Jobs, or Services posts). One caveat: LinkedIn's Help pages block automated fetching, so those two were read through search-result snippets of the Help articles rather than from the pages themselves. Treat them as well-sourced but re-verify in the composer if a draft depends on the exact number. The **fold** — roughly 140 characters on mobile and 210 on desktop before "...see more" — has **no LinkedIn documentation at all**; it is third-party consensus (AuthoredUp, Hootsuite, EmbedSocial) and drifts with layout and device, so treat it as a target, not a boundary.

## When to Use

- "Draft a note about X" / "Draft a Substack article about X"
- "Draft a post about X" / "Turn this into an X thread" / "Tweet this finding"
- "Draft a LinkedIn post about X" / "Draft a quick LinkedIn post asking my network for X"
- "Turn these notes into a Flotsam & Jetsom piece"
- "Rewrite this technical finding as a substack post"
- "I want to write about [topic] but make it sound like my stuff"
- "Convert this LinkedIn text into a proper Substack draft"

## The format gate (interactive, minimal)

Keep this light. It exists so the agent stops guessing, not to run an interview.

1. **Format — named by Patrick, never inferred.** The formats are `note`, `article`, `post` — and a post may be a single post or a `thread` — plus `linkedin`. Do not infer it from the topic, the size of the seed, or what he pasted. If he didn't name one, ask in one line. Do not draft until it's named. "LinkedIn post" names the format; a *topic* that merely sounds professional does not.
2. **The point — one sentence.** Reflect your read of it back and let him confirm or correct. Propose; don't interrogate. An empty question ("what's the angle?") is worse than a wrong guess he can fix.
3. **Post type — articles and LinkedIn only.** Articles: reflective/PSA or news-cycle. LinkedIn: `technical` (a finding, a PSA), `commentary` (riding news), `job-search` (an availability or referral ask), or `company` (a Peregrine Design Werx post). Recommend one. For a LinkedIn `job-search` post the ask is itself the decision — carry it into the thesis line rather than defaulting to "please share".
4. **Then stop and wait.** Never write prose in the same turn as a question.

If he hands you a complete brief — format, point, angle — reflect it back in one line and draft. Don't re-ask what he already told you.

Record it in the draft header:

```
> THESIS: [one sentence]
> FORMAT: note | article | post | linkedin
> TYPE: reflective/PSA | news-cycle   (articles only)
> TYPE: technical | commentary | job-search | company   (linkedin only)
> TYPE: thread   (posts only, optional)
```

An idea that can't survive as one sentence isn't ready to draft. An idea that needs more than 200 characters to say isn't a Note — say so and offer it as an article instead. The same test holds at 280: an idea that outgrows one post is a thread, and one that outgrows three is an article. LinkedIn is the one format with room to spare — 3,000 characters is roughly 450-600 words, i.e. article length — so the discipline there is not the cap. It's the fold and the one-ask rule.

## Hard length caps

All caps are **ceilings, not targets.** A 90-character note is fine. A 400-word article is fine. Being over a cap is a defect and gets fixed before the file is saved.

- **Note ≤ 200 characters**, counted mechanically. The cap covers the whole body, **link URLs included** — a pasted Substack URL eats 50-60 characters, so a linked note gets ~140 characters of prose. Budget for that up front rather than trimming after.
- **Article ≤ 800 words.** Inside it: reflective/PSA runs 450-650; news-cycle can use the whole 800. The published chip salesman post hit ~1000 and read as a ramble — 800 is the ceiling now, not 900.
- **X post ≤ 280 characters each**, counted the way X counts: **every URL costs 23 characters** however long it really is, so one link leaves ~257 characters of prose and two links leave ~234. A thread is several posts, each under the cap — never one long post broken up cosmetically.
- **LinkedIn post ≤ 3,000 characters** — LinkedIn's limit, not ours, and the only cap in this skill that comes from a platform instead of Patrick's taste. No other number is imposed: a 900-character post and a 2,400-character post are both legitimate. The working band for engagement is 1,300-2,500 characters (AuthoredUp's median-engagement data), while an ask-shaped post usually lands better under ~1,400. Two things matter more than total length: the **first ~140 characters**, which is all LinkedIn shows before "...see more", and **one ask per post**. An over-3,000 draft gets rewritten or split, never saved.

If a note runs over, the idea is too big for a note — don't shave wording, split the idea or promote it to an article.

## How to Run

Load this skill, then name the format and the topic. The agent:

1. Re-reads the published posts via `web_extract` on `https://prasta.substack.com/archive`
2. Locks format + thesis with you (format gate above) — no prose until you confirm
3. Drafts to the structure for that format
4. Verifies the draft against the voice checks and the hard cap, using `scripts/count.py`
5. Writes it to `$DRAFTS/YYYY-MM-DD-DRAFT-<note|article|post|linkedin>-<slug>.md` (`$DRAFTS` is defined under **Output destination**), reports the absolute path and the counted length

## Draft file shape

Metadata block, a `---` rule, then the body. The rule is what makes counting mechanical: everything after the first `---` is the body, and the body is exactly what gets pasted into the destination.

```markdown
> THESIS: [one sentence]
> FORMAT: note
> TYPE: —
> PUBLISH: Create → Note, or https://substack.com/notes

---

[body — nothing but what gets pasted in]
```

For articles, `TYPE:` carries reflective/PSA or news-cycle and `PUBLISH:` points at https://prasta.substack.com/publish/home.

For an X post, `PUBLISH:` is https://x.com/compose/post and the body is the post itself. For a **thread**, the body is every post in order, separated by a line containing only `===` — that line is a file convention and never gets pasted:

```markdown
> THESIS: [one sentence]
> FORMAT: post
> TYPE: thread
> PUBLISH: https://x.com/compose/post — paste the posts in order, drop the `===` lines

---

[first post]

===

[second post]

===

[last post — the link goes here]
```

For a **LinkedIn post**, `PUBLISH:` names the composer and the body is the post itself. LinkedIn has no `===` separators and no thread form: one post is one post, and if the idea needs two, it's an article.

```markdown
> THESIS: [one sentence]
> FORMAT: linkedin
> TYPE: job-search | technical | commentary | company
> PUBLISH: paste into https://www.linkedin.com/feed/ — this skill never posts

---

[the post — nothing but what gets pasted in]
```

Drafts written before this convention existed have no `---` rule at all — an audit of the legacy `~/.hermes/outputs/substack-drafts/` found six. Two had metadata blocks and were fixed by inserting the rule; the other four are LinkedIn drafts with no header block, which now have a header shape to migrate to (add the `>` block, add the `---` rule, then re-count). `scripts/count.py` counts a headerless file whole and silently, and warns only when there *is* a metadata block to separate — that is the one case where the header would inflate the count.

## Output destination

**Drafts land in iCloud Drive, not `~/.hermes`** — Patrick wants them reachable from every device (MacBook, iPhone, iPad), so the folder syncs through iCloud instead of living only on the Studio:

```
DRAFTS="/Users/macstudio/Library/Mobile Documents/com~apple~CloudDocs/Hermes/shit-posting"
```

That is the Studio's path. It is the **same iCloud folder** he sees on the MacBook as `/Users/prasta/Library/Mobile Documents/com~apple~CloudDocs/Hermes/shit-posting` — one Apple ID, one synced folder, two local paths. Write the Studio path and it appears on the other devices on its own. **Quote `$DRAFTS` in every shell command:** the path contains spaces and the literal tildes in `com~apple~CloudDocs`, so an unquoted reference word-splits.

The slug carries the format: `YYYY-MM-DD-DRAFT-note-<slug>.md`, `YYYY-MM-DD-DRAFT-article-<slug>.md`, `YYYY-MM-DD-DRAFT-post-<slug>.md` (a thread is still `post`, one file, posts separated by `===`), or `YYYY-MM-DD-DRAFT-linkedin-<slug>.md`. Published/compiled outputs drop the `DRAFT` marker. When a piece goes live, compile the generated draft and the published version into one comparison MD and save it here.

The folder is named `shit-posting` — Patrick's naming, and his file. One thing to know about where the history lives: `~/.hermes/outputs/` is **gitignored** (the repo's `.gitignore` is deny-all `/*` with an allow-list, and `outputs/` is not on it), so drafts there were never in the daily git backup either — iCloud's own version history is the only copy chain, here as it was before. The legacy `~/.hermes/outputs/substack-drafts/` folder is now empty; the pre-move drafts live here.

**Path gotcha:** do NOT write to `/Users/prasta/...` from the Studio — that path does not exist on this machine, and `/Volumes/prasta` is the MacBook's home share (often unmounted; iCloud Drive is not reachable through it anyway). `/Volumes/macstudio` is the MacBook's SMB view of the *Studio's* home and is not a mount on the Studio at all. iCloud Drive is the one folder that exists on both machines, under different local paths.

**Eviction gotcha:** iCloud can offload a draft it has already synced, leaving a dataless placeholder on disk. `read_file` returns it **blank and reports no error**, and a plain read can raise `OSError: [Errno 11] Resource deadlock avoided`. If a draft in `$DRAFTS` reads as empty, materialise it first: `brctl download "<path>"`, wait a beat, then read.

The `~/.hermes/outputs/README.md` signpost documents the outputs convention for the producers that still write under `~/.hermes`; shit-posting is listed there as having moved off it (to iCloud).

The same iCloud folder carries a **read-only snapshot of this skill** under `skill/` — `SKILL.md`, `templates/post-outline.md`, `scripts/count.py`, and a README explaining the layout — so the rules and the cap checker are readable and runnable from a phone or the MacBook without touching the Studio. It is a copy, never the skill: after editing this skill, refresh the snapshot with the three `cp` lines in that folder's README, or the copy silently goes stale and a later session reads rules that no longer apply.

## Quick Reference

**Voice markers to hit:**
- Opens on a specific moment, but VARIED: the coffee/dog desk scene was used once (moats post) and is played out. Rotate openers — news lead, machine anecdote, insider angle, cold-open quote, a plain ask.
- Alternate title (articles only): `### Alternate Title: [a sly PSA / confession / framing]`
- Casual asides: parenthetical links, emoji-free wit, inline footnotes
- One-liner verdicts on the tech: "48 hours. Not months. Two days."
- Dry signposting: "No Biggie.", "Yada yada.", "I'm choosing to believe that's a bug"
- Tech shorthand without apology: CLI commands in backticks, tags at the bottom
- Ends with a list of takeaways or habits (bulleted, 3–4 items) — OPTIONAL, not mandatory. Patrick has dropped it when the action beat already lands in the prose; bolted-on lists read as padding. If the body already delivers the takeaway, end on the closer.
- Tagline: "musing for my own amusement, and hopefully yours too."

**X post markers:**
- The hook *is* the post. No warm-up, no "I've been thinking about..." — the first line has to survive a quote-post preview.
- One aside, same hard rule as articles. At 280 characters a second aside is a third of the post.
- Links get the t.co 23-character budget, so a linked post is prose plus a link, not a link with commentary bolted on.
- `@` mentions and 0-2 inline hashtags are allowed — the one place a tag is legitimate in this skill.
- No sign-off, no tagline, no "musing for my own amusement" — that's the Substack footer's job, not a post's.

**LinkedIn post markers:**
- The first ~140 characters are the whole post for most readers; the rest is the reward for the click. Lead with the claim, the ask, or the number — never with a greeting, "I'm excited to share", or a hashtag.
- Same one-aside rule as everywhere else. LinkedIn is long enough to *tempt* a third aside, and that is exactly how these turn into essays.
- Plain text only: no markdown, no `**bold**` that renders as asterisks, no unicode-bold tricks. Blank lines between paragraphs (LinkedIn collapses runs of them), short paragraphs, and a list of short lines when the rhythm calls for it.
- **One ask.** "Share if you know someone" plus "DM me" plus "tell me your thoughts" is three asks and gets zero.
- No engagement-bait framing — "Agree?", "Thoughts?", "Repost if you care" all read as a growth tactic. His real close is a plain question or an open door (the shell-access post's pattern).
- No tag block by default. The technical posts carry 3-5 at the bottom; a job-search or commentary post reads better with none, or one (`#OpenToWork`, and only if the profile setting agrees with it).
- His LinkedIn register is direct and declarative, not corporate. Same first person as everything else, with the jargon stripped rather than added.

**Article structure:**
1. Hook (specific moment or discovery)
2. "Then I saw / I found / it turned out" — the pivot to finding
3. Technical explanation (the meat — CLI commands, API keys, configs)
4. "To be clear:" — a clarifying note that defuses alarmism
5. Actionable fix (commands to run, toggles to flip)
6. "The broader reminder" — the general takeaway
7. List of habits / what to keep in mind — optional; skip when the body already delivers the actionable takeaway
8. Sign-off: optional cultural reference, sometimes with a link

## Note structure (≤ 200 characters)

One idea. No title, no alternate title, no header, no tag block, no takeaway list, no "To be clear:" — nothing labeled. The structure is a shape, not a scaffold.

1. **The line** — the whole point in one sentence, front-loaded, because the feed truncates.
2. **Optional second line** — the turn, the caveat, or the dry aside. Often where the wit lives.
3. **Optional link or image** — links get a rich preview; linking your own post is a legitimate use.

At 200 characters the aside budget is zero-to-almost-nothing. Pick either the wit line or the detail, never both.

Worked examples (both under cap):

```
Notes have no character limit. That's not permission.
One idea, said once. Anything more is an article.
```

```
Your agent doesn't need more tools. It needs
fewer, with better descriptions.
```

## Post structure (≤ 280 characters)

One idea per post, same discipline as a Note with different physics: the timeline is public, strangers reply, and a quote-post preview truncates well before the cap — so the hook has to sit inside the first ~120 characters or the post travels without its point. Patrick's account is a standard 280, not Premium long-form. That is a hard cap, not a formatting preference.

1. **The line** — the point, front-loaded.
2. **Optional turn** — the aside, the caveat, the counterpunch. One, maximum.
3. **Optional link** — costs exactly 23 characters however long it actually is.
4. **Hashtags** — only when they route the post to a real audience. 0-2, inline, never a block.

**Threads.** Unnumbered, and every post independently readable, because a thread gets picked up from the middle. The link goes in the **last** post, so the thread earns the click instead of spending it early. In the draft file the posts are separated by a line containing only `===`. Count a thread with `count.py thread` (per-post caps), never `count.py post`.

Worked examples, both under cap:

```
Qualcomm's CEO told the market 100B-parameter phones by 2028,
then told his own staff they consistently fell short. Same
quarter, two audiences.
```

```
100B-parameter phones by 2028 for the market. "You consistently
fell short, ttfn" for your own staff. Same month.
https://prasta.substack.com/p/breaking-news-chip-salesman-wants
```

X does not reward the constructed two-beat punch the way a Note does — there's no title, no formatting, no preview of your own piece to lean on. Say the thing, land it, stop.

## LinkedIn structure (≤ 3,000 characters)

Different physics a third time. The audience is people who have worked with him, the cost of a bad post is social rather than algorithmic, and it gets read at two speeds: ~140 characters by most, the whole thing by a few. So the shape is a hook that survives the fold, then a body that rewards the click.

1. **The hook** — inside the first ~140 characters. The point, the ask, or the number. This is the only line most readers get.
2. **The context** — one short paragraph. What happened, what he's after, what changed.
3. **The substance** — the specifics: role, industry, stage, tools, numbers. Vague posts get vague help.
4. **The ask or the takeaway** — one, stated plainly. "Put us in touch" / "here's what I'd check on your own machine" / "the trade is worth naming".
5. **Optional close** — a plain question, an open door to DMs, or one quiet line. Never "thoughts?", never "repost for reach".

**`job-search` posts** have their own shape, and they are the one LinkedIn type where the ask is not optional:

- **Say he's looking, in the first line.** Buried availability posts fail. LinkedIn's own job-seeker guidance points people at the Open to Work signal — the post is what turns that signal into someone acting on it.
- **Name the title, the industry, and the location answer.** One role, one place. "Account Executive, AI/ML infrastructure, remote or Vermont" beats "open to opportunities in tech".
- **One or two proofs with a detail.** Not a résumé — the résumé is the profile the post sends people to.
- **One specific ask.** Introductions or referrals, said plainly. A focused request is something a network can execute; "open to anything" is not.
- **`#OpenToWork` only if the profile setting agrees.** The post and the setting should tell the same story, and the setting has its own audience control (recruiters only, or everyone).

### LinkedIn specifics: documented vs. repeated

The link penalty, the posting hour, and the edit myth are the three claims an agent is most likely to state as fact and shouldn't. This table exists so a draft says something defensible instead of repeating a blog post.

| Claim | Status | What to actually write |
|---|---|---|
| Posts cap at 3,000 characters | **Documented** — LinkedIn Help, "Post and share updates" | State it flat. |
| Native scheduling exists | **Documented** — LinkedIn Help, "Schedule posts": clock icon in the create-post window, 10 minutes to 3 months out, not available for Events/Jobs/Services | State it flat. |
| "...see more" lands at ~140 chars mobile / ~210 desktop | **Third-party consensus**, no LinkedIn documentation; drifts with layout and device | Say "roughly", never a hard number. |
| External links cost reach | **Contested.** LinkedIn's public line is that in-post links are fine. Independent measurement (~300k posts, Mar-Jun 2026, van der Blom) associated one caption link with ~16-19% lower median reach. The widely repeated "50-60%" has no LinkedIn source | Record the direction; refuse to quote a percentage as fact. |
| Put the link in the first comment instead | **Contested, and probably backwards.** LinkedIn now filters link-bearing comments so other members don't see them by default | Never recommend this workaround. |
| The first 60-90 minutes decide reach | **Folklore.** No LinkedIn-published window; the idea traces back to a 2017 post about spam classifiers | "Be around to reply" is the honest version. |
| Editing a post after publishing suppresses reach | **Unproven.** Nothing published by LinkedIn either way, and no independent measurement | Don't repeat it. |

Drafting consequence: write the post so it stands on its own without a click, put a link in the body only when it genuinely helps the reader, and never build a draft around a reach hack that may not exist.

## Procedure

**Step 1 — Map your voice from the published posts.**

Substack posts and his LinkedIn drafts are different registers; read one of each. The published archive is the article voice (`https://prasta.substack.com/archive`); `$DRAFTS/` holds the LinkedIn voice — the Kiro CLI shell-access post, the PDW About post, and the Qualcomm layoff post are the three references that exist.

| Element | "Coffee" post | "Moats" post |
|---|---|---|
| Opening | "I went to delete..." on his personal machine | Morning routine ("coffee in hand, dog at my feet") |
| Tone | Investigative, slightly alarmed but not panicked | Contemplative, market-observer vibe |
| Tech depth | Deep CLI config, AWS data paths | Market timing, iteration velocity |
| Takeaway format | Numbered list + "Read what tools add to..." | Single metaphor: "speed-to-market isn't a moat" |
| Sign-off | GI JOE PSA reference | Dog wants to go outside 🐾 |

(The coffee/dog opener and dog sign-off in the table are historical — both are retired as formulas; see Quick Reference and Pitfalls.)

**Step 2 — Gather sources.**

Use `web_extract` and `web_search` to verify technical claims before writing. Don't make up specs, API names, or command syntax — if you can't link it, don't state it. A Note can link but cannot argue: if a claim needs a source to be credible, it's an article, not a note. A LinkedIn post sits in between: it can carry a claim, but any platform-mechanics claim in it has to come from the documented-vs-repeated table above.

**Step 3 — Write the draft.**

Articles follow the full structure (Type A / Type B detail lives in `templates/post-outline.md`):

```
# [Title that sounds like a headline from a tech blog you half-trust]

### Alternate Title: [A sly framing device — PSA, confession, or hot-take setup]

[Specific moment that led to the discovery.]

[The pivot: "Then I saw..." / "This morning made it visceral." / "What I found..."]

[Technical explanation: 2-3 paragraphs of real meat. CLI commands in backticks,
 config snippets in code blocks, inline links to docs.]

[Clarification: "To be clear: this isn't X, and nothing was hidden." — defuses
 the reader's panic without soft-pedaling the real issue.]

[Actionable fix: exact commands to run, toggles to flip, links to settings UI.]

[Quirk note: one curious thing, worth flagging on your own machine. Phrased as
 "worth checking your own toggles for:"]

[Transition to broader takeaway: "The broader reminder is a trade we make
 constantly without noticing:" or similar.]

[Takeaway list: 3-5 bullets of habits or principles — optional.]

[Sign-off: brief, human, varied.]
```

Notes follow the three lines in Note structure above. Nothing else. Posts follow the four lines in Post structure above, and a thread is that shape repeated with `===` between the posts. LinkedIn posts follow LinkedIn structure above — and a `job-search` post follows its five points, which are not optional there.

**Step 4 — Count it, then save it.**

Run the cap check (below) before writing the file. A note over 200 characters does not get saved — it gets rethought. The same goes for a post over 280, an article over 800, and a LinkedIn post over LinkedIn's 3,000: the file is not written until the count is clean. Then write to `$DRAFTS/` (create the directory if missing) and report the absolute path plus the counted length. For LinkedIn, report the fold position and any advisory notes the checker printed as well — the link and hashtag decisions belong in the reply, not buried in the file.

**Step 5 — Apply voice polish.**

Read the draft back. Check:
- [ ] Could Patrick have genuinely written this? (no coffee/dog imagery — that opener is retired)
- [ ] Does every technical claim have a source or a caveat?
- [ ] Is there exactly one dry wit aside (articles) or at most one (notes)? Hard rule — Patrick wants the draft tight; wit goes off the rails if it's loose.
- [ ] Does it end on a human moment, not a call-to-action to subscribe?
- [ ] Articles: tags at the bottom in `#Tag1 #Tag2 #Tag3` format. Notes: no tag block at all. Posts: 0-2 inline hashtags, no tag block.
- [ ] Posts: hook inside the first ~120 characters, one aside, link budgeted at 23 characters.
- [ ] Threads: every post standalone, link in the last one, `===` separators present, counted per post.
- [ ] LinkedIn: hook inside the first ~140 characters, plain text only (no markdown, no unicode-bold), one ask, no engagement-bait, no tag block unless the tags route somewhere real.
- [ ] LinkedIn `job-search`: the ask is specific and single, and the title, industry, and location are all named explicitly.
- [ ] Under the cap for its format.

## Pitfalls

- **Never infer the format.** Patrick names it. Guessing wrong wastes the whole draft, not just a line.
- **A Note is not a compressed article.** If the draft wants a "To be clear:" paragraph, a fix sequence, or a sourced claim, it's an article. Stop and say so.
- **Keep the dry wit TIGHT** — one good aside per piece, not three. This is a hard rule Patrick set deliberately: looser wit risks going off the rails. The draft stays tight; if a news-cycle article earns more asides, add them in editing, never in the draft.
- **Caps are ceilings.** Don't pad an article to reach 800, and don't treat 200 characters as a quota to fill. Both are maximums.
- Don't reuse the same domestic scene-setting as a formula (coffee in hand, dog at my feet). Repeated dog/coffee openers and sign-offs read as shtick and Patrick will call it out.
- Don't editorialize about "evil corporations" — the alarmism is always undercut.
- Don't pad with "as we all know" — Patrick assumes competence in the reader.
- Don't end with "Subscribe for more" — let the piece breathe, the footer already prompts.
- **An X post is not a Note pasted into a different box.** The extra 80 characters are not room for a second idea — same one-idea discipline, public audience, link budget. If the draft wants a second idea, that's a thread; if it wants three, it's an article.
- **Don't spend the link early in a thread.** A mid-thread link peels readers out before the thread has made its case. Last post.
- **LinkedIn is not "the professional one".** His LinkedIn voice is direct and declarative, but not corporate — the same first person as everywhere else, with the jargon stripped rather than added. No "thrilled to announce", no "excited to share", no "I'm humbled by". He doesn't talk like that anywhere.
- **The LinkedIn fold is 140 characters, not 3,000.** A post can be long and still fail at character 141. Draft the hook first, then the body.
- **One ask per LinkedIn post.** An availability post, an intro request, and a call for comments are three different posts. Stacking them is the most common way a job-search post dies.
- **LinkedIn has no markdown.** Asterisks stay literal, `#` starts a hashtag, and headings don't exist. Formatting is line breaks, short paragraphs, and the occasional list.
- **Don't invent a LinkedIn reach number.** The external-link penalty, the "golden hour", and "editing kills reach" are all repeated far more confidently than they are documented — see the documented-vs-repeated table.
- **A Note is shorter than a LinkedIn post and an article is longer.** Don't let either voice leak into the other.
- **Never post, and never report a post as live.** This skill is draft-only: it does not call `xurl`, and `xurl` is not installed on the Studio anyway. The only proof an X write happened is the `xurl` response (post ID or URL) and there is no API path here — so nothing in this skill may describe an X post as published. Same for LinkedIn: there is no API path, and "scheduled" or "posted" is never something this skill accomplished.

## Verification

Count the body mechanically with the skill's own script. It takes the body as everything after the first `---` rule, so a body containing its own `---` horizontal rule still counts correctly, and it enforces the right unit per format — characters for notes and LinkedIn posts, X-weighted characters for posts, words for articles:

```bash
S=~/.hermes/skills/productivity/shit-posting/scripts/count.py

python3 $S note     "$DRAFTS/YYYY-MM-DD-DRAFT-note-slug.md"
python3 $S article  "$DRAFTS/YYYY-MM-DD-DRAFT-article-slug.md"
python3 $S post     "$DRAFTS/YYYY-MM-DD-DRAFT-post-slug.md"
python3 $S thread   "$DRAFTS/YYYY-MM-DD-DRAFT-post-slug.md"
python3 $S linkedin "$DRAFTS/YYYY-MM-DD-DRAFT-linkedin-slug.md"
```

`post` and `thread` report both the X-weighted count (what X actually enforces, URLs collapsed to 23 characters) and the raw character count, so a post that only fits because of link collapsing is visible rather than hidden. `thread` prints one line per post. `linkedin` enforces LinkedIn's 3,000-character limit and then, **without failing the draft**, reports the two fold positions, the first-paragraph length, the number of external links in the body, and the hashtag count — so the decisions that actually shape a LinkedIn post's reach are visible in the output instead of being made silently. The script exits `1` when anything is over cap and `0` when everything fits — never `0` on an over-cap draft — so it is safe to chain with `&&`.

Then ask yourself: would this land in the same thread as the Kiro CLI and kickbacks.ai posts? If yes, it's yours. If it reads like a Medium post or a press release, rewrite the hook and the takeaway list.

**Pitfall: never rebuild the check as an inline one-liner.**
- **Why:** the failure is invisible on exactly the drafts that pass. Quote splicing turns `"OVER" if ...` into an unbound Python name, so the check raises `NameError` only on the over-cap branch — a silent pass on compliant drafts, a crash on the one case that matters. The old snippet's escaped braces were the same shape of bug: a check that looked right and reported nothing real.
- **Fix:** call `scripts/count.py`. There is no shell quoting to splice, it reports a real number, and it cannot exit `0` on an over-cap draft.
- **Rule:** the counter lives in the script directory, not on a command line.

## Post-publish feedback loop

After a piece goes live, pull the dashboard analytics and log the numbers so the loop closes on actual outcomes. Use the headless browser (browser-use skill) against Patrick's signed-in Chrome: open `https://prasta.substack.com/publish/home` in a new tab (don't disturb the visible tab), read the Overview and Recent posts numbers, and report subscribers, views, and open rate per post. Notes also carry per-note `View stats` (new free/paid subs, followers, clicks, shares), available within 24 hours and refreshing hourly — that's the only per-note number worth pulling. Save a dated snapshot to `$DRAFTS/` if tracking over time. The dashboard is behind Patrick's login — ride the existing Chrome session; stop and ask if it hits a login wall, MFA, or consent prompt.

X is different and simpler: this skill never posts, so a live X post means Patrick posted it, and the numbers sit behind the X app's per-post analytics. There is no API path here — `xurl` is not even installed — so ask him for the numbers rather than reaching for a tool that isn't there.

LinkedIn is the same shape as X: manual, and the numbers live behind per-post analytics ("View analytics" on the post, or Analytics & tools for the portfolio view). What LinkedIn Help documents there: **impressions**, the **in-network vs out-of-network** percentage split, **members reached** (distinct members and Pages, an estimate, no repeat views), and a demographic breakdown — and the Help page itself warns the numbers are estimates rather than precise. Retention differs by metric: discovery and engagement counts for 1,000 days, members reached for 400, demographics for 180. Ask him for the numbers, or read them from the post while he's signed in; there is no API path here either.

## Templates

`templates/post-outline.md` (load via `skill_view`) carries fill-in-the-blanks for each structural section with your voice already baked into the phrasing suggestions, plus the Type N note, Type A/B article, Type X post/thread, and Type L LinkedIn skeletons.

`scripts/count.py` is the cap checker — see Verification for usage. It is the only sanctioned way to count a draft.