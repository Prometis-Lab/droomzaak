# Droomzaak Pitch Video — Voice-Over Script & ElevenLabs Setup

> The narrator script, ready to paste into **ElevenLabs v3**. Flemish (nl-BE), warm radio-ad narrator. The hero never speaks — all language is here.
>
> Story: [`droomzaak-grounding-storyline.md`](droomzaak-grounding-storyline.md) · Shots: [`droomzaak-shotlist-worksheet.md`](droomzaak-shotlist-worksheet.md)
> **Status:** draft v1 · **Owner:** Track C · 2026-05-30

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

| # | Shot | Flemish text *(exact)* | Delivery note | EN gloss |
|---|------|------------------------|----------------|----------|
| 1 | S1 | **Je job beu?** | light, teasing open — a knowing smile | "Fed up with your job?" |
| 2 | S2 | **Was dit je droomjob?** | gentle, almost rhetorical | "Was this your dream job?" |
| 3 | S3 | **Wat dan wel?** | curious, inviting — sets up the reveal | "Then what?" |
| 4 | S4 | **Dit meer je stijl?** | playful, warm | "More your style?" |
| 5 | S5 | **Of dit?** | a beat quicker — momentum | "Or this?" |
| 6 | S6 | **Ondernemen, da's een zaak van dromen.** | warm, confident — the thesis line; small pause after "Ondernemen," | "Entrepreneurship — it's a matter of dreams." |
| 7 | S8 | **Laat administratie en keuzestress je dromen niet tegenhouden.** | reassuring, grounded | "Don't let paperwork and choice-stress hold your dreams back." |
| 8 | S8 | **Bezoek onze website en bouw je droomzaak.** | clear, warm call to action | "Visit our site and build your dream business." |

> Lines 7 + 8 can be rendered as one continuous take for natural flow, or separately for edit control.

---

## Pronunciation & phrasing notes (nl-BE)

- **"da's"** — keep the colloquial elision of *dat is* → *da's*. It's warmer and more Flemish than the full form. If the TTS mispronounces it, fall back to writing **"dat is"** but keep the relaxed delivery.
- **Soft G** — a proper Flemish (southern) soft *g* in *job, droomjob, dromen, zaak, tegenhouden*. Verify the chosen voice isn't a hard-G (northern nl-NL) timbre.
- **"keuzestress"** — one word, stress on *keu-ze-stress*; let it sound mildly exasperated.
- **"droomzaak"** — the product name; even, clear, slight lift — it's the payoff word.
- **Pace** — short questions land best with a tiny pause *after* each; line 6 wants a comma-beat after "Ondernemen,".

---

## Timing map (approximate)

| Line | Lands on | ~duration |
|---|---|---|
| 1 "Je job beu?" | end of S1 | ~1.0s |
| 2 "Was dit je droomjob?" | S2 | ~1.4s |
| 3 "Wat dan wel?" | S3 transform | ~1.0s |
| 4 "Dit meer je stijl?" | S4 transform | ~1.2s |
| 5 "Of dit?" | S5 transform | ~0.8s |
| 6 "Ondernemen, da's een zaak van dromen." | S6 | ~2.2s |
| 7 "Laat administratie en keuzestress..." | S8 | ~2.4s |
| 8 "Bezoek onze website en bouw je droomzaak." | S8 | ~2.2s |
| **Total VO** | | **~12s spread across ~45s** |

The VO is sparse by design — the transforms and music carry the rest.

---

## Generation steps

1. In ElevenLabs, **select the Flemish male voice** directly (not via locale dropdown).
2. Set the model (v3) + the suggested settings above.
3. Paste **line 1**, render, listen for soft-G + warmth; adjust settings once, then keep them fixed.
4. Render lines 2–8 with the same locked settings (consistency across the spot).
5. Export each as **WAV** (highest quality); name `vo_01.wav` … `vo_08.wav`.
6. Drop into the edit as the timing spine; the picture cuts to the VO.

## Music & SFX (reference — see checklist)
- **Music:** upbeat indie-pop, ~45s, light build, lands on the CTA (Suno, or licensed).
- **SFX:** paper thud (S1), a soft "whoosh" on each transform (S3–S5), rapid pop/click stack on the tab-explosion (S7), gentle UI chime on the landing page (S8).
