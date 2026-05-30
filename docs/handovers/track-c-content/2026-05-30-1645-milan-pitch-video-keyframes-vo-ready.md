# Handover — pitch video: keyframes + Flemish VO done, ready for Runway

**Track:** track-c-content · **Author:** milan · **2026-05-30 16:45**

## State now
The "Guided Journey" pitch spot is **ready to generate video**. Concept locked, **all 6 keyframes built + conformed**, and the **Flemish VO is recorded**. What's left is the Runway video generation, the screen-capture/landing-page assets, music, and the edit. Supersedes the 14:49 blueprint handover.

- **Keyframes:** `pitch/keyframes/final/KF0–KF5.png`, all uniform **864×1214 (5:7 master)**, Lore centered, identity consistent (Nano Banana / Gemini). Originals in `pitch/keyframes/`.
- **Voice:** Flemish VO clips in `pitch/voice_clips/*.mp3` (+ `normalized/`), generated in ElevenLabs. ⚠️ Wording was refined during recording (e.g. "Ben je je job beu?", "Wat zou je droomjob dan wel zijn?", "Dit misschien meer je stijl?", "Of misschien deze?") — **the clips are now the source of truth for narration**, slightly ahead of `droomzaak-vo-script.md`.

## What I just did (this session)
- Built the prompt-craft tooling: `media-prompt-craft` skill + `media-prompt-smith` agent (registered in CLAUDE.md), with **per-model detail-level rules** (image = narrative + concrete specifics; Runway = simple/positive/motion-only/one-scene/no-negatives).
- Re-synced the worksheet's **Runway prompts (S1–S8)** to those rules (stripped "Old Spice/cinematic" conceptual phrasing → concrete motion).
- Refined keyframe prompts: **KF0/KF4 gained a side monitor**, added **KF5 (over-the-shoulder)** for the keuzestress/CTA beats.
- Reviewed the generated keyframes, picked the Gemini set, and **conformed all six to 864×1214 centered on Lore** (cropped KF0/KF4 from landscape, trimmed KF1/KF5 to match; KF5 trimmed on the left to protect the on-screen Google search).
- Corrected the master format in the docs: **5:7 (864×1214), not 9:16**.

## Next concrete step
Generate **S1–S8 in Runway Gen-4.5** from the `final/` keyframes (mapping below), ~10s each, 2–3 variants, cut on the movement. Then assemble: VO as the timing spine + music + the screen-capture composite + landing page → color grade.

```
S1,S2: start=final/KF0        S3: KF0→KF1   S4: KF1→KF2   S5: KF2→KF3
S6: KF3→KF4                   S7: start=final/KF5 (+ screen-capture comp)   S8: edit (screen→landing page)
```

## Open questions / blockers
- **Droomzaak landing-page screenshot** (S8 end beat) — still needed: live/staging URL or a capture. Only hard external dependency.
- **Accounts:** Runway (video) + Suno/music still to set up. Images (Gemini) + voice (ElevenLabs) done.
- **Tab-explosion screen** for S7 — record a real browser (query "Hoe start ik een eigen zaak?") to composite onto KF5's monitor.
- Optional: sync `droomzaak-vo-script.md` text to the actual recorded clip wording.

## Exact entry points
- Keyframes (use these): `pitch/keyframes/final/` · prompts + shot→frame mapping + aspect note: `pitch/droomzaak-shotlist-worksheet.md`
- VO clips: `pitch/voice_clips/` (+ `normalized/`) · VO script/settings: `pitch/droomzaak-vo-script.md`
- Character lock + style bible: `pitch/droomzaak-lore-reference.md` · story spine: `pitch/droomzaak-grounding-storyline.md`
- Pipeline/accounts/QA: `pitch/droomzaak-pitch-video-checklist.md`
- Prompt help: agent `media-prompt-smith` (invokes skill `media-prompt-craft`)

## Gotchas hit
- **Master ratio is 5:7 (864×1214), not 9:16** — Gemini's native dream-frame ratio. All transform start/end pairs must share it; the `final/` set already does.
- **Runway Gen-4.5 has no negative prompting** — prompts are positive + motion-only; never append the image negative list to a Runway prompt.
- **Keyframe identity** held by attaching the locked Gemini reference on every Nano Banana generation; KF0/KF4 are mildly soft from the portrait upscale (fine — drab office + Runway regenerates).
- **KF4 ≈ KF0 by design** — the "changed" beat comes from a warmer grade + the S6 performance, not a regen.
- macOS `.DS_Store` now gitignored.

## Verification
```
magick identify -format "%f %wx%h\n" pitch/keyframes/final/*.png   # 6 frames, all 864x1214
ls pitch/voice_clips/*.mp3 | wc -l                                  # VO clips present
git log --oneline -3
```
