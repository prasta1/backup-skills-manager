# DESIGN.md — Fleet Catalog

<!-- impeccable:design-schema 1 -->

## World

Monochrome Product Surface (user-chosen direction, seed 26f17ebb), adapted
from a marketing grammar to a reference-catalog structure. The fleet catalog
reads as a **printed reference document**: near-black ink on fine near-white
paper, hairline rules, tabular figures, and one restrained oxide-red accent
used only for breakage and the masthead mark. It refuses the generic dark
dashboard and any claim-and-proof marketing structure.

## Design tokens

| Token | Value | Role |
|---|---|---|
| `--paper` | `#f7f5f1` | page ground (warm near-white) |
| `--ink` | `#1a1815` | primary text |
| `--grey` | `#6b655c` | secondary text, labels |
| `--line` | `#d9d3c9` | hairline rules |
| `--accent` | `#a33a2a` | the ONLY status color — breakage ONLY (no bench, no usage, warn chips) |
| `--mono` | ui-monospace stack | model IDs, figures, labels, chips |
| `--display` | Space Grotesk 500/700 (embedded base64 woff2) | masthead, section headings, stat numerals, ghost numbers, crest monogram |

## Type strategy

- Display voice: Space Grotesk (500/700), embedded as base64 woff2 so the
  page stays offline/self-contained — a geometric sans at two weights per the
  direction, replacing the platform-sans display the craft floor bans.
- Body: system-ui stack.
- Data voice: monospace for every ID, figure, label, chip, and badge — the
  instrument-readout character.
- All functional text ≥11px.

## Status encoding

- **One accent, one meaning:** oxide red appears only where something needs
  attention — the `no bench` / `no usage` stats, the warn chip. The FLEET
  mark is ink; there is no brand color. Positive status is ink, never a
  second hue.

## Finish details (hybrid direction, locked 2026-10-24)

- Masthead: 44px display, `3px double` ink rule under the header.
- Crest: 42px circle monogram in the header right; hidden ≤700px.
- Stat numerals: 34px display with tighter tracking.
- Ghost section numbers: outlined 01/02/03 (1.5px stroke, transparent
  fill) sitting right-aligned on each h2; injected by JS at render;
  hidden ≤700px.
- Paper grain: SVG `feTurbulence` noise as a fixed overlay at 4.5%
  opacity — the page reads as printed matter.

## Information architecture

The five questions are the spine, each a section:

1. **Text Models (36)** — llama-swap served LLMs, sortable/filterable table.
2. **Image Models (13)** — ComfyUI + Unsloth disk-scanned models; the
   censored/uncensored column is the image fleet's capability axis.
3. **Tuning (49)** — every model's enabled/available/untouched optimization
   buckets; the untouched column is what's ready for tuning.
4. **Disk cost** — the summary strip (GB per host, total).
5. **Health** — `no bench` count in the strip; ghosts and orphans surface in
   the generator's check output and the notes.

## Components

- Hairline-ruled tables with mono headers, right-aligned tabular numerals.
- Ink-outline chips (sharp corners, 3px) for filters; active chip fills ink.
- Summary strip as hairline-divided cells, not cards.
- Rows highlight on hover with a faint accent wash.

## Responsive

- ≤1000px: hide numeric detail columns 5–9 (GB→Quant).
- ≤700px: also hide columns 10–14 (Vis→Qual), leaving ID/Host/Cap/Group/
  Reqs/Last/Bench/Usage.

## Anti-identity

Not a dashboard, not marketing, not a dark console. No cards-as-everything,
no pill badges, no glow, no gradient text. The page is a reference you
consult, not a surface you watch.