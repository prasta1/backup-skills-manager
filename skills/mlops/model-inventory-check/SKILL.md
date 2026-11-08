---
name: model-inventory-check
description: Use when auditing models across a multi-machine AI stack.
---
# Model Inventory Check Procedure

This procedure is used to systematically check for model existence, state, and serving configuration across the local model repositories (Studio and MacBook Pro).

## 1. Check Primary Inference Host (Studio)
The Studio is the canonical inference host. Verification must confirm not just disk presence, but service availability.

1.  **Verify Serving Registration:** Inspect the `llama-swap` configuration on the Studio for the desired model ID.
    *   **Command:** `grep -i "<model_id>" ~/.hermes/llama-swap/config.yaml`
    *   **Goal:** Confirm the model is explicitly listed in the configuration (e.g., `mb-model-id`).
2.  **Verify Disk Integrity:** Check the local model paths on the Studio.
    *   **Command:** `ls -la /Users/macstudio/Models/`
    *   **Goal:** Ensure the GGUF files and associated structure exist outside of cache/stub directories.

## 2. Check Auxiliary/Development Host (MacBook Pro)
The MacBook Pro may hold development versions or local clones.

1.  **Search Local Repos:** Scan the expected developer model directory.
    *   **Command:** `ssh -o ConnectTimeout=8 macbook 'ls -la /Users/prasta/Models/gguf/unsloth/'`
    *   **Goal:** Confirm weights are present.
2.  **Verify Service Integration:** If the model is intended for the fleet, verify it is registered in the MacBook's serving environment.
    *   **Command:** `ssh -o ConnectTimeout=8 macbook 'grep -i "<model_id>" ~/.hermes/llama-swap/config.yaml'`
    *   **Goal:** Confirm the model is serving (Note: The MBP is primarily for dev/local inference).

## 3. Analyze Model Variants (Quant & MTP)
Models often come in variants that are physically different even if they share a base quantization.

*   **Q/Q-Family Quants:** Different suffixes (e.g., `Q4_K_S` vs `Q4_K_M` vs `Q8_0`) represent different bit-depth and performance profiles.
*   **MTP Variant:** The Model Training Parameter (MTP) variant, when present, contains extra tensors (the MTP head) and will result in a significantly larger file size than the non-MTP version, even if the base quant is identical.

## Pitfalls
*   **Cache Stubs vs. Live Models (Pitfall):** Finding a model's path in a HuggingFace cache (e.g., `~/.hf/hub/...`) does not mean the model is available or functional. These are often just commit pointers or partial downloads. *Mechanism: The cache does not track service registration or completeness, so it is not a functional weight.*
*   **Unregistered Weights (Pitfall):** Having a fully downloaded GGUF file on a local drive is insufficient if it is not explicitly defined in the `llama-swap` configuration. *Mechanism: The inference engine only routes requests for models explicitly declared in the service registry.*
*   **MTP Head Tensor Size (Pitfall):** The MTP variant is larger due to extra head tensors. *Mechanism: These tensors are part of the model's functional metadata and are not excluded from file size calculations.*