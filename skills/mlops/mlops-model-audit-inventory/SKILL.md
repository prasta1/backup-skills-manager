---
name: mlops-model-audit-inventory
description: Audit model fleet config, disk presence, and serving health.
---
## Procedure

1.  **Configuration Audit**: Load and parse `llama-swap/config.yaml` to generate a definitive list of all active `model_id` keys and their expected serving paths.
2.  **Disk Presence Check**: Cross-reference every path from the configuration audit against the local filesystem to ensure all expected GGUF artifacts are present.
3.  **Orphan Identification**: Scan the entire `~/models/gguf` directory for any GGUF artifacts whose absolute paths do not appear in the configuration list.
4.  **Operational Health Check**: Query the `activity.sqlite` database to identify usage patterns for all models.
5.  **Transient Error Analysis**: For models reporting errors, use SQL to extract the time, path, and error message to identify common failure modes.
6.  **Health Verification (The "Invalid" Check)**: For models flagged as potentially invalid or broken, perform a live `curl` request to the `/v1/chat/completions` endpoint with a high-token-budget, substantive query (not a single-word prompt) to verify content generation and measure latency/token throughput (TPS).

## Pitfalls
- **The Reasoning Model Artifact:** If a model is flagged as "invalid" or "broken," do not assume the file is corrupt. High-reasoning models (like MTP/Draft-MTP) often consume their entire token budget on a `Thinking Process` preamble, resulting in zero or near-zero `content` before the response. Test with a query requiring significant generation.
- **Serving Layer Truth:** Rely on the `activity.sqlite` database for usage and operational truth. Configuration files only list potential; the serving layer records what actually runs.
- **Canonical Location:** Always assume the canonical model path is `~/models/gguf/unsloth/` unless explicitly configured otherwise, but verify symlinks against this path to prevent breakage during cache cleanup.

## Workflow Notes
The inventory is a multi-stage process because the source of truth for each piece of the audit differs: `config.yaml` for definition, `ls`/`stat` for disk, and `activity.sqlite` for health/usage.
