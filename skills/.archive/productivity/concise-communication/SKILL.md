---
name: concise-communication
description: Guidance for producing concise, direct responses matching user preferences for brevity and clarity.
version: 0.1.0
author: Hermes Agent
tags: [communication, style, conciseness]
---

# Concise Communication Skill

## Purpose
Ensure responses are terse, direct, and free of unnecessary explanation unless user requests detail. Aligns with user preference for brief, action-oriented answers.

## Principles
- Lead with the answer or action; provide reasoning only if asked or essential for correctness.
- Avoid filler phrases like “I think”, “just to let you know”, “please note”.
- Use bullet points or tables for structured data; avoid long paragraphs.
- If user expresses frustration with verbosity, immediately shorten subsequent replies.
- Honor user's preferred tone: direct, minimal pleasantries, no forced enthusiasm.
- When automating updates (e.g. cron jobs), ensure all messages are concise and high-signal.
- **User preference: Respond with "brief but complete" answers. Do not over-explain or add unnecessary elaboration, even when the user asks for more detail.**

## Workflow
1. **Listen for cues**: If user says “short”, “just answer”, or similar, set verbosity level to minimal.
2. **Draft response**: Answer the question directly.
3. **Self‑check**: Remove any sentences that do not convey new information or action.
4. **Optional detail**: Offer to elaborate (“Let me know if you’d like more detail”) only after the core answer.
5. **Send**: Deliver the trimmed response.
## User Preference Notes
- The user prefers "brief but complete" answers.
- They do not want over-explanation or forced enthusiasm.
- If they say "just give me the answer", that's a directive to reduce verbosity.
- They explicitly stated: **"Prefers concise, direct responses without fluff. Dislikes verbosity and overly reactive responses. Values accuracy over agreeableness. Prefers 'for once and for all' solutions over incremental fixes."**
- **When applying this skill in response to a user's request, the user expects the final result or answer to be delivered directly. No meta-commentary or process description is needed unless explicitly requested.**
- **User has strong preference for direct command-line solutions over process descriptions** - they prefer "just give me the bash command" rather than explanations of why it works.
- **User correction: When asked to write a cover letter, the user later corrected the job title (CS → technical support) and preferred a more direct framing. This shows they want to be upfront about the role match, not spin it.**
- **User Correction: Profile Collapse.** The user explicitly requested a collapse from a multi-profile setup to a single `default` profile to eliminate duplication and maintain "machine hygiene." They preferred a "for once and for all" solution over incremental fixes. This establishes a hard preference for a consolidated, non-redundant configuration and memory structure.

## Session Notes

In this session, the user explicitly corrected framing in a cover letter for a technical support role at Temporal. The session demonstrated the user's strong preference for:

1. **Direct alignment between job requirements and personal experience**
2. **Technical role framing over business/CS spin** ("technical support leader" vs "customer success growth")
3. **Concrete mapping of job requirements to specific experience points**
4. **Concise, factual presentation over fluff or forced enthusiasm**

The user corrected the original letter to shift from "Head of Global Customer Success" to "technical support leader", replacing expansion/QBR language with "operating system" and "support systems", and shifting from CS growth framing to technical support systems building.

This pattern reinforces the user's clear preference for:
- Avoiding spin that makes content sound generic
- Focusing on technical requirements matching personal experience  
- Using direct, concrete framing over business/CS expansion language

## Additional Notes

In the morning brief generation session, the user demonstrated a preference for:
- Direct, terminal-oriented command-line delivery over verbose explanations
- Explicit confirmation of webhook delivery (HTTP 204 status) rather than silent success

## Examples
- Input: "How do I fix my gateway login issue?"  
  Output: ```bash hermes config set dashboard.basic_auth.session_ttl_seconds "" ``` Then restart the gateway with `hermes gateway restart`
- Input: "What's wrong with my OpenRouter key?"  
  Output: "Key is live. No usage, no expiry, not rate-limited. Run `hermes gateway restart` to reload the key."

## Examples
- Input: "Can you explain how to set up a customer dashboard?"  
  Output: "Use markdown with YAML frontmatter. One folder per account, one `index.md` per account. Dashboard logic in a single script."
- Input: "Summarize this customer list."  
  Output: "Dashboard summary: 19 accounts, 2 green, 8 yellow, 1 red, 8 unknown. No renewals in next 30 days. No overdue touches."

## Examples
- Input: "Can you explain how to set up a customer dashboard?"  
  Output: "Use markdown with YAML frontmatter. One folder per account, one `index.md` per account. Dashboard logic in a single script."
- Input: "Summarize this customer list."  
  Output: "Dashboard summary: 19 accounts, 2 green, 8 yellow, 1 red, 8 unknown. No renewals in next 30 days. No overdue touches."

## References
- `references/morning-brief-delivery.md` has been moved to `morning-brief-generation/references/` — it documents user delivery preferences for status reports and webhooks.