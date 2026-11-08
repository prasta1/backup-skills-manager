# Studio Fleet: llama-swap id → HF tokenizer

`llama-benchy` needs a `namespace/model` tokenizer name. llama-swap ids are
not in that format, so omitting `--tokenizer` makes the tool fall back to
`gpt2` — silently mis-sizing every `--pp` and `--depth` count.

Every `OK` row below was load-tested on this Studio with
`llama_benchy.corpus.LightweightTokenizer.from_pretrained()` on 2026-09-28.
`--model` is the llama-swap id; the value in the second column is what goes
in `--tokenizer`.

## Text / vision models

| `--model` | `--tokenizer` | Status |
|-----------|---------------|--------|
| `ms-devstral-24b` | `mistralai/Devstral-Small-2-24B-Instruct-2512` | OK |
| `ms-gemma-4-26b-moe` | `google/gemma-4-26B-A4B-it` | OK |
| `ms-gemma-4-12b` | `google/gemma-4-12B-it` | OK |
| `ms-gemma-4-e4b` | `google/gemma-4-E4B-it` | OK |
| `ms-glm-4.6-vision` | `zai-org/GLM-4.6V-Flash` | OK |
| `ms-kat-coder-v2.5` | `Kwaipilot/KAT-Coder-V2.5-Dev` | OK |
| `ms-qwen3.6-35b-a3b` | `Qwen/Qwen3.6-35B-A3B` | OK |
| `ms-qwen3-coder-30b` | `Qwen/Qwen3-Coder-30B-A3B-Instruct` | OK |
| `ms-qwen3-vl-8b` | `Qwen/Qwen3-VL-8B-Instruct` | OK |
| `ms-gpt-oss-20b` | `openai/gpt-oss-20b` | OK |
| `ms-granite-4.2-3b` | `ibm-granite/granite-4.2-3b` | OK |
| `ms-granite-4.2-8b` | `ibm-granite/granite-4.2-8b` | OK |
| `ms-ministral-3-3b` | `mistralai/Ministral-3-3B-Instruct-2512` | OK |
| `ms-qwen3.5-4b-mtp` | `Qwen/Qwen3.5-4B` | OK |

## Gated upstream — use the substitute

These canonical repos return **401** without a token, which triggers the gpt2
fallback. Each row lists a load-tested stand-in. Tokenizer vocabularies match
across these fine-tunes (same base family), so the substitute is accurate for
token counting; it is not the canonical repo, so pin it deliberately.

| `--model` | Canonical (401) | Verified substitute | Base family |
|-----------|-----------------|---------------------|-------------|
| `ms-qwopus3.8-27b-flash` | `Qwen/Qwen3.8-27B-Flash` | `Qwen/Qwen3.8-27B` | Qwen3.8-27B (see note) |
| `ms-nuextract3` | `numind/NumExtract3-1.5` | `Qwen/Qwen3.5-4B` | Qwen3.5-4B |
| `ms-muse-glimmer-30b` | `inclusionAI/Muse-Glimmer-30B` | — UNRESOLVED | unknown |

**Note on `ms-qwopus3.8-27b-flash`:** the llama-swap config description calls
it Qwen3.5-based, while the model name says Qwen3.8-27B. Unverified which is
right. `Qwen/Qwen3.8-27B` is the better bet on the name; if prefill numbers
look wrong, try `Qwen/Qwen3.5-4B` and compare. Set `HF_TOKEN` to settle it.

**`ms-muse-glimmer-30b`** has no verified tokenizer. Either export one with
`llama-gguf` / `transformers` into a local dir and pass that path to
`--tokenizer`, or accept the gpt2 approximation and say so in any writeup.

## Local tokenizer directories (no network, no auth)

`--tokenizer` also accepts a local path. A directory containing
`tokenizer.json`, or the `tokenizer.json` file itself, both work — verified:

- `/Users/macstudio/models/Yanun/Swift-Qwen3.8-27b-oQ4e-mtp` — Qwen3.8-27B family
- `/Users/macstudio/models/Yanun/Swift-Qwen3.8-27b-oQ4e-mtp/tokenizer.json`
- `/Users/macstudio/models/prism-ml/Ternary-Bonsai-27B-mlx-2bit`
- `/Users/macstudio/models/lmstudio-community/Qwen3.8-27B-MLX-4bit/tokenizer.json`

The `models/gguf/` tree has **no** `tokenizer.json` anywhere — the GGUFs there
ship without sidecar tokenizers, so every llama-swap id must resolve via the
HF Hub (or `HF_TOKEN`) or a local dir listed above.

## Not benchmarkable

`ms-bge-m3-1024` and `ms-bge-reranker-v2-m3` serve embeddings, not
`/v1/chat/completions`. `llama-benchy` evaluates against the chat endpoint
only. Benchmark their latency with the `embedding-path-audit` skill instead.

## Checking an id that isn't listed

```bash
# via the terminal tool
curl -s https://huggingface.co/api/models/<owner>/<repo>
```

200 or 401 both mean the repo exists (401 = gated, needs `HF_TOKEN`). 404 means
the name is wrong. Then load-test it the way the table above was built:

```bash
/Users/macstudio/.local/share/uv/tools/llama-benchy/bin/python -c "
from llama_benchy.corpus import LightweightTokenizer
LightweightTokenizer.from_pretrained('<owner>/<repo>'); print('OK')"
```

Model ids churn. `~/.hermes/llama-swap/config.yaml` is the source of truth for
what is served; re-derive from there rather than trusting this table forever.
