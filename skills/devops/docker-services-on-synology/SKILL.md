---
name: docker-services-on-synology
description: Deploy and manage Docker-based services on Synology NAS — setup, file transfer, Container Manager, and service-specific configuration.
trigger: User mentions deploying a service on tanker, Synology, Synology NAS, or Docker on the NAS.
---

# Docker Services on Synology NAS

Pattern for deploying Docker-based services (Immich, n8n, etc.) on a Synology NAS via Container Manager / Docker compose.

> 2026-10-01: examples below point at the Studio's old LM Studio endpoint (`100.89.133.43:1234`). The Studio's inference endpoint is now llama-swap on `:9292` (HTTPS over the tailnet); substitute that when wiring a container to local inference.

## Prerequisites

- SSH access to the Synology (user `prasta` on `tanker.local`)
- Docker is Container Manager package (binary at `/usr/local/bin/docker` on the Synology)
- Docker compose v2 is built into the Synology docker binary (`docker compose`, not `docker-compose`)

## File Transfer from macOS / Linux

When cloning repos on a Mac or transferring code to the Synology:

1. **Clone on the Mac** (faster network, more tools available):
   ```
   git clone --depth 1 <repo-url> /tmp/repo-name
   ```
2. **Transfer via SSH tar pipe** (cleaner than scp):
   ```
   cd /tmp/repo-name && tar czf - . | ssh prasta@tanker.local "cd /target/path && tar xzf -"
   ```
3. **Clean up macOS resource fork files** immediately on the NAS (these cause Python `SyntaxError: source code string cannot contain null bytes`):
   ```
   ssh prasta@tanker.local "cd /target/path && find . -name '._*' -type f -delete && find . -name '@eaDir' -type d -exec rm -rf {} + 2>/dev/null"
   ```
   **Do NOT skip this step** — the `._` files and `@eaDir` directories from macOS SMB get baked into Docker images at build time and corrupt Python source files.

## Docker Compose on Synology

### Syntax Notes (older compose version)

- `env_file` must use **simple string syntax**, not long-form:
  ```yaml
  # ✅ Correct
  env_file: .env
  # ❌ Older env_file syntax not supported
  env_file:
    - path: .env
  ```
- `restart: always` works as expected
- Health checks use the standard syntax

### Service Port Strategy

Synology has a built-in PostgreSQL on port 5432. Docker services that need PostgreSQL should:
- **Not map the host port** — use Docker internal DNS (`postgres:5432` or `database:5432`) for inter-service communication
- The database service in `docker-compose.yml` should only expose the container port, not map it to a host port
- Example: `ports: []` on the database service (or omit the `ports:` block entirely)

### Common Commands

```
/usr/local/bin/docker compose up -d                     # Start all services
/usr/local/bin/docker compose up -d --build <service>   # Rebuild and start one
/usr/local/bin/docker compose down                      # Stop (preserves volumes)
/usr/local/bin/docker compose down -v                   # Stop and delete volumes
/usr/local/bin/docker compose build <service>            # Build without starting
```

### Restarting the Docker Daemon

If Docker daemon crashes (OOM, etc.), restart Container Manager via Synology's package manager:

```
sudo /var/packages/ContainerManager/scripts/start-stop-status restart
# OR
sudo /usr/syno/bin/synopkg restart ContainerManager
```

The daemon can hang (socket exists but `docker ps` hangs). Kill stuck docker client processes first:
```
pkill -f 'docker'
```

## Communication Pattern with User

During long-running infrastructure work (builds, SSH commands, Docker compose operations):

- **Provide a status update after each major operation completes** — don't batch multiple SSH commands silently and only report at the end
- If an operation takes >30 seconds, the user can't tell if you're stuck or still working; send a brief update
- **Lead with what succeeded**, then summarize any issues and the fix
- Keep output terse: a 3-line status table is better than raw logs

## pgvector Embedding Dimension Handling

**Common pattern**: The migration bootstrap creates `Vector(1536)` by default. If your model needs a different dimension (e.g. Qwen3 embeddings at 2560):

1. Start the stack with `EMBEDDING_VECTOR_DIMENSIONS=1536` in `.env` (matches the migration default)
2. Wait for the API to pass health checks
3. Drop HNSW indexes first (separate transaction):
   ```sql
   DROP INDEX IF EXISTS ix_documents_embedding_hnsw;
   DROP INDEX IF EXISTS ix_message_embeddings_embedding_hnsw;
   ```
4. ALTER columns:
   ```sql
   ALTER TABLE public.documents ALTER COLUMN embedding TYPE vector(2560) USING NULL;
   ALTER TABLE public.message_embeddings ALTER COLUMN embedding TYPE vector(2560) USING NULL;
   ```
5. Update `.env` to `EMBEDDING_VECTOR_DIMENSIONS=2560` and restart
6. **Do NOT use the `configure_embeddings.py` script** — it wraps everything in one transaction (LOCK → DROP indexes → ALTER → CREATE indexes). When the HNSW CREATE fails at >2000 dims, the ENTIRE transaction is rolled back, including the ALTER and DROP. The indexes are restored, the columns stay at 1536, and you're back where you started. Always do DROP and ALTER in separate transactions.

**When the vector store is pgvector** (not lancedb), the missing HNSW indexes mean ANN queries fall back to exact nearest-neighbor search, which is slower but functional for development or low-volume deployments.

## lancedb SIGILL on Synology (Intel Celeron CPUs)

**lancedb will NOT work on Synology NAS hardware.** Its native Rust binary (shipped via `pip install lancedb` in the Docker build) is compiled for CPUs with AVX2/AVX512 instruction sets. Synology Celeron/J-series CPUs do not support these. Importing `lancedb` crashes with:

```
Illegal instruction
exit code: 132 (SIGILL)
```

Symptoms: the `import lancedb` hangs or crashes silently during container startup. The FastAPI lifespan function (which probes external vector stores) hangs, the health check fails, and Docker restarts the container in a crash loop.

**Fix**: Set `VECTOR_STORE_TYPE=pgvector` in `.env` instead. The pgvector extension handles vector storage directly in PostgreSQL without native CPU-dependent binaries.

Do not attempt workarounds (compiling from source, using older lancedb versions) — the CPU lacks the required instruction set at the hardware level.

## Tailscale DNS on Synology

Synology's Tailscale installation does NOT support MagicDNS — `.ts.net` hostnames like `studio.taile85139.ts.net` cannot be resolved:

```
curl: (6) Could not resolve host: studio.taile85139.ts.net
```

**Always use the Tailscale direct IP** (e.g. `100.89.133.43`) for inter-service communication from Docker containers on the Synology. This applies to:
- LLM backend URLs in `.env`
- Embedding model `BASE_URL` configs
- Any cross-machine service endpoints

Verify reachability with:
```
curl -s --connect-timeout 5 http://100.89.133.43:1234/v1/models
```

## Docker Health Check Crash Loop

Two common issues cause the API container to enter a crash loop where it keeps restarting as `unhealthy`:

### 1. IPv6 localhost on Synology

On Synology Docker, `localhost` resolves to `::1` (IPv6 loopback), but the server binds `0.0.0.0` (IPv4-only). The health check fails with:
```
OSError: [Errno 99] Cannot assign requested address
```
or, if the server isn't listening yet:
```
OSError: [Errno 111] Connection refused
```

**Fix**: Use `127.0.0.1` explicitly in health check test commands:
```yaml
healthcheck:
  test: ["CMD", "python", "-c",
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]
  interval: 5s
  timeout: 5s
  retries: 5
  start_period: 20s    # Essential for migration-heavy startups
```

### 2. start_period adequacy

Services that run database migrations at startup (Alembic, etc.) need a `start_period` long enough for the migration to complete before the first health check runs. With 10+ migration files, set `start_period: 20s` or higher.

### 3. lancedb SIGILL (see above)

If the container is configured for lancedb on Synology, the crash loop is caused by SIGILL during `import lancedb` in the lifespan. Switch to `VECTOR_STORE_TYPE=pgvector`.

## Scheduled Maintenance

Synology DSM has **no crond/crontab** — the `crontab` binary doesn't exist. Scheduled tasks must run via:

1. **DSM Task Scheduler** (GUI: Control Panel → Task Scheduler) — for Synology-native cron
2. **Hermes cron jobs** (preferred when a linked macOS client is always on) — Hermes cron SSHes into tanker to run commands

### Hermes Cron Pattern for Synology

Create a cron job on the Hermes client (MBP or Studio) that SSHes into tanker:

```bash
hermes cron create \
  --name "tanker Docker maintenance" \
  --schedule "0 5 1 * *" \
  --prompt "Run Docker cleanup on tanker via SSH. SSH to prasta@tanker.local and run:
  /usr/local/bin/docker system prune -a -f --volumes
  /usr/local/bin/docker builder prune -a -f
Report how much space was reclaimed in one line."
```

The key constraints:
- Set `enabled_toolsets: ["terminal"]` to minimise token overhead
- Use `deliver: "local"` (or a gateway platform)
- Limit `repeat` (e.g. 4) for trial runs before making permanent

### Regular Maintenance Tasks

| Task | Schedule | Command |
|------|----------|---------|
| Docker prune | Monthly (1st at 5am) | `docker system prune -a -f --volumes` |
| Database backup | Daily (3am) | `pg_dump \| gzip > backup.sql.gz` |
| Container log check | Quarterly | `docker ps --size` + `du -sh /var/lib/docker/containers` |

### Docker Log Rotation

Without limits, Docker logs grow unbounded on Synology. Configure globally:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Write to `/etc/docker/daemon.json` and restart Docker:
```bash
sudo /var/packages/ContainerManager/scripts/start-stop-status restart
```

This caps each container at 30MB of logs. Existing logs are not trimmed — only new logs after the config change.

## Verification

After deployment, verify:
```
curl http://tanker.local:8000/health    # Should return {"status":"ok"}
docker ps --format '{{.Names}} {{.Status}}'    # All services healthy
```

## References

The `references/` directory contains service-specific deployment recipes and client configuration guides.

> **Honcho: retire complete, do not reintroduce.** That memory provider is not part of this
> stack — it was removed from core, is not installed on this host, and has no config, service
> or process here. This section exists only so a future session does not rediscover it and
> provision something. The 2026-10-02 prune archive (`~/.hermes/_archive/honcho-prune-20261002/`)
> was itself removed; there is nothing left to read.
