# Dither Globe — React → Vanilla JS port

How to drop the rotating dithered globe (from https://dithercn.dev/r/dither-globe.json) into a STATIC HTML one-pager with no React, no build step. Used for the NousCon 2026 itinerary hero.

## Source registry items

- dither-globe: https://dithercn.dev/r/dither-globe.json (the React component + render math)
- dither-core: https://dithercn.dev/r/dither-core.json (Bayer4 matrix, thresholdAt, hooks — ignore the hooks, they're React)
- world-land: https://dithercn.dev/r/world-land.json (the 480×240 RLE land mask, Natural Earth public domain — copy the RUNS string verbatim)

## What to copy

1. **Land mask**: the `RUNS` RLE string + `ALPHABET` + decode (`landMask()`), `landCoverage(lat, lon)`. Tests: decode lands on 115,200 cells with ~33% land; known points (London, NYC, Vermont = land; mid-Atlantic, Pacific = ocean).
2. **Bayer4 matrix**: `bayerRanks(4)` + `thresholdAt(x,y) = (ranks[(y%4)*4+(x%4)] + 0.5) / 16`. Cells ink when `tone > thresholdAt(...)`.
3. **Render math**: `buildDisc` (sphere + halo pixel lists), `makeView`/`toWorld`/`toView`, `fromLatLon`, `lightVector`, `surfaceTone` (land vs ocean + terminator), `paintSphere`, `paintAtmosphere`, `projectPoint`, `paintMarker`/`paintMarkers` (pulsing rings), `arcPoint`/`paintArcs` (lifted great-circle arcs with a traveling head).
4. **Boot**: canvas + `requestAnimationFrame` loop; spin += speed*delta; scene = {disc, light, ocean, land RGBA, accent, view: makeView((start+spin)*RAD, -tilt*RAD)}; paint sphere → atmosphere → putImageData → arcs → markers.

## Config choices that matter

- `RADIUS_SHARE` (globe fraction of canvas): 0.42 looks small; 0.47 fills better. Canvas 400×400 @ cell=2 → 200×200 dither grid.
- `start` (initial facing longitude): set near -70 to open on the US East Coast so US markers/arcs show immediately.
- `cell = 2` CSS px per dither cell is a good detail/cost balance.
- Land + accent colors: pass the page palette (warm paper land, amber accent reads well on dark).
- Sea is transparent (canvas shows page background); atmosphere ring is subtle and optional.

## Pitfalls

- The registry files are TypeScript/React; strip hooks (useFrameLoop, useCanvasSize, useDitherColors, useGlobeTurn, usePrefersReducedMotion) and replace with a rAF loop + fixed colors.
- Keep the RUNS string byte-exact — any truncation corrupts the mask (test decode coverage before shipping: 115,200 cells, ~33% land).
- `wrap()` for threshold lookup and mask columns; landCoverage needs the bilinear blend for smooth coasts.
- Print: a still first frame is fine (rAF-free page = one painted frame), or render a static frame on load.

## Verification without a browser

Decode the RUNS string in node and assert: decoded cells == LAND_COLUMNS*LAND_ROWS (115,200), land % ≈ 33, and Cambridge VT / NYC / London land=true while mid-Atlantic / Pacific land=false. That proves the mask; the render math is a faithful copy of the component.
