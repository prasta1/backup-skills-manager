# Delta / Check-In Status Reports

Some status reports are **deltas** — follow-up pulses that compare against a prior report and report only what changed.

## Use Cases

- **Midday check:** "What changed since the morning brief?"
- **Afternoon pulse:** "Any new events since the midday check?"
- **Evening wrap:** "What happened since the last check-in?"

## Pattern

1. Read the baseline (from prior job output in cron context)
2. Re-check the same sources with same window/filter
3. Report only what changed
4. When a source is unavailable, say so clearly

| Scenario | Response |
|----------|----------|
| Nothing changed | One sentence: "Nothing has changed since [time]." |
| New event appeared | "New item since brief: [detail]" |
| Existing item changed | "[Item]: [old state] → [new state]" |
| Something resolved | "[Issue]: resolved." |
| Something broke | "[Issue]: new problem — [detail]" |

## Cron Context

The baseline arrives as structured text under `## Output from job '<job_id>'`.

## Integration Constraints

- `execute_code` is blocked in cron
- Google Calendar needs Python 3.10+; use Hermes venv
- Linear works via API key in env
- Terminal works normally for curl
