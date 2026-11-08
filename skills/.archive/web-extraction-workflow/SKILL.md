---
name: web-extraction-workflow
description: Use when interacting with Firecrawl via the Hermes agent.
---
# Firecrawl Workflow & Integration Guide

This guide covers the two primary ways Firecrawl is used within the Hermes ecosystem (Plugin vs. CLI) and outlines critical configuration pitfalls to ensure reliable extraction and data retrieval.

## Procedure: Using Firecrawl
1.  **For Data Extraction/Scraping (Preferred):** Use the `web_extract` tool. This invokes the `web/firecrawl` Python plugin (SDK v4.17.0) which is managed by the Hermes agent. It handles the direct request to scrape a single URL and is the standard, reliable path for structured content.
2.  **For Autonomous Workflows:** Use the `firecrawl-agent` or `firecrawl-cli` skills. These wrap the standalone npm CLI tool, allowing for complex multi-page crawling, data mapping, and automated workflows that go beyond simple extraction.

## Critical Integration Pitfalls

### 1. SDK vs. CLI Disconnect
The web provider plugin (`web/firecrawl`) and the standalone shell skills (`firecrawl-cli`) are **completely independent**. A configuration change (like adding an API key) may affect the plugin but not the CLI, or vice versa. 
*   *Pitfall:* Do not assume a configuration fix for the plugin will automatically fix the CLI skills.

### 2. The Managed Gateway Hijack (Runtime Behavior)
Despite configuration in `~/.hermes/config.yaml:119` indicating a direct backend, the `web_extract` tool often routes through the **Nous Tool Gateway** (`https://firecrawl-gateway.nousresearch.com`). This occurs because the underlying selection logic checks a centralized tool selection store (`read_selection("web")`). 
*   *Pitfall:* If the selection store is empty, the plugin defaults to the managed provider path, bypassing explicit direct API configurations.

### 3. The Environment Variable Trap (CLI Failure)
The `.env` file is susceptible to a critical configuration error where an API key is mistakenly assigned to `FIRECRAWL_API_URL`. 
*   *Pitfall:* This error is fatal for the CLI skills, as they attempt to parse the key string as a URL. The plugin often ignores this error because the managed path (Gateway) short-circuits the request before using the key.
*   *Lesson:* Always verify that `FIRECRAWL_API_URL` is a valid, full HTTP/HTTPS endpoint and is not merely a credential.

## Recommended Fix
If using the direct cloud API, remove the `FIRECRAWL_API_URL` entry from `.env`. Let the SDK fall back to `https://api.firecrawl.dev` while relying on the `FIRECRAWL_API_KEY`. This simplifies configuration and prevents the CLI skills from failing.
