#!/usr/bin/env python3
"""
facecrop_qc.py — build labeled contact sheets from a facecrop.py report.

The identity filter gets to ~98%; human QC closes the rest. This makes
that cheap: 6-per-row grids with the source filename + match score under
every crop, sorted riskiest-first, borderline (score < --score) red-bordered,
confident green-bordered.

Outputs into <crops_dir>/qc/:
  borderline-N.jpg   score < --score (default 0.40), riskiest first
  confident-N.jpg    score >= --score
  manifest.json      sheet -> crop -> score map

Usage:
  facecrop_qc.py <crops_dir> [--score 0.40]
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

crops_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
score_cut = 0.40
if "--score" in sys.argv:
    score_cut = float(sys.argv[sys.argv.index("--score") + 1])

report_path = crops_dir / "report.json"
qc_dir = crops_dir / "qc"
qc_dir.mkdir(exist_ok=True)

with open(report_path) as f:
    report = json.load(f)
ok = [r for r in report if r.get("status") == "ok"]
# output field names the kept crop file; source is the QC label
ok.sort(key=lambda r: r["best_score"])  # riskiest first

borderline = [r for r in ok if r["best_score"] < score_cut]
confident = [r for r in ok if r["best_score"] >= score_cut]


def font(size):
    for p in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Helvetica.ttf",
              "/Library/Fonts/Arial.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


THUMB, COLS, ROW, PAD, LABEL_H, SHEET = 180, 6, 5, 8, 26, 24


def draw_sheet(subset, name):
    sheets = []
    total = (len(subset) + SHEET - 1) // SHEET
    for i in range(0, len(subset), SHEET):
        chunk = subset[i:i + SHEET]
        rows = (len(chunk) + COLS - 1) // COLS
        W = COLS * (THUMB + PAD) + PAD
        H = rows * (THUMB + LABEL_H + PAD) + PAD + 30
        sheet = Image.new("RGB", (W, H), (28, 28, 32))
        d = ImageDraw.Draw(sheet)
        f_small = font(16)
        d.text((PAD, 8),
               f"{name} sheet {i//SHEET+1}/{total}  (crops {i+1}-{i+len(chunk)} of {len(subset)})",
               fill=(220, 220, 220), font=font(20))
        y0 = 34
        for j, r in enumerate(chunk):
            col, row = j % COLS, j // COLS
            x = PAD + col * (THUMB + PAD)
            y = y0 + row * (THUMB + LABEL_H + PAD)
            src = crops_dir / r["output"]
            if not src.exists():
                continue
            img = Image.open(src).convert("RGB")
            img.thumbnail((THUMB, THUMB), Image.LANCZOS)
            sheet.paste(img, (x + (THUMB - img.width) // 2, y + (THUMB - img.height) // 2))
            border = (200, 60, 60) if r["best_score"] < score_cut else (60, 160, 80)
            d.rectangle([x, y, x + THUMB, y + THUMB], outline=border, width=2)
            label = f"{Path(r['source']).name[:26]}  {r['best_score']:.2f}"
            d.text((x + 2, y + THUMB + 4), label, fill=(200, 200, 200), font=f_small)
        out = qc_dir / f"{name}-{i//SHEET+1}.jpg"
        sheet.save(out, "JPEG", quality=88)
        sheets.append(str(out))
    return sheets


b_sheets = draw_sheet(borderline, "borderline")
c_sheets = draw_sheet(confident, "confident")

manifest = {
    "score_cut": score_cut,
    "total_ok": len(ok),
    "borderline_count": len(borderline),
    "confident_count": len(confident),
    "borderline_sheets": b_sheets,
    "confident_sheets": c_sheets,
}
with open(qc_dir / "manifest.json", "w") as f:
    json.dump(manifest, f, indent=1)

print(f"borderline: {len(borderline)} crops -> {len(b_sheets)} sheets")
print(f"confident:  {len(confident)} crops -> {len(c_sheets)} sheets")
print(f"QC sheets in {qc_dir}")