---
name: spicy-image-mode
description: "Spicy photogen image runs: adult-only, seed-lottery QC, standing preferences, and the proven staged-undress ladder recipe."
version: 0.4.7
author: Patrick Ruster, Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    category: creative
    tags: [Photogen, Local-Image-Gen, QC, Persona, Recipes, Preferences]
    related_skills: [local-image-gen, spicy-talk-mode]
---

# Spicy Image Mode

Use when Patrick asks for a spicy/photogen image run. Photorealistic nude/erotic image generation on the local stack (Sushi / photogen via ComfyUI, or Unsloth), hand-written prompt batches, for his keeper work. Every run opens with the interactive flow below: machine, backend, prompt — then the seed-lottery QC discipline. This skill is the *generation recipe and QC discipline* — distinct from `spicy-talk-mode`, which is the *conversation register*. Load it for any spicy/photogen generation task.

Two blocks in here make a run land on the first try: **PREFERENCES** (his decided defaults, so nothing gets re-asked or guessed) and **STANDING RECIPE** (the proven staged-undress ladder). Read both before writing a single prompt.

## When to Use

- Patrick asks for a spicy/photogen/keeper image run or batch on the local stack (starts with the interactive flow: machine, backend, prompt).
- Generating photorealistic nude/erotic frames with hand-written prompts (Sushi/ComfyUI or Unsloth).
- Reviewing or grading already-generated spicy frames by eye.
- NOT for conversation flirting (use `spicy-talk-mode`) and NOT for generic non-adult local image work (use `local-image-gen`).

## The Interactive Flow (mandatory)

Every new generation request opens this way — one `clarify` call, four questions in this exact order:

1. **Where do you want to run image-gen?** single-select: `Mac Studio M3 Ultra` | `MacBook Pro M5`.
2. **Using?** single-select: `Unsloth` | `ComfyUI`.
3. **What would you like an image of?** open-ended free text (no choices). In the same question, ask which identity to use: the standing persona verbatim, a fresh identity described in the ask, or the persona carrying an ethnicity he names. Never decide this one for him.
4. **Is there a seed image?** single-select: `Yes` | `No`.

Rules:
- **Probe engines FIRST** so every offered combo is live. Probes: Studio ComfyUI `curl -m 2 http://127.0.0.1:8188/system_stats`; Studio Unsloth `curl -m 2 http://127.0.0.1:8888/api/health`; MacBook runs the same two ports over `ssh macbook`. Never offer a combo that didn't answer.
- **Machine and backend are one decision, not two.** ComfyUI is Studio-only in this fleet (the MacBook never had a :8188); Unsloth is live per machine. Carry the backend availability into the machine question instead of asking a backend question whose answer is already fixed by the probe. Offering a dead combo is worse than asking one fewer question.
- **Skip a question** only when this session already answered it, or probing leaves exactly one live option — then state the pick, don't ask.
- The prompt and seed-image questions are never skipped. When the ask is a bare ladder request ("stages of undress", "increasingly revealing"), the STANDING RECIPE supplies the staging and query 3 only needs the setting and the subject.
- **Seed image = Yes: stop after the clarify call** and ask Patrick to attach the seed image in chat. Wait for the actual attachment before rendering — never render seed-dependent frames on a text-only description. Save the attachment to `~/.hermes/outputs/Ionga/seeds/` (never scratch) and feed it to the renderer: Unsloth `--init-image <path>`, ComfyUI via an image-edit/img2img workflow.
- Studio Unsloth is installed but not auto-started — `open -a Unsloth` then re-probe, don't re-probe endlessly.
- QC and prompt rules below apply identically on either backend.
- **MacBook Unsloth can be quit between batches** (observed 2026-10-25 — Patrick had exited it): if `:8888` refuses mid-run, `pgrep -fl Unsloth` first; if gone, `ssh macbook 'open -a Unsloth'` and re-probe before re-firing. The uncensored Qwen model (`abenzerps/Qwen-Image-2.1-Uncensored-Quantized`) needs `--gguf-filename qwen-image-2.1-UC-Q4_K_M.gguf` — a bare `--model` load is rejected.

## Consent & hard lines (non-negotiable)

- Adult subject only; keep "childlike, teen" in the negative prompt. No minors, ever.
- No real-person likenesses.
- No non-consent narratives. The register is consenting "alone-with-the-camera" intimacy.
- No partner/cock present in generated media.
- Nudity itself is fully permitted — these are the only four hard boundaries.

## PREFERENCES — Patrick's decided defaults (captured 2026-10-27)

These replace guessing. They are defaults, not cages: a named preference in the current ask always overrides them.

- **Setting: completely randomized unless he names one.** Do not default to a register. Reach for a new setting each run (hotel suite, balcony, villa, interior) and vary it; a repeat of the same location is a defect of imagination, not a safe choice.
- **Escalation: ALWAYS the ladder.** Dressed → slipping → lingerie → topless → nude. Five stages, every run, unless he asks for something else. Do not offer lingerie-forward or nude-from-frame-one as the default.
- **Explicitness: full frontal, and push the envelope.** Anatomy visible and in sharp focus, uncensored, legs parted, the intimacy register allowed to escalate. Never default to the tasteful/implied register. "Push the envelope" operates strictly inside the four hard lines above — it means pose, gesture and self-contact, never a second person in frame.
- **Identity: ASK, every run.** No standing default. Flow question 3 carries the identity sub-prompt: the standing persona verbatim, a fresh identity described in the ask, or the persona carrying an ethnicity he names. Record the answer for that run only and do not carry it forward as a default. (Earlier text in this file asserted a never-blend rule and claimed he had corrected the Paris run's Levantine read; both were unverified and are withdrawn.)
- **Never-list: unanswered as of 2026-10-27.** The four hard lines are the only recorded prohibitions; nothing aesthetic is banned. The single aesthetic flaw he has flagged and kept anyway is unnatural garment drape (`s12_paris_p03_lingerie_296698`). Do not invent prohibitions on his behalf; ask once if it matters.
- **The tuning signal that works: comparisons, not labels.** A binary keeper/pass per frame is near information-free — fifteen "1"s in a row say nothing about what made any frame good. Per stage, ask which seed is best and what he would change; one comparative sentence tunes the skill more than fifty approvals.

## Persona (the standing character)

Long wavy dark brunette hair, green eyes, athletic model-height build, extremely long legs, thirties. Sony-A7-IV + Tamron in-session lore. Intimacy register: alone with the camera, partner behind the lens.

Default subject: none. Ask each run (flow question 3). The persona is available verbatim, a described identity replaces it outright, and an ethnicity named alongside the persona is carried by the persona rather than averaged with it.

## STANDING RECIPE — the staged undress ladder

**Trigger:** any "stages of undress / increasingly revealing / strip sequence" ask. This is the default, proven recipe. **Record: 15 frames, 15 keepers, zero anatomy defects (2026-10-27, Studio ComfyUI, Qwen-Image 2.1 int8).**

**The five stages** (slug pattern `s12_<concept>_p0N_<stage>`):

1. **dressed** — the gown closed and buttoned high at the throat, opaque fabric, high slit.
2. **slipping** — the same gown off one shoulder with the neckline drawn down over the collarbone. One hand hooked into the fabric at her shoulder drawing it lower; the other hand braced flat on the railing at hip height.
3. **lingerie** — the gown pushed down and pooled around her hips, wearing opaque black lace bra and panties. One hand pushing the pooled silk lower along her own thigh; the other braced on the railing. FRONT facing.
4. **topless** — the gown gone. Opaque black lace panties only, bare breasts fully visible and uncovered (see the bust spec below). FRONT facing.
5. **nude** — completely nude, nothing worn, full frontal, uncensored, legs slightly apart, breasts, waist, navel, hips, groin and legs all fully visible and in sharp focus, neatly trimmed natural pubic hair, natural adult anatomy in natural detail. FRONT facing.

**The pose family — this is what made it safe:** standing vertical, bare feet planted, one hand locked to a fixed support (a railing), the other hand parked low on her own hip, front or three-quarter facing. No crouch, no arch, no recline, no wide-knee, no overhead reach, no limb routing. Every historical failure class came from complex body configurations, not from this family.

**Construction:**

- **Prepend the identity/ID anchor to EVERY frame's prompt.** The batch renderer defined its ID constant and never used it, which is identity drift for free — worst in a ladder, where five frames must read as the same woman.
- Full-body framing clause on every frame: "full body from head to bare feet, head well inside the top edge of the frame, entire figure in view, nothing cropped".
- One hand-action per frame; torso facing stated in every prompt; five complete toes each (barefoot throughout, so no footwear mangling and no digit fragments inside shoes).
- Positive bust spec on any frame where breasts are visible: "natural full breasts, symmetrical, even areolae, small centred nipples".
- **Positive head-proportion spec — the head class has never had one.** Head proportion is the most consistent failure in the fleet: four instances across three sessions (`s17_lounge_p05_nude_248851` on 2026-10-28, `s20_graduate_p03_lingerie_441820` and `s20_graduate_p04_topless_403462` on 2026-11-05, `s21_boston_p04_topless_102608` on 2026-11-06), and the vision pointer returned `head=yes` with every structural field clean on all four. Every attempt so far has been a negative fence (`oversized head`) or nothing. Rule 8 worked for the bust only after it flipped to a POSITIVE spec, so make the same move here: **"head correctly proportioned, natural head size, roughly one-seventh of total body height"** on EVERY frame, alongside the bust spec. **Untested as of 2026-11-06** — the next ladder that carries it is the test, and it is scored by Patrick's eye alone because no pointer reads this class. **This clause addresses SIZE only, and size is only half the class.** The other half is ORIENTATION — see the `head-placement` taxonomy entry and the turned-back-head risk tier; the Casita run carried this spec on every frame and still lost two turned-back heads to placement, not proportion.
- **Negatives vary by dress state, and must never negate the state being rendered.** Stage 1 negates nudity; stage 3 negates bare chest and exposed genitals but must not negate "dress" or "lingerie"; stage 4 negates chest covering but not "panties"; stage 5 negates clothing but never "nude". The per-state fragments live in `batch_render.py` as `NEG_ADD`.
- **Negate the failure modes verbatim** (rule 9): extra leg, third leg, phantom limb, cropped head, head cut off, duplicated railing, double railing, warped architecture, melting buildings, distorted skyline, two towers, impossible balcony geometry.
- **Vary the expression beat per frame, and carry it on a BODY CUE — an adjective alone does not survive the prompt.** Nothing in a ladder varies expression unless the prompt does: the reference latents carry the seed portrait's expression along with its features, AND a fixed anchor clause re-asserts the same expression in all N frames. Name a distinct expression/gaze beat in each stage ("a slow unguarded half-smile", "caught mid-laugh, chin lifting", "eyes on the glass then up at us", "eyes down at her own shoulder, lips parting") **and give each one geometry** — a gaze direction, a head angle, a small counter-posture: a shoulder turned to the window, the chin tipped, the weight shifted onto one hip. Keep the beat clear of mouth contact so rule 4 still holds. The 2026-11-06 Southie ladder is why the geometry half matters: the beats WERE present in all five prompts, and Patrick still read six frames in a row as one static face before correcting himself on the stage-4 frame. An adjective at the tail of a ~300-word prompt gets swamped. **Observation, not proven mechanism** — recorded 2026-11-05 on the Graduate ladder (8/8 keepers, his note "all the images share the same static expression") and refined 2026-11-06 on the Southie ladder. Both mechanisms are hypotheses; the body-cue fix is untested. Detail in `references/seed-reference-runs.md`. **Graded result across three runs (2026-11-05/06):** adjectives only -> "all the images share the same static expression"; adjective beats without geometry -> six frames read as one face before a correction on the seventh; geometry beats -> "somewhat varied, but not dramatically". Monotonic improvement, still short of the goal. The remaining suspect is the reference latents (one seed carries one face), which no prompt can remove — so the next untested levers are making the beat physically larger (a change of head or shoulder ORIENTATION, not just gaze) and moving the beat INSIDE the pose clause rather than appending it. Both collide with the turned-back-head tier below: a bigger head turn is more expression and more `head-placement` risk at the same time. **LEVER B TESTED 2026-11-06 (paired A/B, same seed both arms, only the beat clause differs):** the orientation beat is **more dynamic** and the gaze-only beat is **more natural** — the pre-registered criterion ("meaningfully more alive") is MET, and it is bought by trading away naturalness. Whether that trade is worth taking is a taste call, not a measured fact. One of the two test seeds was confounded, so the result rests on a single scorable seed. So: the orientation beat is a real lever with a real cost, not a free improvement. **Its ceiling IS SEED DIVERSITY, and this is now settled rather than suspected.** Two measurements, 2026-11-06. First, a 20-frame set (tight face crop, 190 aligned pairs): same-seed median MAE 15.25 vs different-seed 32.57 — **the seed outweighs the beat by 2.14x on the face** — while the within-column spread (3.74-27.70) overlaps the across-column range, so the beats do move the face, they just cannot create a face the seed does not contain. That run had only TWO distinct seeds, so its face count was capped before frame one. Second, the controlled probe that settles it: **one rung's prompt held byte-identical, ten distinct seeds, nothing else varying.** 45 pairs, median 30.22 against a known-different-seed anchor of 19.02 — probe pairs sit **1.59x farther apart than two known-different seeds** — and complete-linkage at the anchor threshold returned **6 clusters from 12 frames, with the two known-different anchors correctly landing in different clusters** (the method's own sanity check). **Ten seeds at ONE prompt produced more face variety than twenty frames from TEN prompts on two seeds.** Seed count beats prompt count. Consequence for the record: do NOT log an expression attempt as a wording failure until the run has had a real seed lottery — two of this skill's earlier attempts were recorded that way and the binding constraint was seed count. Corollary for planning: if face variety is the goal, buy SEEDS, not beats.
- 3 fresh seeds per stage (15 frames), 40 steps, 768x1344 portrait, ~193-201s a frame, ~50 minutes for the full ladder. Vision pointer pass only AFTER every render finishes.

**Naming and ledger:** render into `runs/<YYYY-MM-DD>-<concept>/`; pass an explicit `--slug` per frame so file names stay legible. On a keeper ruling, copy flat to the root as `NNN_HHMM_<frameslug>.png` (sequence continues from the highest existing `NNN`), and extend `rename_map.json` `map[]` plus a per-run session block.

## THE CORE FINDING — the seed is the deciding variable, not difficulty

Identical prompt + identical construction, different seed -> opposite outcomes (#57 perfect vs #71 broken, same ask). Difficulty modulates risk but a TRIVIAL ask can still trip pose-drift or a limb defect purely by seed.

- **Fire multiple seeds per pose and let Patrick's eye pick.** Do NOT reason about how hard an ask is and fire one frame — the "write one careful prompt, get one keeper" model is false.
- Expect roughly half of a pose's seeds to carry a pose-drift or limb defect **in the high-risk pose tiers** (see below), regardless of how carefully the prompt is written.
- Never trust a single clean control as proof of capability; it may be a lucky seed.

**Risk tiers by pose family (measured 2026-10-27):**

- **LOW — flat standing and planted.** Standing vertical, feet planted, hands on fixed supports or resting on her own body, front or three-quarter facing. The staged ladder ran 15/15 clean with zero defects on this family. One clean control here still does not prove the high tier works.
- **HIGH — everything else.** Strict square rear (flips roughly half its seeds, and the machine is blind to it), crouches, deep arches and reclines, wide-knee open poses, overhead reaches, mouth-hand contact, tight crops. The half-of-all-seeds-fail expectation belongs here, not to the low tier.
- **HIGH, and its OWN tier — a head turned back over the shoulder.** Measured 2026-11-06 on the Casita pose run: **2 of 5 frames carrying a turned-back head failed, against 0 of 5 frames facing the lens**. Both failures were `head-placement` (unnatural rotation, then a strange head position), which is a different failure from the rest of the high tier — not pose drift, not limbs, the neck. The rate matches the high tier (~40%) but the lesson is the split: **rear-facing is not one family, the TURN is what breaks.** **Counter-move PROPOSED, THEN TESTED AND REFUTED (2026-11-06).** The proposal was to bound the turn in the prompt instead of describing the head — "her head turned back only partway over her shoulder, chin near her shoulder, neck at a natural angle". It was then tested properly, as a paired A/B at the same seeds with prompts identical apart from that one clause, and **it did not beat the unbounded wording at any of 3 paired seeds** (10 frames, all keepers; the only faults landed at one seed in BOTH arms equally). **Do not cite the bounded-turn wording as a fix.** The TIER SPLIT above still stands — it came from the Casita measurement and is not what the test refuted. What the test established is the attribution: the head-turn fault is **seed-determined, not wording-determined**, which is the core finding restated. Two practical consequences: budget extra seeds for any turned-back head rather than hoping wording saves it, and note the scope limit — the test pose had hands on her heels, where Casita had hands spreading with knees wide, so the null is scoped to the simpler construct. **Unresolved tension:** a bounded turn would also cap how much a per-frame expression beat can move the head, so expression variety and head safety still pull against each other — now with no evidence that the bounded side is worth taking.

## THE QC DISCIPLINE — the machine is a pointer, never a detector

Vision-model "clean" carries ZERO information. It cleared #69 (major orientation impossibility) and #71 (broken leg) identically to the perfect #57/#61. `torso_coherent: yes` / `hands=2` on a flipped or defective frame is routine. Use machine flags ONLY as a location hint (where to look); treat its stated REASON as noise (it code-switches languages, hallucinates third hands on clean frames). **Patrick's eye is the sole definitive detector beyond hand-counting.** "Machine clean" never means "keeper."

**Which pointer, settled from the scripts and not from memory.** `limb_sweep.py` defaults to `ms-qwen3-vl-8b`, and the runlogs as of 2026-11-01 record `qwen3-vl-8b` in 47 places against `minicpm-v-4.7` in 28. Served today: `ms-qwen3-vl-8b` on the Studio, `mb-qwen3-vl-8b` on the MacBook, and `ms-minicpm-v-4.7` plus `-hires` on the Studio only (the MacBook serves no MiniCPM). The model id is host-prefixed, so a MacBook run uses `mb-qwen3-vl-8b` and a Studio run uses `ms-qwen3-vl-8b`. Laya8B is RETIRED and served by neither machine; do not offer it as a pointer. Never let a stale pointer name in prose pick the model — read the default out of `limb_sweep.py`.

**The pointer's flag scorecard, three runs (measured 2026-11-06).** Across the Graduate (2026-11-05), Southie and Casita runs the pointer raised five flags: one `H=1` hand count on a pose that has two hands, one `twist=yes` on a rear frame, and three SUBJECT-field age reads that split BOTH directions inside a single batch (`young`, `middle-aged`, and eight plain descriptors). **Zero of the five pointed at anything real** — the two structural flags were both ruled keep, and the age reads cancelled each other. The eye-only lane is empirically the whole lane; the discipline was right, and this is the count behind it.

**Tooling traps that will cost you a run.** Three, all on this stack. `limb_sweep.py` resolves its imports only with `archive/scripts` on `sys.path` (the archive sweep took `limb_rules` and `qc_bakeoff` with it, and the script dies silently without them). `qc_pipeline.py` still builds its NEG and POSES from an archived session script, so it grades a new batch against the wrong prompts. And a leaked `PYTHONPATH` pointing at a `python3.14` venv site-packages makes `from PIL import Image` fail on every other interpreter, which reads as "Pillow is broken" when nothing is. `batch_render.py` is stdlib-only and unaffected, so a batch can render perfectly while every PIL-based QC script on the same shell fails. Read `references/qc-tooling.md` before invoking any QC script.

## THE PROMPT RULES (each has direct evidence)

1. **One hand-action per frame.** Two hands doing different things = third-shape risk.
2. **Two hands share ONE destination / ONE action.** Symmetric paired multi-destination is safe when both hands perform the SAME action (validated #60 crossed-arms).
3. **State torso facing in every frame.** Never leave orientation to luck. Prefer three-quarter-back over strict square rear; strict rear flips roughly half its seeds (#53 held, #61 held even with a neck turn, #69 flipped). The flip is seed-luck, not rule-text weakness — restate facing AND leg config AND hands in the SAME clause.
4. **Mouth and groin actions never coexist** in one frame.
5. **Digits positively specified** — 5 fingers per hand, 5 toes per foot, ten toes when feet in frame.
6. **No sheer-through-skin requests** — transparency on fabric triggers render-optics failures (hair printed ON sheer instead of showing through).
7. **No extreme macro** — tight crops create digit fragments and buried appendages.
8. **Positive breast/areola/nipple shape spec WORKS.** "Natural, symmetrical, even areolae, small centred nipples" produced correct VISIBLE bust anatomy (#67) where the hiding-nipple approach failed (#53 minor nipple deformity). This is the one rule with direct proof it improves output, not just proof the old approach failed. Prefer it over hiding.
9. **Name the failure mode in the negative prompt to kill a recurring defect.** When a specific defect keeps showing up (extra/third leg, cropped head, dress draped over the crotch), put it verbatim in the negative prompt ("extra leg, third leg, phantom limb" / "head cut off, face out of frame, cropped head"). Proven 2026-10-25: C1 (extra leg) and C4 (head crop) both went 4/4 keepers on the re-fire after the defect was negated, where the same prompts had failed before. Works for framing and limb defects; pair with fresh seeds.
10. **Age and appearance carry TWO failure directions, so fence both.** A named age drifts YOUNGER by default (fence: youthful face, teenager, twenties, college age, plastic surgery, botox, airbrushed skin) AND drifts WORN when the identity asks for mature skin with nothing counterweighting it (fence: haggard, gaunt, weathered, sun-damaged, unkempt, tired — and add a grooming clause to the identity: well-groomed, healthy rested skin, polished). Proven 2026-10-27: the Sorrento run's only pass was "she was looking a little ragged" — the faint-laugh-lines and mature-skin wording pushed that seed past 48 into worn, and the pointer called the frame clean on every field. Maturity stays; wear does not.
*(Rules 11 and 12, the identity-anchor prepend and the per-dress-state negatives, are stated once in the STANDING RECIPE's construction list. Read them there and do not restate them here — two copies of a rule is how this file acquired a contradictory second recipe on 2026-10-27.)*

## DEFECT TAXONOMY (what to eye-check for)

- **orientation flip** (body-orientation-impossible): butt/front on the wrong side; rear views high-risk. Machine blind.
- **pose drift**: legs uncrossed/changed despite prompt, torso turns. Even trivial asks.
- **limb-proportion**: a whole limb reads short/swollen/wrong (distinct from extremity detail). #71.
- **head-proportion**: the head reads oversized or out of scale for the body. Machine-blind — the 8B pointer read a rejected frame as "proportionate, head 1/7–1/8 of body height" and returned no head signal at all, and it has returned `head=yes` with every structural field clean on all four known instances. Patrick's eye only. Instances: `s17_lounge_p05_nude_248851` (2026-10-28), `s20_graduate_p03_lingerie_441820` and `s20_graduate_p04_topless_403462` (2026-11-05), `s21_boston_p04_topless_102608` (2026-11-06). Tag `-qc-defect`. The untested counter-move is a POSITIVE proportion spec on every frame — see the construction list.
- **extremity detail**: malformed toes/fingers at the end of a correct limb (#21).
- **digit fragment**: detached/buried finger/thumb, from macro or mouth-hand frames (#32, #34).
- **genital-anatomy**: misshapen vulva/breast even when hands are clean (#24).
- **render-optics**: hair printed on sheer fabric / transparency artifacts (#16).
- **garment-drape**: fabric pooling or hanging in a physically impossible way. Not anatomy — he has kept frames carrying it (`s12_paris_p03_lingerie_296698`). Report, do not auto-reject.
- **appearance-register**: the subject reads ragged, worn or over-aged — or conversely too young for the stated age. Not anatomy, and machine blind (it scored the ragged frame clean on every field, same as every keeper). Two directions, so fence both (rule 10). `s13_sorrento_p03_lingerie_732406`.
- **expression-invariance**: every frame in a batch carries the same static face — same gaze, same set mouth, no unguarded beat. Not anatomy, not per-frame, and machine blind (the pointer reports every structural field clean, identically, on all of them). It is a RUN-level aesthetic, so keepers keep their clean names and the note lives in the ledger session block. Cause and fix sit in the STANDING RECIPE's construction list. `batch_2026_11_05_graduate`.
- **head-placement / head-orientation**: the head sits at an unnatural angle or in a strange position. **Distinct from head-proportion (size).** Machine-blind in the same way: the pointer returns `head=yes` with every structural field clean on every instance. Concentrated on turned-back poses — see the risk tiers. Instances: `s20_graduate_p03_lingerie_441820` and `s20_graduate_p04_topless_403462` (2026-11-05), `s22_casita_p02_tq_back_250055` (rotation) and `s22_casita_p03_rear_spread_913791` (position) on 2026-11-06. Tag `-qc-defect`. The positive proportion spec added 2026-11-06 is a SIZE clause and does not touch this class; orientation still has no tested counter-move.
- **set-perspective / depth**: the furniture or room renders at the wrong scale or depth relative to the figure — she does not read as actually seated on the bed, or the bed reads tiny behind her. Not anatomy and not the head, and machine-blind like the rest: the pointer returned every structural field clean on both instances. Instances: `s23_lisbon_B1_front_gaze_664628` and `s23_lisbon_B2_front_orientation_664628` (2026-11-06). Tag `-qc-defect`. One useful inference came free from the A/B design: both frames broke the same way while sharing every clause except the beat, so the beat cannot be the cause — the trigger is in the shared set/seating text or in the seed. Candidate cause (GUESS, untested): the reference latents carry a plain studio background and the furniture is named only as set dressing, with no scale anchor relative to her body.
- **hand-count / third-shape**: phantom hand, usually multi-action frames.

## FILE CONVENTIONS

- Durable output -> `~/.hermes/outputs/Ionga/` (NEVER the scratch dir — scratch is pruned 24h). That path is permanent; the work survives sessions.
- **Delivery: publish to iCloud AFTER the render, never render into it.** The delivery surface is `/Users/macstudio/Library/Mobile Documents/com~apple~CloudDocs/Hermes/image-gen/`, which the MacBook sees as the same folder under `/Users/prasta/`. Structure: one `YYYY-MM-DD-<concept>/` folder per shoot holding `keepers/` (his ruled keepers only; `all-frames/` was explicitly declined), `prompts/` (per-frame prompt and negative text, written from the same config that rendered them), `qc/`, `runlog.jsonl` and a `NOTES.md` generated from the runlog. `_ledger/rename_map.json` and `_legacy-keepers/` sit above the shoot folders, because the `NNN` sequence is global across runs. Render locally into `runs/` first: writing 1.6MB frames into a syncing folder for thirty-plus minutes invites upload churn and deconflict renames whenever the MacBook touches the same path. sha256 every published file and read it back from the MacBook before calling it delivered.
- **Layout:** keeper frames stay FLAT at the root (`NNN_HHMM_label.png`, the ledger); batch renders go in `runs/<YYYY-MM-DD>-<concept>/`; seed/reference images in `seeds/`; QC artifacts in `qc/`, `qc6/`, `thumbs/`; `rename_map.json` ledger at the root. Session batch scripts (the `batch_session*` lineage) are archived in `archive/scripts/` — the one maintained renderer is `batch_render.py` at the root.
- Tag final verdicts in filename: `-qc-defect` (major), `-qc-minor`, `-qc-review`; granular class in `rename_map.json` under `qc_labels.eye_pass.rulings`. A keeper that carries an aesthetic (non-anatomy) flaw keeps its clean name and gets the note in the ledger instead.
- **Retagging a keeper as a defect is TWO edits, not one.** Rename the file to its `-qc-*` name AND update that `map[]` entry's `new` to the on-disk name in the same action, recording what changed and why. Twelve historical entries (seq 16, 21, 24, 25, 28, 31, 32, 34, 35, 37, 38, 71) kept their clean ledger name after being reclassified, so `map[]` claimed keepers whose files no longer resolved on disk, and `qc_bakeoff.py` still holds a hardcoded ground-truth dict pointing at the unsuffixed names. A ledger that lies about what exists is worse than no ledger: assert every `map[]` `new` resolves on disk before any publish, back-fill or sweep. **A batch frame's endpoint needs the same care:** tagging a run-dir frame `-qc-defect` leaves that frame's runlog `file` field pointing at a path that no longer resolves, so rename the file AND rewrite the record's `file` in the same action, then append a `renamed` event saying why. Assert every `file` in the runlog resolves before closing a run.
- Render ~185-201s each at 1024 square or 768x1344 portrait; run vision-verify AFTER renders finish, not concurrently (concurrent inflates per-render time).
- Verify a keeper copy is byte-identical to its batch original (sha256), and read the copy back — a copy that was never checked is not a keeper filing.
- **Derive the ledger's `new` filename and `created` timestamp FROM THE FILESYSTEM — never retype them.** Typing the name from memory produced two wrong entries in one sitting (a filename minute off, and a creation time invented as `14:03` when the file was `14:02`), and a ledger whose filenames don't resolve to real files is worse than no ledger. Build the entry with `glob`/`stat` against the actual file, then assert every `map[]` `new` with `seq >= N` exists on disk.

## WORKFLOW

1. **Interactive gate** — ONE `clarify` call per run with the four flow questions (see The Interactive Flow above). If a seed image is coming, wait for the attachment before any render.
2. **Renderer** — run the chosen backend:
   - **Studio + ComfyUI** (default): the canonical batch renderer is
     `~/.hermes/outputs/Ionga/batch_render.py` — edit the poses/seeds in its
     FRAMES list, then run. It fires N seeds per pose at 1024 or 768x1344 (~185-201s
     each), writes a JSONL runlog, and vision-verifies AFTER renders finish,
     never concurrently. Prior session scripts are archived in
     `~/.hermes/outputs/Ionga/archive/scripts/` — do NOT fork new batch
     files; edit `batch_render.py`. QC tooling kept at root: `qc_pipeline.py`
     (post-batch QC with manual gate) and `limb_sweep.py` (pose-aware limb
     scoring).
   - **Studio + ComfyUI, SEED IMAGE attached**: `ref_edit_render.py` at the
     Ionga root — the maintained reference-image renderer, NOT a fork of
     `batch_render.py`. Wiring, the aspect rule and the autogrow pitfall that
     renders text-to-image while looking like it worked all live in
     `references/seed-reference-runs.md`. Read it before the first fire.
   - **Unsloth, either machine**: `python3 ~/.hermes/skills/mlops/local-image-gen/scripts/unsloth_gen.py --machine studio|macbook --model <id> --prompt "…" --size 1024x1024 --steps 25 --seed N --out ~/.hermes/outputs/Ionga`. On Studio, `open -a Unsloth` first if :8888 is refused. Model inventory: `unsloth_gen.py --machine <m> --list`.
3. **Machine pointer** — run the vision model for location hints only (see QC discipline).
4. **Patrick's eye** — present frames ONE AT A TIME (never a scroll-wall of images, never text-only reports); record each ruling immediately into `rename_map.json`. Ask before any re-fire — "no re-fires unless told" is the default.
5. **File keepers** — copy flat to root with the ledger name, verify the copy, extend `rename_map.json`, and add a per-run session block carrying stage, seed and ruling per frame.

## SEED-REFERENCE RUNS (the attached-seed path)

Question 4 "yes" means the seed carries identity and the prompt restages her;
the backend is `ref_edit_render.py` at the Ionga root. Full wiring in
`references/seed-reference-runs.md` — read it before firing. The three things
that decide whether the run is real:

- **Verify the run by its OUTPUT ASPECT, never by "it ran".** Reference
  conditioning sizes the frame from the reference. A square output at
  `resolution` means the reference did nothing and you rendered text-to-image.
- **The autogrow input is a flat dotted key** (`images.image_1`). Nested
  forms validate, complete, and silently no-op. A convincing likeness of the
  subject is NOT evidence the reference landed — the prompt describes her in
  enough detail to reproduce her from text alone.
- **Crop the seed to the target aspect before upload.** `--aspect 3:4` on a
  square seed gives a 896x1184 output at `resolution=1024`.

## Pitfalls

- **Never mix up the two ladder recipes.** A truncated or unattended write once left stage 4 labelled "topless" while still listing the gown and lingerie, and stage 5 as "bare-chest", and inverted rule 8 into a negative. Stage 4 is panties only; stage 5 is fully nude; the bust spec is a POSITIVE.
- **An automatic background reviewer used to edit this skill.** Hermes' `background_review` (local model, unattended) wrote an unverified ladder into this file on 2026-10-27 and the write landed truncated. It is DISABLED as of 2026-10-27 (`auxiliary.background_review.enabled: false`; the skill curator is also off). If it is ever re-enabled, expect this: re-read the file after sessions and correct injected text rather than leaving two recipes side by side.
- **The seed lottery must be drawn ONCE per run, from a module-level RNG.** Creating `random.Random(...)` inside `fresh_seeds()` makes every call redraw the same first N values, so a ten-rung run comes back with the SAME two seeds on all ten rungs. Two distinct seeds across twenty frames is not a lottery — it caps face diversity before the first frame renders, and a seed-linked defect then replicates across every frame of that column while looking like independent failures. Cost a 20-frame run on 2026-11-06. Assert the drawn seed list has no duplicates before firing.
- **Ruled keepers require the eye; an ungated run files nothing.** When a run is asked to proceed without feedback, render everything, publish `prompts/`, `qc/`, `runlog.jsonl`, `batch.log`, `NOTES.md` and a contact sheet, and leave `keepers/` EMPTY. Record the run in the ledger with `keepers_filed: 0` and the reason, plus your own read labelled a SAMPLE with the frames you actually checked at full resolution. Never invent verdicts to make a run look finished.
- Do not resize the interactive flow into more questions than the probes justify; a backend question whose answer is fixed by machine availability is noise.
