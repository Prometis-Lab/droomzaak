# Handover — AI pitch-video blueprint + prompt-craft tooling

**Track:** track-c-content · **Author:** milan · **2026-05-30 14:49**

## State now
The **full blueprint** for a ~45s fully-AI-generated Flemish marketing film is written, committed, and self-consistent — but **no media has been generated yet**. Concept = **"Guided Journey"**: a fourth-wall-aware hero (Lore) is transported through transforming worlds by a Flemish narrator only she can hear (Old Spice continuity × Deadpool wink); ends on the keuzestress tab-explosion → Droomzaak CTA. All generation prompts (image keyframes, video shots, VO) are copy-paste-ready. A `media-prompt-smith` agent + `media-prompt-craft` skill exist to craft/refine prompts. Committed: `38b85d9` (docs), `e5616fe` (agent+skill). Tree clean.

## What I just did (commits `38b85d9`, `e5616fe`)
- **5 pitch docs** in `pitch/`: grounding storyline (invariant spine + 8-line Flemish duet), Lore reference + style bible (master identity block, 4 wardrobe states, KF0–KF4 prompts), shot worksheet (S1–S8 Runway Gen-4.5 prompts + start/end-frame transform method), VO script (ElevenLabs Flemish setup), production checklist (Nano Banana → Runway → ElevenLabs pipeline, accounts, QA).
- **Tooling**: `media-prompt-smith` agent + `media-prompt-craft` skill (tandem), registered in `CLAUDE.md`.
- Locked via interview: Lore = late-20s, slim, black curly hair, brown skin, bubbly; worlds = admin office → bistro → florist → bike workshop; warm radio-ad nl-BE narrator; upbeat indie-pop; query *"Hoe start ik een eigen zaak?"*; tools = Runway Gen-4.5 + Nano Banana Pro + ElevenLabs; 16:9 + 9:16; no subtitles.

## Next concrete step
**Draft the Lore hero-reference prompt** (in progress next) → paste into **Nano Banana Pro** (no signup; uses Google access) to lock her identity, then generate **KF0–KF4**. Everything downstream inherits consistency from that one image. See `pitch/droomzaak-lore-reference.md` §4 Step 1–2.

## Open questions / blockers
- **Droomzaak landing-page screenshot** — only hard external dependency; needed for final beat S8 (16:9 + 9:16). Get live/staging URL or capture.
- **Account signups** still needed: Runway (video), ElevenLabs (voice), Suno (music). Images covered (Google/ChatGPT).
- **2 confirmations**: florist + bike-workshop wardrobe defaults (`droomzaak-lore-reference.md` §3); eyeball Lore from first real Nano Banana output before mass-generating.

## Exact entry points
- Story (invariant): `pitch/droomzaak-grounding-storyline.md`
- Lore identity + keyframe prompts: `pitch/droomzaak-lore-reference.md` §1 (master block), §4 (steps)
- Shot prompts: `pitch/droomzaak-shotlist-worksheet.md` (S1–S8, variant tracker to fill)
- VO + ElevenLabs settings: `pitch/droomzaak-vo-script.md`
- Pipeline/accounts/QA: `pitch/droomzaak-pitch-video-checklist.md`
- Prompt help: dispatch agent `media-prompt-smith` (invokes skill `media-prompt-craft`)

## Gotchas hit
- **ElevenLabs**: pick the Flemish voice *directly*, not via the "Dutch (Belgium)" locale dropdown (routes to GCP/Azure).
- **Transforms**: same Lore pose/framing across keyframes; Runway start-frame=KF(A), end-frame=KF(B); generate ~10s, cut ~2–3s on the movement.
- **Consistency**: paste Lore's master identity block *verbatim* every time (paraphrase = drift); Nano Banana Identity-Lock beats Midjourney here and needs no new account.
- **Narration is trade-agnostic** — only the visuals + Google query name the trade, so new dream worlds are swappable modules without touching VO/music.

## Verification
Docs render + cross-link; gate green; tree clean:
```
ls pitch/                     # 5 .md docs
git log --oneline -2          # 38b85d9 docs(pitch), e5616fe chore(agents)
git status --short            # clean
```
No media assets exist yet (`find pitch -type f \( -name '*.png' -o -name '*.mp4' -o -name '*.wav' \)` → empty) — expected; generation is the next phase.
