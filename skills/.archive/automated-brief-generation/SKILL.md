---
name: automated-brief-generation
version: 1.0
description: Use when generating daily/weekly status briefs.
---
# automated-brief-generation

**Use when** creating a structured, automated daily or weekly briefing (e.g., morning/evening runs). This skill ensures the brief adheres to Patrick's preference for conciseness and actionable data, and addresses known infrastructural pitfalls in the data sources.

## Procedure
1. **Environment Check:** Verify that all necessary tools and dependencies are correctly installed.
2. **Infrastructure Scan:** Execute the `hermes-agent` infrastructure probes to confirm service health (`gateway`, `llama-swap`, `webui`, etc.).
3. **Data Fetch (Weather):** Attempt to fetch weather data.
    *   **Pitfall: API Instability:** The default Open-Meteo provider is prone to transient network stalls/timeouts, leading to "Outlook unavailable" status.
    *   **Fix:** Use the OpenWeather API (requires `OPENWEATHER_API_KEY` in `.env`) and implement a robust retry loop with exponential backoff (3 attempts total) before reporting the weather source as unavailable.
4. **Data Fetch (Reminders):** Fetch Linear issues using the 30-day filter.
    *   **Format Rule:** The worker script (`linear-stale.py`) must be patched to emit a single markdown-link line per reminder, rather than a multi-line block.
    *   **Example:** `[ID · age · team · title](URL)`
5. **Work Status Generation:** Generate the focus areas list, ensuring the language remains current with Patrick's job search (e.g., "AI/ML infrastructure Account Executive roles"), avoiding older framing.
6. **Output Compilation:** Assemble the brief, ensuring the "Work Priorities" block is preserved accurately.
7. **Execution:** Run the brief script (`hermes cron run <job_id>`).
8. **Verification:** Confirm the output artifact contains successful rendering of all markdown links and the correct weather status (data or "Unavailable").

## Pitfalls & Workarounds
*   **Dependency Corruption:** If a cron job fails with `No module named 'pydantic_core._pydantic_core'`, the worker's python environment is corrupted.
    *   **Fix:** Force a dependency refresh by running `pip install --upgrade pydantic pydantic-core` within the cron worker environment.
*   **Weather Timeout:** Transient connectivity issues are network stalls, not API errors. Treat "Outlook unavailable" as a connectivity failure requiring the retry logic fix.
*   **Code Fixes:** The `linear-stale.py` script is prone to syntax errors (e.g., missing loop headers, incorrect indentation) when patching. Always verify the entire loop block after a `patch` operation.
