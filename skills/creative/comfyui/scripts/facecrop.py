#!/usr/bin/env python3
"""
facecrop.py — identity-based face cropping for reference-image sets.

For every image in a folder:
  1. Detect all faces + 512-d embeddings (insightface buffalo_l)
  2. Build the "target identity" from single-face images (dominant cluster)
  3. Pick the face matching the target identity best (cosine >= --score)
  4. Tight-crop, square, <= max px, save with report

Why identity (not largest-face / best-quality): in group photos the
largest or sharpest face is often NOT the subject you want. Clustering
single-face images finds *who* the folder is mostly about; matching
every other face against that cluster keeps only that person. The
--score threshold is the QC lever: 0.40 = training-grade (drop the
ambiguous tail), 0.35 = inclusive (more volume, needs human QC).

Output layout (created next to the source folder or where you say):
  <out>/*.jpg              matched crops, <source-stem>.jpg
  <out>/report.json        every crop: source file, output name, size, score
  <out>/too-small/         crops < 256px (distant faces, not worth keeping)

Filename collisions are handled (same photo in two formats, e.g.
IMG_1261.HEIC + IMG_1261.JPG): the first writes <stem>.jpg, the second
writes <stem>_2.jpg. Nothing is silently clobbered and report.json keys
every entry to its SOURCE file, so the mapping is exact.

Dependencies (one-time, in a venv — this script is NOT stdlib-only):
  python -m venv ~/.hermes/cache/scratch/faceenv
  ~/.hermes/cache/scratch/faceenv/bin/pip install \
      insightface onnxruntime opencv-python-headless pillow-heif numpy
Buffalo_l model (~280 MB) auto-downloads from GitHub on first run.

Usage:
  facecrop.py <in_dir> <out_dir> [--max-px 1024] [--margin 0.4]
              [--score 0.40] [--seed-min 3] [--limit N] [--json report.json]
"""
import argparse, json, os, sys
from pathlib import Path

# ---- graceful dependency check (skill convention: no raw ImportError) ------
try:
    import numpy as np
    from PIL import Image, ImageOps
except ImportError:
    print("ERROR: facecrop.py needs numpy + Pillow. Create the venv and install deps:", file=sys.stderr)
    print("  python -m venv ~/.hermes/cache/scratch/faceenv", file=sys.stderr)
    print("  ~/.hermes/cache/scratch/faceenv/bin/pip install insightface onnxruntime opencv-python-headless pillow-heif numpy", file=sys.stderr)
    sys.exit(2)

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass  # HEIC optional; non-HEIC images still work

try:
    from insightface.app import FaceAnalysis
except ImportError:
    print("ERROR: insightface not installed. Create the venv and install deps:", file=sys.stderr)
    print("  python -m venv ~/.hermes/cache/scratch/faceenv", file=sys.stderr)
    print("  ~/.hermes/cache/scratch/faceenv/bin/pip install insightface onnxruntime opencv-python-headless pillow-heif numpy", file=sys.stderr)
    sys.exit(2)


def norm_emb(emb):
    e = np.asarray(emb, dtype=np.float64).ravel()
    n = np.linalg.norm(e)
    return e / n if n > 0 else e


def cosine(a, b):
    return float(np.dot(a, b))


def output_names_for(source_name: str, used: set[str], out_dir: Path) -> str:
    """<stem>.<anyext> -> <stem>.jpg, deduplicating shared stems with _2, _3."""
    stem = Path(source_name).stem
    name = stem + ".jpg"
    if name not in used:
        return name
    i = 2
    while f"{stem}_{i}.jpg" in used:
        i += 1
    return f"{stem}_{i}.jpg"


def main():
    p = argparse.ArgumentParser(description="Identity-based face crop for reference sets")
    p.add_argument("in_dir")
    p.add_argument("out_dir")
    p.add_argument("--max-px", type=int, default=1024)
    p.add_argument("--margin", type=float, default=0.40)
    p.add_argument("--score", type=float, default=0.40,
                   help="cosine match threshold: 0.40 training-grade, 0.35 inclusive+QC")
    p.add_argument("--min-crop", type=int, default=256,
                   help="crops smaller than this land in too-small/")
    p.add_argument("--seed-min", type=int, default=3, help="min cluster size to treat as identity")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--json", default=None)
    args = p.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exts = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".gif", ".bmp"}
    files = sorted([f for f in in_dir.iterdir() if f.suffix.lower() in exts])
    if args.limit:
        files = files[:args.limit]

    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_size=(640, 640))

    # -------- Pass 1: detect + embed every face ------------------------------
    images = []
    for fi, f in enumerate(files):
        try:
            img = Image.open(f)
            img = ImageOps.exif_transpose(img).convert("RGB")
        except Exception as e:
            print(f"skip {f.name}: {e}", file=sys.stderr)
            images.append({"file": f.name, "faces": [], "img": None, "error": str(e)})
            continue
        arr = np.asarray(img)
        faces = app.get(arr)
        rec = {"file": f.name, "faces": [], "img": img}
        for fa in faces:
            rec["faces"].append({
                "bbox": [float(x) for x in fa.bbox],
                "emb": norm_emb(fa.normed_embedding),
                "det": float(fa.det_score),
                "quality": float(getattr(fa, "face_quality_score", 0.0) or 0.0),
            })
        images.append(rec)
        if (fi + 1) % 50 == 0:
            print(f"pass1 {fi+1}/{len(files)}", file=sys.stderr)

    # -------- Pass 2: target identity from single-face images ----------------
    singles = [r for r in images if len(r["faces"]) == 1]
    print(f"single-face images: {len(singles)}", file=sys.stderr)
    clusters = []
    for r in singles:
        e = r["faces"][0]["emb"]
        best_i, best_s = None, -2.0
        for i, c in enumerate(clusters):
            s = cosine(e, c["sum"] / c["n"])
            if s > best_s:
                best_s, best_i = s, i
        if best_i is not None and best_s >= 0.45:
            c = clusters[best_i]
            c["sum"] += e; c["n"] += 1
        else:
            clusters.append({"sum": e.copy(), "n": 1})
    clusters.sort(key=lambda c: c["n"], reverse=True)
    print("cluster sizes:", [c["n"] for c in clusters], file=sys.stderr)
    if not clusters or clusters[0]["n"] < args.seed_min:
        print("ERROR: no dominant identity cluster found (folder may have no clear subject)", file=sys.stderr)
        sys.exit(2)
    target = clusters[0]
    target_emb = target["sum"] / target["n"]
    print(f"target identity: cluster of {target['n']} single-face images", file=sys.stderr)

    # -------- Pass 3: pick + crop --------------------------------------------
    too_small_dir = out_dir / "too-small"
    too_small_dir.mkdir(exist_ok=True)
    used_names: set[str] = set()
    report = []
    for r in images:
        best_face, best_score = None, -2.0
        for fa in r["faces"]:
            s = cosine(fa["emb"], target_emb)
            if s > best_score:
                best_score, best_face = s, fa
        if best_face is None or best_score < args.score:
            report.append({"source": r["file"], "status": "nomatch", "faces": len(r["faces"]),
                           "best_score": round(best_score, 3), "output": None})
            continue
        img = r["img"]
        W, H = img.size
        x1, y1, x2, y2 = best_face["bbox"]
        fw, fh = x2 - x1, y2 - y1
        pad_x = fw * args.margin
        pad_up = fh * args.margin * 1.2
        pad_dn = fh * args.margin * 0.8
        cx1 = max(0, x1 - pad_x); cy1 = max(0, y1 - pad_dn)
        cx2 = min(W, x2 + pad_x); cy2 = min(H, y2 + pad_up)
        side = max(cx2 - cx1, cy2 - cy1)
        sx = min(max(0, cx1 - (side - (cx2 - cx1)) / 2), W - side)
        sy = min(max(0, cy1 - (side - (cy2 - cy1)) / 2), H - side)
        crop = img.crop((int(sx), int(sy), int(sx + side), int(sy + side)))
        if side > args.max_px:
            crop = crop.resize((args.max_px, args.max_px), Image.LANCZOS)
        out_name = output_names_for(r["file"], used_names, out_dir)
        if crop.width < args.min_crop:
            crop.save(too_small_dir / out_name, "JPEG", quality=92)
            report.append({"source": r["file"], "status": "toosmall", "faces": len(r["faces"]),
                           "best_score": round(best_score, 3), "output": f"too-small/{out_name}",
                           "size": crop.width})
            continue
        crop.save(out_dir / out_name, "JPEG", quality=92)
        used_names.add(out_name)
        report.append({"source": r["file"], "status": "ok", "faces": len(r["faces"]),
                       "best_score": round(best_score, 3), "output": out_name, "size": crop.width})

    if args.json:
        with open(args.json, "w") as f:
            json.dump(report, f, indent=1)
    ok = sum(1 for x in report if x["status"] == "ok")
    nomatch = sum(1 for x in report if x["status"] == "nomatch")
    small = sum(1 for x in report if x["status"] == "toosmall")
    print(f"done: {len(report)} images | matched {ok} | nomatch {nomatch} | toosmall {small}", file=sys.stderr)
    scores = sorted(x["best_score"] for x in report if x["status"] in ("ok", "toosmall"))
    if scores:
        print(f"match scores: min {scores[0]:.3f} / med {scores[len(scores)//2]:.3f} / max {scores[-1]:.3f}", file=sys.stderr)


if __name__ == "__main__":
    main()