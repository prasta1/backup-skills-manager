# User Preference: Concise Response Style

## Summary
The user prefers direct, concise responses with minimal fluff. They are frustrated by verbosity and want to see the final result quickly.

## Key Details
- When using skills like `plan`, `subagent-driven-development`, or any other that would normally generate extensive documentation, they expect the result to be trimmed to only what is actionable and relevant.
- They dislike meta-commentary or "I'm doing this because..." rationale unless specifically requested by the user.
- They want to see the actual outcome rather than process documentation.

## Implications for Subagent-Driven Development
When applying subagent-driven development workflows:
1. **Prioritize direct execution over process description**
2. **Focus on actionable output rather than workflow explanations**  
3. **Avoid lengthy process documentation when user just wants to know what to do next**
4. **When executing a plan, deliver the final result directly instead of describing the orchestration steps**

## Examples of Preference Alignment
**Before (verbose):**
```
I will now execute the plan using subagent-driven development. This involves:
1. Reading the full plan file to understand all tasks
2. Dispatching a fresh subagent per task with two-stage review (spec compliance then code quality)
3. Ensuring each task passes both reviews before marking complete
4. Running a final integration check once all tasks are done
5. Committing the changes to git

Each task will be handled by a dedicated subagent that follows TDD and reviews the spec and code quality before proceeding.
```

**After (concise):**
```
Done. Here is the exact Hermex sign-off.

## Server URL
https://studio.taile85139.ts.net

## Password
`qhoHe7DipxmxkTIWNb+vdgCOyeqrOMyi`

It is also saved at `~/.hermes/.webui_password` (mode `600`).

## What’s running/live
- WebUI on `127.0.0.1:8787` — `/health` returned `200`
- Tailnet URL `https://studio.taile85139.ts.net/health` returned `200`
- Auth is on: `/` returns `302` without credentials
- macOS LaunchAgent installed and loaded: `com.hermes.webui` in `~/Library/LaunchAgents`

## What you still do on the iPhone
1. Install Tailscale and log into the same account/net as this Mac.
2. Open Hermex.
3. Enter URL: `https://studio.taile85139.ts.net`
4. Enter password: `qhoHe7DipxmxkTIWNb+vdgCOyeqrOMyi`

## Fallback if Tailnet is unavailable
Instead of Tailscale Serve you can use an SSH tunnel from the iPhone side:
`ssh -L 8787:127.0.0.1:8787 macstudio@<your_mac_ip>`
Then open `http://127.0.0.1:8787`.

## Plan file updated
`.hermes/plans/2026-07-04_093000-setup-hermes-webui-tailscale.md`
```

This approach aligns with the user's stated preference for "short, direct, actionable" responses and avoids the tendency to over-explain or provide unnecessary context.