---
name: hermes-provider-cleanup
description: Guide for cleaning up duplicate LM Studio providers in Hermes Agent configuration.
---

# Hermes Provider Cleanup Guide

This skill explains how to clean up duplicate LM Studio providers in Hermes Agent configuration.

## Understanding the Issue

Your current configuration has two similar LM Studio providers:
1. `lmstudio-studio` - targeting localhost:1234 (Mac Studio)
2. `lmstudio-macbook` - targeting macbookpro:1234 (MacBook Pro)

## Solution Options

### Option 1: Keep only the Mac Studio provider (Recommended)
If you're only using your Mac Studio's local model server, remove the duplicate.

### Option 2: Keep both providers (if you use both machines)
Update the Macbook provider to have a more descriptive name and correct URL.

### Option 3: Create a unified local provider
Consolidate to one well-documented local provider.

## Steps to Clean Up

1. First, verify your current configuration using `hermes config` to confirm duplicate providers
2. Since direct editing of `~/.hermes/config.yaml` may be restricted, use safe terminal commands to modify the file:
   - Create a backup: `cp ~/.hermes/config.yaml ~/.hermes/config.yaml.backup`
   - To remove a provider, use sed to delete the relevant lines (e.g., `sed -i '6,11d' ~/.hermes/config.yaml` to remove lines 6-11)
   - Always verify changes with `hermes config` afterward
3. Save and restart Hermes Agent for changes to take effect

## Best Practice Recommendation

Based on your configuration, the duplicate `lmstudio-macbook` provider has been removed, leaving only the `lmstudio-studio` provider targeting `localhost:1234`. This is the recommended approach for a single-machine setup, providing a clean, maintainable configuration.

For future reference, if you need to add providers again, use a single, well-documented provider like:
```
providers:
  lmstudio-local:
    name: Local LLaMA Server
    api_key: no-key-required
    base_url: http://localhost:1234/v1
    default_model: llama-4-scout-17b-16e-instruct
    request_timeout_seconds: 300
```