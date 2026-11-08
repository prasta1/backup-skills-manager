# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Generated static HTML + markdown + JSON, emitted by a Python generator
(`scripts/fleet_catalog.py`) from the llama-swap config and the model
directories on disk. No framework, no build step, no runtime — the artifact
is the deliverable. Existing codebase answers the stack; not a greenfield
decision.

## Users

Patrick — sole operator of his own model fleet (Mac Studio M3 Ultra + MacBook
Pro M5). Personal tooling, not shared. He runs the generator and reads the
catalog to understand, audit, and tune his fleet.

## Product Purpose

Answer five questions about the model fleet, for both text LLMs (llama-swap
served) and image models (ComfyUI / Unsloth Studio):

1. What do I actually have, and what is it for?
2. Which models are vision-capable and which are embeddings? (capability; for
   image models, censored vs uncensored)
3. What is the disk cost of the fleet, per model?
4. Is anything broken? (missing files, orphans, broken symlinks, image ghosts,
   config inconsistencies)
5. What optimizations are available, executed on, and left untouched for
   tuning?

Success means Patrick can answer any of these from one generated artifact,
without hand-maintaining a second copy of a model id.

## Positioning

A mechanically-derived catalog that never guesses — the single source of
truth for the fleet. Every field is read from the config, measured from disk,
or marked null. It is a mirror, not an editor. A neighboring tool could not
truthfully copy "derived mechanically, never guesses" without the same
discipline.

## Operating Context

- Run `python3 scripts/fleet_catalog.py` to regenerate; `--check` validates
  without writing.
- Outputs land in the iCloud Hermes infra folder —
  `~/Library/Mobile Documents/com~apple~CloudDocs/Hermes/infra/fleet-catalog/`,
  the same folder the MacBook sees at
  `/Users/prasta/Library/Mobile Documents/com~apple~CloudDocs/Hermes/infra/fleet-catalog/` —
  as `catalog.json`, `catalog.md`, `catalog.html` (interactive viewer),
  `catalog-widget.html`. One synced copy on every device, no second location
  to drift.
- Text LLMs derive from the llama-swap `config.yaml` (Studio + MacBook via
  the mounted share). Image models derive from the model directories on disk
  (no config file exists for them); MacBook HF-cache sizes are measured over
  ssh because the SMB mount cannot read HF-cache symlinks.
- The curated capability map for the tuning view lives in
  `references/optimizations.md` — the single place to add an optimization.

## Capabilities and Constraints

- Two fleets in one catalog: text LLMs (rich fields: ctx, params, quant,
  arch, bench, usage) and image models (id, host, backend, role, size,
  censored, steps, optimizations).
- Per-model `optimizations` buckets: enabled / available / untouched, plus a
  fleet-wide tuning view.
- Offline: never probes a live backend or external API. Local ssh to the
  MacBook is the one exception (HF-cache sizes).
- The catalog never guesses: `censored` is only asserted when the filename
  says so; blank cells mean "not stated / not measured".
- Read-only: it does not rename, edit config, or make judgment calls.

## Brand Commitments

None binding. No name, voice, or identity constraints were given. The
"FLEET CATALOG" masthead and instrument-panel aesthetic are the current
visual implementation, not a committed brand.

## Evidence on Hand

- The live fleet itself: 36 text LLMs, 13 image models (as of 2026-10-24).
- The five questions, confirmed by Patrick as the product contract.
- `references/optimizations.md` — the curated capability map.
- No testimonials, customers, or external claims exist; do not fabricate any.

## Product Principles

1. Never guess — a blank cell is honest, a guessed value is not.
2. Mechanically derived — the catalog is a mirror of config and disk, never a
   hand-maintained copy.
3. One source of truth — the catalog is the artifact downstream tools read
   instead of re-typing a model id.
4. Offline and self-contained — the HTML works without a CDN or network.
5. Answer the five questions — every field and section serves one of them.

## Accessibility & Inclusion

No product-specific accessibility requirement was established. The HTML is a
self-contained dark-theme page; no contrast or keyboard-navigation standard
was committed.
