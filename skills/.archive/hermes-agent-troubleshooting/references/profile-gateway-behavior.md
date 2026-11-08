# Profile Gateway Behavior - Real-World Case

## Context
User had issues with gateway behavior when switching between Hermes profiles. They were surprised to see "disconnected gateway" warnings when switching between personal and work profiles, which they thought was a regression.

## What Actually Happened
The user had created new Hermes profiles (`personal`, `work`) today, and these were configured with fresh gateway.pid files but no messaging platform tokens. The gateway is a per-profile service that handles:

1. Messaging platforms (Telegram, Discord)
2. Cron jobs
3. Webhooks

## Expected Behavior 
- The `default` profile has a launchd service running its gateway (PID 46272)
- The other profiles have no gateway because they were just set up and have no messaging platform tokens configured
- Each profile runs its own independent gateway process

## Resolution
The user was using the desktop app which showed "disconnected gateway" for non-default profiles. This is actually correct behavior - it's just showing the status of each profile's gateway process independently.

To enable gateways for other profiles:
```bash
hermes --profile personal gateway install
hermes --profile work gateway install
```

But unless these profiles have their own Telegram/Discord bots configured, there's nothing for the gateway to do. Chatting across profiles in the desktop app or TUI works fine without it.

## User Preference Alignment
The user prefers to understand what they're seeing rather than have a "new behavior" explanation. They explicitly said they prefer "for once and for all" solutions over incremental fixes, which means they want to understand why something is working as designed rather than being treated as a bug.