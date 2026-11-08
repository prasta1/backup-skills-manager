# Authoring a llama-swap model entry

Applies when adding or editing a model block in `~/.hermes/llama-swap/config.yaml`
(Studio `:9292`, MacBook `:8999`). llama-swap hot-reloads the file (`--watch-config`), so an
edit applies with no restart.

## Verify the GGUF header before copying any speculative-decoding flag

`--spec-type draft-mtp` (speculative decoding off the model's own multi-token-prediction head) is
worth roughly +23% to +89% across this fleet, so it is tempting to copy the flag from a sibling
entry. **Do not.** The flag only does anything if the GGUF actually carries the head, and
quantisation can drop it.

Check the header first, every time:

```bash
python3 - <<'PY'
import gguf
r = gguf.GGUFReader("model.gguf")
f = lambda k: (r.get_field(k).contents() if r.get_field(k) else None)
print("arch:", f("general.architecture"))
names = [t.name for t in r.tensors]
mtp = [n for n in names if "nextn" in n.lower() or "mtp" in n.lower()]
print("nextn/mtp tensors:", len(mtp), mtp[:4])
print("total tensors:", len(names))
PY
```

Zero nextn/MTP tensors means **no** `--spec-type draft-mtp`.

Measured 2026-10-10: Underdog Saluki 27B 1.0 (IQ2-mix, a 2-bit quant of Qwen3.8-27B) reports
`qwen35`, `block_count` 64, 851 tensors, and **zero** nextn tensors. The head the full-size
Qwen3.8-27B carries was dropped by the 2-bit quant. Its siblings `mb-qwen3.8-27b` and
`mb-qwen3.6-35b-a3b-mtp` do carry it, which is exactly how a blind copy ships a broken flag.

**Never port spec *settings* across hosts.** The optimum is host-specific: for the same file, bare
draft-mtp wins on the MacBook while capped + ngram wins on the Studio. Measure on the machine that
will serve it.

## Model id prefix is host-scoped, and there are no aliases

`ms-*` on the Studio, `mb-*` on the MacBook. A wrong-prefix or stale id hard-404s
(`no router for requested model`) instead of falling back, and a liveness-only probe still reports
healthy. Confirm against the live list before writing a client or a cron job's model field:

```bash
curl -s http://127.0.0.1:9292/v1/models   | jq -r '.data[].id'   # Studio
curl -s http://100.68.81.83:8999/v1/models | jq -r '.data[].id'  # MacBook
```

## Agent models need a 64K context floor

Hermes hard-fails an agent turn on a model below 64K context (`MINIMUM_CONTEXT_LENGTH = 64_000`).
Model cards routinely recommend 32K; set `--ctx-size 65536` for anything Hermes will route to.
Remember `--parallel N` divides that budget per request, so `--parallel 2` halves the usable window.

## Qwen3.8-family entries need `--jinja`

`--jinja` enables the model's own chat template, which is what parses tool calls and splits the
thinking block into `reasoning_content`. Without it, tool calls fail to parse and thinking tags
leak into message content.

## A model entry in llama-swap is ONLY half the wiring: Hermes needs its own context_length

llama-swap serves a model, but the context window Hermes compacts against is resolved from Hermes
config (`providers.<name>.models.<id>.context_length`), NOT from llama-swap's `--ctx-size`.
Resolution order (hermes-agent `agent/model_metadata.py` get_model_context_length): explicit
per-model config → provider-level `context_length` default → live `/models` probe → hardcoded
catalog → 256K fallback. A live probe that returns `null` context_length (common for custom
llama-server builds like b11960) is treated as missing, so the provider default wins.

Consequence (hit 2026-11-01 on ms-laguna-xs-2.1): the model served 262144 but Hermes had no
per-model entry and its provider default was 65536 → Hermes compacted agent sessions at ~60K
even though the server would take 256K. The llama-swap config was correct the whole time.

So when adding a llama-swap model entry, ALWAYS add the matching per-model `context_length` in
`~/.hermes/config.yaml` under the same provider. Point it at the SERVING window
(`--ctx-size`), not the GGUF max — a 262144-header model served at 65536 must be 65536, or Hermes
overestimates and smacks the server cap mid-request instead of compacting. Two models can share a
header max and differ in serving ctx; the serving number is the one that matters.

Verify the resolve, not just the YAML:

```bash
cd ~/.hermes/hermes-agent && ./.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, '.')
from hermes_cli.config import get_compatible_custom_providers, load_config_readonly
from hermes_cli.config_providers import get_custom_provider_context_length
cfg = load_config_readonly()
cps = get_compatible_custom_providers(cfg)
print(get_custom_provider_context_length('<id>', 'http://127.0.0.1:9292/v1', custom_providers=cps))
PY
```

## Verify the load, not just the YAML

A parsed config is not a working model. After adding an entry, confirm in the live API:

```bash
curl -s http://HOST:PORT/v1/models | jq '.data[] | select(.id=="<id>") | {id, status, capabilities}'
```

Expect `status.value == "loaded"` after a real request, plus the capability flags the entry claims
(`function_calling`, `vision`). A vision entry is only proven by an actual image inference, not by
the `vision: true` flag alone.
