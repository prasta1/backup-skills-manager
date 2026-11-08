# Delta / Check-In Status Reports

**Absorbed from:** `morning-brief-generation`

Not all status reports are full scans. Some are **deltas** — a follow-up pulse that compares against a prior report and reports only what changed.

## Pattern

1. Read the baseline (from prior job output in cron context)
2. Re-check the same sources with same window/filter
3. Report only what changed
4. When a source is unavailable, say so clearly

| Scenario | Response |
|----------|----------|
| Nothing changed | "Nothing has changed since [time]. Still [status]." |
| New event/task appeared | "New item since brief: [detail]" |
| Existing item changed | "[Item]: [old state] → [new state]" |
| Something resolved | "[Issue]: resolved." |
| Something broke | "[Issue]: new problem — [detail]" |

## Cron Constraints

- `execute_code` is blocked in cron
- Google Calendar needs Python 3.10+; use Hermes venv
- Linear works via API key in env
- Terminal works normally for curl