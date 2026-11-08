---
name: tinyfish-integration
description: "Integrate TinyFish AI for web automation and search tasks."
version: 0.1.0
author: Hermes
platforms: [macos, linux]
metadata.hermes.tags:
  - AI
  - Automation
  - Web
  - Search

---

# TinyFish Integration

This skill helps integrate TinyFish AI for web automation, search, and browser tasks. It does not cover advanced customization or model training.

## When to Use
- Automate web workflows using TinyFish's Agent API
- Fetch clean page content using TinyFish's Fetch API
- Search the web using TinyFish's Search API
- Control a remote browser session using TinyFish's Browser API

## Prerequisites
- TinyFish API key
- Authentication set up via TinyFish's MCP or API keys
- Hermes terminal tool configured

## How to Run
Invoke through the `terminal` tool to set up and run tasks using TinyFish's APIs.

## Quick Reference
- Agent API: `https://agent.tinyfish.ai/v1/automation/...`
- Search API: `GET https://api.search.tinyfish.ai`
- Fetch API: `POST https://api.fetch.tinyfish.ai`
- Browser API: `POST https://api.browser.tinyfish.ai`

## Procedure
1. Set up authentication using TinyFish's API keys or MCP.
2. Use the `terminal` tool to invoke TinyFish's APIs.
3. For web automation, use the Agent API with natural-language goals.
4. For fetching content, use the Fetch API.
5. For browser automation, use the Browser API.

## Pitfalls
- TinyFish's Agent and Browser APIs require credits.
- Ensure you handle authentication securely, especially when using MCP.
- Be aware of rate limits and error codes for debugging.

## Verification
Run a test task using the `terminal` tool and verify the output matches expectations.

---

This skill is designed to integrate TinyFish AI with Hermes for efficient web automation, search, and browser tasks. For more details, refer to the [TinyFish Documentation](https://docs.tinyfish.ai/).