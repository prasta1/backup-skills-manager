---
name: smart-tv-troubleshooting
description: "Smart TV app HDMI/input troubleshooting and content mapping. Confirm environment, clarify ambiguous requests, and never fabricate fixes."
version: 1.0
category: smart-tv-troubleshooting
---

# Smart TV Troubleshooting (HDMI / Input Mapping)

Always-on rules for smart TV / TV-app work (e.g., cleanyourtv, input mapping, HDMI troubleshooting guides):

## Before Changing Anything

1. **Verify the workspace/repo exists.** The workspace snapshot (e.g., `/Users/prasta/Projects/forks/fork-cleanyourtv`, branch `fix/hdmi1-troubleshooting`) must resolve to an actual directory on this host before editing. If it points to a missing path, ask which directory to use or confirm the repo is elsewhere — don't assume.
2. **Check branch/state.** Confirm the branch mentioned in the workspace exists (`git status`, `git branch`) before making edits.

## Clarify Ambiguous Requests

TV-related requests like "unable to use HDMI ports" or "get those mapped" are often ambiguous. Use **concrete multi-select clarifications** rather than open-ended questions. Offer: (a) smart TV app input mapping, (b) troubleshooting guide content, (c) remote/HDMI switching, (d) the affected ports (HDMI 1/2/3/ARC/all), and (e) what's broken (input selection, signal detection, port recognition, physical connection).

Pitfall: If the user responds with "I don't actually know — the post is just listed as unavailable," treat it as a **content/documentation issue** (a missing or broken troubleshooting entry) rather than a hardware/app mapping bug. Don't invent a code fix when the actual task is updating a guide or mapping entry.

## When the Session Ends Unresolved

If clarification times out or the user cannot confirm the failure mode, do NOT write up untested attempts as a reliable workflow. Note the unverified paths and ask for confirmation on the next turn.

References:
- `references/hdmi-ports.md` — clarification checklist for HDMI/input tasks.
- `references/clarification-pattern.md` — concrete multi-select clarification technique.

## Style Preference

Keep responses concise. The user prefers brief, direct answers — no preamble restating the request, no verbose process narration. Confirm briefly, ask briefly, deliver briefly.
