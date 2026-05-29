---
name: dream-narrative-style
description: Use when generating or reviewing the Droomzaak Chapter-5 dream narrative, the Tuesday-morning simulation card, or any founder-facing prose in the package. Encodes the tone guardrails (warm, concrete, third-person reportage, grounded in the founder's own words, never extrapolating beyond the data) that keep the output from landing as cringey AI-magazine prose — the top content risk — plus the compose_package serialization contract.
---

# Dream-narrative style

The dream narrative is the pitch climax (PRD §2 Ch.5, §5.4) and a top risk (§6.1): AI prose easily lands as cringey, second-person aspirational magazine copy. **Rigid** on tone and length, flexible on wording.

## Voice
- **Warm, concrete, grounded.** Numbers and rules *frame* the dream; they never gate it (§1.4). Dream-first, not form-first.
- **Third-person reportage, not second-person aspiration.** Write *about* the founder + the plan as an OOG advisor would in a write-up — not "Imagine yourself…", "Your dream awaits…".
- **Grounded in the founder's own words.** Reuse the vibe quote from Chapter 1; reflect actual parameters (seats, neighbourhood, scale) — no invented detail.
- **Never extrapolate beyond the data.** The Tuesday-morning card (open 8u, ~80 covers/day, ~€280k/yr, take-home estimate) must be **conservative** and traceable to the chapter's numbers (footfall composite, Belfirst peer cohort). If a figure isn't supported, don't print it.
- **Name uncertainty, point to humans** (OOG / FAVV / Stad Gent). Do not fake certainty.
- **Length-capped:** three short paragraphs for the narrative; one tight card for the simulation.

## Structure (Chapter 5 package top)
1. **Narrative** — 3 paragraphs: the dream as stated → what the data says makes it plausible here → the honest caveat + the next concrete step.
2. **Jouw dinsdagochtend** — one day-in-the-life card: opening time, estimated covers, estimated turnover, estimated monthly take-home. Every number conservative + labelled an estimate.

## Implementation
- `generate_dream_narrative(...)` is an LLM tool with a **style guide in the prompt + two-shot examples** (kept in the prompt, not hardcoded output). Dutch primary (`AGENT_LANGUAGE=nl`), EN fallback.
- `compose_package(state)` is **pure Python** — serializes the full chapter state (narrative, chosen address, niche numbers, permit checklist, subsidies, legal-form, hand-off block) into the renderer input. No reasoning in `compose_package`; all judgement lives in the tools that filled `state`.
- **Pre-screen before Saturday** (§6.1): generate for Lisa AND the Sofie/retail path, read both aloud. If either makes someone wince, tighten the style guide before the demo.

## Review test
Read it aloud in your head. Passes if it sounds like a thoughtful advisor, every number traces to a chapter, caveats are present, nobody winces. Fails if it sounds like a horoscope, a brochure, or a pitch to the founder.
