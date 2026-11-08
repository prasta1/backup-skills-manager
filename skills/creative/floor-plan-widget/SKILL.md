---
name: floor-plan-widget
description: "Build a draggable, to-scale floor-plan widget for any room."
version: 0.1.0
author: Patrick Ruster, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [floor-plan, layout, widget, svg, drafting]
    related_skills: [impeccable]
---

# Floor-Plan Widget Skill

Builds a single-file, draggable, to-scale floor-plan widget (SVG) for any room — garage, office, shop, workshop. Items are draggable, resizable, rotatable; doors/windows straddle the boundary; a measurement tool reports edge-to-edge clearances; units toggle ft/in/mm; layouts save/export/load; a technical-drawing (blueprint) aesthetic is built in.

## When to Use

- User wants to plan or rearrange a room's layout (garage, office, shop, workshop, studio).
- User wants a draggable floor plan to iterate on placements.
- User wants to measure clearances between objects in a space.
- User wants a reusable, parameterized layout widget for a new room.

Don't use for: full architectural CAD, structural drawings, or anything needing real dimensioned engineering output.

## Prerequisites

- None. The widget is a single self-contained HTML file (no build step, no dependencies).
- A browser to view it (the Hermes desktop app renders it via `::preview{file="..."}`).

## How to Run

1. Copy `templates/floor-plan.html` to a working file.
2. Edit the `CONFIG` object at the top of the `<script>` (room dimensions, items, doors/windows, colors, title).
3. Open the file in a browser, or preview it in chat with `::preview{file="/abs/path/floor-plan.html"}`.
4. Iterate: drag items, measure clearances, save/export.

## Quick Reference

- `CONFIG.room` — `{width, depth, unit}` in feet (or inches/mm via `unit`).
- `CONFIG.items` — array of `{id, label, x, y, w, h, color, kind}`. `kind:'opening'` = door/window (straddles boundary, lockable).
- `CONFIG.title` — the drafting title block text.
- Buttons: Reset, Grid, Measure, Units, Lock, Save, Coords, PNG, Load.
- Full config reference: `docs/config.md`. Public-facing docs: `README.md`.

## Procedure

1. **Set the room.** In `CONFIG.room`, set `width` and `depth` (in feet by default; set `unit:'in'` or `'mm'` to change).
2. **Add items.** In `CONFIG.items`, add one object per item: `{id, label, x, y, w, h, color, kind}`. Coordinates are top-left in the room's unit. Set `kind:'opening'` for doors/windows (they straddle the boundary and are lockable).
3. **Set the title.** `CONFIG.title` feeds the drafting header.
4. **Preview and iterate.** Open the file. Drag items to place them; double-click (rapid) to rotate; use Measure to check clearances; toggle Units; Lock building features when placed.
5. **Save/export.** Use Save (localStorage), Coords (TSV), PNG (image), or Load (TSV) as needed.

## Pitfalls

- Coordinates are top-left corners, not centers. The measurement tool computes true edge-to-edge gaps.
- Doors/windows (`kind:'opening'`) are clamped to the room walls so they can straddle the boundary; floor items are clamped to the canvas.
- Rotation requires two rapid clicks (≤250ms apart), not a slow double-click.
- The widget is a single file; localStorage persistence is per-browser. Use Export Coords (TSV) for a portable backup.
- The `CONFIG` object is the only thing to edit for a new room — do not edit the rendering code below it.

## Verification

- Open the file; the room renders at the configured dimensions with all items.
- Drag an item; it tracks the cursor 1:1 (no drift).
- Click Measure, then an item; edge-to-edge clearance lines appear with labels.
- Toggle Units; labels switch ft/in/mm.
- Lock building; doors/windows become immovable.
- Export PNG produces a valid image.
