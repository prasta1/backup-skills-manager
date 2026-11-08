#!/usr/bin/env python3
"""Flat-design background cutout: near-white flood-fill -> transparent PNG.

Use ONLY for flat-vector art on a solid white field where the subject is
enclosed by a dark outline/border (t-shirt designs, stickers, logos). Fails on
photos, white-in-subject, or non-white backgrounds — use rembg or the qwen
bgremoval graph there.

Usage:
  python cutout_flat.py INPUT.png [--out OUT.png] [--size 4096] [--white 235]
"""
import argparse, os
import numpy as np
from collections import deque
from PIL import Image, ImageFilter


def cutout(src, out, target=4096, white_thresh=235, feather=0.9):
    img = Image.open(src).convert("RGBA")
    scale = target / max(img.size)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    rgb = np.array(img.convert("RGB")).astype(np.int16)
    # Background = near-white in ALL channels (yellow fill is high-luminance but
    # low in B, so it is NOT near-white and survives).
    near_white = (rgb[:, :, 0] > white_thresh) & (rgb[:, :, 1] > white_thresh) & (rgb[:, :, 2] > white_thresh)
    h, w = near_white.shape
    # 4-connected flood-fill from the corners over near-white only: removes the
    # contiguous white field, never isolated white specks or dark subject pixels.
    bg = np.zeros((h, w), bool)
    q = deque()
    for c in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if near_white[c[1], c[0]]:
            q.append(c); bg[c[1], c[0]] = True
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not bg[ny, nx] and near_white[ny, nx]:
                bg[ny, nx] = True; q.append((nx, ny))
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    alpha = np.array(Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(feather)))
    rgba = np.array(img); rgba[:, :, 3] = alpha
    Image.fromarray(rgba, "RGBA").save(out)
    a = alpha
    print(f"transparent {int((a == 0).sum()) / a.size * 100:.1f}%  "
          f"opaque {int((a == 255).sum()) / a.size * 100:.1f}%  -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src")
    ap.add_argument("--out")
    ap.add_argument("--size", type=int, default=4096)
    ap.add_argument("--white", type=int, default=235)
    ap.add_argument("--feather", type=float, default=0.9)
    a = ap.parse_args()
    out = a.out or os.path.splitext(a.src)[0] + "_transparent.png"
    cutout(a.src, out, a.size, a.white, a.feather)
