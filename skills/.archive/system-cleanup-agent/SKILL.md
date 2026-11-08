---
name: system-cleanup-agent
description: Use when retiring a deprecated Hermes component.
version: 1.0.0
author: Ionga (Hermes Agent)
license: Proprietary
when_to_use: Use when removing or deprecating a core system component or service from the Hermes stack to ensure clean state and prevent stale capabilities, code references, or runtime failures.
---
# System Cleanup Agent
This procedure outlines the high-integrity, multi-phase process for removing dead or deprecated infrastructure components to ensure they do not resurface as stale capabilities, code references, or runtime failures.

## Phase 1: Discovery (Read-Only Audit)
Before making any changes, locate *all* traces of the component across the system to ensure nothing is missed.
1. **Search File System:** Use `search_files(pattern='component_name', target='files')` to find all related files. Use `terminal(command='grep -ril component_name /path/to/search')` to locate references within contents.
2. **Check Core Config:** Review primary configuration files to see if the component is listed as active.
3. **Check Runtime Artifact Locations:** Inspect expected deployment and state directories (e.g., `launchd` plists, `docker-compose.yml`, protected folders).
4. **Verify Tooling:** Check the active skill list and installed MCP services (`skills_list`) to confirm if the component is still a registered tool.

## Phase 2: Identifying Mechanisms and Dependencies
Determine the exact mechanism by which the component is invoked or listed.
*   **The Listing Mechanism:** Identify if the component is discovered via a directory scan (e.g., a `plugins/` folder) or explicitly listed in a configuration file.
*   **The Dependency Check (Pitfall):** Before proceeding, check for external dependencies related to the component. A test suite failure may be a pre-existing dependency issue, not the component itself. Run isolated tests against the component's service to verify its current state *before* removal.

## Phase 3: Remediation (Surgical Edits)
Once all traces are known, proceed with staged removal.
1. **State Change Preparation:** Run `git status` to capture the exact scope of the change.
2. **Core Removal:** Delete the primary directory/package (`rm -rf plugins/component_name`).
3. **Code and Configuration Patching:**
    *   **Configuration:** Patch all known config files to remove the entry.
    *   **Dead Code:** Search for and surgically patch the codebase to remove dead function bodies, class definitions, and API surface area. Use `patch` for targeted replacement of function definitions or class usages.
    *   **Documentation/Metadata:** Remove references from CLI help text and service tables.
4. **Stub Replacement (If needed):** If the component was replaced by a functional stub, ensure the stub's API contract precisely matches the original component's contract. **Pitfall:** Stubs are often built with internal assumptions that differ from the real interface. Always verify the original provider's API using `git show HEAD:original_file` to check method names and argument signatures.
5. **Test Fixes:** Address test failures. If a test fails due to the removal, do not guess the fix. Analyze the test's assertion. If the test relies on the component, rewrite the test to assert against the *interface* or a minimal local stub.

## Phase 4: Verification and Finalization
1. **Run Verification Tests:** Execute the full test suite (`pytest`) to confirm no regressions were introduced. Isolate errors before assuming the change caused them.
2. **Final State Check:** Run discovery scripts to ensure no stray artifacts remain.
3. **Commit:** Once the test suite is green, commit all changes.

## Pitfalls to Avoid
*   **The Deletion Fallacy:** Never assume a directory delete is enough. Configuration and import paths must be purged.
*   **The Test Illusion:** A failing test suite is a failure of the *setup*, not necessarily the *change*. Is the test itself brittle? Is the environment broken?
*   **API Contract Drift:** When replacing a dead component, verify the stub's interface against the original provider's API contract.
*   **Unresolved Failures:** Do not capture an unresolved failure as a workflow. If a complex sequence leads to a failure, document only the working alternative.