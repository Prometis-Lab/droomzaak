---
name: media-prompt-craft
description: Use when writing or refining generation prompts for the Droomzaak pitch video's image, video, and voice models — Runway Gen-4.5 (video), Nano Banana Pro and GPT Image 2 (image keyframes), and ElevenLabs (Flemish VO). Encodes each model's prompt grammar, the start/end-frame transform method, character-consistency (Identity Lock) rules, the Droomzaak brand palette + negative lists, and the copy-paste output contract. Pairs with the media-prompt-smith agent.
---

# Media prompt-craft (Droomzaak pitch video)

How to write prompts that paste straight into our generators and produce **on-brand, character-consistent** output on the first or second try. **Rigid** on the house rules and output contract; **flexible** on creative wording.

> Ground truth lives in `pitch/`: the invariant story is `droomzaak-grounding-storyline.md`; Lore's identity + style bible is `droomzaak-lore-reference.md`; the shot format is `droomzaak-shotlist-worksheet.md`; the VO is `droomzaak-vo-script.md`. Prompts must honour those — never contradict the grounding storyline.

## The pipeline (where each prompt feeds)
```
Nano Banana / GPT Image 2 → keyframes (KF) ──► Runway Gen-4.5 (image-to-video, start/end frame) ──► edit
ElevenLabs → Flemish VO ─────────────────────────────────────────────────────────────────────────► edit
```
Image prompts make the **keyframes**; the video prompt animates **between** them; the voice prompt is the **narrator**. Get the keyframes right first — everything downstream inherits their consistency.

## House rules (always)
1. **English** for image + video prompts (models prompt best in EN); **Flemish (nl-BE)** for the VO *text*.
2. **Lore's master identity block is verbatim and identical** in every image prompt (copy it from the reference doc). Never paraphrase it — paraphrase = drift.
3. **Same framing + pose** across transform keyframes; change only world + wardrobe + expression. The locked pose is what makes the Old Spice transform seamless.
4. **Generate long, cut short** — ask for ~10s video clips; the edit uses ~2–3s. Say so in the prompt notes, not the prompt body.
5. **Brand palette**: warm earth tones (terracotta, mustard, olive, warm wood) in the dream worlds; the "before" office is **deliberately desaturated grey**. The contrast is the story.
6. **Never break the device**: only Lore is fourth-wall-aware; the world stays committed to normalcy. Don't prompt the world to react to her.
7. **Append the negative list** to every **image** prompt — but **never to a video/Runway prompt** (Gen-4.5 has no negative prompting; phrase positively instead). **Never invent** beyond the grounding storyline.

## Level of detail — the right amount (per model)
Detail level is **model-specific**; matching it is what separates a first-try hit from a re-roll.

- **Image (Nano Banana Pro, GPT Image 2) — richly descriptive, but as prose.**
  - **Narrative, not keyword-soup** — write sentences that *direct the scene*; the models' strength is language. A descriptive paragraph beats a comma-list of disconnected words.
  - **Concrete specifics beat vibe-words** — "warm bulb light with one tube flickering, sawdust hanging in the air, a grease smudge on her apron" is information; "stunning, cinematic, 8K, ultra-detailed" is noise the model discards.
  - **Structure beats length** — Subject → action → context → composition → lighting → constraints. Start from **3–5 core elements** (they reliably hold ~7–8); spend the detail budget on light, surface, and wardrobe, not adjectives.
  - **Repeat the invariants every time** ("same woman, same face and hair, same framing — only the world changes") or the model quietly redesigns what you wanted kept. Negatives help here — keep the negative list.
- **Video (Runway Gen-4.5) — simple, positive, motion-only.**
  - **Keep it short** — the keyframe already defines the look; an over-stuffed prompt fights the image. One clear instruction set.
  - **Positive phrasing only** — describe what *should* happen ("she alone, turning toward camera"), never what to avoid; Gen-4.5 has no negative prompting and may invert it.
  - **Motion, not appearance** — say what *moves/happens next*, translated into **concrete physical action** ("she steps forward and the shelves slide past her"), never a feeling or concept ("a magical vibe").
  - **One scene per clip** — don't stack multiple changes; the transform is carried by the two keyframes + a single motion. 5s simple / 10s multi-motion.

## Per-model prompt grammar

### Nano Banana Pro (image keyframes) — primary
- **Identity Lock**: attach the saved Lore hero reference as input on *every* generation; it supports multiple reference images for a stronger lock. Reuse the same seed where exposed.
- **Prompt order**: `[MASTER IDENTITY BLOCK] + wardrobe state + world/setting + lighting + framing (medium, chest-up, eyeline to camera, centered) + expression + "[negative list]"`.
- Excellent at **legible text** — fine for the Google-search screen if generated.
- **Write it as narrative prose with concrete specifics** (see Level of detail), not a keyword list or generic adjectives.
- Keep backgrounds purposeful, not cluttered. One clear subject (Lore), centered.

### GPT Image 2 (image keyframes) — backup
- Conversational + reasons before generating; upload the hero reference, then describe the change in plain language: *"Same woman, same face and hair, same medium framing looking at camera, now in [world] wearing [wardrobe], [expression], warm cinematic light."*
- Strong text rendering; can hold a character across up to ~8 images in a set. Good fallback if Nano Banana drifts on a specific world.

### Runway Gen-4.5 (video) — the transforms
- **Mode**: image-to-video. For a world-change set **start frame = KF(world A)** and **end frame = KF(world B)** — Runway rebuilds the world around the held pose.
- **Prompt the MOTION that carries the cut**: a *pull-forward*, *whip-pan*, *turn*, *duck-and-rise*, *push-in*. Camera + body motion hides the seam.
- Use directional camera language: `slow push-in`, `dolly`, `crane up`, `whip-pan`, `static`. Keep motion **moderate–high** for transforms, gentle for reveals.
- Single shots (no transform): one keyframe as start frame + an action description.
- **Keep it simple, positive, one scene** (see Level of detail): short prompt, positive phrasing only, a single motion — and **do not append the image negative list** (Gen-4.5 has no negative prompting).
- Always note: generate ~10s, 2–3 variants, cut on the movement. 16:9 master; 9:16 by reframing centered Lore.

### ElevenLabs (Flemish VO)
- **Select the Flemish (nl-BE) voice directly** (Jan Schevenels / Hans Claesen / Walter / Jann) — *not* via the "Dutch (Belgium)" language dropdown (that can route to GCP/Azure voices).
- Model **v3** (most expressive); lock settings after one test: stability ~50%, similarity ~75%, style low–moderate, speed slightly slow. Warm radio-ad read, knowing half-smile, not hammy.
- Render **line-by-line** for clean timing; export WAV. Audio tags (`[warm]`) only sparingly.
- **nl-BE notes**: keep the `da's` elision; verify a **soft G** (southern) timbre; `keuzestress` mildly exasperated; `droomzaak` even and clear (the payoff word).

## Output contract (what a good prompt deliverable looks like)
- Prompts in **fenced code blocks**, copy-paste-ready, one per shot/keyframe.
- For video: name the **start/end keyframes**, the **camera/transition**, and the **gen-vs-cut** durations.
- For images: include the **master identity block + wardrobe + world + negative list**.
- Mirror the worksheet's shot IDs (S1–S8, KF0–KF4) so it drops straight in.
- Offer **2–3 variant angles** when a shot is risky (transforms, hands, text).

## Negative list (append to image prompts)
```
avoid: plastic skin, waxy AI sheen, over-saturation, warped hands, extra fingers,
distorted face, glasses, heavy makeup, stock-corporate gloss, cluttered background,
text artifacts, watermark.
```

## Review test
Would this paste straight into the tool and produce: (1) recognisably **the same Lore**, (2) on the **brand palette**, (3) honouring the **grounding storyline**, (4) with the **device intact** (only she's aware)? If any answer is "maybe", tighten before handing it over. Model prompt-grammars drift — if unsure a syntax is current, web-check the latest Runway / Nano Banana / ElevenLabs prompting guide, but default to these rules.

## Sources (detail-level guidance)
Runway [Gen-4 prompting guide](https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide) + [Academy](https://academy.runwayml.com/guides/prompting-guide) (simple, positive, motion-only, one scene, no negatives); Google [Nano Banana prompting guide](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana) (narrative > keywords); OpenAI [GPT Image prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide) (concrete specifics, structure > length, repeat invariants). Re-verify before a major regen — these models update often.
