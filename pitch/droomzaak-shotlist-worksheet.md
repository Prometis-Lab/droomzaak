# Droomzaak Pitch Video — Shot & Generation Worksheet

> The build sheet. Copy-paste each prompt into **Runway Gen-4.5**. Keyframes (KF) come from [`droomzaak-lore-reference.md`](droomzaak-lore-reference.md); narration from [`droomzaak-vo-script.md`](droomzaak-vo-script.md); story from [`droomzaak-grounding-storyline.md`](droomzaak-grounding-storyline.md).
>
> **Target final cut:** ~45s · **16:9 master** (+ 9:16 social) · **Status:** draft v1 · 2026-05-30

---

## How to use this sheet

- **Pipeline:** Nano Banana keyframe(s) → Runway Gen-4.5 *image-to-video* → cut on movement in the edit.
- **Generate long, cut short.** Generate ~10s per shot; use only the 2–3s where the action lands. The extra frames are "handles" for clean match-cuts.
- **The transform method (core craft):** for each world-change, set Runway's **start frame = KF of world A** and **end frame = KF of world B** (same Lore pose). Runway rebuilds the world around the held pose → seamless Old Spice transform. Prompt describes the *motion* that carries the cut (pull-forward, whip-pan, turn).
- **Settings:** Gen-4.5, image-to-video, 16:9, ~10s, motion moderate-high. Generate **2–3 variants per shot**, pick the best.
- **Audio:** none from Runway — VO + music + SFX are added in the edit.

---

## Keyframes required (make these first, in Nano Banana)

`KF0` grey desk · `KF1` bistro · `KF2` florist · `KF3` bike workshop · `KF4` desk (changed). See the reference doc §4.

---

## Shotlist

> `GEN` = generate length · `CUT` = target length in final edit · `VO` = narrator line over this shot

### S1 · The grey desk *(setup)*
- **Frames:** start = KF0 · **GEN** ~10s → **CUT** ~6s · **VO:** *(none, then)* "Je job beu?"
- **Camera/transition:** slow push-in; ends on her sigh + papers thudding onto desk.
- **Runway prompt:**
```
A young woman with black curly hair sits slumped at a grey bureaucratic office desk
buried in stacks of paperwork, dull fluorescent light, desaturated cold colours, she
sighs heavily and rests her head in her hand, a fresh stack of papers drops onto the
desk. Static-to-slow-push-in, cinematic 35mm, melancholic, mundane.
```

### S2 · The voice *(fourth wall opens)*
- **Frames:** start = KF0 (same desk) · **GEN** ~10s → **CUT** ~5s · **VO:** "Was dit je droomjob?"
- **Camera:** static medium; she lifts her head, glances around for the voice, then looks **straight at camera**, then shakes her head.
- **Runway prompt:**
```
The same woman at the grey desk lifts her head, looks around confused searching for
an unseen voice, then turns and looks directly into the camera, slightly puzzled, then
shakes her head with faint disappointment. Subtle, natural performance, cinematic, eyeline to lens.
```

### S3 · Transform → BISTRO *(Wat dan wel?)*
- **Frames:** start = KF0 · **end = KF1** · **GEN** ~10s → **CUT** ~3s · **VO:** "Wat dan wel?"
- **Camera/transition:** she's **pulled forward**; the grey office rebuilds into a cozy bistro around her, her clothes resolve into the terracotta apron, coffee machine steams. She smiles, surprised.
- **Runway prompt:**
```
Seamless continuous transformation: the woman is pulled forward toward camera as the
grey office instantly rebuilds around her into a warm cozy rustic bistro, her grey
clothes morph into a colourful top and terracotta apron, a coffee machine puffs steam
beside her, warm golden light floods in, she smiles in delighted surprise. Locked
framing on the woman, world morphs around her, whip-motion, Old Spice style seamless
set transformation, cinematic.
```

### S4 · Transform → FLORIST *(Dit meer je stijl?)*
- **Frames:** start = KF1 · **end = KF2** · **GEN** ~10s → **CUT** ~3s · **VO:** "Dit meer je stijl?"
- **Camera/transition:** on a turn/whip-pan the bistro becomes a flower shop; apron changes; blooms fill the frame; she lights up.
- **Runway prompt:**
```
Seamless continuous transformation on a quick turn: the bistro rebuilds around the
woman into a bright flower shop overflowing with colourful blooms, her apron becomes
an earthy florist apron, warm daylight, she looks around blooming with joy. Locked
framing on the woman, world morphs around her, Old Spice style seamless transition, cinematic.
```

### S5 · Transform → BIKE WORKSHOP *(Of dit?)*
- **Frames:** start = KF2 · **end = KF3** · **GEN** ~10s → **CUT** ~3s · **VO:** "Of dit?"
- **Camera/transition:** a duck/whip and the flowers become an industrial bike-repair workshop; work apron; she ends with a confident **nod at camera**, happy.
- **Runway prompt:**
```
Seamless continuous transformation on a duck-and-rise: the flower shop rebuilds into
an industrial urban bike-repair workshop with bikes and tools, warm bulb light and
steel, her apron becomes an olive canvas work apron with a bandana, she looks amazed
then nods confidently at the camera with a big natural smile. Locked framing on the
woman, world morphs around her, Old Spice style seamless transition, hint of Ghent, cinematic.
```

### S6 · Back to reality
- **Frames:** start = KF3 · **end = KF4** · **GEN** ~10s → **CUT** ~4s · **VO:** "Ondernemen, da's een zaak van dromen."
- **Camera/transition:** gentle dissolve back to the grey desk; same woman, but a new spark in her eye.
- **Runway prompt:**
```
Gentle dissolve from the workshop back to the grey bureaucratic office desk, the same
woman now sitting there again in grey, but with a new spark of determination in her
eyes, she looks at her computer. Cinematic, the colour slightly warmer than before.
```

### S7 · The keuzestress *(tab explosion)*
- **Frames:** start = KF4 (or a fresh over-shoulder still) · **GEN** ~10s → **CUT** ~5s · **VO:** *(none — let it play)*
- **Camera:** over-the-shoulder on her monitor; a Google search **"Hoe start ik een eigen zaak?"**; one browser tab pops open, then another, then many in fast succession until the screen drowns in pop-ups; slow **push-in** to the screen.
- **Runway prompt:**
```
Over-the-shoulder shot of the woman at the grey desk looking at her computer monitor,
a Google search page reads "Hoe start ik een eigen zaak?", suddenly browser tabs and
pop-up windows start opening one after another faster and faster until the whole screen
is overwhelmed with chaotic pop-ups, the camera slowly pushes in toward the screen,
she looks overwhelmed. Cinematic, comedic overwhelm.
```
> **Tip:** the tab-explosion + final query text may render cleaner as a **real screen-capture** (record a browser, or build a quick mock) composited in the edit, rather than fully generated. See Non-Lore assets.

### S8 · The brand *(resolution + CTA)*
- **Frames:** screen-capture → Droomzaak landing page · **GEN** n/a (edit/comp) → **CUT** ~6s + ~2s end card · **VO:** "Laat administratie en keuzestress je dromen niet tegenhouden. Bezoek onze website en bouw je droomzaak."
- **Build:** the push-in transitions into a clean screen capture → **fades to black** → resolves on the **real Droomzaak landing page** → logo end card (`droomzaak.png`) on warm earth tone, tagline *"Van droom naar zaak."*

---

## Non-Lore assets (gather / build separately)

- [ ] **Tab-explosion screen** — record a real browser or build a mock; the cleanest path for legible text. Final query: **"Hoe start ik een eigen zaak?"**
- [ ] **Droomzaak landing-page screenshot** — *needs the live/staging URL or a screen-capture from you* (chosen end beat). Capture in 16:9 and a 9:16 crop.
- [ ] **Logo end card** — from `droomzaak.png`, warm earth-tone background, tagline.

---

## Variant tracking (fill in as you generate)

| Shot | Prompt ver | Tool | File name | Pick? | Notes |
|------|-----------|------|-----------|-------|-------|
| S1 |  | Runway |  |  |  |
| S2 |  | Runway |  |  |  |
| S3 |  | Runway |  |  |  |
| S4 |  | Runway |  |  |  |
| S5 |  | Runway |  |  |  |
| S6 |  | Runway |  |  |  |
| S7 |  | Runway/capture |  |  |  |
| S8 |  | edit |  |  |  |

---

## 9:16 social cut notes
- Re-frame each shot to center Lore (she's always centered, so it crops well).
- Either generate native 9:16 from 9:16 keyframes, or reframe the 16:9 master in the edit.
- The tab-explosion + landing page need a 9:16 capture/crop.
- Keep the same VO + music; tighten to ~30–40s if needed for social.
