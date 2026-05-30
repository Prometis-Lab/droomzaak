# Droom landing page — design

**Date:** 2026-05-30
**Branch:** `feat/dream-landing` (off `YC-branch`)
**Track:** B (frontend / canvas)

## Goal

A full-screen warm-orange landing that greets a *fresh* founder, hides the map, and
forces the five-chapter journey to start from one sentence. The founder types their
dream, clicks **Droom**, and the input box physically flies into the right-side chat
slot as the map fades in behind it — a real shared-element (FLIP) transition.

## When it shows (the "fresh session" rule)

App holds a `landed` boolean:

- `false` on a new session and after **+ Nieuwe droom** → overlay renders.
- Flips to `true` the moment the founder dreams (on submit).
- The chapter-load effect sets `landed = true` when `chapterState.dream_profile !== null`,
  so reloading an *in-progress* session skips straight to the map. `dream_profile` is
  the durable signal (in-memory `messages` is empty after reload, so it can't be used).

The overlay only renders while `!landed`. The full app (rail + map + panel) always
mounts underneath, opaque overlay on top — which is what the FLIP needs to measure the
destination rect.

## Layout

- **Backdrop:** `position: fixed` full-viewport (covers the 88px chapter rail too —
  truly full-screen). Warm gradient: `--ochre` → `--terracotta` over `--paper`.
- **Card:** centered, paper-colored (`--paper`), rounded, soft shadow. The cream-bg
  logo blends into the paper card seamlessly. Contains:
  - `droomzaak.png` logo (~96px) — copied to `frontend/public/droomzaak.png`, served at `/droomzaak.png`.
  - Wordmark **Droomzaak** (serif `--font`).
  - Tagline: *"Ondernemen, dat is een zaak van dromen."*
  - Large `<textarea>` — same placeholder as chapter 1
    (*"Een kleine veganistische bistro, koffie 's ochtends, dichtbij de Vrijdagmarkt…"*).
  - **Droom** button (terracotta), disabled while empty.

## The FLIP morph

A `ref` on the landing card (source) and a `ref` threaded down to `AgentPanel`'s
`.chat-input` container (destination). On submit:

1. Measure both rects via `getBoundingClientRect()`.
2. Fire `onDream(text)` → App sets `landed = true` and calls existing `handleSend(text)`
   (sends the dream as turn 1; the agent starts chapter 1, founder sees their dream as
   message 1 with the agent reply loading).
3. The card is fixed at its source rect, then animates `transform: translate()+scale()`
   to the destination rect (~600ms `cubic-bezier`) while the backdrop fades to
   transparent, revealing the live map. On `transitionend`, the overlay unmounts.

**Reduced motion:** if `prefers-reduced-motion`, skip the flight — crossfade the overlay
out instead.

**Missing destination:** if the chat input rect is unavailable (panel was collapsed via
the persisted `panelCollapsed` flag, so `.chat-input` isn't mounted), fall back to the
same crossfade — never animate toward a zero rect.

## Files

| File | Change |
|---|---|
| `frontend/src/components/DreamLanding.tsx` | **new** — overlay + card + FLIP logic. Props: `targetRef: RefObject<HTMLElement>`, `onDream: (text: string) => void`. |
| `frontend/src/App.tsx` | `landed` state; `dream_profile → landed` effect; render `<DreamLanding>` when `!landed`; thread `chatInputRef` to `AgentPanel`; wire `onDream` (set landed + handleSend). `handleNewChat` resets `landed = false`. |
| `frontend/src/components/AgentPanel.tsx` | accept + attach a forwarded `ref` to the `.chat-input` container. |
| `frontend/src/index.css` | `.dream-landing` overlay, card, gradient, button, morph/fade transitions, reduced-motion fallback. |
| `frontend/public/droomzaak.png` | **new** — logo asset (copied from repo root). |

## Out of scope (YAGNI)

- No new backend/agent changes — reuses `handleSend` and the existing chat turn.
- No persistence of `landed` to localStorage — `dream_profile` already covers reload.
- No multi-step landing / onboarding carousel — one card, one input, one button.

## Verification

- `tsc -b` clean, `npm run build` passes.
- Fresh load → landing shows full-screen; map hidden.
- Type + Droom → card flies to chat slot, map fades in, dream appears as message 1,
  agent reply loads. Overlay gone.
- **+ Nieuwe droom** → landing returns.
- Reload mid-journey (dream already extracted) → no landing, straight to map.
- `prefers-reduced-motion` → crossfade, no flight, same end state.
