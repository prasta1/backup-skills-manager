# Check battery — copy/paste reference

Grouped by subsystem. All read-only.

## Gateway

```bash
launchctl list | grep -iE "hermes|llama"
ps -eo pid,lstart,etime,command | grep -E "hermes.*(gateway|serve)" | grep -v grep
cat ~/.hermes/state/gateway.heartbeat ~/.hermes/state/gateway.lifecycle.json
cat ~/.hermes/gateway_state.json    # platforms.*.state, needs_attention, exit_reason
tail -40 ~/.hermes/logs/gateway.error.log
grep -E "ERROR|CRITICAL" ~/.hermes/logs/errors.log | tail -20
```

## llama-swap / local inference

```bash
curl -s 127.0.0.1:9292/v1/models | jq -r '.data[] | "\(.id)\t\(.status.value)"'
curl -s -o /dev/null -w '%{http_code}\n' 127.0.0.1:9292/v1/models
grep -A14 '<model-id>:' ~/.hermes/llama-swap/config.yaml | grep -E "name:|ctx-size"
launchctl print gui/$(id -u)/ai.llama-swap | grep -E "state|runs|last exit"
```

## Cron

```bash
hermes cron list
hermes cron doctor
hermes cron incidents
hermes cron runs <job_id>
hermes cron status
sqlite3 ~/.hermes/cron/executions.db \
  "select substr(started_at,1,19), job_id, status, substr(coalesce(error,''),1,70)
   from executions order by started_at desc limit 20;"
```

## MCP

```bash
hermes mcp list
hermes mcp test <name>              # want: Auth ok / Connected / Tools discovered
grep "failed initial connection" ~/.hermes/logs/errors.log | tail -5
grep -E "registered [0-9]+ tool" ~/.hermes/logs/agent.log | tail -5
ls -la ~/.hermes/mcp-tokens/
```

## Watchdogs

```bash
ls -la ~/.hermes/state/ | grep -E "_fails|ack|outcomes"
~/.hermes/scripts/watchdog_outcomes.sh; echo "exit=$?"
bash ~/.hermes/scripts/<watchdog>.sh; echo "exit=$?"   # 0 = silent = healthy
```

## Hosts / tailnet

```bash
tailscale status
last -5                                   # crash session end + next console login
ssh macbookpro 'launchctl print gui/501/ai.llama-swap | grep -E "state|runs|last exit"'
ssh macbookpro 'fdesetup status; sudo -n true 2>&1'
ping -c2 100.68.81.83; ping -c2 100.89.133.43
```

## Ports / services

```bash
~/.hermes/scripts/port-inventory.sh
lsof -nP -iTCP -sTCP:LISTEN | grep -E "9292|1234|8765|8642|8999|5432"
pg_isready -h 127.0.0.1 2>&1
```

## Aux / model resolution

```bash
hermes config get auxiliary
hermes config get providers.llama-swap.context_length
cd ~/.hermes/hermes-agent && HERMES_HOME=~/.hermes ./venv/bin/python -c \
  "from agent.model_metadata import MINIMUM_CONTEXT_LENGTH as M; print(M)"
```
