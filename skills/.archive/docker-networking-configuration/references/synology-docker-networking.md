# Synology NAS Docker Networking Guide

## Overview

Synology NAS devices run native Docker instead of Docker Desktop, which affects how containerized services communicate with host machines. The key difference is that `host.docker.internal` (which works in Docker Desktop) does not resolve to the host machine on Synology.

## Network Topology

### Tailscale Setup
- **Mac Studio**: 100.89.133.43 (Tailscale IP)
- **Synology NAS**: 100.102.22.38 (Tailscale IP) 
- **Network**: taile85139.ts.net tailnet

### Docker Container Networking
When running Docker containers on Synology NAS:
- Containers can access host services via `100.89.133.43` (Mac Studio's Tailscale IP)
- Containers cannot use `host.docker.internal` as it resolves to nothing
- All services must use explicit IP addresses or Tailscale hostnames

## Common Issues

### 1. Stalled Honcho Deriver
**Problem**: Queue shows 396 total work units, 264 done, 0 in-progress, 132 pending
**Root Cause**: Deriver worker cannot reach LM Studio at `http://host.docker.internal:1234/v1`
**Fix**: Replace with `http://100.89.133.43:1234/v1` or `http://studio.taile85139.ts.net:1234/v1`

### 2. Vector Store SIGILL on Celeron
**Problem**: `lancedb` causes SIGILL errors on Synology's Celeron processor
**Fix**: Change `VECTOR_STORE_TYPE=pgvector` in `.env`

## Configuration Pattern

### Before (Broken on Synology)
```bash
# In .env file
DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=http://host.docker.internal:1234/v1
EMBEDDING_MODEL_CONFIG__OVERRIDES__BASE_URL=http://host.docker.internal:1234/v1
VECTOR_STORE_TYPE=lancedb  # Causes SIGILL on Celeron
```

### After (Fixed for Synology)
```bash
# In .env file  
DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=http://100.89.133.43:1234/v1
EMBEDDING_MODEL_CONFIG__OVERRIDES__BASE_URL=http://100.89.133.43:1234/v1
VECTOR_STORE_TYPE=pgvector  # Compatible with Celeron
```

## Verification Commands

### Check Docker connectivity from NAS to Mac Studio:
```bash
# From Synology NAS (tanker)
ping -c 3 100.89.133.43

# Test LM Studio endpoint
curl -s http://100.89.133.43:1234/v1/models | head -5

# Check queue status
curl -s http://tanker.local:8000/v3/workspaces/hermes/queue/status
```

### Check service status:
```bash
# From Synology NAS (tanker)
docker ps | grep -E "(api|deriver)"

# Check for errors in logs
docker logs api_1 2>&1 | tail -20
```

## Troubleshooting Steps

1. **Verify network connectivity** between NAS and Mac Studio
2. **Check all model endpoint URLs** in `.env` files for `host.docker.internal`
3. **Test each endpoint individually** with curl
4. **Restart Docker containers** after configuration changes
5. **Monitor queue status** to ensure backlog is consumed

## Best Practices

1. **Use explicit IP addresses** instead of `host.docker.internal` in production
2. **Document network topology** for distributed services
3. **Test all endpoints** before deploying to production
4. **Monitor queue status** for evidence of stalled processing