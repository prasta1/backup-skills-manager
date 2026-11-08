# Humanizer: 34 AI-Writing Patterns (Condensed Reference)

Full-length version ported from [blader/humanizer](https://github.com/blader/humanizer), based on Wikipedia's "Signs of AI writing" (WikiProject AI Cleanup).

## Content Patterns (1-6)

1. **Significance inflation** — "stands/serves as a testament to", "pivotal moment", "enduring legacy", "indelible mark"
   - Before: "marks a pivotal moment in the evolution of"
   - After: just describe what happened

2. **Notability inflation** — citing publications without context
   - Before: "cited in The New York Times, BBC, Financial Times"
   - After: "In a 2024 New York Times interview, she argued that..."

3. **Superficial -ing phrases** — "highlighting...", "emphasizing...", "reflecting..."
   - Before: "showcasing how these tools can contribute to better outcomes, highlighting the interplay"
   - After: "These tools improve outcomes by combining automation and human judgment."

4. **Promotional language** — "boasts a", "vibrant", "groundbreaking", "breathtaking", "must-visit"
   - Before: "Nestled within the breathtaking region... stands as a vibrant town"
   - After: "Alamata Raya Kobo is a town in the Gonder region of Ethiopia"

5. **Vague attributions** — "Industry reports", "Experts argue", "Observers have noted"
   - Before: "Experts believe it plays a crucial role"
   - After: "According to a 2019 survey by the Chinese Academy of Sciences"

6. **Formulaic challenges sections** — "Despite its... faces several challenges"
   - Before: "Despite challenges typical of urban areas, traffic congestion and water scarcity. Despite these challenges, continues to thrive."
   - After: "Traffic congestion increased after 2015 when three new IT parks opened."

## Language Patterns (7-13)

7. **Overused AI words** — actually, additionally, align with, crucial, delve, enhancing, fostering, garner, highlight, interplay, intricate, key, landscape, pivotal, showcase, tapestry, testament, underscore, valuable, vibrant
   - Marketing/blog clichés: "at the end of the day", "moving forward", "deep dive", "game-changer", "circle back", "unpack", "navigate"

8. **Copula avoidance** — "serves as", "stands as", "boasts", "features" → use "is"/"are"
   - Before: "Gallery 825 serves as LAAA's exhibition space"
   - After: "Gallery 825 is LAAA's exhibition space"

9. **Negative parallelism** — "Not only... but...", tailing negations ("no guessing")
   - Before: "It's not just about X; it's about Y"
   - After: "X, and also Y."

10. **Rule of three** — forced triple lists
    - Before: "keynote sessions, panel discussions, and networking opportunities"
    - After: "The event includes talks and panels. There's also time for networking."

11. **Elegant variation** — excessive synonym substitution (repetition-penalty code)
    - Before: "The protagonist... the main character... the central figure... the hero"
    - After: "The protagonist" (use the same term)

12. **False ranges** — "from X to Y" where X/Y aren't on a meaningful scale
    - Before: "from the Big Bang to the cosmic web, from star birth to dark matter"
    - After: "The book covers the Big Bang, star formation, and current dark matter theories."

13. **Passive voice & subjectless fragments**
    - Before: "No configuration file needed. The results are preserved automatically."
    - After: "You do not need a configuration file. The system preserves the results."

## Style Patterns (14-19)

14. **Em dash overuse** (—) — use commas, periods, or parentheses instead

15. **Overuse of boldface** — mechanical emphasis in bold

16. **Inline-header vertical lists** — bold headers + colons + paragraphs

17. **Title case in headings** — "Strategic Negotiations And Global Partnerships" → "strategic negotiations and global partnerships"

18. **Emojis** — don't decorate headings or bullets with emojis

19. **Curly quotation marks** — "…" → straight quotes "…"

## Communication Patterns (20-25)

20. **Collaborative artifacts** — "I hope this helps!", "Of course!", "Let me know if..."

21. **Knowledge-cutoff disclaimers** — "as of my last update", "while specific details are limited"

22. **Sycophantic tone** — "You're absolutely right that..."

23. **Filler phrases** — "In order to" → "To", "Due to the fact that" → "Because"

24. **Excessive hedging** — "It could potentially possibly be argued..."

25. **Generic positive conclusions** — "the future looks bright", "exciting times lie ahead"

## Advanced Style Patterns (26-34)

26. **Hyphenated word pair overuse** — third-party, cross-functional, client-facing, data-driven, real-time, end-to-end

27. **Persuasive authority** — "The real question is", "At its core", "What really matters"

28. **Signposting** — "Let's dive in", "Let's explore", "Here's what you need to know"

29. **Fragmented headers** — heading followed by paragraph that just restates it

30. **Forced metaphors** — inventive but decorative metaphors that get explained right after

31. **Dramatic fragmentation** — subjectless fragments, "X. And Y. And Z." runs

32. **Rhetorical questions** — "What makes an API good? It comes down to predictability."

33. **Sentence-opener tics** — "So...", "Look,", "Interestingly...", "Importantly..."

34. **Reassurance kickers** — "And that's okay.", "There's nothing wrong with that.", "no shame in..."

## Quick Process

1. Read the input text carefully (use `read_file` for files)
2. Identify all instances of the patterns above
3. Rewrite each problematic section
4. Ensure: natural when read aloud, varied sentence structure, specific details, matching tone
5. Show the rewrite
6. Ask: "What makes the below so obviously AI generated?" → answer → revise
