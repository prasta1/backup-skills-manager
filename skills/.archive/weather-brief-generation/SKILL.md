---
name: weather-brief-generation
description: Use when generating the daily weather brief for Hermes.
---
# Weather Brief Generation Procedure

This skill dictates the correct workflow and pitfalls for retrieving and formatting daily weather data for the Hermes brief.

## Procedure:
1.  **Constraint Check:** Before starting, verify the necessary environment variables (e.g., `OPENWEATHER_API_KEY`) are correctly set in `~/.hermes/.env`.
2.  **API Selection (Pitfall Guard):**
    *   **Do not use One Call API 3.0** unless billing is explicitly activated.
    *   **Use OpenWeather API 2.5 ("Current Weather"):** This endpoint is stable, widely documented, and does not require a paid subscription to function.
    *   The script for this is located at `scripts/weather-brief.py`.
3.  **Execution:** Run the deterministic script:
    `python3 scripts/weather-brief.py`
4.  **Result Handling:**
    *   If the script outputs the expected formatted weather block, integrate it directly into the brief.
    *   If the script outputs **"WEATHER SOURCE UNAVAILABLE"**, report that the weather outlook is unavailable and proceed with the brief. Never invent a forecast.
5.  **Error Recovery (Pydantic):** If the script fails due to environment errors (e.g., `pydantic_core` not found), force a dependency re-install for the cron environment before retrying the run.

## Pitfalls & Lessons:
*   **API Lock:** Choosing a weather API version (e.g., 3.0) without confirming a paid subscription will result in a 401 Unauthorized error, halting the brief.
*   **Connectivity:** The Studio's transient network stalls can cause timeouts even with key-based APIs; the current script incorporates 20s timeout and retry logic for resilience.
*   **Graceful Degradation:** A missing weather source is a hard failure of the data, not a failure of the brief; the brief must report the absence of data rather than guessing.

## Verified implementation details (2026-09-28)

`scripts/weather-brief.py` calls the **OpenWeather 2.5 "Current Weather"** endpoint, not One Call
3.0, which returns 401 without an activated billing plan. It wraps the call in **3 attempts with
exponential backoff** and a **20 s timeout**.

The Studio has a **known susceptibility to transient network stalls** against external weather APIs
(`api.open-meteo.com` and peers). These present as connection timeouts, not HTTP errors, and they are
intermittent: the same call often succeeds on retry. Design every fetch path with retries *before*
reporting failure, and never treat a single timeout as "the source is down."

**Do not add a second API key to chase this.** The operational standard for external data sources is
zero-auth sources wherever they are usable: simpler, one fewer secret, and one fewer thing to rotate.
Accept lower robustness in exchange and handle it with retries rather than authentication.