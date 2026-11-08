---
name: concise-communication-session-notes
description: "Session-specific notes from the concise-communication skill, documenting user communication preferences."
---

# Concise Communication — Session Notes (absorbed from concise-communication)

This file consolidates the session-specific content from the archived `concise-communication` skill, including user preference notes, session observations, and additional notes that were specific to particular interactions. The general class-level principles are preserved at the bottom and also captured in `status-reporting-best-practices.md`.

## User Preference Notes (original source: concise-communication skill)

- The user prefers "brief but complete" answers.
- They do not want over-explanation or forced enthusiasm.
- If they say "just give me the answer", that's a directive to reduce verbosity.
- They explicitly stated: "Prefers concise, direct responses without fluff. Dislikes verbosity and overly reactive responses. Values accuracy over agreeableness. Prefers 'for once and for all' solutions over incremental fixes."
- When applying this skill in response to a user's request, the user expects the final result or answer to be delivered directly. No meta-commentary or process description is needed unless explicitly requested.
- User has strong preference for direct command-line solutions over process descriptions — they prefer "just give me the bash command" rather than explanations of why it works.
- User correction: When asked to write a cover letter, the user later corrected the job title (CS to technical support) and preferred a more direct framing. This shows they want to be upfront about the role match, not spin it.
- User Correction: Profile Collapse. The user explicitly requested a collapse from a multi-profile setup to a single `default` profile to eliminate duplication and maintain "machine hygiene." They preferred a "for once and for all" solution over incremental fixes. This establishes a hard preference for a consolidated, non-redundant configuration and memory structure.

## Session Notes (original source: concise-communication skill)

In a session, the user explicitly corrected framing in a cover letter for a technical support role at Temporal. The session demonstrated the user's strong preference for:

1. Direct alignment between job requirements and personal experience
2. Technical role framing over business/CS spin ("technical support leader" vs "customer success growth")
3. Concrete mapping of job requirements to specific experience points
4. Concise, factual presentation over fluff or forced enthusiasm

The user corrected the original letter to shift from "Head of Global Customer Success" to "technical support leader", replacing expansion/QBR language with "operating system" and "support systems", and shifting from CS growth framing to technical support systems building.

This pattern reinforces the user's clear preference for:
- Avoiding spin that makes content sound generic
- Focusing on technical requirements matching personal experience
- Using direct, concrete framing over business/CS expansion language

## Additional Notes (original source: concise-communication skill)

In the morning brief generation session, the user demonstrated a preference for:
- Direct, terminal-oriented command-line delivery over verbose explanations
- Explicit confirmation of webhook delivery (HTTP 204 status) rather than silent success

## General Principles (class-level)

These class-level principles are also captured in `references/status-reporting-best-practices.md`:

1. Lead with the answer or action; provide reasoning only if asked or essential for correctness.
2. Avoid filler phrases like "I think", "just to let you know", "please note".
3. Use bullet points or tables for structured data; avoid long paragraphs.
4. If user expresses frustration with verbosity, immediately shorten subsequent replies.
5. Honor user's preferred tone: direct, minimal pleasantries, no forced enthusiasm.
6. When automating updates (e.g. cron jobs), ensure all messages are concise and high-signal.
