# Vision benchmarking protocol, ranking rules, oMLX endpoint

Moved out of MEMORY.md on 2026-10-01: these are procedures for this skill, not every-turn facts.

## Vision runs

1. Image integrity: always verify the input image against `references/vision_ground_truth.json` when using `--vision`. The rubric warns when the image does not match the ground truth, and scores are meaningless until it does.
2. Scoring focus: prioritize `quality_score` and `count_people` over `tok/s` and `median_tok_s`. Vision throughput on the Studio is noisy and unreliable; the quality axis is the only trustworthy metric.
3. Workflow: `scripts/run_interactive.py` for selection, then `scripts/benchmark.py --vision <image path>`.
4. Import shadowing in `scripts/prompts.py`: load the ground-truth family by explicit file path, `grounded = os.path.join(os.path.dirname(...), "..", "prompts", "vision_grounded.py")`, never `from prompts import vision_grounded`.

## Ranking rules

- Rank by throughput per active parameter / GB resident, not raw tokens/s; raw speed is dominated by MoE vs dense architecture.
- Evaluation gap: there is no standardized long-context retrieval accuracy probe, so context-window claims (e.g. 64K) are unverified by these tools.

## oMLX endpoint on the Studio

oMLX serves on :8010 (`settings.json` `server.port`), not 8000, and requires an API key (`auth.skip_api_key_verification=false`). `references/endpoints.json` carries `api_key=file:/Users/macstudio/.omlx/settings.json#/auth/api_key`; `discover_endpoints.py` and `benchmark.py` send it as Bearer. oMLX loads models on demand, so `/v1/models` is empty until a model loads.
