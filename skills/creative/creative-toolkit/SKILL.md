---
name: creative-toolkit
description: "Diagrams, text humanization, sketches, and AI music."
version: 1.0.0
author: Hermes Curator
license: MIT
tags: [creative, design, writing, music, diagrams, humanize, prototyping]
metadata:
  hermes:
    tags: [creative, design, writing, music, diagrams, humanize, prototyping]
    category: creative
---

# Creative Toolkit

A unified skill for creative content: architecture diagrams, text humanization, UI mockups, and songwriting with AI music. Each section below is a distinct workflow — pick the one matching the request.

## When to Use

- "architecture diagram" → **Architecture Diagrams**
- "humanize this text" / "de-ChatGPT" → **Text Humanization**
- "2-3 design variants" → **UI Mockup Sketching**
- "write a song" / "Suno prompt" → **Songwriting & AI Music**

## Skill Inventory

| Skill | Purpose | Status |
|---|---|---|
| architecture-diagram | Dark-themed SVG architecture diagrams as HTML | absorbed |
| humanizer | Strip AI-isms and add real voice to text | absorbed |
| sketch | Throwaway HTML mockups: 2-3 variants to compare | absorbed |
| songwriting-and-ai-music | Songwriting craft and Suno AI music prompts | absorbed |

---

## Architecture Diagrams (absorbed from architecture-diagram)

Generate dark-themed technical architecture diagrams as standalone HTML files with inline SVG. No external tools, no API keys.

### Scope — Best For:
- Software system architecture (frontend/backend/database)
- Cloud infrastructure (VPC, regions, subnets, managed services)
- Microservice/service-mesh topology
- Database + API maps, deployment diagrams

### Workflow
1. User describes architecture (components, connections, technologies)
2. Generate HTML file following the design system
3. Save with `write_file` to `.html`
4. Open in browser — works offline

### Color Palette
| Component | Fill (rgba) | Stroke (Hex) |
|---|---|---|
| Frontend | rgba(8, 51, 68, 0.4) | #22d3ee |
| Backend | rgba(6, 78, 59, 0.4) | #34d399 |
| Database | rgba(76, 29, 149, 0.4) | #a78bfa |
| AWS/Cloud | rgba(120, 53, 15, 0.3) | #fbbf24 |
| Security | rgba(136, 19, 55, 0.4) | #fb7185 |
| Message Bus | rgba(251, 146, 60, 0.3) | #fb923c |
| External | rgba(30, 41, 59, 0.5) | #94a3b8 |

### Key Rules
- Rounded rectangles (rx=6), 1.5px strokes
- Double-rect masking: opaque bg (#0f172a) behind semi-transparent fill
- Arrows drawn early (after grid) so they render behind boxes
- Security flows: dashed rose lines (#fb7185)
- Security Groups: dashed (4,4); Regions: large dashed (8,4), rx=12
- Height: 60px (services), 80-120px (large); Min 40px gap
- Message Buses go in the gap between services
- Legend: outside all boundaries, 20px below lowest

**Template:** `templates/architecture-diagram-template.html` — working examples of all components, arrows, boundaries, legend.

---

## Text Humanization (absorbed from humanizer)

Remove AI-generated text patterns to make writing sound natural and human. Based on Wikipedia's "Signs of AI writing" guide (WikiProject AI Cleanup).

**Key insight:** LLMs guess the statistically most likely next token, producing telltale patterns.

### When to Use
- "Humanize this text", "de-AI", "de-slop", "un-ChatGPT"
- Review text for AI tells before publishing
- Match user's writing voice

### The 34 Patterns
1. Significance inflation — "stands as", "testament to", "pivotal"
2. Notability inflation — citing publications without context
3. Superficial -ing — "highlighting", "emphasizing"
4. Promotional language — "boasts", "groundbreaking"
5. Vague attributions — "experts argue", "industry reports"
6. Formulaic challenges — "Despite challenges, continues to thrive"
7. Overused AI words — actually, additionally, crucial
8. Copula avoidance — "serves as" → "is"
9. Negative parallelism — "Not only... but..."
10. Rule of three — forced triple lists
11. Elegant variation — excessive synonym cycling
12. False ranges — "from X to Y" on non-scales
13. Passive voice & subjectless fragments
14. Em dash overuse (—)
15. Overuse of boldface
16. Inline-header vertical lists
17. Title case in headings
18. Emojis in headings
19. Curly quotation marks
20. Collaborative artifacts — "I hope this helps!"
21. Knowledge-cutoff disclaimers
22. Sycophantic tone
23-25. Filler, hedging, generic conclusions
26. Hyphenated word pair overuse
27. Persuasive authority ("at its core")
28. Signposting ("Let's dive in")
29. Fragmented headers
30. Forced metaphors
31. Dramatic fragmentation
32. Rhetorical questions answered
33. Sentence-opener tics ("So...", "Interestingly...")
34. Reassurance kickers ("And that's okay")

### Process
1. Read input text (`read_file` for files)
2. Identify all pattern instances
3. Rewrite problematic sections
4. Add personality: opinions, varied rhythm, complexity, "I"
5. Final pass: "What makes this AI?" → answer → revise

### Voice Calibration
If user provides a writing sample, analyze sentence patterns, word choice, paragraph structure, punctuation habits — then match their voice. Don't upgrade casual to formal.

**License:** MIT (ported from blader/humanizer — see `references/humanizer-license.md`)

---

## UI Mockup Sketching (absorbed from sketch)

Use when the user wants to **see a design direction before committing** — disposable HTML mockups for comparison.

### When NOT to Use
- Production component — use proper development
- Polished one-off HTML (landing page, deck)
- Diagram — use Architecture Diagrams above
- Design already locked — just build it

### Core Method
```
intake → variants → head-to-head → pick winner (or iterate)
```

### Intake (skip if user gave enough)
1. "What should this feel like?"
2. "What apps capture the feel?"
3. "What's the single most important user action?"

### Variants (2-3, never 1, rarely 4+)
Stances: Density (compact/airy/dense), Emphasis (content/action/tool-first), Aesthetic (editorial/utilitarian/playful), Layout (single-column/sidebar/split).

Each: self-contained HTML, inline style, system fonts, fake content, interactive state. Verify with browser tools.

### Design Principles
Bold, content-informed palette. One color dominates (60-70%). Safe fonts (Arial, Calibri, Cambria, Times, Courier) — avoid Aptos. Dark bg for titles, light for content. Avoid centered body text, accent bars, cream/beige, overflow, AI hallmarks.

**Attribution:** GSD project's `/gsd-sketch` workflow (MIT © 2025 Lex Christopherson).

---

## Songwriting & AI Music (absorbed from songwriting-and-ai-music)

GUIDELINES, not rules. Art breaks rules on purpose.

### Structure
- `ABABCB` — pop/rock | `AABA` — jazz/ballad | `ABAB` — simple | `AAA` — strophic

Building blocks: Intro, Verse, Pre-Chorus, Chorus, Bridge, Outro.

### Rhyme Types
Perfect, Family, Assonance, Consonance, Near/slant.

### Emotional Arc
Contrast is key: whisper before scream, sparse before dense, slow before fast.

### Writing Tips
Show, don't tell. The hook = title/core phrase at the hardest-hitting spot. Prosody: stable feelings → settled melodies.

### Suno Prompt Formula
Genre + Mood + Era + Instruments + Vocal Style + Production + Dynamics. Describe the dynamic arc, not just genre. 1000 chars. No artist names.

**Metatags:** [Intro] [Verse] [Chorus] [Bridge] [Outro] [Whispered] [Belted] [Falsetto] [Female Vocals]. In BOTH style and lyrics. Max 5-8 per section.

### Phonetic Tricks
Spell as they sound ("through" → "thru"). ALL CAPS = louder. Vowel extension ("lo-o-o-ove"). Spell numbers ("twenty four seven"). Space acronyms ("A I").

### Workflow
Concept/hook → Map structure → Brainstorm → Draft → Read aloud → Build prompt → Add metatags → Generate 3-5 variants → Pick best.

### Local Music
- heartmula — full songs with vocals (8-16GB VRAM)
- audiocraft — MusicGen/AudioGen

---

## References

- `templates/architecture-diagram-template.html` — Complete SVG template (absorbed from architecture-diagram)
- `references/humanizer-patterns.md` — Full 34-pattern reference with before/after (absorbed from humanizer)
- `references/humanizer-license.md` — MIT license from blader/humanizer
