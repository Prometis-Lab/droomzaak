export const CHAPTERS = [
  { id: "1_droom", icon: "💭", label: "Droom" },
  { id: "2_niche", icon: "👥", label: "Niche" },
  { id: "3_waar", icon: "📍", label: "Waar" },
  { id: "4_vergunningen", icon: "📋", label: "Vergunningen & geld" },
  { id: "5_pakket", icon: "📦", label: "Pakket" },
] as const;

export type ChapterId = (typeof CHAPTERS)[number]["id"];

type Props = {
  current: ChapterId;
  onAdvance?: (to: ChapterId) => void;
};

export function ChapterRail({ current, onAdvance }: Props) {
  const currentIdx = CHAPTERS.findIndex((c) => c.id === current);
  return (
    <nav className="chapter-rail">
      <div className="brand">Droom&shy;zaak</div>
      {CHAPTERS.map((c, i) => {
        const isActive = c.id === current;
        const isComplete = currentIdx > i;
        const canAdvance = isComplete || isActive;
        return (
          <button
            key={c.id}
            className={[
              "chapter-step",
              isActive ? "active" : "",
              isComplete ? "complete" : "",
            ].join(" ")}
            disabled={!canAdvance}
            onClick={() => canAdvance && onAdvance?.(c.id)}
            title={c.label}
          >
            <span className="icon">{c.icon}</span>
            <span className="num">{i + 1}</span>
            <span className="label">{c.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
