# Model Client-State Quirks: Dangling Model Entries
This reference documents a specific state issue where model IDs persist in the client-side desktop application's local storage, despite not being routable on the host server.

## The Problem
A model ID (e.g., `qwopus`) can be added to the client's local model list (persisted in the desktop app's leveldb) even if it was never registered in the `llama-swap` provider configuration. Selecting this non-existent model ID results in a guaranteed HTTP 404 from the proxy because the host service has no router for that specific ID.

## The Mechanism
The client application maintains a persistent cache of models it has interacted with. This cache is independent of the host model configuration. If a model is selected via a direct input or a corrupted state, the client state (LevelDB) will hold the ID, leading to a hard 404 on the server side, as the server only validates against its active configuration.

## Pitfall: Persistent 404s
**Pitfall:** If a model selection results in a 404 error but the model ID is unknown to the agent's logic, check the client's local storage (LevelDB) for lingering entries.
**Why:** The client state maintains a local model registry that is not synchronized with the server's active model configuration.

## Resolution
To resolve the 404, the dangling model ID must be removed from the client-side application's local state (typically by clearing the cache or manually deleting the entry from the app's local database files).

## Relevant Files
*   `llama-swap/config.yaml`: Source of truth for routable models.
*   `Local Storage/leveldb/*`: Location of the client's persistent model cache.
