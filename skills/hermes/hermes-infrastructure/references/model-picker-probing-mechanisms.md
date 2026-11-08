# Model Picker Probing Mechanism

When the Hermes desktop application renders the model selection list, it does not read from a static list. Instead, it performs a live discovery process that can interact with and potentially modify the system's configuration.

## Core Workflow
1. **Context Loading:** The process first loads the current configuration via `load_picker_context()`.
2. **Discovery Payload Generation:** It calls `build_model_options_payload()`. When configured to `refresh=True`, this function triggers discovery across all managed and custom providers.
3. **Live Probing:** Each provider is actively probed (e.g., making calls to `http://127.0.0.1:9292/v1/models` for `llamaswap-ms`).
4. **Persistence:** **Pitfall:** A successful discovery payload is persisted back into the central `config.yaml` file via the `_save_discovered_models_to_config` method.
5. **Caching:** The resulting payload is then used to render the UI elements.

## Pitfalls to Avoid
*   **Discovery Persistence:** Always assume a fresh probe with `refresh=True` might *write* to `config.yaml`. If you are only running diagnostics, intercept/neutralize the `save_config` function to prevent accidental config modification.
*   **Stale Process Cache:** The most common error is a long-lived desktop agent process holding a memory snapshot of the provider catalog from before a model deletion. This state is isolated to the running process and is independent of the disk-written configuration. The only guaranteed fix is to restart the desktop process.
*   **Non-Blocking vs. Refresh:** Standard open probes (`refresh=False`) only warm up missing models in the background to avoid UI degradation; full `refresh=True` is required to clear stale or verify missing items aggressively.
