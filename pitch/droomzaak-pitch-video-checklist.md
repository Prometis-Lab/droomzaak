# Droomzaak — AI Pitch Video: Production Checklist

> Master checklist for the **"Guided Journey"** spot — a ~45s fully AI-generated Flemish brand film. This is the *process hub*; the creative + generation detail lives in the linked docs.
>
> - **Story spine (invariant):** [`droomzaak-grounding-storyline.md`](droomzaak-grounding-storyline.md)
> - **Lore reference + style bible:** [`droomzaak-lore-reference.md`](droomzaak-lore-reference.md)
> - **Shot & generation worksheet:** [`droomzaak-shotlist-worksheet.md`](droomzaak-shotlist-worksheet.md)
> - **VO script + ElevenLabs setup:** [`droomzaak-vo-script.md`](droomzaak-vo-script.md)
>
> **Status:** draft v2 (re-synced to Guided Journey concept) · **Owner:** Track C · 2026-05-30

---

## 0. Spec sheet (decisions locked)

| Field | Value |
|---|---|
| **Concept** | Guided Journey — fourth-wall-aware Lore transported through transforming worlds by a narrator only she can hear (Old Spice continuity × Deadpool wink) |
| **Audience** | Broad marketing / launch (website CTA + social) |
| **Length** | ~60s master (brand spot ~38s + product-demo tail ~22s; scales by adding dream modules) |
| **Language** | Flemish (nl-BE) narrator VO · **no subtitles** · hero non-speaking |
| **Hero** | Lore — late 20s, slim, black curly hair, brown skin, no glasses, bubbly |
| **Worlds** | Bureaucratic admin office (before) → bistro → florist → bike workshop → back → keuzestress → Droomzaak landing page → **product demo** → CTA/end card |
| **Format** | **5:7 portrait master, 864×1214** (native ratio of the Gemini dream frames). All 6 keyframes conformed to it in `pitch/keyframes/final/`. Vertical/social-friendly; a 16:9 or true-9:16 cut later via Runway Expand. |
| **Video tool** | Runway Gen-4.5 (image-to-video, start/end-frame transforms) |
| **Image tool** | Nano Banana Pro (Gemini) — identity-locked keyframes · backup GPT Image 2 |
| **Voice tool** | ElevenLabs v3 — Flemish male, warm radio-ad narrator |
| **Music** | Upbeat indie-pop (Suno or licensed) |
| **Delivery** | Copy-paste prompt sheets |
| **Tagline / CTA** | Signature: *"Ondernemen, da's een zaak van dromen."* · Spoken CTA: *"Bezoek onze website en laat ons je helpen je droomleven waar te maken. droomzaak.be, want ondernemen, da's een zaak van dromen."* · End-card tagline: *"Van droom naar zaak."* |

---

## 1. The pipeline (how the pieces connect)

```
Nano Banana ──(KF0–KF4, identity-locked)──► Runway Gen-4.5 ──(S1–S8 clips)──► Edit
   (keyframes)        start/end frames        (image-to-video)        │
ElevenLabs (Flemish VO) ───────────────────────────────────────────► │
Suno (music) + SFX ────────────────────────────────────────────────► ├─► Color → 16:9 master
Screen-capture (tabs) + Droomzaak landing page ────────────────────► │       └─► 9:16 social
```

---

## 2. Accounts & signups (you have LLM providers only)

| Need | Tool | Account status |
|---|---|---|
| Keyframes / character | **Nano Banana Pro (Gemini)** or **GPT Image 2 (ChatGPT)** | ✅ reuse existing Google / ChatGPT — no signup |
| Video shots | **Runway** | ⚠️ new signup + credits needed |
| Flemish VO | **ElevenLabs** | ⚠️ new signup needed |
| Music | **Suno** | ⚠️ new signup, *or* license a track / use a royalty-free library |
| Edit / color | **DaVinci Resolve** | free download |

> **All-Google fallback** (avoids Runway + ElevenLabs signups, lower control): Veo 3.1 via **Google Flow** for video + **Google Cloud TTS** nl-BE voice. Use only if you want to stay inside Google; Runway + ElevenLabs remain the quality pick for the transforms and narrator.

---

## 3. Production checklist

### Phase A — Pre-production (lock before generating)
- [ ] Story spine approved (grounding storyline).
- [ ] **Lore hero reference** generated + saved (lore-reference §4, Step 1).
- [ ] **KF0–KF4** keyframes generated, identity-locked, same pose (Step 2).
- [x] VO script final-read for natural nl-BE (vo-script §pronunciation) — ear-checked on the rendered clips.
- [ ] Runway + ElevenLabs + Suno accounts ready; Resolve installed.
- [ ] Decide tab-explosion + landing page = real capture (recommended) vs generated.

### Phase B — Asset generation
- [ ] **Video** — generate S1–S7 in Runway (2–3 variants each, ~10s, cut to target). Use start/end frames for the transforms (S3–S6). (S8–S10 are edit/screen-capture, not Runway.)
- [x] **Narrator VO** — ✅ rendered (ElevenLabs v3) + loudness-normalized to −16 LUFS / −1.5 dBTP WAV in `pitch/voice_clips/normalized/` (10 clips). See vo-script.
- [ ] **Music** — one ~60s upbeat indie-pop track, light build to the CTA; duck under the S9 product-demo VO.
- [ ] **SFX** — paper thud, transform whooshes, tab-explosion pop-stack, landing-page chime, subtle UI ticks under the product demo.
- [ ] **Screen assets** — tab-explosion capture/mock (query *"Hoe start ik een eigen zaak?"*) + **Droomzaak landing-page screenshot** *(need live URL/capture from you)* + **product-demo screen capture (S9, joint)** + logo end card from `droomzaak.png`.

### Phase C — Assembly & polish
- [ ] **Edit** — lay VO as the timing spine; cut each transform **on the movement**; sync music build to the CTA.
- [ ] **Color** — unify all Runway clips to the warm earth-tone palette; keep the office deliberately desaturated. *(Non-negotiable — AI clips drift in grade.)*
- [ ] **Comp** — transform seams, push-in into the screen capture, fade-to-black → landing page.
- [ ] **Titles** — end-card tagline only (no subtitles).
- [ ] **Audio mix** — VO clarity first, music ducked under VO, SFX balanced.
- [ ] **QA** — Lore consistency across worlds, no warped hands/faces, palette holds, fourth-wall device clean (only Lore aware), nl-BE reads naturally, brisk pace.
- [ ] **Export** — 5:7 portrait master, 864×1214 (H.264/H.265) → a 16:9 or true-9:16 cut later via **Runway Expand** (this 5:7 won't cleanly crop to either).

---

## 4. Tools shortlist (research-backed)

| Need | Pick | Notes |
|---|---|---|
| Keyframes / consistency | **Nano Banana Pro** | "Identity Locking", multi-reference — best for one character across worlds. Backup: GPT Image 2. |
| Video | **Runway Gen-4.5** | start/end-frame control + multi-shot continuity = clean match-cuts. |
| Flemish VO | **ElevenLabs v3** | pick the Flemish voice directly (not via BE locale dropdown). |
| Music | **Suno** | or licensed/royalty-free. |
| Edit / color / mix | **DaVinci Resolve** | free, strong color. |

**Sources:** image-model consistency ([Nano Banana vs Midjourney](https://nanoimagine.art/blog/nano-banana-vs-midjourney-2026), [GPT Image 2 guide](https://www.befreed.ai/blog/gpt-image-2-guide-2026)); video models ([Pixflow](https://pixflow.net/blog/best-ai-video-generator/)); Flemish TTS ([ElevenLabs](https://elevenlabs.io/text-to-speech/dutch), [SpeechGen](https://speechgen.io/en/tts-dutch-belgium/)); AI marketing-video workflow ([digen.ai](https://resource.digen.ai/ai-video-generation-for-marketing-2026/)).

---

## 5. Open items / risks
- [ ] **Droomzaak landing-page asset** — provide the live/staging URL or a screen-capture for the end beat (5:7 portrait, 864×1214, or letterbox).
- [ ] **Product-demo capture (S9)** — joint screen capture of the live app to match the 16.3s `product_description` VO (describe-dream → Droomkaart/insights → location/permits/financial → package); 5:7 portrait or letterbox. *Tonal note: this beat drops the Lore fourth-wall device — keep it brisk so it reads as proof.*
- [ ] **Florist + workshop wardrobe** — defaults set in lore-reference §3; confirm or tweak.
- [ ] **Risk: character drift** — mitigate with Nano Banana Identity Lock + reusing the hero reference every time; budget extra variants.
- [ ] **Risk: colour drift** — the Phase-C grade is mandatory.
- [ ] **Risk: transform seams** — generate long for handles; cut strictly on movement; same pose across keyframes.
- [ ] **Risk: text rendering** (Google search beat) — prefer a real screen-capture over generated text.
- [ ] **Scope** — this is a post-hackathon marketing film; don't let it pull focus from Saturday's working demo (PRD §5.2 freeze at hour 6).
