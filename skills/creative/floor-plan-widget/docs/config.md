# Floor-Plan Widget — Configuration Reference

Everything the widget renders is driven by the `CONFIG` object at the top of the `<script>` in `templates/floor-plan.html`. Edit only this block for a new room; the rendering code below it reads from here.

## `title`

```js
title: { kicker: 'SVEN\u2019S SHOP', name: 'FLOOR PLAN' }
```

- `kicker` — the large bold line in the drafting header.
- `name` — the smaller tracked line beside it.

## `room`

```js
room: { width: 22.67, depth: 24.0, unit: 'ft' }
```

- `width` / `depth` — room dimensions in the configured unit.
- `unit` — `'ft'`, `'in'`, or `'mm'`. This sets the default display unit for measurement labels. Coordinates in `items` are always in feet internally; the unit only affects how measurement labels render.

## `scale`

```js
scale: 26
```

Pixels per foot. Higher = larger rendering. 26 is a good default for a room up to ~25 ft.

## `asideWidth`

```js
asideWidth: 12
```

Width (in feet) of the SET ASIDE drop zone to the right of the room, where you can park items while rearranging.

## `grid`

```js
grid: 0.25
```

Snap increment in feet. 0.25 = 3 inches. Set to `0.1` for finer, or `0.5` for coarser.

## `storeKey`

```js
storeKey: 'floor-plan-layout-v1'
```

The localStorage key used for Save/Load persistence. Use a unique value per room so layouts don't collide.

## `items`

```js
items: [
  { id:'desk', label:'Desk', x:1, y:1, w:6, h:3, color:'#8a5fd6' },
  { id:'door', label:'Door', x:0, y:2, w:0.4, h:3, color:'#F97316', kind:'opening' }
]
```

Each item:

| Field | Type | Description |
|---|---|---|
| `id` | string | unique identifier (used for save/load matching) |
| `label` | string | text shown on the box |
| `x`, `y` | number | top-left corner position, in feet |
| `w`, `h` | number | width and height, in feet |
| `color` | string | hex fill color |
| `kind` | string | optional. `'opening'` = door/window (straddles boundary, lockable) |

**Coordinates are top-left corners, not centers.** The measurement tool computes true edge-to-edge gaps.

### Doors & windows (`kind:'opening'`)

- Clamped to the room walls, so they can **straddle the boundary** (extend past the footprint) — they're elevated and don't conflict with floor items.
- Lockable via the **Lock** toggle.
- Excluded from measurement (they're thin strips, not floor objects).

## `legend`

```js
legend: [
  { color:'#8a5fd6', label:'Desk' },
  { color:'#F97316', label:'Doors' }
]
```

Color/label pairs shown below the plan. One entry per distinct color you use.

## Example: a small office

```js
var CONFIG = {
  title: { kicker: 'MY OFFICE', name: 'FLOOR PLAN' },
  room: { width: 12, depth: 10, unit: 'ft' },
  scale: 26,
  asideWidth: 8,
  grid: 0.25,
  storeKey: 'my-office-layout-v1',
  items: [
    { id:'desk', label:'Desk', x:1, y:1, w:6, h:3, color:'#8a5fd6' },
    { id:'chair', label:'Chair', x:2, y:4.5, w:2, h:2, color:'#2563eb' },
    { id:'shelf', label:'Shelf', x:8, y:1, w:2, h:6, color:'#b9bdc4' },
    { id:'door', label:'Door', x:0, y:2, w:0.4, h:3, color:'#F97316', kind:'opening' },
    { id:'win', label:'Window', x:6, y:0, w:3, h:0.4, color:'#0EA5E9', kind:'opening' }
  ],
  legend: [
    { color:'#8a5fd6', label:'Desk' },
    { color:'#2563eb', label:'Chair' },
    { color:'#b9bdc4', label:'Shelf' },
    { color:'#F97316', label:'Doors' },
    { color:'#0EA5E9', label:'Windows' }
  ]
};
```
