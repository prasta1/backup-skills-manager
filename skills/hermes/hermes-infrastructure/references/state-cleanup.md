# State Cleanup and Verification Procedure

This document details the correct, non-destructive workflow for auditing and resolving inert, nested runtime state within the Hermes environment. Nested state typically manifests as directories like `~/.hermes/.hermes/`, which are inert artifacts of improper environment configuration (e.g., setting `HERMES_HOME` too deeply).

## 1. Audit and Identify Scope
Before any removal, you must determine the full scope of the artifact and ensure it is not the primary, active state.

1.  **Identify Scope:** Start by listing the contents of the main state directory using `find -L` to follow symlinks and identify all subdirectories and files recursively. This confirms the extent of the pollution.
2.  **Check Tracking:** Run `git -C ~/.hermes ls-files .hermes` to verify if the artifact is being tracked by the outer repository. If it is, the artifact is part of the version history and should only be deleted if the entire branch/state is obsolete.
3.  **Determine Existence:** Use `ls -la /path/to/suspected/artifact` to confirm its actual existence on the file system.

## 2. Resolution
If the artifact is confirmed inert (i.e., it is not the active state and is not critical to the repo history):

1.  **Resolution:** Use `rm -r /path/to/artifact` to remove the state.
2.  **Verification:** Immediately run `git status` to ensure the deletion does not interfere with current tracked files.
3.  **Confirmation:** Run `hermes gateway list` to confirm that the main gateway is functioning correctly with the corrected state.

**Pitfall:** Deleting state without first checking tracking or identifying the correct artifact path can lead to data loss or breaking an existing deployment. Always use `find -L` to follow symlinks and verify the inert status before `rm -r`.