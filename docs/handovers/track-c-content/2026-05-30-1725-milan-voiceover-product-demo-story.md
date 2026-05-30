# Handover — Pitch VO rendered + product-demo story extension

**Track:** C (content/pitch) · **Author:** Milan · **Date:** 2026-05-30 17:25 · **Branch:** `milan_dev`

## State now
- **Voice-over is fully rendered and edit-ready.** All 10 narrator clips exist as source MP3 in `pitch/voice_clips/` and as **loudness-normalized WAV** (−16 LUFS / −1.5 dBTP, mono 44.1 kHz) in `pitch/voice_clips/normalized/`. Ear-checked for nl-BE soft-G + warmth. These WAVs are the timing spine for the edit.
- **Story extended with a product-demo beat.** We noticed the dream-transforms weren't showing the actual product enough, so the resolution now walks through the real app before the CTA. Spot grows ~45s → **~60s**.
- **All four pitch docs are synced** to the new story (grounding storyline, shotlist, VO script, checklist). No known inconsistencies left.
- **Not yet done:** S1–S7 Runway video, the S9 product-demo screen capture, music, SFX, the edit. (Track-C asset generation continues.)

## What we did this session
1. **Validated + normalized the VO.** Rendered clips in ElevenLabs v3 (Flemish male, settings per VO script). Some lines were *lengthened* during generation because 2–3-word fragments read poorly in TTS — the as-generated wording is now the source of truth (see VO script table). Two-pass `ffmpeg loudnorm` → `normalized/` (originals untouched).
2. **Added the product-demo tail.** Old single "Beat 8 / S8 (brand)" split into **S8 website reveal → S9 product demo (NEW) → S10 CTA + end card**.
3. **Changed the CTA.** Old *"...bouw je droomzaak"* is gone. New closer re-uses the signature line: *"Bezoek onze website en laat ons je helpen je droomleven waar te maken. droomzaak.be, want ondernemen, da's een zaak van dromen."* The *zaak* pun now bookends Beat 6.
4. **Deprecated** the superseded `droomzaak_dot_be` clip → `pitch/voice_clips/deprecated/` (replaced by `droomzaak_be_CTA`). Old `bezoek_..._bouw_je_droomzaak` clip removed (replaced by longer `bezoek_onze_website`).
5. **Updated the grounding storyline (the spine) to v3** — sanctioned by the team — so the invariant arc/resolution/CTA reflect the product beat.

## The final clip inventory (normalized/, maps to shots)
| Shot | Clip | Text |
|---|---|---|
| S1 | `Ben_je_je_job_beu` | "Ben je je job beu?" |
| S2 | `was_dit_dan_je_droomjob` | "Was dit dan je droomjob?" |
| S3 | `wat_zou_je_droomjob_dan_wel_zijn` | "Wat zou je droomjob dan wel zijn?" |
| S4 | `dit_misschien_meer_je_stijl` | "Dit misschien meer je stijl?" |
| S5 | `of_misschien_deze` | "Of misschien deze?" |
| S6 | `ondernemen_das_een_zaak_van_dromen` | "Ondernemen, da's een zaak van dromen." |
| S8 | `Laat_administratie_en_keuzestress_je_dromen_niet_tegenhouden` | "Laat administratie en keuzestress je dromen niet tegenhouden." |
| S9 | `product_description` | (16.3s product-demo VO — describe-dream → guidance → "Zodat jij kan blijven dromen.") |
| S10 | `bezoek_onze_website` | "Bezoek onze website en laat ons je helpen je droomleven waar te maken." |
| S10 | `droomzaak_be_CTA` | "droomzaak.be, want ondernemen, da's een zaak van dromen." |
*(S7 keuzestress = no VO.)*

## Next concrete steps
1. **Capture the S9 product demo** (joint) — live app screen recording: describe-dream input → Droomkaart/data-source insights → location, permits, financial expectations → het pakket. **5:7 portrait (864×1214)** or letterbox. ~16s to match `product_description.wav`. Keep it brisk — proof, not a feature tour.
2. **Generate S1–S7 in Runway** (Gen-4.5, start/end-frame transforms) per the shotlist prompts; keyframes are conformed in `pitch/keyframes/final/`.
3. **Edit:** lay the `normalized/*.wav` as the timing spine; music (~60s, duck under S9); grade to warm earth tones.

## Open questions / decisions
- **Grounding storyline invariant #9 was changed** (CTA no longer "bouw je droomzaak"). Team sanctioned it this session; flag if anyone disagrees.
- **Product-demo aspect:** desktop web app into a 5:7 portrait frame — capture portrait-friendly, or letterbox a desktop capture? (Affects how the demo is recorded.)
- **`droomzaak.be`** — confirm that's the real live domain before the end card.
- **Repo weight:** `voice_clips/` WAVs + `deprecated/` are tracked binaries. Decide whether to `.gitignore` `deprecated/` / large WAVs.

## Entry points
- Story spine: `pitch/droomzaak-grounding-storyline.md` (v3 — narration duet table + Beats 8/9/10)
- Shots: `pitch/droomzaak-shotlist-worksheet.md` (S8/S9/S10, Non-Lore assets, variant table)
- VO: `pitch/droomzaak-vo-script.md` (as-generated 10-clip table + measured timing map)
- Checklist: `pitch/droomzaak-pitch-video-checklist.md` (spec sheet, Phase B/C, open items)
- Audio: `pitch/voice_clips/normalized/` (edit-ready) · `pitch/voice_clips/deprecated/` (superseded)
- Skill: `media-prompt-craft` (+ `media-prompt-smith` agent) for any prompt/VO work.

## Gotchas hit
- **ElevenLabs hates short fragments** — 2–3-word lines (`"Wat dan wel?"`) generate poorly; lengthen them (we did, S3–S5). Reflected in the as-generated table.
- **`ffmpeg loudnorm` two-pass:** the `linear=true` token mangled the filter string on this build — dropped it; two-pass with measured values still normalizes accurately. The re-run loop auto-skips already-normalized clips (idempotent).
- **Master is 5:7 portrait (864×1214)**, NOT 16:9 or 9:16 — a stale 16:9 note was corrected in the shotlist/checklist. Any new asset (incl. the demo capture) must target 5:7 or letterbox.

## Verification
- Loudness consistency: `cd pitch/voice_clips/normalized && for f in *.wav; do ffmpeg -hide_banner -i "$f" -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | grep input_i; done` → every clip ≈ −16 LUFS.
- Active-set integrity: 10 MP3 in `voice_clips/` ↔ 10 WAV in `normalized/`, no orphans.
