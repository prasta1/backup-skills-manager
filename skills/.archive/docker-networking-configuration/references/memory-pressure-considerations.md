# Memory Pressure Considerations in Distributed AI Systems

## Overview

In distributed AI systems where containers are deployed on resource-constrained hosts (e.g., Synology NAS), memory pressure can cause instability. This guide outlines how to handle memory constraints that may manifest as OOM errors or system instability.

## Memory Limit Configuration

### NanoClaw Container Memory Limits

The `CONTAINER_MEMORY_LIMIT` environment variable controls the maximum memory a NanoClaw agent container can consume. The default (4GB) may be insufficient for AI workloads under pressure.

### Example Fix:
```bash
# In .env file (not src/config.ts - that's the override path)
CONTAINER_MEMORY_LIMIT=6g
```

### Verification:
```bash
# Check that containers respect the limit
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Memory}}" | grep nanoclaw
```

## Memory Pressure Symptoms

- Containers being killed with OOM (Exit code 137)
- Host system becoming unresponsive or sluggish
- AI services failing to start or respond with timeouts
- Models failing to load due to memory exhaustion

## Memory Optimization Strategies

### 1. Adjust Container Limits
```bash
# Increase limit to prevent OOM
CONTAINER_MEMORY_LIMIT=6g
```

### 2. Model Management in LM Studio
- Keep only necessary models loaded in LM Studio to reduce baseline memory usage
- Use `lms ps` to view current model residency and TTLs
- Consider unloading models that aren't actively needed (if no sessions depend on them)

### 3. Host Resource Monitoring
```bash
# Monitor system memory usage
free -h

# Check Docker container resource consumption
docker stats --no-stream | grep nanoclaw
```

## Troubleshooting Memory Issues

### When containers OOM:
1. Check if `CONTAINER_MEMORY_LIMIT` in `.env` is set appropriately
2. Verify containers actually respect the limit (not being overridden by Docker Compose)
3. Consider reducing memory pressure from host services or other containers

### When host memory is tight:
1. Evaluate if other processes on the host are consuming excessive memory
2. Consider restarting NanoClaw containers to clear any accumulated state
3. Review Docker daemon configuration for memory limits on the host

## Best Practices

1. **Proactive Monitoring**: Use `docker stats` to monitor container memory usage
2. **Conservative Limits**: Set limits slightly below actual available host memory to prevent system instability  
3. **Documentation**: Record the rationale for specific container limits in `.env` files
4. **Stability Testing**: Test with different memory limits to find optimal balance between performance and stability