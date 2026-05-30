import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
  type TransitionEvent,
} from "react";

// Mirror of the chapter-1 placeholder in AgentPanel — the founder's first line.
const PLACEHOLDER =
  "Een kleine veganistische bistro, koffie 's ochtends, dichtbij de Vrijdagmarkt…";

type Props = {
  // The live chat-input container the card flies into. May be null if the
  // panel is collapsed — we fall back to a plain fade in that case.
  targetRef: RefObject<HTMLDivElement | null>;
  // Fired once, on submit: send the dream to the agent.
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
  // Fallback so a dropped transitionend (background tab, coalesced frame) can
  // never strand the overlay over a live session. onExited is idempotent.
  const exitTimer = useRef<number | null>(null);
  useEffect(() => () => {
    if (exitTimer.current !== null) clearTimeout(exitTimer.current);
  }, []);

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
        const dx = to.left - from.left;
        const dy = to.top - from.top;
        const sx = to.width / from.width;
        const sy = to.height / from.height;
        setFlightStyle({
          ...base,
          transformOrigin: "top left",
          transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`,
          opacity: 0,
        });
      });
    }

    setLeaving(true);
    onDream(text);
    exitTimer.current = window.setTimeout(onExited, 800);
  };

  // The backdrop fade is the source of truth for "exit done"; the timer is the
  // safety net if its transitionend never arrives.
  const handleTransitionEnd = (e: TransitionEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget && e.propertyName === "opacity") {
      if (exitTimer.current !== null) clearTimeout(exitTimer.current);
      onExited();
    }
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
