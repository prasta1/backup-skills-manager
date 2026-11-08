---
name: system-config-and-asset-management
description: Standardize asset names and update paths.
---
# System Configuration and Asset Management

This skill standardizes asset names and updates referencing configurations, prioritizing minimal, outcome-focused execution.

## ⚙️ Standing Principles (User Preference)
1.  **Action-First & Direct:** Deliver the final state change (e.g., "Renamed X to Y.") and outcome. Avoid overly verbose diagnostic narratives.
2.  **Integrity First:** Any filesystem change affecting a running service (e.g., `llama-swap`) MUST be followed by a service verification step (hot-reload or health check) to ensure the change was valid.
3.  **Minimal Scope:** Only perform the change strictly necessary to meet the convention; do not initiate broad, unnecessary system audits.

## 🛠️ Procedure: Asset Cleanup
1.  **Audit Convention:** Examine the asset's current name against its source (e.g., HF repo name, internal standard).
2.  **Determine Required Change:** Decide if the change is a necessary convention correction or a subjective preference.
3.  **Execute Change:** Perform the rename or move using `terminal` or `patch`.
4.  **Update References:** Locate and update all configuration files (e.g., `config.yaml`) referencing the old path.
5.  **Verify Live Service:** Trigger service hot-reloading/checks to confirm the service is correctly referencing the new path.

## ⚠️ Pitfalls and Rules
*   **The Conventional Trap:** Do not force a standardized name if the current name is the established convention from the source. Verification against the source is mandatory before renaming.
*   **Service Dependency Failure:** Filesystem changes to running services *must* be validated. Silent service degradation is a high-cost failure.
