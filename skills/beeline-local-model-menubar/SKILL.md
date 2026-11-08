---
name: beeline-local-model-menubar
description: Use when building or debugging the Beeline menubar model monitor for the MacBook/Mac Studio local LLM fleet (llama-swap, LM Studio, tailnet, SSH loopback, activity.sqlite).
metadata:
  type: project
---

Beeline is a SwiftUI `MenuBarExtra` app in `~/Projects/apps/active/ios-macos/beeline`
(on the MacBook Pro). It monitors llama-swap and LM Studio on both the MacBook and
the headless Mac Studio, reads throughput from each machine's `activity.sqlite`,
and can load/unload models from the menu. Built on the MacBook, not the Studio —
`~/beeline-dev` on the Studio is a scratch mirror, rsynced across.

Non-obvious facts about this fleet, each learned by hitting it:

- The Studio's `~/.ssh/config` maps `studio.taile85139.ts.net` to the **MacBook's**
  address (100.68.81.83), so SSH from the Studio to "itself" lands on the wrong
  machine. Address the Studio as `macstudio@studio.taile85139.ts.net`.
- The Studio's llama-swap serves **HTTPS only** on the tailnet; plain HTTP returns
  400. Loopback accepts either.
- Studio LM Studio (`:1234`) and MacBook LM Studio (`:41343`, not 1234) bind
  loopback only and must be reached over SSH.
- llama-swap writes **`-1`** into `tokens_per_second`/`prompt_per_second` for
  requests with no measurable generation rate — every embedding request. Filtering
  those out silently erases all embedding activity.
- LM Studio 0.4.x: `load` takes `{"model": key}`, `unload` takes
  `{"instance_id": id}` — different parameters, both on `/api/v1/models/*`.
  It also answers HTTP 200 with an embedded `error` object.
- `/v1/models` has no residency info and its `status` field is an **object**;
  `/running` is the residency source of truth.

Verify with `swift run beeline-report` (add `BEELINE_THROUGHPUT_WINDOW_HOURS=24`
for an idle machine) and `BEELINE_LOG=/tmp/beeline.log open dist/Beeline.app`.
See [[studio-headless-no-ssh-self-alias]].