# Seed-reference runs — ComfyUI + Qwen-Image 2.1 (verified 2026-10-28)

When the interactive flow's question 4 is "yes", the attached seed holds the
identity and the prompt restages her into the named setting. The renderer is
`~/.hermes/outputs/Ionga/ref_edit_render.py` (Ionga root, maintained — do not
fork it per run).

## Invocation

```
env -u PYTHONPATH -u PYTHONHOME /Users/macstudio/ComfyUI/venv/bin/python \
  ref_edit_render.py \
  --seed-image ~/.hermes/outputs/Ionga/seeds/<seed>.jpg \
  --aspect 3:4 \
  --prompt-file <run>/<slug>.prompt.txt \
  --neg-file <run>/<slug>.neg.txt \
  --seed 639417 --steps 40 --resolution 1024 \
  --slug s16_<concept>_p01_<stage> --outdir runs/<date>-<concept>
```

`--probe` drops to 12 steps / resolution 512 for a ~35s sanity check. Use it
before the first full frame of a new run shape; it costs nothing and it is the
only cheap way to catch a dead reference path.

**The `env -u PYTHONPATH -u PYTHONHOME` is required.** The Hermes venv's PIL
shadows the ComfyUI venv's and `import PIL` dies with
`ImportError: cannot import name '_imaging'` because the venv is on
Python 3.14 while Hermes' PIL is built for the system python.
`run_workflow.py` has the same problem in reverse (its `requests` import fails
under `/usr/bin/python3`). `/opt/homebrew/bin/python3` works for
`run_workflow.py`; the ComfyUI venv python works for `ref_edit_render.py`.

## Graph wiring that matters

- **`TextEncodeQwenImage21` has THREE outputs**: `positive`, `negative`,
  `latent`. The latent is an empty latent sized from the FIRST reference image
  and **must** feed `KSampler.latent_image`. Substituting an
  `EmptySD3LatentImage` shifts the edit — that is what the node's own tooltip
  warns about.
- **Denoise stays 1.0.** Reference latents are spliced into the conditioning
  as edit-style conditioning, not used as img2img init noise.
- `cfg` 1.0, `sampler_name` euler, `scheduler` simple — same as the proven
  text batches.
- `clip_name` stays `qwen3vl_8b_int8_convrot.safetensors` with
  `type: qwen_image`. Do not switch to the `qwen3.5_9b_..._pe_t2i` encoder for
  a reference run: the vision-capable VL encoder is what handles the images.
- Pass `vae` (from `VAELoader`) into `TextEncodeQwenImage21`. Without it the
  node never builds `ref_latents` and the reference degrades to vision only.

## THE AUTOGROW TRAP — the one that wastes an afternoon

`images` is a `COMFY_AUTOGROW_V3` input. In `comfy_api/latest/_io.py`,
`Autogrow._expand_schema_for_dynamic` expands it into **flat dotted input ids
on the node itself** — `images.image_1`, `images.image_2`, ... — and only
registers a row when that exact key is present in the submitted inputs. The
row is then rebuilt into `{"images": {"image_1": <IMAGE>}}` by
`build_nested_inputs` before `execute()` sees it.

So the only wire format that works is:

```json
"5": {"class_type": "TextEncodeQwenImage21",
      "inputs": {"clip": ["2", 0], "prompt": "...", "negative_prompt": "...",
                 "resolution": 1024, "vae": ["3", 0],
                 "images.image_1": ["4", 0]}}
```

Both plausible-looking alternatives are **accepted by validation, run to
completion, and do nothing**:

- `"images": [{"image": ["4", 0]}]` (the shape the shipped
  `qwen_portrait_768x1344.json` uses as an empty placeholder)
- `"images": {"image_1": {"image": ["4", 0]}}`

With `images={}` the node takes its `keep_vision = len(ref_latents) == 0`
branch, so the vision tower is fed the image but nothing is spliced as latents,
and `latent_w = latent_h = resolution`. Result: a square render at
`resolution`, indistinguishable at a glance from a good reference run.

**Detection rule:** a reference run whose output is square at `resolution`
means the reference did not land. Read the output aspect, not the exit code.
`ref_edit_render.py` prints `server_dims` from the ComfyUI history metadata for
exactly this reason.

**Corollary — do not accept resemblance as proof.** The invented ID anchor in
the prompt describes hair, skin, age and build in enough detail that a pure
text-to-image render of it produces a convincing match. The 2026-10-28 first
attempt produced a plausible dark-haired mature Mediterranean woman on a
boudoir set with zero reference conditioning. Only the aspect ratio exposed it.

## Aspect ratio and framing

Output aspect = reference aspect. `resolution` sets the area, not the shape:
at `resolution=1024`, a 3:4 reference renders 896x1184. A chest-up seed can be
restaged to full-body by prompt, but a square seed cannot become a tall frame —
center-crop it first (`--aspect 3:4` writes `<seed>_ref3x4.png` next to the
original in `seeds/`).

## File naming

Output names are deterministic from `--slug` + `--seed`, so a re-run at the
same slug/seed **overwrites the previous frame**. The script appends a
prompt_id prefix when the target already exists — keep that, and when
re-downloading from `/view` by hand, name the file deliberately rather than
letting two renders share a path.

## The gallery-sweep race — renders that look lost are only moved

`ai.hermes.comfyui-gallery-sweep` (LaunchAgent, StartInterval 600) runs
`gallery.py sweep`, which **MOVES** every file out of ComfyUI's spool
(`~/ComfyUI/output`) into `~/Pictures/ComfyUI/<YYYY-MM>/` and **renames** it
`<slug-from-prompt>_<seed>_<NN>.png`. Nothing is lost and nothing is broken —
but any filename `/history` reports stops resolving at `/view` the moment the
sweep ticks, which can land seconds after a render completes.

Compounding it: SaveImage's filename counter restarts between runs, so
`qwen21ref__00001_.png` gets reused for different images across sessions. A
request for it can therefore 404 while a *different* image already sits in the
gallery under that name.

Two rules, both learned the hard way on 2026-10-28:

1. **Never write a download without checking status and size.** A `/view`
   that returns 404 still yields `r.content == b""`; writing it produced a
   0-byte file reported as a successful frame. Require HTTP 200 *and* a
   plausible length before claiming a keeper.
2. **Fall back to the gallery, don't re-render.** `ref_edit_render.py`'s
   `gallery_recover()` matches a gallery file by seed + the exact
   `TextEncodeQwenImage21` prompt read out of the PNG's tEXt chunk.
   Re-rendering instead is a trap: ComfyUI caches per-node outputs, so
   re-submitting an identical graph returns `execution_cached` on every node,
   completes in ~3s, and hands back the same already-swept filename — a fast
   "success" that produces nothing.

Corollary for long batches: a driver that dies mid-frame is harmless. The
render is still on the server; only the download is missing. Check the gallery
before re-firing anything.

## Ladder over a seed — `ladder_render.py`

The 5-stage recipe applied to an attached seed runs through
`~/.hermes/outputs/Ionga/ladder_render.py`: it holds the ID anchor, the five
stage prompts, the per-stage negatives and the seed lottery, and shells out to
`ref_edit_render.py` once per frame. `--resume` parses `runlog.jsonl` and skips
every `(slug, seed)` already logged ok, so a killed driver restarts where it
stopped. Launch it as a tracked background process with
`persist_on_release=true` — a foreground tool timeout takes the process group
with it and silently kills the batch (this cost a full ladder restart on
2026-10-28).

## Run ledger (2026-10-28, boudoir single frame)

- seed `639417`, Studio ComfyUI, Qwen-Image 2.1 int8, 40 steps,
  resolution 1024, 3:4 crop of a 1024x1024 seed -> **896x1184, 250.1s**.
- Patrick asked for a single frame, so no seed lottery was fired. The pose
  family was the LOW tier (seated upright on the bed edge, front facing, both
  feet planted, both hands on her own thighs = one shared action), which is
  the family that ran 15/15 clean in the staged ladder.
- Pointer pass reported clean on head, hand count, feet, limbs, orientation,
  mirror, clothing and genital focus. Face read late-40s/early-50s, polished,
  not worn (rule 10 fence held). Flagged to Patrick: the hair rendered as a
  chin/above-shoulder bob rather than the seed's shoulder-length loose waves,
  and the pointer described one foot on the bed against the prompt's
  both-feet-planted — pose drift, his eye decides.

## Run ledger (2026-10-28, emerald-satin lounge ladder)

- Setting: the SEED'S OWN ROOM (leather armchair, backlit bottle shelf, brass
  lamp), not a fresh location. The reference latents already hold that room, so
  keeping the prompt in agreement with them is the lowest-drift choice, and the
  green satin blouse gives the ladder a real starting garment instead of an
  invented one. Barefoot from stage 1, per the recipe.
- Garment arc: emerald satin blouse buttoned high + long black skirt -> collar
  open and drawn off one shoulder -> satin pooled at the hips over opaque black
  lace bra and thong -> lace thong only, bare breasts -> entirely nude, legs
  open, explicit.
- 5 stages x 3 fresh seeds, 896x1184 at resolution 1024 off a 3:4 crop,
  40 steps, ~205-250s a frame.
- Two frames hit the gallery-sweep race and both were recovered from
  `~/Pictures/ComfyUI/2026-10/`, verified distinct by pixel diff (mean abs
  diff 22.7) rather than by file size.

## Expression invariance — one seed, one face (2026-11-05)

The Graduate ladder (2026-11-05-graduate-1967, 10 frames, 8 keepers, 2
head-class defects) rendered every frame with the SAME expression. Patrick
called it unprompted: "all the images share the same static expression." Two
mechanisms, neither proven:

1. **The reference latents carry the expression with the identity.** The seed
   was a single portrait holding one face configuration — that unwavering gaze,
   lips slightly parted. Reference conditioning splices those latents into every
   frame, so the expression rides along with the features. One seed in, one
   expression out.
2. **The construction re-asserted it.** The ID anchor ended `poised
   self-assured expression` and the pose clause ended `chin level`, verbatim in
   all ten prompts, and no frame named a different expression, gaze direction or
   unguarded beat. The config comment even recorded "identical clauses every
   frame" as a feature.

Mechanism 2 is visible in the prompt text on disk; mechanism 1 is a guess. The
fix is untested: name a distinct per-frame expression/gaze beat and vary it
across the ladder, kept clear of mouth contact (rule 4). Recorded in the run's
ledger session block under `observations` as `expression-invariance` — run-level
aesthetic, not anatomy, so the keepers kept their clean names.

**Related, same run:** two frames came back with head-class defects
(`head-placement`, and `head-proportion` + `head-placement`) and the pointer
returned every structural field clean on both.

## Refinement 2026-11-06 — the beat has to be geometry, not an adjective

The Southie ladder (2026-11-06-southie-triple-decker, 10 frames, 9 keepers) was
the first run to carry the expression rule. It shipped five named beats, one per
stage, and Patrick still read the first six frames as one static face — "it
seems like we arent varying the facial expressions" — then corrected himself on
the stage-4 frame: "oh wait, this one is varied."

With the beats demonstrably present in the prompt text, the weak landing is the
finding. An adjective at the tail of a ~300-word prompt gets swamped, especially
with reference latents pushing one face configuration underneath it. The
untested fix is to give each beat geometry the way the pose clauses have it: a
gaze direction, a head angle, a small counter-posture (a shoulder turned to the
window, the chin tipped, the weight shifted onto one hip). Geometry survives a
long prompt; mood does not.

## Head proportion — four for four, and the pointer is blind to all of them

The stage-4 frame of the same run was ruled "head is out of scale", making four
instances across three sessions (2026-10-28, two on 2026-11-05, one on
2026-11-06). On every one the pointer returned `head=yes` with H=2, orph=0,
armsImp=no, twist=no, oneWoman=yes. It is the fleet's most consistent defect and
the only one no pointer has ever caught.

Every attempt to control it so far has been a negative fence or nothing at all.
The untested counter-move follows rule 8's precedent — the bust only came right
after it flipped from hiding to a POSITIVE spec — so the ladder now carries
"head correctly proportioned, natural head size, roughly one-seventh of total
body height" on every frame. That is a proposal with no evidence behind it yet;
the run that carries it is the test.

**Pointer SUBJECT field, calibration.** The pointer flagged one frame in each of
these two runs with a "young" read against "adult woman" everywhere else. In the
Graduate run that frame was a real defect (head class); in the Southie run the
flagged frame was kept clean. Now 1-for-2. It stays a look-here pointer whose
stated reason is noise.

## The Casita pose run — a head turned back is its own risk tier (2026-11-06)

`2026-11-06-casita-tao`, 10 frames, 8 keepers, 2 defects. A POSE-VARIETY run rather
than the ladder: six distinct nude poses, non-uniform seed counts (3 on the strict
rear, 2 on the recline and the three-quarter back, 1 on each safer pose). New
backdrop, picked for having a bed, a rug and a deep window sill so every requested
pose had a real surface.

**The finding.** Both defects were heads on TURNED-BACK poses, and nothing else in
the batch broke:

| frames | head position | outcome |
|---|---|---|
| `p02_tq_back_410074`, `p03_rear_spread_760301`, `p03_rear_spread_580183` | turned back | keep |
| `p02_tq_back_250055` | turned back | **pass — head-placement (unnatural rotation)** |
| `p03_rear_spread_913791` | turned back | **pass — head-placement (strange position)** |
| recline x2, rug, bed edge, standing | facing the lens | keep, all five |

2 of 5 turned-back heads failed, 0 of 5 lens-facing. That is the ~half rate the high
tier is documented to produce, but on a failure mode the tier list did not name:
not pose drift, not limbs — the neck. Rear-facing should not be one family.

**The counter-move is untested.** Bound the turn rather than describing the head:
"her head turned back only partway over her shoulder, chin near her shoulder, neck
at a natural angle", beside the existing "neck twisted the wrong way" negation.
There is a real tension here — bounding the turn also caps how far a per-frame
expression beat can move the head, so expression variety and head safety pull
against each other on rear frames.

**The proportion spec was aimed at the wrong half.** Every frame of this run carried
"head correctly proportioned, natural head size, roughly one-seventh of total body
height". Both defects are ORIENTATION, not size. The proportion half of the head
class is therefore unexercised by this run — not disproven, never tested. Size and
orientation are separate classes with separate levers.

**The expression refinement, graded.** Third data point on the expression rule:
adjectives only -> "all the images share the same static expression"; adjective
beats without geometry -> six frames read as one face; geometry beats (this run) ->
"somewhat varied, but not dramatically". Monotonic improvement, still short. The
remaining suspect is the reference latents themselves, which no prompt removes.

**The seed lottery paid out.** Non-uniform budget behaved exactly as designed: the
hardest pose got 3 seeds and produced 2 keepers, the second hardest got 2 and
produced 1, the recline got 2 and produced 2. A uniform one-seed-per-pose run would
have shipped a third of the rear set.

**Pointer scorecard, now three runs.** Five flags raised, zero carrying signal: one
`H=1` hand count (ruled keep), one `twist=yes` (ruled keep), three SUBJECT-field age
reads splitting both directions inside one batch. Use it as a look-here pointer and
nothing more.

## The Lisbon A/B — how to test a prompt lever, and what happened when we did (2026-11-06)

`2026-11-06-lisbon-ab`, 10 frames, 8 keepers, 2 defects. A PAIRED A/B TEST rather
than a shoot, run because three sessions had produced 25 keepers and 5 defects with
every defect a head, and the two halves of that class need opposite levers.

**The design, which is the reusable part.** Two poses, two arms each. Arms within a
group render at the SAME seeds, and the prompts are identical apart from one clause.
The driver now enforces that: it refuses to fire if two arms differ by more than the
intended clause or if their negatives differ at all, and it prints the receipt before
spending a GPU-second — rear pair differed over 109 of 1945 chars (shared prefix
1205, suffix 631), front pair over 210 of 2159 (prefix 1191, suffix 758). That is what
makes the result attributable. Without it, a difference between arms is
indistinguishable from seed luck — which is exactly what made the previous three runs
unattributable.

**LEVER A (bounded head turn): NULL.** 3 seeds x 2 arms, all 6 frames keepers. The
only faults landed at seed `881822`, in BOTH arms equally (`-qc-minor` on 216 and
217). At every paired seed the arms matched. The unbounded wording — the one that
produced two hard Casita defects — produced three clean keepers here. **The head-turn
fault is seed-determined, not wording-determined.** The bounded-turn counter-move
must not be cited as a fix.

**LEVER B (orientation beat): PARTIAL.** Seed `881822`: orientation **more dynamic**,
gaze-only **more natural**, both keepers — the pre-registered criterion met, and bought
by trading away naturalness. Seed `664628`: both arms defective on set-perspective, so
uninformative for the lever. One of two seeds scorable.

**The free inference from pairing.** At `664628` both arms broke the same way while
sharing every clause except the beat. So the beat cannot be the cause of a fault
common to both — the trigger is in the shared text (the room description or the
seating clause) or in the seed. A single-arm run could not have told us that.

**The honest summary.** Neither lever beat seed luck. Across four paired seeds the
outcome tracked the seed, not the wording. THE CORE FINDING — the seed is the deciding
variable — held up under a controlled test for the first time.

**Also new:** `set-perspective / depth` as a defect class (2 instances, both machine-clean).

## The Milan 20-frame run — the seed lottery bug, and what the face measurement showed (2026-11-06)

`2026-11-06-milan-suite-escalation`, 20 frames, 10 escalation rungs x 2 seeds, run
UNGATED on request (no feedback, start to finish). No keepers filed, by design.

**The bug that shaped the whole run.** Every rung drew the same two seeds
(930250, 388640) — two distinct seeds across twenty frames. Cause: `fresh_seeds()`
constructed its `random.Random` inside the function, so all ten calls redrew the
same first two values. Disclosed at frame 16 of 20, not at close-out. Fixed:
`ladder_render.py` now builds one module-level `_SEED_RNG` per run.

**The face measurement.** Patrick's read was "basically only 3 or 4 variations on
the face across the whole set." Measured programmatically rather than agreed with:
head region cropped from all 20 frames, each pair aligned over a small shift
search to remove framing jitter, MAE computed. Two crops were tried — a wider
head-and-shoulders box and a tight face box:

| crop | same-seed median MAE | diff-seed median MAE | ratio |
|---|---|---|---|
| head + shoulders (270x195) | 12.51 | 21.90 | 1.75x |
| tight face (145x105) | 15.25 | 32.57 | 2.14x |

The seed outweighs the prompt on the face, and the effect is STRONGER on the
tight crop — so it locks the face itself, not just the hair and lighting around
it. But the within-column spread (3.74-27.70) overlaps the across-column range
(9.84-53.80), so the ten different beats DO move the face; they just cannot make
a face the seed does not contain. Two seed families x ~2 visual reads each is the
three-to-four faces Patrick saw. **The count was capped before the first frame.**

Method limits worth keeping attached: the cluster count came back as one group,
which is a single-linkage chaining artifact and was NOT reported as a finding —
the median ratio is the finding. MAE on a 145x105 crop also picks up hair
position and lighting, not only the face. Alignment search was +-16px at full res.

**Lesson:** do not record a failed expression attempt as a wording failure until
the run has had a proper seed lottery. This is the test still outstanding: hold
one rung's prompt FIXED, vary only the seed across ten draws, and re-run the crop
measurement. More faces means the lever was never the problem; a handful of faces
means the reference latents dominate regardless of noise.

**Structural change from this run.** The driver is now shared and each run is a
config module it loads (`run_override.py` beside `ladder_render.py`) — one
renderer, one config per run, no forked renderers. A 20-frame run is now a ~200
line config instead of an edit to a 500 line script.

## The seed-diversity probe — the question settled (2026-11-06)

`2026-11-06-milan-seed-probe`, 10 frames, a measurement set rather than a shoot.

**Design, and why it is the cleanest test in this thread.** ONE rung's prompt held
byte-identical — read verbatim out of the Milan run's own `s24_milan_r07.prompt.txt`
and `.neg.txt` (sha256 `3027a0e344d02867` both sides) rather than retyped — with TEN
distinct seeds. Same seed image, room, pose, garment state and lighting clause. The
seed is the only thing in the run that moves. Ten distinct seeds were drawn with no
repeats, which also confirmed the once-per-run RNG fix under load.

**Scoring.** Same head-crop / aligned-MAE script as the Milan measurement, with the
Milan `r07` pair (two KNOWN different seeds at this exact prompt) as the anchor.

- anchor, two known-different seeds: **MAE 19.02**
- probe, 45 pairs among 10 seeds: median **30.22** (q25 21.69, q75 39.44, min 13.11, max 49.42)
- pairs fall below 0.75x anchor: **3 of 45**
- probe median / anchor: **1.59x**
- complete-linkage at the anchor threshold: **6 clusters from 12 frames**
- and the method validates itself: the two Milan anchors landed in DIFFERENT clusters

**Result: face diversity scales with seed count.**

| run | prompts | seeds | distinct faces |
|---|---|---|---|
| Milan escalation | 10 different | 2 | 3-4 |
| seed probe | 1, fixed | 10 | ~6 |

Ten seeds at a single prompt produced more face variety than twenty frames from ten
different prompts did. **Seed count beats prompt count.** The expression rule was
never the whole problem; it was operating inside a two-drawer box, and two earlier
attempts were logged as wording failures on that basis.

**Nuance worth keeping:** 3 of 45 pairs were notably more similar than the anchor, so
the seed is a LOTTERY, not a dial — some draws collide. And complete-linkage at the
anchor distance groups conservatively, so six is a floor on distinct faces, not a
ceiling.

**Method limits:** MAE on a 145x105 crop picks up hair position and lighting, not only
the face; the alignment search is +-16px at full res; first measurement's cluster count
came back as one group under SINGLE linkage, which chains everything — use complete
linkage or the count is meaningless.

**Launch pitfall, cost one log:** `... python3 driver.py | tee runs/<dir>/batch.log`
fails when the run directory does not exist yet — `tee` opens the file before the
driver creates the dir, tee dies with "No such file or directory", and the run
completes with no log on disk. `mkdir -p` the run directory first.




