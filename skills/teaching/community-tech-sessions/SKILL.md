---
name: community-tech-sessions
description: "Design community workshops for non-technical learners."
---

# Community Tech Sessions

Design one-hour or multi-session community education that demystifies technical topics for non-technical audiences. The goal is informed participation, not engineering fluency.

## When to use

- User mentions workshop, session, class, or series for local community members
- Audience is general public, older skew, makerspace, library, Front Porch Forum types
- Topic is AI, agents, local inference, open-source tools, or similar technical subjects
- Format is modular (pick-and-choose from a menu) or fixed sequence

## Core principles

1. **End every session with one concrete 24-hour action.** Low bar. Familiar context. The goal is familiarity, not productivity.
2. **Lead with what's already in their world.** Maps, spellcheck, camera face-tagging, spam filters, Waze. Reframe AI as familiar, not new.
3. **Vocab first, then explanation.** Open with a plain-language definitions block before any deep explanation. Use this block to establish shared vocabulary for the whole series. No jargon after this section.
4. **Address fears head-on rather than dodging them.** Name the fear directly, respond honestly but plainly, then move on. Fear drops when people understand what something actually is.
5. **Live demos beat slides.** Always have a pre-recorded fallback ready. A demo that breaks is itself a useful moment if acknowledged honestly.
6. **Handouts leave the room.** Print a one-pager: what we covered, one thing to try, blank space for questions, and a teaser for the next session.

## Audience assessment before building (absorbed from ccb-edu)

Run a feeler post before drafting a full curriculum, and build only the modules the responses justify.

1. Identify the audience segment.
2. Draft the feeler post: one-sentence description, candidate topic lines, format and duration, one feedback prompt. Include the motivation line: community demystification, not sales.
3. Use responses to pick 3–6 modules and their order.

Default 60-minute shape when nothing else is specified: hook or recap 3–5 min, core content 10–15, live demo 15–20, fear reducer plus Q&A 5–10, wrap-up and 24-hour action 5. From session 2 on, open with a 2–3 minute recap; each session assumes only prior content.

## Session module numbering

Use lowercase module IDs so they work as filenames and handout labels:

- `m0` — optional series orientation: who this is for, how to choose sessions, what to bring, one framing line for the whole series.
- `m1`–`m<n>` — one-hour standalone modules in a pick-and-choose menu.

`m0` is a lightweight connector. It does not teach AI concepts. Its job is to lower the activation energy for showing up and to give attendees a shared vocabulary for the rest of the series.

## Module archetypes

Not every hour slot needs the same shape. Use the archetype that fits the content.

**Foundation (`m1`)**
- Vocab block first.
- Relatable opening hook with show of hands.
- One main concept, plain analogy, existing-tools examples.
- Fear reducer with 2–3 named fears.
- Live demo showing capability and a clean failure.
- Handout with carry-forward vocabulary.

**Conceptual (`m2`)**
- Short recap of prior session or handout vocab.
- One conceptual leap explained with metaphor.
- Local real-world examples that make it concrete.
- Brutal honesty about current limitations.
- Live demo or tool walkthrough that shows failure modes.
- Fear reducer focused on the new fear this concept creates.

**Hands-on (`m3`)**
- Minimum viable setup described in plain language.
- Hardware/software requirements stated honestly.
- Concept preview with plain-language explanation.
- Live demo on real hardware in the room when possible.
- Recording/screenshot backup and a stated fallback plan.
- Low-bar next action that does not require troubleshooting.

**Practical skill (`m4`)**
- One skill, not three.
- Pattern or framework taught with live examples in sequence: bad prompt, improved prompt, result.
- Attendee practice time with feedback.
- Guardrails on when not to use the skill.
- One-page cheat sheet or handout they can keep.

**Applied (`m5`)**
- Mental filter first: what's good for AI, what's bad for AI.
- Local examples drawn from business, local government, schools, personal life.
- Group activity where attendees name their own tasks.
- Live prompts based on what the room surfaced.
- Practical Q&A with real tasks from the audience.

**Closing policy (`m6`)**
- Recap of durable concepts from earlier sessions.
- Privacy/tradeoff framing without fear-mongering.
- Evaluation checklist attendees can reuse.
- Long open Q&A on fears and policy.
- Close with a durable decision-making frame, not just a to-do.

## Syllabus template

When the user asks for a syllabus, rough framework, or module menu, return a modular draft with these sections:

1. Core framing held across every session.
2. Module menu with short bullet outlines.
3. Suggested lightweight series if attendance skews casual.
4. Feeler post skeleton for gauging interest.
5. Logistics to flag before the first session.

Keep it riff-friendly, not final. The user is using it to generate discussion, not to publish.

## Session module template

Every module outline should contain:

```
## Session goal
One sentence: what attendees should be able to say by the end.

## Timing (X minutes total)
Table of segments with minutes.

## Vocab if this is session 1, or reminder if recurring
New terms introduced in this session, plain language.

## Opening hook
Interactive show-of-hands or relatable question, not slides.

## Core explanation
Plain-language analogy or metaphor. Max one main concept.

## Where it's already in their lives
Examples they already use without thinking.

## Limitations / risks / fear reducer
What it cannot do. Address the top 2-3 fears you expect to hear.

## Live demo
Two-part preferred: show capability, then show a clean failure or fabrication to demonstrate limits.

## Open Q&A
Let them drive. Anticipate 3-4 common questions and write plain-language answers.

## 24-hour action item
One specific, low-bar thing they can try before the next session.

## Handout outline
What we covered | One thing to try | Questions I still have | Coming next
```

**Vocab-first rule at the syllabus stage:** Do not write module outlines or syllabus menus without a vocab block for session 1. The definitions section is not optional polish — it's the foundation that prevents confusion from compounding across sessions. If you catch yourself drafting content before vocab, stop and write the definitions first.

## Vocab-first opening rule

Do not open session 1, or any module that introduces new terminology, with deep explanation. Insert a definitions block first:

- Use a numbered or bolded term/definition list
- Each term gets one sentence maximum
- No etymology, no history, no links
- Include the acronym and spelled-out form
- Add one local example when possible

The definitions section becomes the stable vocabulary for the entire series. Reference it from session 2 onward.

## Fear-reduction pattern

For each expected fear, structure the response in three moves:

1. Name the fear plainly
2. Distinguish the real concern from the movie version
3. Give one sentence that resolves it

Format example:
> **Fear: "Is it going to take my job?"**
> It automates specific tasks within jobs, not whole jobs wholesale. People who learn to use it alongside existing skills will have an advantage.

Session 1 typically needs 2–3 named fears. Later sessions need 1–2 specific to the new concept.

## Live demo design

Every module with a live demo should cover both capability and limitation in a single viewing:

- Show something that works and feels locally relevant
- Then show a clean failure: hallucination, wrong answer, broken tool call
- Narrate both as normal expected behavior, not surprise
- If demo fails before it starts, pivot to a recording within 30 seconds and acknowledge it
- A failed demo is informative if you name it out loud

## 24-hour action rules

- Must require no new software install unless the session itself walked through the install
- Must connect to something they already care about (garden, business, school, town)
- Must be observable: they should be able to say "yes, I tried it" tomorrow
- Do not assign homework that requires a follow-up session to complete

Offer a lower-bar fallback when the primary action feels like a barrier: watch a walkthrough, read one example, check one setting.

## Handout template

```markdown
# What we covered
- Three bullets on the new concepts

# One thing to try this week
- One specific action, named and bounded

# Questions I still have
(blank space)

# Coming next
[Module title + one-line description]
```

Keep the blank question space. That blank invites the follow-up conversation that turns attendees into returning attendees.

## Severity classification

When reviewing or iterating on session content, classify issues as:

- **Hard break:** Timing is wrong, demo will fail at the venue, or content is incorrect in a way that undermines trust
- **Latent risk:** Fear-reduction section downplays real concerns, demo shows unrealistic capability, no action item
- **Polish:** Wording could be clearer, analogy doesn't land for a Vermont audience, handout formatting

Lead with hard breaks when recommending changes. Do not suggest polish when latency or correctness issues exist.

## References and templates

- `references/module-archetypes.md` — quick lookup for the module shape to use for each `m<n>` session.
- `templates/handout.md` — generic one-page handout template to copy and fill for each session.
- `references/session-modules.md` — M1–M6 outlines from the AI syllabus (from ccb-edu).
- `references/definitions-pattern.md` — plain-language definitions opener (from ccb-edu).
- `references/fear-reduction-bank.md` — fear types and responses from the AI syllabus (from ccb-edu).
- `references/feeler-post-template.md` — feeler post template (from ccb-edu).

Use these when drafting or reviewing modules so the output stays structurally consistent.

## Pitfalls

- **Don't skip definitions because "they'll figure it out."** They won't. The vocab block prevents confusion from compounding across sessions.
- **Don't use metaphors from inside Silicon Valley.** Grocery stores, shaker tables, and snowblower maintenance land. LLM supply chains and token budgets don't.
- **Don't paper over real privacy concerns.** Name them, then reframe: "That's real, and that's exactly why we're covering local AI next."
- **Don't overestimate attention span.** One hour means one main concept plus one demo. Anything more is noise.
- **Don't skip the fallback demo.** Internet failure, GPU overload, model crash — any of these will happen at least once. Have screenshots or a recording on a second device.
- **Don't let `m0` creep into teaching content.** If it teaches AI concepts, it is not an orientation module. Keep it to logistics, expectations, and framing only.