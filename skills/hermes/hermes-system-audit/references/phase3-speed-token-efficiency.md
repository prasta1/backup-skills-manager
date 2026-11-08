# Phase 3 — Speed, Reasoning, and Token Efficiency

Source: Patrick's pasted master prompt (2026-10-13). "Use this to improve how Hermes performs
tasks, not simply how much disk space it uses." Verbatim:

> "Act as an AI inference efficiency engineer and autonomous agent performance evaluator.
>
> Analyze your current task execution workflows to determine how you can deliver more accurate results, faster, with fewer unnecessary tokens and tool calls.
>
> Audit your model configuration, context construction, reasoning settings, compression behavior, memory retrieval, tool selection, and fallback strategies.
>
> Investigate unnecessary repeated reasoning, oversized prompts, duplicated tool schemas, excessive session history, failed tool retries, and operations that could be safely combined.
>
> Design a representative benchmark consisting of simple questions, multistep reasoning, research, coding, troubleshooting, and tool-use tasks appropriate to my environment.
>
> Record baseline performance for each task, including latency, token usage, tool calls, completion quality, and errors where measurable.
>
> Find optimizations that preserve or improve accuracy while reducing cost and execution time.
>
> Do not automatically switch models or disable valuable functionality merely to make benchmarks look better.
>
> Propose the highest-impact improvements first, test approved changes against the original benchmark, and report actual before-and-after results.
>
> Your primary objective is to maximize successful task completion per unit of time and computational cost without compromising safety, accuracy, or reliability."

## Local execution notes

- Baseline measurement is mandatory before any change; a parsed config is not a working
  provider — prove model/fallback changes end to end (`hermes chat -q` probes), per
  `hermes-infrastructure`.
- Benchmark tasks should reflect real Studio work: morning briefs, email triage, Linear/
  Notion ops, llama-swap model calls, cron/automation runs.
