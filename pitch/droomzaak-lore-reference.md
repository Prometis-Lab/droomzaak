# Droomzaak Pitch Video — Lore Character Reference & Style Bible

> **Lock Lore once, reuse everywhere.** Every shot in the film reuses one locked reference of Lore so her identity holds across all worlds. Do this **before** any video generation.
>
> **Primary tool:** Nano Banana Pro (Gemini) — best character consistency via "Identity Locking" (reuses your Google access). **Backup:** GPT Image 2 (ChatGPT). No Midjourney needed.
>
> Story spine: [`droomzaak-grounding-storyline.md`](droomzaak-grounding-storyline.md) · Shots: [`droomzaak-shotlist-worksheet.md`](droomzaak-shotlist-worksheet.md)
> **Status:** draft v1 · **Owner:** Track C · **Last updated:** 2026-05-30

---

## 1. Master identity block (paste into EVERY image prompt)

> Keep this text **identical** across every generation. This is the anchor that keeps her face/hair consistent.

```
Lore — a Belgian woman in her late 20s, slim build, warm medium-brown skin,
voluminous shoulder-length black curly hair, bright expressive eyes, big natural
smile, no glasses, minimal makeup. Bubbly, warm, approachable. Photoreal,
cinematic, natural skin texture, 35mm film look, shallow depth of field.
```

**Consistency rules:**
- Always attach the **locked reference image** as input (Nano Banana: keep the same reference across all generations; it supports multiple reference images for stronger identity lock).
- Keep **framing and pose identical** for transform keyframes (see §4) — medium shot, chest-up, eyeline to camera, centered.
- Change **only** the world + wardrobe between keyframes. Same Lore, same pose.
- Where the tool exposes a seed, **reuse the same seed**.

---

## 2. Style & palette bible

| Element | Direction |
|---|---|
| **Dream-world palette** | Warm earth tones — terracotta, mustard, olive, warm wood, brick. Soft natural light, golden warmth. |
| **'Before' world palette** | Deliberately **desaturated grey** — fluorescent office light, muted blue-grey, lifeless. The contrast IS the story. |
| **Lighting** | Soft, directional, natural. Warm key in dream worlds; flat cold overhead in the office. |
| **Lens / look** | 35mm film, shallow depth of field, gentle grain, cinematic. Eyeline to camera (fourth-wall device). |
| **Energy** | Bubbly, brisk, a little surreal. She's lit like the hero; the world is just set. |
| **Ghent cue** | A subtle glimpse of canal / gabled rooftops / Vrijdagmarkt through a window — never dominant. |

**Negative / avoid list (append to prompts):**
```
avoid: plastic skin, waxy AI sheen, over-saturation, warped hands, extra fingers,
distorted face, glasses, heavy makeup, stock-corporate gloss, cluttered background,
text artifacts, watermark.
```

---

## 3. Wardrobe states (4)

| State | World | Wardrobe |
|---|---|---|
| **BEFORE** | Bureaucratic admin office | Dull, slightly ill-fitting grey blazer over a grey blouse; muted, corporate, desaturated. Tired posture. |
| **BISTRO** | Cozy rustic bistro | Warm colourful top (rust/teal) under a **terracotta linen apron**, sleeves rolled. Relaxed owner-barista energy. |
| **FLORIST** | Bright flower shop | Linen/denim shirt under an **earthy canvas florist apron**, sleeves rolled, a single flower tucked in. Surrounded by blooms. |
| **WORKSHOP** | Industrial bike-repair workshop (urban Ghent) | Practical work shirt, **olive/tan canvas work apron**, hair tied back with a bandana, a touch of honest grease. Steel + warm-bulb light. |

---

## 4. Step-by-step generation

### Step 1 — Generate Lore's locked reference (Nano Banana Pro)

This is the **identity anchor** — generate it first, pick the strongest, and attach it to every keyframe in Step 2. Written as narrative prose with concrete specifics (per `media-prompt-craft` §"Level of detail"); the master identity block is verbatim, with reference-sheet framing layered on for a clean lock. Neutral wardrobe on purpose — no apron, no office grey.

**▶ Primary — 3-angle reference sheet (paste into Nano Banana Pro):**
```
Character reference sheet of the same woman shown from three angles in a single image
— front view, three-quarter view, and profile — on a plain neutral light-grey studio
background, even soft studio lighting, sharp focus on the face, identity fully
consistent across all three views, relaxed friendly expression with a hint of her
natural warmth.

Lore — a Belgian woman in her late 20s, slim build, warm medium-brown skin,
voluminous shoulder-length black curly hair, bright expressive eyes, big natural
smile, no glasses, minimal makeup. Bubbly, warm, approachable. Photoreal, cinematic,
natural skin texture, 35mm film look, shallow depth of field.

She wears a simple plain warm-toned top — neutral wardrobe for an identity reference
(no apron, no office wear).

avoid: plastic skin, waxy AI sheen, over-saturation, warped hands, extra fingers,
distorted face, glasses, heavy makeup, stock-corporate gloss, cluttered background,
text artifacts, watermark.
```

**▶ Also generate 2 variants, then pick the strongest anchor:**
- **Variant B — single front portrait** (often locks tighter than a sheet): *same identity block + avoid list, but* "A clean head-and-shoulders portrait, facing camera directly, plain neutral light-grey studio background, even soft lighting, sharp focus, relaxed neutral expression."
- **Variant C — her bubbly smile** (helps the delighted/amazed world shots): *as Variant B, but* "with her big natural warm smile, eyes bright and happy."

**Pick the winner where:** the curly-hair volume + hairline look natural, the face reads identical across angles, skin tone is consistent and warm (not over-saturated), and the smile is genuine (not uncanny). Save it as `lore_hero_ref_v1.png` — this single image is the identity anchor for everything downstream.

### Step 2 — Generate one keyframe per world (identity-locked)
For each keyframe below: **attach the hero reference from Step 1**, keep the **same medium framing + pose + eyeline-to-camera**, change only world + wardrobe + expression.

| KF | World | Expression | Prompt add-on (after master block + attach reference) |
|---|---|---|---|
| **KF0** | Bureaucratic admin office, grey, fluorescent, stacks of forms; **slim monitor to one side (her left, edge of frame, angled — not blocking her), dull spreadsheet on screen** | bored, deflated | "...wearing the BEFORE wardrobe, seated at a grey office desk buried in paperwork with a slim monitor angled at her left edge of frame (not blocking her), desaturated cold light, looking tired toward camera." |
| **KF1** | Cozy rustic bistro, warm wood, plants, steaming coffee machine | surprised delight | "...wearing the BISTRO wardrobe (terracotta apron), standing in her own cozy bistro, warm golden light, a glimpse of Ghent rooftops through the window, smiling in surprise at camera." |
| **KF2** | Bright flower shop full of blooms | happy, blooming | "...wearing the FLORIST wardrobe, surrounded by colourful flowers in her own shop, warm daylight, delighted, looking at camera." |
| **KF3** | Industrial bike-repair workshop, steel + warm bulbs, urban Ghent | amazed, confident | "...wearing the WORKSHOP wardrobe, in her own bike-repair workshop, bikes and tools around, warm industrial light, amazed and happy, looking at camera." |
| **KF4** | Back at the grey admin desk — **same side monitor as KF0** | changed — a spark in her eye | "...wearing the BEFORE wardrobe again at the same grey desk with the same slim side monitor, light a touch warmer, a new spark of determination, looking at camera." |
| **KF5** | **Over-the-shoulder at the desk** (separate composition) — her shoulder + curly hair soft in foreground, the monitor sharp in centre-right showing Google *"Hoe start ik een eigen zaak?"* | overwhelmed (face mostly unseen) | "Over-the-shoulder from behind her right shoulder at the grey desk, shoulder/hair soft in foreground, monitor sharp showing a Google search 'Hoe start ik een eigen zaak?', clean legible on-screen text, desaturated office. For S7 keuzestress + S8 push-in." |

> Keep **KF0–KF4** in the **same chest-up framing + face scale** so Runway can morph the *world* around a held Lore (the seamless transform). **KF5 is a separate over-the-shoulder composition** for S7 — it only needs the hero reference for hair/skin (face mostly unseen). KF0 and KF4 share the same desk + side-monitor layout so we can cut to KF5 and end on that screen. The conformed set (all **864×1214, 5:7**) lives in `pitch/keyframes/final/` — use that for Runway.
>
> **Note (master block):** the §1 identity block ends with "big natural smile" — that's an *expression*, not a stable trait, and it conflicts with the non-smiling KF0/KF4/KF5. In keyframe prompts, set expression per-shot and drop the fixed smile. Worth moving "big natural smile" out of §1's identity line into a "characteristic warm smile when happy" note.

### Step 3 — Hand off to Runway
These keyframes become the **start/end frames** in the shot worksheet. See [`droomzaak-shotlist-worksheet.md`](droomzaak-shotlist-worksheet.md).

---

## 5. GPT Image 2 alternative (if you prefer ChatGPT)
Same flow, conversational: upload the hero reference, then ask for each world keyframe — *"Same woman, same face and hair, same medium framing looking at camera, now in [world] wearing [wardrobe], [expression], warm cinematic light."* GPT Image 2 holds identity well and renders any on-screen text cleanly (useful for the Google-search beat).

## 6. Quick checklist
- [ ] Hero reference generated + saved (Step 1)
- [ ] KF0–KF5 generated, identity-locked, conformed to 864×1214 in `final/` (Step 2)
- [ ] 9:16 keyframe crops (optional)
- [ ] All saved + named (e.g. `lore_KF1_bistro_v1.png`) for the worksheet
