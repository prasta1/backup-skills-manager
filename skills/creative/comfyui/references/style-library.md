# Style Library — Qwen-Image-2.1 flat print-generation styles

Drop-in style fragments for flat print-design generation — signs, stickers,
logos, posters, any flat graphic. Road signs are one application, not the
definition. Usage protocol:

1. Keep the SUBJECT CORE unchanged: the subject, layout, and any text of the
   design. (Signs are one application — the protocol is identical for logos,
   stickers, posters, and illustrations.)
2. Replace the style fragment (currently "Flat vector t-shirt graphic ... sticker-style
   screen-print design") with one entry below. Machine-readable copy of every
   fragment lives in `references/style-presets.json` — the `run_style_sweep.py`
   script reads THAT file, so keep it in sync whenever a fragment changes.
3. Keep the same seed across a style comparison — only the style varies, so the
   comparison is honest.
4. Verify text spelling after every style change; text reliability varies by style.
5. Check the `cutout` flag before promising a transparent PNG — several styles
   break the near-white flood-fill assumption (pitfall 0m).

| Style | Vibe | Text risk | Cutout (0m) |
|-------|------|-----------|-------------|
| flat-sticker | default, current look | low | works |
| vintage-road-sign | weathered highway, aged | low-mid | works (age texture may fringe) |
| woodcut | carved relief, bold lines | low-mid | works |
| risograph | limited palette, grain | mid | works |
| serigraph-poster | bold print poster, halftone | low-mid | works |
| minimal-line | thin line art, negative space | mid | works |
| comic-ink | bold ink + halftone | mid | works |
| childrens-watercolor | soft wash, friendly | HIGH — text blurs | NON-white bg → no |
| neon-night | glowing tubes on dark | HIGH — text glows | NON-white bg → no |
| midcentury-atomic | googie shapes, retro | low-mid | works |

---

## flat-sticker *(default — the current wooly-bear/eft look)*

**Fragment:**
> Flat vector t-shirt graphic on a plain white background. Clean, crisp, flat
> colors, no gradients, no shading, no drop shadow, sticker-style screen-print
> design.

**Workflow:** steps 25, cfg 1.0. **Cutout:** near-white flood-fill. **Text:** excellent.

## vintage-road-sign

**Fragment:**
> Vintage weathered highway warning sign graphic on a plain white background.
> Aged 1970s screen-print look, slightly distressed paint, subtle print wear and
> chipping at the edges, faded but readable black lettering, muted retro yellow,
> flat colors, no gradients, no drop shadow.

**Workflow:** steps 25, cfg 1.0. **Cutout:** works, but the distress texture can
leave faint fringe — feather slightly more (0m) and verify by pixel stats.
**Text:** good; mild weathering is part of the look, so small character wear is
on-brand, not a defect.

## woodcut

**Fragment:**
> Bold black woodcut / linocut print graphic on a plain white background. Carved
> relief-print style, thick expressive black lines, visible gouge marks and
> ink-stamped texture, small amount of printed ink noise, no gray tones, no drop
> shadow, strong contrast.

**Workflow:** steps 25, cfg 1.0. **Cutout:** works — dark linework on white is the
ideal case for the near-white flood-fill. **Text:** good, bold; keep it thick.

## risograph

**Fragment:**
> Risograph print graphic on a plain white background. Limited 2-3 color palette,
> visible paper grain, slight ink misregistration offset, flat layered colors, no
> gradients, no drop shadow, zine-style print texture.

**Workflow:** steps 25, cfg 1.0. **Cutout:** works; the grain is light on white.
**Text:** mid — misregistration is authentic, but spelling must still be checked.

## serigraph-poster

**Fragment:**
> Bold serigraph / screen-print poster graphic on a plain white background.
> Limited flat palette, visible halftone dots in shading, thick even ink layers,
> slight ink bleed at edges, poster-art composition, no gradients, no drop shadow.

**Workflow:** steps 25, cfg 1.0. **Cutout:** works. **Text:** good.

## minimal-line

**Fragment:**
> Minimalist thin line-art graphic on a plain white background. Single-weight
> fine black lines, generous negative space, no fills except one accent color
> (e.g. the sign's yellow), no shading, no gradients, no drop shadow, elegant
> simple composition.

**Workflow:** steps 25, cfg 1.0. **Cutout:** works. **Text:** mid — thin lettering
can lose readability; bump text weight in the subject core or accept finer text.

## comic-ink

**Fragment:**
> Bold comic-book ink graphic on a plain white background. Thick confident ink
> outlines, halftone-dot shading, slightly exaggerated shapes, dynamic line
> weight, flat colors, no gradients, no drop shadow.

**Workflow:** steps 25, cfg 1.0. **Cutout:** works. **Text:** mid — comic lettering
is stylized; state "clean readable sans-serif" in the subject core or expect
comic-style letterforms.

## childrens-watercolor

**Fragment:**
> Soft children's book watercolor illustration. Gentle hand-painted wash
> textures, warm friendly palette, soft edges, subtle paper texture, no harsh
> outlines, no gradients banding, charming and approachable.

**Workflow:** steps 25, cfg 1.0. **Text:** HIGH risk — lettering blurs or softens;
reserve for wordless or short-text designs. **Cutout:** does NOT fit the 0m
near-white flood-fill (no flat white field) — use rembg / qwen bgremoval, or keep
it on a white/cream background field on purpose.

## neon-night

**Fragment:**
> Glowing neon tube sign at night. Bright saturated glowing outlines in neon
> colors, dark charcoal background, soft glow bloom around the tubes, subtle
> reflection, high contrast.

**Workflow:** steps 25, cfg 1.0. **Text:** HIGH risk — neon tubes blur and blend;
keep slogans short. **Cutout:** does NOT fit the 0m near-white flood-fill (dark
background). Different print path entirely — transparent cut needs real bg
removal, or design it as a full-bleed dark graphic.

## midcentury-atomic

**Fragment:**
> Mid-century atomic-age graphic on a plain white background. Retro googie
> shapes, bold rounded forms, two-tone color blocking, starburst accents, flat
> mid-century palette (cream, mustard, teal, brick), no gradients, no drop shadow.

**Workflow:** steps 25, cfg 1.0. **Cutout:** works. **Text:** good.

---

## Anatomy of a style fragment

Every fragment is a self-contained paragraph that replaces the style sentence in
the base prompt. It follows a fixed order so styles stay comparable:

1. **Medium** — "woodcut", "risograph", "flat vector t-shirt graphic"...
2. **Surface** — paper grain, ink texture, halftone, distress, glow...
3. **Color rule** — flat vs limited palette vs wash (explicitly ban gradients
   unless the style needs them — Qwen respects negative gradient language).
4. **Contrast/edge rule** — thick lines, single-weight, soft edges, no drop shadow.

Keep the SUBJECT CORE's explicit bans ("no drop shadow", "no gradients") in the
fragment too — they are what keep the cutout clean. For styles where that is
impossible (watercolor, neon), the `cutout` flag flips to no and the print path
changes; never silently promise a transparent PNG for those.

## Adding a style

1. Write a fragment with the 4-part anatomy above.
2. Set an honest `text risk` and `cutout` verdict from one test run — do not
   guess either.
3. Add the row to the summary table.
4. Add the fragment to `references/style-presets.json` too — the sweep script
   reads the JSON, not this file.
