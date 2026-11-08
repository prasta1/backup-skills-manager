# Memory Pressure in Distributed AI Systems

## Overview

This guide addresses memory pressure issues that can cause OOM (Out-of-Memory) errors in distributed AI systems, particularly when running containerized services like NanoClaw on resource-constrained hosts.

## Root Cause: Container Memory Limits

The `CONTAINER_MEMORY_LIMIT` environment variable controls how much memory a NanoClaw agent container can consume. When set too low (e.g., 4GB default), the system becomes unstable under memory pressure, leading to OOM kills (exit code 137) or system instability.

## Fix Pattern

### Update the .env file:
```bash
# In ~/nanoclaw/.env (not src/config.ts - that's the override path)
CONTAINER_MEMORY_LIMIT=6g
```

### Apply the fix:
```bash
# Restart NanoClaw to pick up new limit
ncl groups restart ag-main
```

## Verification

Check that containers now respect the limit:
```bash
# Verify .env change
grep CONTAINER_MEMORY_LIMIT ~/nanoclaw/.env

# Check that containers are running with new limit
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}" 2>/dev/null | grep -E "(nanoclaw|NAMES)"
```

## Memory Pressure Symptoms

- Containers being killed with OOM (Exit code 137)
- Host system becoming unresponsive or sluggish
- AI services failing to start or respond with timeouts
- Models failing to load due to memory exhaustion

## Best Practices

1. **Proactive Monitoring**: Use `docker stats` to monitor container memory usage
2. **Conservative Limits**: Set limits slightly below actual available host memory to prevent system instability  
3. **Documentation**: Record the rationale for specific container limits in `.env` files
4. **Stability Testing**: Test with different memory limits to find optimal balance between performance and stability

This skill was updated to capture the user's preference for direct, command-line solutions over process descriptions and their explicit stated preference for "brief but complete" answers.