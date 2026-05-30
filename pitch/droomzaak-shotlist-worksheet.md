# Droomzaak Pitch Video — Shot & Generation Worksheet

> The build sheet. Copy-paste each prompt into **Runway Gen-4.5**. Keyframes (KF) come from [`droomzaak-lore-reference.md`](droomzaak-lore-reference.md); narration from [`droomzaak-vo-script.md`](droomzaak-vo-script.md); story from [`droomzaak-grounding-storyline.md`](droomzaak-grounding-storyline.md).
>
> **Target final cut:** ~60s · **5:7 portrait master, 864×1214** · **Status:** draft v2 (product-demo tail added) · 2026-05-30

---

## How to use this sheet

- **Pipeline:** Nano Banana keyframe(s) → Runway Gen-4.5 *image-to-video* → cut on movement in the edit.
- **Generate long, cut short.** Generate ~10s per shot; use only the 2–3s where the action lands. The extra frames are "handles" for clean match-cuts.
- **The transform method (core craft):** for each world-change, set Runway's **start frame = KF of world A** and **end frame = KF of world B** (same Lore pose). Runway rebuilds the world around the held pose → seamless Old Spice transform. Prompt describes the *motion* that carries the cut (pull-forward, whip-pan, turn).
- **Settings:** Gen-4.5, image-to-video, **5:7 portrait (864×1214)**, ~10s, motion moderate-high. Generate **2–3 variants per shot**, pick the best.
- **Audio:** none from Runway — VO + music + SFX are added in the edit.

---

## Keyframes required (make these first, in Nano Banana)

`KF0` grey desk (with side monitor) · `KF1` bistro · `KF2` florist · `KF3` bike workshop · `KF4` desk (changed, same monitor) · `KF5` over-the-shoulder at desk (screen visible). See the reference doc §4. **Use the conformed `pitch/keyframes/final/` set — all 864×1214.**

---

## Shotlist

> `GEN` = generate length · `CUT` = target length in final edit · `VO` = narrator line over this shot
>
> **Runway prompt style** (per the `media-prompt-craft` skill): simple, **positive phrasing only**, **motion-focused** (the start/end keyframes carry the look — don't re-describe appearance), **one scene per clip**, **no negative list**. Generate ~10s, 2–3 variants, cut on the movement.

### S1 · The grey desk *(setup)*
- **Frames:** start = KF0 · **GEN** ~10s → **CUT** ~6s · **VO:** *(none, then)* "Ben je je job beu?" (`Ben_je_je_job_beu`)
- **Camera/transition:** slow push-in; ends on her sigh + papers thudding onto desk.
- **Runway prompt:**
```
She sits slumped at the desk, lets out a heavy sigh, and lowers her head into her hand;
a fresh stack of papers drops onto the desk in front of her. Slow push-in. She is alone.
```

### S2 · The voice *(fourth wall opens)*
- **Frames:** start = KF0 (same desk) · **GEN** ~10s → **CUT** ~5s · **VO:** "Was dit dan je droomjob?" (`was_dit_dan_je_droomjob`)
- **Camera:** static medium; she lifts her head, glances around for the voice, then looks **straight at camera**, then shakes her head.
- **Runway prompt:**
```
She lifts her head and glances around as if searching for a voice, then turns and looks
directly into the camera; she pauses, then slowly shakes her head. Static shot. She is alone.
```

### S3 · Transform → BISTRO *(Wat dan wel?)*
- **Frames:** start = KF0 · **end = KF1** · **GEN** ~10s → **CUT** ~3s · **VO:** "Wat zou je droomjob dan wel zijn?" (`wat_zou_je_droomjob_dan_wel_zijn`)
- **Camera/transition:** she's **pulled forward**; the grey office rebuilds into a cozy bistro around her, her clothes resolve into the terracotta apron, coffee machine steams. She smiles, surprised.
- **Runway prompt:**
```
She is pulled quickly forward toward the camera; the surroundings sweep past and settle
into the bistro around her, a coffee machine puffing steam beside her, and she breaks into
a surprised, delighted smile. One continuous forward push. She stays centered while the
world around her changes.
```

### S4 · Transform → FLORIST *(Dit meer je stijl?)*
- **Frames:** start = KF1 · **end = KF2** · **GEN** ~10s → **CUT** ~3s · **VO:** "Dit misschien meer je stijl?" (`dit_misschien_meer_je_stijl`)
- **Camera/transition:** on a turn/whip-pan the bistro becomes a flower shop; apron changes; blooms fill the frame; she lights up.
- **Runway prompt:**
```
She turns her shoulders quickly; the surroundings sweep around her from the bistro into a
bright flower shop full of blooms, and she turns back to the camera and lights up with joy.
One continuous turning motion. She stays centered while the world around her changes.
```

### S5 · Transform → BIKE WORKSHOP *(Of dit?)*
- **Frames:** start = KF2 · **end = KF3** · **GEN** ~10s → **CUT** ~3s · **VO:** "Of misschien deze?" (`of_misschien_deze`)
- **Camera/transition:** a duck/whip and the flowers become an industrial bike-repair workshop; work apron; she ends with a confident **nod at camera**, happy.
- **Runway prompt:**
```
She ducks and rises again; as she comes back up the surroundings have swept into a
bike-repair workshop with bikes and tools around her, she looks amazed, then nods
confidently at the camera with a big smile. One continuous duck-and-rise motion. She stays
centered while the world around her changes.
```

### S6 · Back to reality
- **Frames:** start = KF3 · **end = KF4** · **GEN** ~10s → **CUT** ~4s · **VO:** "Ondernemen, da's een zaak van dromen." (`ondernemen_das_een_zaak_van_dromen`)
- **Camera/transition:** gentle dissolve back to the grey desk; same woman, but a new spark in her eye.
- **Runway prompt:**
```
She settles back at the grey office desk and turns to look at her computer, a new spark
of determination in her eyes. Gentle settle, minimal motion. She is alone. (The dissolve
from the workshop is added in the edit; start frame KF3, end frame KF4.)
```

### S7 · The keuzestress *(tab explosion)*
- **Frames:** start = **KF5** (over-the-shoulder, screen visible) · **GEN** ~10s → **CUT** ~5s · **VO:** *(none — let it play)*
- **Camera:** over-the-shoulder on her monitor; a Google search **"Hoe start ik een eigen zaak?"**; one browser tab pops open, then another, then many in fast succession until the screen drowns in pop-ups; slow **push-in** to the screen.
- **Runway prompt:**
```
Over-the-shoulder on her monitor: browser tabs and pop-up windows open one after another,
faster and faster, until the screen fills with them; the camera slowly pushes in toward
the screen as she sits back. She is alone.
```
> **Tip:** the tab-explosion + final query text may render cleaner as a **real screen-capture** (record a browser, or build a quick mock) composited in the edit, rather than fully generated. See Non-Lore assets.

### S8 · Website reveal *(resolution begins)*
- **Frames:** S7 screen-capture → Droomzaak landing page · **GEN** n/a (edit/comp) → **CUT** ~5s · **VO:** "Laat administratie en keuzestress je dromen niet tegenhouden." (`Laat_administratie…tegenhouden`, 4.6s)
- **Build:** the S7 push-in transitions into a clean screen capture → **fades to black** → resolves on the **real Droomzaak landing page**.

### S9 · Product demo *(NEW — proof)*
- **Frames:** screen capture of the **live Droomzaak product** (describe-dream → Droomkaart/insights → *Droomzaak-pakket*) · **GEN** n/a (joint screen capture) → **CUT** ~16s · **VO:** "Het enige dat je moet doen is je droomzaak beschrijven…" (`product_description`, 16.3s)
- **Build:** a tight walkthrough of the actual app — describe-your-dream input → insights from the data sources → location, permits, and financial expectations → the package. Capture **5:7 portrait (864×1214)** or letterbox a desktop capture into the frame. Keep it brisk — it's *proof*, not a manual. *(This beat intentionally drops the Lore device — it's the product itself; keep it short so it reads as proof, not a tangent.)*

### S10 · CTA + end card *(resolution lands)*
- **Frames:** landing page → logo end card (`droomzaak.png`), warm earth tone, tagline *"Van droom naar zaak."* · **CUT** ~6s + ~2s end card · **VO:** "Bezoek onze website en laat ons je helpen je droomleven waar te maken." (`bezoek_onze_website`, 5.4s) → "droomzaak.be, want ondernemen, da's een zaak van dromen." (`droomzaak_be_CTA`, 5.3s)
- **Build:** the CTA closes on the **signature line** — the *zaak* pun bookends Beat 6 (grounding invariant #9 preserved). The end card is the only fully-still moment.

---

## Non-Lore assets (gather / build separately)

- [ ] **Tab-explosion screen** — record a real browser or build a mock; the cleanest path for legible text. Final query: **"Hoe start ik een eigen zaak?"**
- [ ] **Droomzaak landing-page screenshot** — *needs the live/staging URL or a screen-capture from you* (chosen end beat). Capture in 5:7 portrait (864×1214) or letterbox.
- [ ] **Product-demo screen capture (S9, NEW)** — joint capture of the live Droomzaak app: describe-dream input → Droomkaart / data-source insights → location, permits, financial expectations → the package. ~16s to match the `product_description` VO. Target **5:7 portrait (864×1214)** or letterbox a desktop capture.
- [ ] **Logo end card** — from `droomzaak.png`, warm earth-tone background, tagline *"Van droom naar zaak."*

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
| S8 |  | edit |  |  | website reveal |
| S9 |  | capture |  |  | product demo (joint capture) |
| S10 |  | edit |  |  | CTA + end card |

---

## Aspect: 5:7 portrait master — 864×1214 (decided & built)
The Gemini dream frames are **~5:7, not 9:16**. All six keyframes are conformed to **864×1214** in **`pitch/keyframes/final/`** — **use that set for Runway** (every transform start/end pair matches exactly). Originals preserved in `pitch/keyframes/`.
- **KF0, KF4** (shot landscape) → cropped to 5:7 **centered on Lore** (the monitor kept as a left-edge balance).
- **KF1** (was 2:3) → trimmed top/bottom; **KF5** (was 3:4) → trimmed on the left to protect the on-screen Google search; **KF2/KF3** already 5:7.
- KF0/KF4 read near-identical by design — KF4's "changed" feel comes from a **warmer grade + S6 performance**, not a regen.
- A true-9:16 or 16:9 cut later = **Runway Expand** on the finished master (this 5:7 won't cleanly crop to either).

## Other-aspect cuts (from the 5:7 master)
- The master is **5:7 portrait (864×1214)**. For a true-9:16 or 16:9 cut, use **Runway Expand** on the finished master (it won't cleanly crop either way).
- Lore is centered in every shot, so vertical reframes crop cleanly.
- For a short social cut, tighten to ~30–40s by trimming the product-demo tail (S9) and one dream module.
