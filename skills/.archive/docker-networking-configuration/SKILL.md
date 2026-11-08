---
name: docker-networking-configuration
description: Docker networking configuration patterns for distributed AI systems, particularly Honcho and LM Studio setups on Synology NAS
version: 0.1.0
author: Wren (Hermes Agent)
license: MIT
tags: [docker, networking, synology, lmstudio]
---

# Docker Networking Configuration for Distributed AI Systems

## Overview

This skill covers Docker networking patterns that are crucial when deploying distributed AI systems like Honcho on Synology NAS with LM Studio running on Mac Studio. The key issue is that `host.docker.internal` only resolves correctly in Docker Desktop environments (macOS/Windows) but not on Linux-based Docker hosts like Synology NAS.

## Root Cause: `host.docker.internal` Resolution

**Problem**: In `.env` files, Docker services reference `http://host.docker.internal:1234/v1` for LM Studio models. This works on Docker Desktop but fails on native Docker (e.g., Synology NAS).

**Evidence**: When running Honcho server in Docker on Synology, the deriver worker fails to connect to LM Studio because `host.docker.internal` resolves to nothing on the NAS network.

**Solution**: Replace `host.docker.internal` with actual network addresses:
- Tailscale IP: `100.89.133.43` (Mac Studio Tailscale address)
- Tailscale hostname: `studio.taile85139.ts.net` (Mac Studio Tailscale FQDN)
- Local IP: `100.89.133.43` (as seen in Tailscale logs)

## Common Affected Configuration

In `.env` files, these endpoints fail on Synology:
```
DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=http://host.docker.internal:1234/v1
SUMMARY_MODEL_CONFIG__OVERRIDES__BASE_URL=http://host.docker.internal:1234/v1
EMBEDDING_MODEL_CONFIG__OVERRIDES__BASE_URL=http://host.docker.internal:1234/v1
DIALECTIC_LEVELS__minimal__MODEL_CONFIG__OVERRIDES__BASE_URL=http://host.docker.internal:1234/v1
```

## Fix Patterns

### Replace `host.docker.internal` with Tailscale addresses:

**Option 1 - IP Address:**
```
DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=http://100.89.133.43:1234/v1
```

**Option 2 - FQDN (recommended for clarity):**
```
DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=http://studio.taile85139.ts.net:1234/v1
```

## Verification Steps

1. **Verify network connectivity from NAS to Mac Studio:**
   ```bash
   # From Synology NAS (tanker)
   ping -c 3 100.89.133.43
   ```

2. **Test endpoint accessibility:**
   ```bash
   # From Synology NAS (tanker)
   curl -s http://100.89.133.43:1234/v1/models | head -5
   ```

## Pitfalls and Workarounds

### Pitfall 1: Stale Docker Compose Configuration
The `docker-compose.yml` often uses `host.docker.internal` for all services, but these are only valid in Docker Desktop environments.

### Pitfall 2: Vector Store Compatibility Issues
Synology NAS with Celeron processors experience SIGILL errors with lancedb. Alternative vector stores (like pgvector) must be used.

### Solution: Environment-specific Configuration
Create environment-specific overrides in `.env`:
```
# For Synology NAS deployment - fix host.docker.internal
DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=http://100.89.133.43:1234/v1
EMBEDDING_MODEL_CONFIG__OVERRIDES__BASE_URL=http://100.89.133.43:1234/v1
DIALECTIC_LEVELS__minimal__MODEL_CONFIG__OVERRIDES__BASE_URL=http://100.89.133.43:1234/v1

# Fix vector store for Celeron (SIGILL)
VECTOR_STORE_TYPE=pgvector
```

## Recommended Approach

1. **Create a deployment-specific `.env`** for Synology NAS:
   ```bash
   cp .env.template .env.synology
   ```

2. **Update Docker Compose to use environment-specific config**:
   - Mount the correct `.env` file in the Docker containers
   - Ensure all services use the same network address

3. **Verify after restart**:
   ```bash
   # Restart the Honcho services
   docker compose down && docker compose up -d
   
   # Check queue status for backlog completion
   curl -s http://tanker.local:8000/v3/workspaces/hermes/queue/status
   ```

## Troubleshooting Checklist

- [ ] `host.docker.internal` entries in `.env` are replaced with actual IPs or hostnames
- [ ] Docker containers can reach the model server (LM Studio) on Tailscale network  
- [ ] Vector store compatibility verified (no SIGILL on Celeron)
- [ ] Queue status shows progress instead of stalled sessions
- [ ] Deriver worker processes messages successfully

## Memory Pressure Considerations

In distributed AI systems where containers are deployed on resource-constrained hosts (e.g., Synology NAS), memory pressure can cause instability. When running LM Studio models in containers with tight limits, consider:

1. **Container Memory Limits**: Configure appropriate limits to prevent OOM kills (e.g., `CONTAINER_MEMORY_LIMIT=6g` in NanoClaw .env)
2. **Model Caching Behavior**: Some models cache embeddings or intermediate states in memory that can cause bloat under pressure
3. **Host Resource Monitoring**: Use `docker stats` to monitor actual container memory usage vs limits to detect when limits are too tight

This skill now includes a note about memory pressure in relation to Docker container deployment patterns.

## Related Skills

- `hermes-configuration` - General Hermes configuration patterns
- `mlops-llm-workflows` - MLOps workflows with Docker deployment
- `hermes-agent-troubleshooting` - Tailscale and remote connectivity issues

## References

- `references/synology-docker-networking.md` - Detailed Synology NAS networking guide
- `references/memory-pressure-considerations.md` - Memory pressure handling in distributed AI systems