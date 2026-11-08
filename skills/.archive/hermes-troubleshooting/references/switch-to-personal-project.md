---
name: switch-to-personal-project
description: Quickly switch the active Hermes project to Personal and optionally sync the terminal cwd.
---

# Switch to Personal Project

Quickly activate the Personal project and optionally sync the terminal cwd.

## Steps
1. Switch desktop sidebar project to Personal:
   ```json
   {
     "project": "Personal"
   }
   ```
2. Optionally sync the terminal shell to the Personal project directory:
   ```bash
   cd /Users/macstudio/.hermes/projects/Personal
   ```
3. Confirm the active project is `personal` before returning control.

## Notes
- Run from any project context. No prior state required.
- If Personal does not exist in `project_list`, report and stop.
- Do not switch to any other project without request.