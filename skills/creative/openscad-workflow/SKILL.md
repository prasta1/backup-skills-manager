---
name: openscad-workflow
description: Use when authoring OpenSCAD parts and rendering them to STL.
trigger: User mentions OpenSCAD, .scad files, parametric CAD, or rendering a part to STL for the garage shop (CNC, laser, 3D printing).
version: 1.0.0
author: Ionga
license: MIT
metadata:
  hermes:
    tags: [openscad, cad, stl, 3d-printing, garage-shop]
    related_skills: [docker-services-on-synology]
---

# OpenSCAD Workflow

## When to Use

Use this when Patrick wants to design, generate, or render a parametric CAD part in OpenSCAD — for the garage shop (CNC, laser, 3D printing) or any STL output. OpenSCAD is a text format, so authoring needs no special tooling; this skill encodes the render-on-MacBook + store-on-NAS loop.

Author `.scad` on the Studio, render on the MacBook, store on the NAS. OpenSCAD is a text format — no skill needed to author it; the value here is the render + storage loop.

## The four legs (all verified working)

1. **Author** `.scad` on the Studio (any editor / write_file)
2. **Render** on the MacBook's OpenSCAD CLI
3. **Store** sources + STL on the NAS at `Projects/openscad/` over SSH
4. **Open** the source in the OpenSCAD GUI on the MacBook for review

## Key facts

- **OpenSCAD lives on the MacBook**, not the Studio: `/opt/homebrew/bin/openscad` (v2026.10.11), reachable via `ssh macbook`.
- **NAS `home` share** = `/volume1/homes/prasta/` on tanker. The `Projects/openscad/` dir maps to `/volume1/homes/prasta/Projects/openscad/`.
- **The SMB mount `/Volumes/home` is often NOT mounted** on the Studio, and the keychain has NO password stored for `tanker` — the GUI mount (`osascript mount volume`) hangs on a credential dialog that can't be answered headlessly. **Use SSH to tanker instead** (`ssh tanker` works with key auth).
- `/Volumes` is root-owned; `mkdir -p /Volumes/home` fails with permission denied. Don't try to create the mount point.

## Workspace layout (on the NAS)

```
Projects/openscad/
├── src/   ← .scad sources
└── stl/   ← rendered STL outputs
```

## The loop

### 1. Author the .scad

Write the source on the Studio (e.g. in scratch or a local project dir), then push to the NAS `src/` (use the SSH pipe — scp to tanker is broken):

```bash
cat /path/to/part.scad | ssh tanker 'cat > /volume1/homes/prasta/Projects/openscad/src/part.scad'
```

### 2. Render on the MacBook

```bash
scp /path/to/part.scad macbook:/tmp/part.scad
ssh macbook 'openscad -o /tmp/part.stl /tmp/part.scad 2>&1'
scp macbook:/tmp/part.stl /path/to/part.stl
```

Render output is terse and useful: it reports vertices/facets, genus, and any errors. A clean render ends with `Status: NoError` and `Genus: 0`.

### 3. Store on the NAS

```bash
cat /path/to/part.stl | ssh tanker 'cat > /volume1/homes/prasta/Projects/openscad/stl/part.stl'
```

### 4. Open in the OpenSCAD GUI on the MacBook

Patrick reviews parts in the OpenSCAD GUI on the MacBook. Push the source there and open it:

```bash
cat /path/to/part.scad | ssh macbook 'cat > /tmp/part.scad'
ssh macbook 'open -a OpenSCAD /tmp/part.scad'
```

`/tmp` is fine for a quick look but won't survive a reboot — offer to drop a copy somewhere permanent (e.g. `~/Projects/openscad/`) if Patrick wants to keep it on the MacBook.

## Pitfalls

- **Never use `osascript mount volume` for the NAS** — it hangs on a credential prompt. SSH is the reliable path.
- **`scp` to tanker FAILS** (`dest open ... No such file or directory`) even though `ssh tanker` works — the sftp subsystem path resolution is broken. Use the SSH pipe instead: `cat file | ssh tanker 'cat > /path/on/nas'`.
- **Don't try to create `/Volumes/home`** — root-owned, permission denied.
- **Clean up macOS resource forks** if you ever tar a directory from macOS to the NAS (`._*` files, `@eaDir` dirs) — they corrupt things downstream. See the docker-services-on-synology skill for the exact cleanup commands.
- **`$fn` for smoothness**: set `$fn = 64` (or higher) for curved parts; default is coarse.
- **Units**: OpenSCAD is unitless; for the garage shop treat 1 unit = 1 mm.
- **`linear_extrude` extrudes along Z** — if you build a profile in the XY plane and want the extrusion along X, you must `rotate([0,90,0])` the result, and the profile's X axis becomes the final Z (height). Easier: build the part directly as explicit boxes in final orientation.
- **Check `Genus` in the render output**: `Genus: 0` = clean manifold (slicer-safe). `Genus: -1` = non-manifold (separate solids touching at faces) — wrap touching parts in `union()` and make sure they actually overlap, not just touch.
- **Verify geometry programmatically, not by eye**: parse the STL and check the bounding box and cross-sections. The vision model can confidently report a flat block when the channel is missing.

## Verification

After any render, confirm the STL came back with real content (not zero bytes) and, if it matters, that the render reported `NoError`.

```bash
ls -la /path/to/part.stl   # non-zero size
```
