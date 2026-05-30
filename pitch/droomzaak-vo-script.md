# Droomzaak Pitch Video — Voice-Over Script & ElevenLabs Setup

> The narrator script, ready to paste into **ElevenLabs v3**. Flemish (nl-BE), warm radio-ad narrator. The hero never speaks — all language is here.
>
> Story: [`droomzaak-grounding-storyline.md`](droomzaak-grounding-storyline.md) · Shots: [`droomzaak-shotlist-worksheet.md`](droomzaak-shotlist-worksheet.md)
> **Status:** draft v2 — synced to as-generated clips + product-demo tail · **Owner:** Track C · 2026-05-30
>
> ✅ **Rendered & loudness-normalized.** All 10 clips live in `pitch/voice_clips/` (source MP3) and `pitch/voice_clips/normalized/` (edit-ready WAV, −16 LUFS / −1.5 dBTP). The table below is the **as-generated** wording (some lines were lengthened during generation because very short fragments read poorly in TTS). Superseded clips are in `pitch/voice_clips/deprecated/`.

---

## Voice selection (ElevenLabs)

- **Pick a Flemish (nl-BE) male voice directly** from the voice library — e.g. **Jan Schevenels, Hans Claesen, Walter, or Jann**. ⚠️ Do **not** select via the "Dutch (Belgium)" *language* dropdown — that can route you to GCP/Azure voices. Choose the voice itself.
- **Model:** Eleven v3 (most expressive) — or Multilingual v2 if v3's nl-BE handling is weaker on test.
- **Direction:** warm, confident, polished radio-ad narrator — a knowing half-smile, but smooth (not over-teasing).

**Suggested settings** (tune on a test render):
| Setting | Value | Why |
|---|---|---|
| Stability | ~50% | Consistent "radio" read without flatness |
| Similarity | ~75% | Stay true to the chosen voice |
| Style exaggeration | low–moderate | Warmth without hammy delivery |
| Speed | slightly slow | Let each short line land; brisk *picture*, unhurried *voice* |

> **v3 audio tags** (optional, sparingly): a `[warm]` or `[smiling]` cue at the open can add the knowing tone. Avoid heavy tags — the warmth should feel natural.

---

## The script (paste each line; render line-by-line for clean timing)

| # | Shot | Clip (`normalized/*.wav`) | Flemish text *(as generated)* | Delivery note |
|---|------|------|------|------|
| 1 | S1 | `Ben_je_je_job_beu` | **Ben je je job beu?** | light, teasing open — a knowing smile |
| 2 | S2 | `was_dit_dan_je_droomjob` | **Was dit dan je droomjob?** | gentle, almost rhetorical |
| 3 | S3 | `wat_zou_je_droomjob_dan_wel_zijn` | **Wat zou je droomjob dan wel zijn?** | curious, inviting — sets up the reveal |
| 4 | S4 | `dit_misschien_meer_je_stijl` | **Dit misschien meer je stijl?** | playful, warm |
| 5 | S5 | `of_misschien_deze` | **Of misschien deze?** | a beat quicker — momentum |
| 6 | S6 | `ondernemen_das_een_zaak_van_dromen` | **Ondernemen, da's een zaak van dromen.** | warm, confident — the thesis line; small pause after "Ondernemen," |
| 7 | S8 | `Laat_administratie_en_keuzestress_je_dromen_niet_tegenhouden` | **Laat administratie en keuzestress je dromen niet tegenhouden.** | reassuring, grounded |
| 8 | S9 | `product_description` | **Het enige dat je moet doen is je droomzaak beschrijven, en wij loodsen je doormiddel van inzichten uit allerlei databronnen door alle beslissingen van locatie en vergunningen, tot wat je kan verwachten op financieel vlak. Zodat jij kan blijven dromen.** | the product-demo VO over the live screen capture; even, confident, unhurried — it's proof |
| 9 | S10 | `bezoek_onze_website` | **Bezoek onze website en laat ons je helpen je droomleven waar te maken.** | warm call to action |
| 10 | S10 | `droomzaak_be_CTA` | **droomzaak.be, want ondernemen, da's een zaak van dromen.** | the closer — the *zaak* pun bookends line 6; clear, slight lift on "droomzaak.be" |

> S7 (tab-explosion) carries **no VO** — let it play. Lines 9 + 10 can run as one continuous CTA take or separately for edit control. The signature line returns in clip 10 — that's the deliberate payoff (grounding invariant #9).

---

## Pronunciation & phrasing notes (nl-BE)

- **"da's"** — keep the colloquial elision of *dat is* → *da's*. It's warmer and more Flemish than the full form. If the TTS mispronounces it, fall back to writing **"dat is"** but keep the relaxed delivery.
- **Soft G** — a proper Flemish (southern) soft *g* in *job, droomjob, dromen, zaak, tegenhouden*. Verify the chosen voice isn't a hard-G (northern nl-NL) timbre.
- **"keuzestress"** — one word, stress on *keu-ze-stress*; let it sound mildly exasperated.
- **"droomzaak"** — the product name; even, clear, slight lift — it's the payoff word.
- **"loodsen"** (clip 8) — soft Flemish G/oo; "we guide you through" — steady, reassuring, not rushed despite the long sentence.
- **"droomleven"** (clip 9) — warm, clear compound; the emotional promise of the CTA.
- **"droomzaak.be"** (clip 10) — read the URL evenly ("droomzaak punt be"); then the comma-beat before the signature line lands the pun.
- **Pace** — short questions land best with a tiny pause *after* each; line 6 wants a comma-beat after "Ondernemen,". Clip 8 is long — keep it unhurried and let the picture (the demo) lead.

---

## Timing map (measured — actual clip durations)

| Clip | Lands on | duration |
|---|---|---|
| 1 "Ben je je job beu?" | end of S1 | 1.62s |
| 2 "Was dit dan je droomjob?" | S2 | 1.85s |
| 3 "Wat zou je droomjob dan wel zijn?" | S3 transform | 2.32s |
| 4 "Dit misschien meer je stijl?" | S4 transform | 1.93s |
| 5 "Of misschien deze?" | S5 transform | 1.49s |
| 6 "Ondernemen, da's een zaak van dromen." | S6 | 2.74s |
| 7 "Laat administratie en keuzestress…" | S8 (website reveal) | 4.62s |
| 8 "Het enige dat je moet doen…" *(product demo)* | S9 | 16.30s |
| 9 "Bezoek onze website…" | S10 | 5.43s |
| 10 "droomzaak.be, want ondernemen…" | S10 end card | 5.28s |
| **Total VO** | | **~43.6s across ~60s** |

The front half (clips 1–6) stays sparse — the transforms and music carry it. The back half (clips 7–10) is denser because the **product-demo tail is VO-led**: clip 8 alone is 16.3s of continuous narration over the screen capture.

---

## Generation steps — ✅ done (for reference / re-renders)

1. In ElevenLabs, **select the Flemish male voice** directly (not via locale dropdown).
2. Set the model (v3) + the suggested settings above.
3. Paste a line, render, listen for soft-G + warmth; adjust settings once, then keep them fixed.
4. Render the remaining lines with the same locked settings (consistency across the spot).
5. Export MP3 → clips named descriptively in `pitch/voice_clips/`. **Loudness-normalized** to −16 LUFS / −1.5 dBTP WAV in `pitch/voice_clips/normalized/` (two-pass `ffmpeg loudnorm`).
6. Drop the **normalized WAVs** into the edit as the timing spine; the picture cuts to the VO.

> To re-render or add a clip: generate the MP3 into `pitch/voice_clips/`, then re-run the loudnorm pass (it auto-skips already-normalized clips). Avoid 2–3-word fragments — they read poorly in TTS; lengthen as we did for clips 1–5.

## Music & SFX (reference — see checklist)
- **Music:** upbeat indie-pop, **~60s**, light build; carries the front transforms, ducks under the product-demo VO (S9), lands on the CTA (S10). Suno, or licensed.
- **SFX:** paper thud (S1), a soft "whoosh" on each transform (S3–S5), rapid pop/click stack on the tab-explosion (S7), gentle UI chime on the landing-page reveal (S8) and subtle UI ticks under the product demo (S9).
