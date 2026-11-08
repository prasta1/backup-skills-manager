# Delta / Check-In Status Reports

Not all status reports are full scans. Some are **deltas** — a follow-up pulse that compares against a prior report and reports only what changed.

## Use Cases

- **Midday check:** "What changed since the morning brief?"
- **Afternoon pulse:** "Any new events since the midday check?"
- **Evening wrap:** "What happened since the last check-in?"
- **Any cron job whose prompt includes prior run output as context**

## Pattern

### 1. Read the baseline

The baseline report is typically delivered as context in the cron prompt (output from a preceding job). Read it to establish the "before" state.

### 2. Re-check the same sources

Run the same queries as the baseline report — same calendar window, same task filter. Only this time the goal is **diff detection**, not enumeration.

### 3. Report only what changed

| Scenario | Response |
|----------|----------|
| Nothing changed | One sentence: "Nothing has changed since [time]. Still [status]. |
| New event/task appeared | "New item since brief: [detail]" |
| Existing item changed | "[Item]: [old state] → [new state]" |
| Something resolved | "[Issue]: resolved." |
| Something broke | "[Issue]: new problem — [detail]" |

### 4. When integration is unavailable

If a source that worked in the baseline is now unavailable, say so clearly. The delta might be "can't verify" rather than "no change," and that distinction matters.

## Cron Context Delivery Pattern

The baseline arrives as structured text under the heading:

```
## Output from job '<job_id>'
```

This is the prior job's complete response. Use it as the "before" state.

## Integration Constraints in Cron

Cron jobs run without a user present. This affects which tools are available:

- **execute_code is blocked** — no arbitrary Python that calls Hermes tools
- **Google Calendar** — requires Python 3.10+ for the google-api.py script (cron default is often 3.9.x); use the Hermes venv python3.11 at `~/.local/bin/python3.11` or ~/.hermes/hermes-agent/venv/bin/python3.11
- **Google token** — must be at `~/.hermes/google_token.json`; if missing, calendar cannot be checked
- **Linear** — works via the API key in env or the linear_api.py script (no Python version issue)
- **Terminal** — works normally for curl and other system commands

## Example: Full Delta Report

```
Nothing has changed since the morning brief. Linear still shows no assigned issues.
```

## Example: Partial Delta (source unavailable)

```
Linear still clean. Couldn't verify calendar from this session — no Google auth available.
The morning brief had it clear, so unlikely anything changed.
```