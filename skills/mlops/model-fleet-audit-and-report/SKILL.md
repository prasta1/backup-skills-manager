---
name: model-fleet-audit-and-report
description: Comprehensive LLM fleet audit and HTML report generation.
---

# Model Fleet Audit and Report

Automated process for inventorying, validating, and reporting on the local LLM model fleet (GGUF/llama-swap).

## Procedure
1. **Scan & Identify:**
    * Use `terminal` to find all potential model artifacts and serving paths.
    * Cross-reference paths against `config.yaml` to build the initial roster.
2. **Gather Ground Truth (Audit):**
    * **Crucial:** Do not rely on agent memory. Read all specs live from disk.
    * Extract data: Model ID, Size, Arch, **Trained Max Context Length** (from GGUF metadata), Serving config (`--ctx-size` / `--ctx-pool`, `--parallel` / `--slots`, and `Per request` calculation).
3. **Report Generation:**
    * Use `execute_code` to build a data-driven, self-contained HTML report.
    * Report must include: Findings summary, detailed **Model Specification Table** (with new context columns), and a **Tuning Lever Matrix**.
4. **Verification:**
    * Use `vision_analyze` or `browser_snapshot` on the rendered HTML to confirm correct data alignment and legibility.
5. **Finalize:**
    * Save the HTML report to a canonical scratch path.

## Pitfalls and Lessons
* **Reasoning vs. Content:** If a model shows no content, verify if it is consuming its entire token budget on a `Thinking Process:` preamble. This is often correct behavior.
* **Source of Truth:** GGUF headers and on-disk config files are the ultimate source of truth, overriding agent memory or logs.
* **Context Interpretation:** `Ctx pool` is the total allocated resource; `Per request` is the calculated slice (`Ctx pool / Slots`).
* **Redundancy Check:** Ensure audit findings are unique and grouped where statuses overlap.
* **Dynamic Reporting:** Report logic must be capable of dynamically reflecting discovered schema changes (e.g., new columns) in the generated output.
