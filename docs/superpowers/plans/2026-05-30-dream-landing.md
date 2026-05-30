# Droom Landing Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A full-screen warm-orange landing that greets a fresh founder, hides the map, and forces the journey to start from one sentence — whose input box flies (FLIP) into the right-side chat slot as the map fades in.

**Architecture:** A `position: fixed` overlay (`DreamLanding`) renders over the always-mounted app while `App.landed === false`. On submit it measures its card rect and the chat-input rect, animates the card from source→destination with a CSS transform while fading the backdrop, then signals `onExited` so App unmounts it. The dream is sent to the agent immediately via the existing `handleSend`.

**Tech Stack:** React 18 + TypeScript, MapLibre (untouched), plain CSS (brand tokens in `index.css`), `getBoundingClientRect` + `requestAnimationFrame` for the FLIP.

**Conventions for this plan:**
- **No per-task git commits.** This repo commits only via `/ship` (CLAUDE.md rule 8). Each task ends by verifying the TypeScript build; the single commit happens through `/ship` at the end.
- Verification command (run from `frontend/`): `npm run build` (= `tsc -b && vite build`). For faster type-only checks: `npx tsc -b`.
- This is visual/animation work with no unit-test harness; verification is the type-check/build passing plus the manual checklist in Task 5.

---

### Task 1: Landing styles

**Files:**
- Modify: `frontend/src/index.css` (append a new section at the end, after line 405)

- [ ] **Step 1: Append the landing CSS block**

Append to the end of `frontend/src/index.css`:

```css

/* ── Droom landing (fresh-session overlay + FLIP morph) ───────── */
.dream-landing {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(120% 120% at 50% 0%, var(--ochre) 0%, var(--terracotta) 55%, var(--terracotta-deep) 100%);
  opacity: 1;
  transition: opacity 0.6s cubic-bezier(0.22, 0.61, 0.36, 1);
}
.dream-landing--leaving { opacity: 0; }

.dream-landing-card {
  width: min(560px, 100%);
  background: var(--paper);
  border-radius: 18px;
  box-shadow: 0 24px 60px var(--shadow), 0 4px 12px var(--shadow);
  padding: 36px 32px 28px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 14px;
}
.dream-landing-card img {
  width: 96px;
  height: 96px;
  object-fit: contain;
}
.dream-landing-wordmark {
  font-family: var(--font);
  font-size: 28px;
  font-weight: 700;
  color: var(--terracotta-deep);
  letter-spacing: 0.01em;
  margin: 0;
}
.dream-landing-tagline {
  font-family: var(--font);
  font-size: 16px;
  font-style: italic;
  color: var(--ink-soft);
  margin: 0 0 6px;
}
.dream-landing-card textarea {
  width: 100%;
  resize: none;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  font-family: var(--font-ui);
  font-size: 15px;
  line-height: 1.4;
  background: #fff;
  color: var(--ink);
}
.dream-landing-card textarea:focus {
  outline: none;
  border-color: var(--terracotta);
}
.dream-landing-btn {
  align-self: stretch;
  border: none;
  background: var(--terracotta);
  color: #fff;
  border-radius: 12px;
  padding: 13px 16px;
  font-family: var(--font-ui);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: background 0.15s;
}
.dream-landing-btn:hover:not(:disabled) { background: var(--terracotta-deep); }
.dream-landing-btn:disabled { opacity: 0.45; cursor: default; }

/* The card while flying to the chat slot — rect is set inline, timing here. */
.dream-landing-card--flying {
  transition:
    transform 0.6s cubic-bezier(0.22, 0.61, 0.36, 1),
    opacity 0.6s cubic-bezier(0.22, 0.61, 0.36, 1);
  box-shadow: 0 24px 60px var(--shadow);
  z-index: 51;
}

@media (prefers-reduced-motion: reduce) {
  .dream-landing { transition: opacity 0.3s linear; }
  .dream-landing-card--flying { transition: opacity 0.3s linear; }
}
```

- [ ] **Step 2: Verify the build still type-checks**

Run (from `frontend/`): `npx tsc -b`
Expected: exit 0, no errors (CSS isn't type-checked, but this confirms nothing else broke).

---

### Task 2: Forward a ref to the chat input

**Files:**
- Modify: `frontend/src/components/AgentPanel.tsx`

The FLIP needs the on-screen rect of the `.chat-input` container. Expose it via a `ref` prop.

- [ ] **Step 1: Add the `chatInputRef` prop and attach it**

In `frontend/src/components/AgentPanel.tsx`:

Change the `Props` type (currently lines 17-22) to add the optional ref:

```tsx
type Props = {
  current: ChapterId;
  messages: ChatMessage[];
  busy: boolean;
  onSend: (text: string) => void;
  chatInputRef?: React.Ref<HTMLDivElement>;
};
```

Change the function signature to destructure it:

```tsx
export function AgentPanel({ current, messages, busy, onSend, chatInputRef }: Props) {
```

Attach it to the existing `.chat-input` div (currently `<div className="chat-input">` on line 50):

```tsx
      <div className="chat-input" ref={chatInputRef}>
```

- [ ] **Step 2: Verify**

Run (from `frontend/`): `npx tsc -b`
Expected: exit 0. (`React` is already imported transitively; if `React` namespace is unresolved, add `import type React from "react";` at the top — but with the project's JSX runtime it resolves. Confirm via the build.)

---

### Task 3: The DreamLanding component

**Files:**
- Create: `frontend/src/components/DreamLanding.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/DreamLanding.tsx` with exactly:

```tsx
import { useRef, useState, type CSSProperties, type RefObject } from "react";

// Mirror of the chapter-1 placeholder in AgentPanel — the founder's first line.
const PLACEHOLDER =
  "Een kleine veganistische bistro, koffie 's ochtends, dichtbij de Vrijdagmarkt…";

type Props = {
  // The live chat-input container the card flies into. May be null if the
  // panel is collapsed — we fall back to a plain fade in that case.
  targetRef: RefObject<HTMLDivElement | null>;
  // Fired once, on submit: send the dream to the agent + mark the app dreamt.
  onDream: (text: string) => void;
  // Fired when the exit animation (or fade) finishes: App unmounts the overlay.
  onExited: () => void;
};

function prefersReducedMotion(): boolean {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

export function DreamLanding({ targetRef, onDream, onExited }: Props) {
  const [draft, setDraft] = useState("");
  const [leaving, setLeaving] = useState(false);
  const [flightStyle, setFlightStyle] = useState<CSSProperties | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  const submit = () => {
    const text = draft.trim();
    if (!text || leaving) return;

    const card = cardRef.current;
    const target = targetRef.current;

    if (card && target && !prefersReducedMotion()) {
      const from = card.getBoundingClientRect();
      const to = target.getBoundingClientRect();
      // Pin the card to its current viewport rect this frame…
      const base: CSSProperties = {
        position: "fixed",
        left: from.left,
        top: from.top,
        width: from.width,
        height: from.height,
        margin: 0,
      };
      setFlightStyle(base);
      // …then next frame, transform it onto the chat-input rect.
      requestAnimationFrame(() => {
        setFlightStyle({
          ...base,
          transformOrigin: "top left",
          transform:
            `translate(${to.left - from.left}px, ${to.top - from.top}px) ` +
            `scale(${to.width / from.width}, ${to.height / from.height})`,
          opacity: 0,
        });
      });
    }

    setLeaving(true);
    onDream(text);
  };

  // The backdrop fade is the source of truth for "exit done".
  const handleTransitionEnd = (e: React.TransitionEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget && e.propertyName === "opacity") onExited();
  };

  return (
    <div
      className={`dream-landing${leaving ? " dream-landing--leaving" : ""}`}
      onTransitionEnd={handleTransitionEnd}
    >
      <div
        ref={cardRef}
        className={`dream-landing-card${flightStyle ? " dream-landing-card--flying" : ""}`}
        style={flightStyle ?? undefined}
      >
        <img src="/droomzaak.png" alt="Droomzaak" />
        <h1 className="dream-landing-wordmark">Droomzaak</h1>
        <p className="dream-landing-tagline">Ondernemen, dat is een zaak van dromen.</p>
        <textarea
          autoFocus
          value={draft}
          placeholder={PLACEHOLDER}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={3}
        />
        <button
          type="button"
          className="dream-landing-btn"
          onClick={submit}
          disabled={leaving || !draft.trim()}
        >
          Droom
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run (from `frontend/`): `npx tsc -b`
Expected: exit 0. (Component is not yet imported — this only checks it compiles in isolation.)

---

### Task 4: Wire the landing into App

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Import DreamLanding**

Add to the import block at the top of `frontend/src/App.tsx` (after the `AgentPanel` import on line 5):

```tsx
import { DreamLanding } from "./components/DreamLanding";
```

- [ ] **Step 2: Add `landed` state and the chat-input ref**

After the `busy` state (line 62: `const [busy, setBusy] = useState(false);`), add:

```tsx
  const [landed, setLanded] = useState(false);
  const chatInputRef = useRef<HTMLDivElement>(null);
```

- [ ] **Step 3: Skip the landing for in-progress sessions**

The chapter-load effect (lines 88-92) currently only sets chapter state. Replace it with a version that also lands the founder if a dream already exists:

```tsx
  useEffect(() => {
    getChapter(sessionId)
      .then((d) => {
        setChapterState(d.chapter_state);
        if (d.chapter_state?.dream_profile) setLanded(true);
      })
      .catch(() => void 0);
  }, [sessionId]);
```

- [ ] **Step 4: Reset `landed` on a new dream**

In `handleNewChat` (lines 96-109), add `setLanded(false);` alongside the other resets — put it right after `setSelectedDatasetId(null);`:

```tsx
    setSelectedDatasetId(null);
    setLanded(false);
```

- [ ] **Step 5: Add the `onDream` handler**

Add this function right after `handleNewChat` (before `handleSend`):

```tsx
  function handleDream(text: string) {
    setLanded(true);
    void handleSend(text);
  }
```

- [ ] **Step 6: Thread the ref into AgentPanel**

In the `AgentPanel` render (line 350), add the `chatInputRef` prop:

```tsx
            <AgentPanel current={current} messages={messages} busy={busy} onSend={handleSend} chatInputRef={chatInputRef} />
```

- [ ] **Step 7: Render the overlay**

Immediately before the closing `</div>` of the `.app` container (after the `panelCollapsed ? ... : (...)` block ends on line 354, before line 355 `</div>`), add:

```tsx
      {!landed && (
        <DreamLanding
          targetRef={chatInputRef}
          onDream={handleDream}
          onExited={() => setLanded(true)}
        />
      )}
```

Note: `onDream` already sets `landed = true`, which unmounts the overlay — but only *after* its own backdrop fade completes is the cleanest path. Because `onDream` flips `landed` synchronously, the overlay would unmount before animating. **Fix in Step 8.**

- [ ] **Step 8: Keep the overlay mounted through its exit animation**

The overlay must survive until `onExited`. Split the concern: `handleDream` must NOT flip `landed`; only `onExited` does. Change `handleDream` (from Step 5) to:

```tsx
  function handleDream(text: string) {
    void handleSend(text);
  }
```

Leave Step 7's render as-is (`onExited={() => setLanded(true)}`). Now: submit → `handleDream` sends the dream + the component plays its fade/flight → `onExited` flips `landed` → overlay unmounts. The map underneath is already mounted, so it's revealed as the backdrop fades.

- [ ] **Step 9: Verify the build**

Run (from `frontend/`): `npm run build`
Expected: exit 0, `tsc -b` clean, Vite bundle written to `dist/`.

---

### Task 5: Manual verification

**Files:** none (browser checks)

- [ ] **Step 1: Run the dev server**

Run (from `frontend/`): `npm run dev`, open the printed localhost URL.

- [ ] **Step 2: Walk the checklist**

- [ ] Fresh load → full-screen orange overlay; logo + wordmark + tagline + textarea + **Droom**; map/rail hidden.
- [ ] Type a dream, press **Droom** (or Enter) → the card flies to the right-side chat slot, the orange backdrop fades, the map + rail appear behind it.
- [ ] After the morph: the dream shows as chat message 1 and the agent reply loads (`Droomzaak denkt na…`).
- [ ] Overlay is fully gone (no leftover fixed element capturing clicks).
- [ ] Click **+ Nieuwe droom** → the landing returns.
- [ ] Reload the page mid-journey (after a dream was extracted) → no landing; straight to the map.
- [ ] In OS settings enable "reduce motion" (or DevTools rendering emulation) → submit does a plain crossfade, no flight, same end state.
- [ ] Collapse the side panel first, then `+ Nieuwe droom`, then submit → no crash; falls back to crossfade (target rect unavailable).

- [ ] **Step 3: Ship**

When the checklist passes, run `/ship` to review → simplify → security-scan → commit. Do not `git push`.

---

## Self-Review notes

- **Spec coverage:** fresh-session rule (Task 4 Steps 2-4), logo+tagline (Task 1, Task 3), FLIP morph (Task 1 `--flying`, Task 3 submit), send-immediately (Task 4 `handleDream`), solid orange backdrop (Task 1 gradient), full-screen incl. rail (Task 1 `inset:0; z-index:50`), reduced-motion + missing-destination fallbacks (Task 3 guards, Task 1 media query). All covered.
- **Type consistency:** `targetRef: RefObject<HTMLDivElement | null>` (Task 3) ← `chatInputRef = useRef<HTMLDivElement>(null)` (Task 4) ← `chatInputRef?: React.Ref<HTMLDivElement>` attached to a `div` (Task 2). Consistent. `onDream`/`onExited` signatures match between Task 3 and Task 4.
- **Mount-through-exit gotcha** is explicitly resolved in Task 4 Step 8 (only `onExited` flips `landed`).
