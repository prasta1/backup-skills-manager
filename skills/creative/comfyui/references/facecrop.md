# Face-crop reference sets (`facecrop.py` + `facecrop_qc.py`)

Use when the user wants a folder of photos turned into **tight, single-person
face crops** — reference images for ComfyUI workflows (Qwen subject refs,
img2img sources, LoRA training sets) or any "crop these to my face" request.

This is INPUT preparation, not generation: it never touches a ComfyUI
server. It feeds the reference slots that `run_workflow.py --input-image`
and the multi-reference workflows consume.

## The two scripts

| Script | Role |
|--------|------|
| `facecrop.py` | Detect all faces, embed them (insightface buffalo_l), cluster the folder's single-face images, pick the dominant identity, match every other face against it, tight-crop the matches. Writes crops + `report.json` + `too-small/` |
| `facecrop_qc.py` | Build labeled contact sheets (`qc/`) from the report so a human can scan and flag strays. **Always run this — the filter is ~98%, human eyes close it** |

## Workflow

```bash
# 1. Crop to the folder's dominant identity (training-grade threshold)
FACEENV=~/.hermes/cache/scratch/faceenv
$FACEENV/bin/python scripts/facecrop.py \
  /path/to/photos /path/to/output --score 0.40

# 2. Build QC sheets (label = SOURCE filename + match score; red = borderline)
$FACEENV/bin/python scripts/facecrop_qc.py /path/to/output --score 0.40

# 3. Human QC: scan qc/borderline-*.jpg first, then confident-*.jpg
#    Tell the user bad ones by the label; purge by source filename
```

Thresholds: **0.40** = training-grade (drops the ambiguous 0.35–0.40 tail;
expect ~5–25% of matches to be borderline there). **0.35** = inclusive
(keeps the tail; only use with QC). The borderline band is real: hats,
sunglasses, odd angles, and age drift all drop cosine similarity — it is
NOT evidence the person is wrong.

## The identity-cluster rationale

Sorted single-face images are clustered greedily by embedding cosine (≥0.45
joins). The **largest cluster is the target identity** — in a folder of the
user's own photos, the dominant recurring face is the user. This beats
largest-face or best-quality picking in group shots: the biggest/sharpest
face is often a bystander, and "quality" tracks sharpness, not identity.

**Failure mode:** a folder with no clear subject (mixed family albums)
produces no dominant cluster → script exits 2 with a clear message. Don't
force it; tell the user the folder has no single dominant subject.

## Output layout

```
<out>/
├── <stem>.jpg          matched crops (<stem>_2.jpg for format twins)
├── report.json         per source: source, output, status, best_score, size
├── too-small/          crops < 256px (distant faces, sub-training-grade)
└── qc/                 30-ish labeled contact sheets + manifest.json
```

## Pitfalls (all verified 2026-10-22)

1. **HEIC needs `pillow-heif`.** `PIL.Image.open` on a `.heic` file fails
   with `UnidentifiedImageError` unless something calls
   `pillow_heif.register_heif_opener()` first. `facecrop.py` does this
   inside a try/except. Install it or every HEIC in the folder dies at
   pass 1. iPhone dumps are mostly HEIC — expect this to matter.

2. **Format twins clobber output names if not handled.** The same photo
   often sits in a folder twice (`IMG_1261.HEIC` + `IMG_1261.JPG`). Naive
   `<stem>.jpg` naming silently overwrites the first with the second.
   `facecrop.py` dedupes with `<stem>_2.jpg` and keys `report.json` to the
   **source** file, so nothing is lost and the mapping is exact. When
   checking completeness, compare report ok-entries to on-disk files with
   the twin rule in mind — a 632-entry report with 5 twins yields 627
   unique files, not a missing-5 bug.

3. **Vision models are unreliable for identity QC.** They judge by
   clothing/background and will call the same person "different people"
   across two crops and confidently describe strangers as the subject.
   Do NOT use a vision model to verify that a face-crop set is one person.
   The user's eyes on the QC sheets are the source of truth.

4. **Deletion authorization is separate.** When the user says delete the
   originals after cropping, confirm the crop set is complete and the user
   has QC'd it BEFORE running the delete. The crops are cheap to lose; the
   source photos are not (even when the user calls them "copies").

5. **Deletes only in the comfyui skill's *scripts* are stdlib-only.**
   `facecrop.py` intentionally breaks that pattern: it needs a venv
   (`~/.hermes/cache/scratch/faceenv`) with insightface + onnxruntime +
   pillow-heif. The script checks deps at import and prints the venv
   command instead of dying with an ImportError. buffalo_l (~280 MB)
   auto-downloads to `~/.insightface/models/` on first run.

6. **HEIF registration is global and harmless.** Registering the opener
   affects all PIL opens in the process; fine for a CLI tool, but don't
   import `facecrop` as a library into a server context expecting pure PIL.