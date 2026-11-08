# Floor-Plan Widget

A single-file, draggable, to-scale floor-plan widget for any room — garage, office, shop, workshop, studio. No build step, no dependencies, no server. Open the HTML in a browser and start arranging.

## Features

- **Draggable, resizable, rotatable items** — grab any box, move it, resize it from the corner handle, rotate with a rapid double-click.
- **Doors & windows** — marked `kind:'opening'`, they straddle the room boundary (elevated, so they don't conflict with floor items) and can be locked in place.
- **Measurement tool** — click an item to see true edge-to-edge clearances to other items and to the walls. Skips doors/windows, set-aside items, overlapping items, and blocked paths.
- **Units toggle** — ft / in / mm.
- **Lock building** — freeze doors/windows once placed.
- **Save / Export / Load** — localStorage persistence, TSV export/import, PNG image export.
- **Technical-drawing aesthetic** — blueprint ground, drafting grid, border frame, registration marks, scale bar, drafting typeface.

## Quick Start

1. Copy `templates/floor-plan.html` to a working file.
2. Edit the `CONFIG` object at the top of the `<script>`.
3. Open the file in a browser.

```html
<!-- templates/floor-plan.html, CONFIG block -->
var CONFIG = {
  title: { kicker: 'MY SPACE', name: 'FLOOR PLAN' },
  room: { width: 20, depth: 16, unit: 'ft' },
  scale: 26,
  asideWidth: 12,
  grid: 0.25,
  storeKey: 'my-space-layout-v1',
  items: [
    { id:'desk', label:'Desk', x:1, y:1, w:6, h:3, color:'#8a5fd6' },
    { id:'door', label:'Door', x:0, y:2, w:0.4, h:3, color:'#F97316', kind:'opening' }
  ],
  legend: [
    { color:'#8a5fd6', label:'Desk' },
    { color:'#F97316', label:'Doors' }
  ]
};
```

## Configuration

See [docs/config.md](docs/config.md) for the full reference.

| Key | Type | Description |
|---|---|---|
| `title` | object | `{kicker, name}` for the drafting header |
| `room` | object | `{width, depth, unit}` — room size in feet (or in/mm) |
| `scale` | number | pixels per foot (default 26) |
| `asideWidth` | number | set-aside zone width in feet (default 12) |
| `grid` | number | snap increment in feet (default 0.25 = 3 in) |
| `storeKey` | string | localStorage key for persistence |
| `items` | array | `{id, label, x, y, w, h, color, kind?}` |
| `legend` | array | `{color, label}` pairs |

## Usage

- **Drag** any box to move it.
- **Resize** from the bottom-right corner handle.
- **Rotate** with two rapid clicks (≤250ms apart).
- **Measure** — toggle Measure, click an item, read the clearances.
- **Units** — cycle ft / in / mm.
- **Lock** — freeze doors/windows.
- **Save / Coords / PNG / Load** — persist, export, and restore layouts.

## License

MIT. See [LICENSE](LICENSE).
