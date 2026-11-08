---
name: read-only
description: Dispatch an investigation subagent that only reports back.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Investigation, Delegation, ReadOnly, Findings, Subagents, NextSteps]
---

# Read-Only Investigation

Dispatches a subagent to investigate a question and come back with findings plus
proposed next steps, and nothing else. The subagent gathers evidence and reports;
it never edits, sends, deletes, installs, restarts, commits, or otherwise mutates
anything. The parent session is likewise forbidden from carrying out a suggested
fix without an explicit yes from the user.

There is no read-only flag in `delegate_task` — enforcement is the written contract
in the child's context, plus the before/after fingerprint in `scripts/guard.py`.
Never claim a guarantee you have not verified with the guard.

Stdlib Python only, no network, portable across macOS and Linux.

## When to Use

- `/read-only <question>` — any task where the answer matters more than the change.
- "Investigate X and tell me what you find" / "look into X, don't touch anything".
- "Diagnose this before we change it" / "I want findings, not a fix".
- Pre-change reconnaissance on a system you have not debugged before.
- Auditing a dependency, a log trail, an API, a repo, or a bill of materials.
- Any time a wrong write is expensive: production configs, live services, customer data.

Not for: making the change, or dispatching a worker that is supposed to ship something.

## Prerequisites

None. No env vars, no credentials, no install. `python3` on PATH is the only
dependency, for the guard script at `scripts/guard.py` (resolves to
`~/.hermes/skills/research/read-only/scripts/guard.py`).

## How to Run

Invoke the investigation through `delegate_task` with a self-contained `context`
that carries the read-only contract, and a `terminal` call to the guard script
either side of the dispatch. Procedure below is the canonical order.

## Quick Reference

- `delegate_task(goal=..., context=..., output_schema=...)` — the dispatch.
- `terminal`: `python3 scripts/guard.py snapshot <path> --out <file>` — before.
- `terminal`: `python3 scripts/guard.py check <path> --out <file>` — after.
- Allowed in the child: `read_file`, `search_files`, `web_extract`, `web_search`,
  `browser_navigate` (fetch and read only), `vision_analyze`, `skill_view`,
  `terminal` (read-only commands only).
- Forbidden in the child: `write_file`, `patch`, `memory`, `cronjob`, any
  `kanban_*` transition, `image_generate`, `text_to_speech`, send or write MCP
  tools (`mcp__linear__save_*`, `mcp__notion__notion_create_*` /
  `_update_*` / `_delete_*`, `mcp__agentmail__send_*` / `create_draft`),
  `imessage` send, `tool_call` to any mutating tool.
- The child's own tool calls and schema errors are in the transcript that
  `delegate_task` reports back — audit it, do not trust the prose.

## Procedure

### 1. Freeze the scope before dispatching

Write down, in your own head or one line of text, the exact boundary of "the
system under investigation": paths, hosts, URLs, services, time window. The
guard can only watch what you name. A scope of "the whole stack" fingerprints
nothing useful.

Also write the single question the child must answer. One question, one child.
If you have three questions, either dispatch three children in one
`delegate_task(tasks=[...])` call or run three separate read-only passes.

### 2. Fingerprint the scope

```bash
python3 ~/.hermes/skills/research/read-only/scripts/guard.py \
  snapshot /path/to/scope --out /tmp/ro-before.json
```

Run it through the `terminal` tool. For a remote-only target (a web service, a
host you cannot reach) there is nothing to fingerprint — say so in your report
and lean on the transcript audit in step 6 instead.

### 3. Write the child contract

The child has no memory of this conversation, cannot ask you anything, and will
fill gaps with assumptions if you leave them. The `context` must therefore carry:

- The question, restated.
- The scope: exact paths, hosts, URLs, and the time window to look at.
- Any focus or exclusion from the user ("look at the auth flow, skip the
  deprecated endpoints"). Every constraint the user gave rides along verbatim.
- The read-only rule, in the child's terms, with the forbidden list above.
- "You cannot ask questions. If something is ambiguous, pick the most likely
  reading, state the assumption, and keep going."
- The reporting shape: findings, each labeled `known` / `likely` / `unverified`,
  with the exact file path, line, URL, or command output that supports it.
- "Do not write notes to disk. Your summary is the only deliverable."
- "End with next steps you recommend, each with the action, the risk, and whether
  it is reversible. Do not perform any of them."

### 4. Dispatch with a schema

`output_schema` is what makes the report machine-checkable and lets the kernel
flag a malformed return. Use this shape:

```json
{
  "type": "object",
  "required": ["verdict", "findings", "open_questions", "next_steps"],
  "properties": {
    "verdict": {"type": "string"},
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["claim", "confidence", "evidence"],
        "properties": {
          "claim": {"type": "string"},
          "confidence": {"type": "string", "enum": ["known", "likely", "unverified"]},
          "evidence": {"type": "string"}
        }
      }
    },
    "open_questions": {"type": "array", "items": {"type": "string"}},
    "next_steps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["action", "risk", "reversible"],
        "properties": {
          "action": {"type": "string"},
          "risk": {"type": "string"},
          "reversible": {"type": "boolean"}
        }
      }
    }
  }
}
```

The return carries `schema_valid` and `schema_errors`. A false means one bounded
correction retry is allowed; anything past that is a bad dispatch, not a bad child.

### 5. Wait. Do not act on anything you just read

`delegate_task` returns inline when nothing else is waiting on the result, and
otherwise delivers the result as a later message between turns. Either way: do
not poll, do not "helpfully" apply a fix, do not start the next step. The
investigation ends at the report.

### 6. Audit before you relay

- Run the guard check (see Verification). A non-zero exit is a real violation —
  say so in the first clause of your report, name the paths that changed, and do
  not paper over it.
- Read the child's transcript for tool calls it should not have made. The prose
  summary is a self-report; a child claiming it only read files may have written
  one.
- Spot-check any `likely` or `unverified` finding by opening the cited path
  yourself. Confirm the line is there. A child that invents a plausible file
  path is rare but not imaginary.

### 7. Relay

Keep it short and put the verdict first:

1. **Verdict** — one line.
2. **Findings** — the load-bearing evidence, not a log dump. Keep the
   `known` / `likely` / `unverified` labels; never launder an inference into a fact.
3. **Open questions** — what the child could not resolve.
4. **Next steps** — each phrased as a proposal with its risk, and each ending in
   a yes/no question for the user. Irreversible work (sends, posts, deletes,
   spends, publishes) always gets its own explicit ask.
5. **Guard result** — held, or violated with the paths listed.

### 8. Execution happens here, not in the child

If the user approves a next step, run it in this session with a normal skill or
a direct `terminal` call. Read-only mode is over. Do not re-dispatch an approved
fix to a subagent still under the read-only contract.

## Pitfalls

- **There is no read-only flag.** `delegate_task` takes no toolsets or
  permission parameter. The contract is prose plus the guard. Say that when
  someone asks how it is enforced.
- **The child's `terminal` is the hole, not `write_file`.** Read-only intent dies
  on `hermes cron run` (which delivers to Discord), `sqlite3 db "delete ..."`,
  `git checkout`/`reset`/`clean`, `launchctl kickstart`/`bootout`, `kill`,
  `rm`/`mv`, `>` redirection, `brew`/`pip install`, `docker rm`. The forbidden
  list in the contract has to name the `terminal` verbs, not just the tools.
- **Browser reads can act.** `browser_navigate` is fine for fetching a page.
  Clicking submit, entering credentials, or touching checkout is an action. The
  contract must say fetch-and-read only.
- **A child cannot ask questions.** Every ambiguity becomes a silent assumption.
  Resolve what you can in the context; require the rest to be labeled.
- **Child summaries are self-reports.** "Fixed", "verified", "I ran it" — none of
  it is evidence until you have seen the output. This is the single most common
  failure mode of delegation.
- **Same-second, same-size edits can hide** from an mtime fingerprint. The guard
  hashes every file under 2 MiB, so normal source and config edits are caught;
  edits to large binaries are caught only by size or mtime. Stated as a limit, not
  a promise.
- **The guard skips what it cannot read** — TCC-protected folders, permission
  denials, sockets. It reports skipped directories loudly. A skip is a coverage
  gap, never a pass. Note the asymmetry: if a directory is unreadable at snapshot
  time but readable at check time, its files appear as `created`, so the guard
  errs toward flagging.
- **VCS and cache dirs are excluded** (`.git`, `node_modules`, `__pycache__`, and
  peers). `git status` rewrites `.git/index`'s stat cache on every run, so hashing
  it produced a false violation on an untouched tree. Version-control state is
  still caught, semantically: HEAD sha plus a hash of `git status --porcelain`.
  A dirty `.git` that predates the snapshot will therefore not flag — snapshot a
  repo only when it is clean, or diff `git status` yourself.
- **Large binaries are compared by size and mtime only** (files >= 2 MiB).
- **Do not keep working while the child runs.** Background results land between
  turns; polling burns context and the user sees nothing.
- **One question per child.** A broad question produces a broad, shallow report.

## Verification

```bash
python3 ~/.hermes/skills/research/read-only/scripts/guard.py \
  check /path/to/scope --out /tmp/ro-before.json
```

Exit 0 and `READ-ONLY HELD` means nothing under the scope was created, modified,
deleted, renamed, or resized. Exit 1 lists the offending paths — that is the
finding, and it goes in the first clause of your report.

Then confirm the audit half: the child's transcript shows no tool call from the
forbidden list, and each `likely` / `unverified` finding resolves when you open
the path it cites. Both halves, or you have not verified the run.
