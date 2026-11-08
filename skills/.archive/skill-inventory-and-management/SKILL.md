---
name: skill-inventory-and-management
description: Audits, verifies, and manages installed skill status.
---
# Skill Inventory and Management

This skill provides a definitive guide for auditing, verifying, and managing the set of active and bundled skills within the Hermes stack.

## Procedure: Skill Verification and Discovery

When asked to locate or verify the presence of a specific skill (e.g., "Is skill X installed?"), follow this sequence to differentiate between source code, active installation, and archival status:

1.  **Check Active Skills:** Run `hermes skills list`. This returns the set of skills currently recognized and enabled by the active profile.
2.  **Audit Installation Paths:** Examine the primary active skill directory (`~/.hermes/skills/`). Verify that the skill's directory (`category/skill-name/`) exists here and contains an `SKILL.md`.
3.  **Audit Source Code (Bundled Skills):** Search the source checkout (`hermes-agent/skills/`) for the skill's name. This identifies bundled source code, but this **does not** equate to an installed skill.
    *   Command: `grep -rn "skill-name" /Users/macstudio/.hermes/hermes-agent/skills/`.
4.  **Check Archival Status:** Inspect the `.archive/` directory (`~/.hermes/skills/.archive/`). Skills moved here are permanently disabled and should not be expected to function.

## Pitfalls and Rules

*   **Bundled vs. Installed:** Skills present in the `hermes-agent` source checkout are source code only. They are *not* installed skills until they are correctly placed in the active skill directory via the Hermes installation mechanism.
*   **Archiving Procedure:** To decommission a skill or entire category, perform a wholesale directory move rather than deleting the skill file itself. The correct procedure is to move the entire category folder: `git mv skills/category/ to skills/.archive/`. This preserves history and avoids leaving orphaned files in the active paths.
*   **Path Distinction:** Always distinguish between the path to the agent's source tree (`/Users/macstudio/.hermes/hermes-agent`) and the path to the live, running skill installation (`/Users/macstudio/.hermes/skills`). The latter is the ground truth for runtime availability.