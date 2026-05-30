import { useState } from "react";
import type { ChapterId } from "./ChapterRail";

export interface ChatMessage {
  role: "user" | "agent";
  text: string;
}

const PLACEHOLDERS: Record<ChapterId, string> = {
  "1_droom": "Een kleine veganistische bistro, koffie 's ochtends, dichtbij de Vrijdagmarkt…",
  "2_niche": "Vraag iets over je niche, of klik ‘Vind je plek’.",
  "3_waar": "Welke plek spreekt je aan? Of typ een adres…",
  "4_vergunningen": "Vraag naar een vergunning, subsidie of de juridische vorm…",
  "5_pakket": "Stel een vraag over je pakket…",
};

type Props = {
  current: ChapterId;
  messages: ChatMessage[];
  busy: boolean;
  onSend: (text: string) => void;
};

export function AgentPanel({ current, messages, busy, onSend }: Props) {
  const [draft, setDraft] = useState("");

  const submit = () => {
    const text = draft.trim();
    if (!text || busy) return;
    onSend(text);
    setDraft("");
  };

  return (
    <div className="agent-panel-body">
      <div className="chat-log">
        {messages.length === 0 && (
          <div className="chat-hint">
            Welkom bij Droomzaak. Vertel in één zin over je droomzaak in Gent — we bouwen
            samen stap voor stap een plan.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.text}
          </div>
        ))}
        {busy && <div className="chat-msg agent thinking">Droomzaak denkt na…</div>}
      </div>
      <div className="chat-input">
        <textarea
          value={draft}
          placeholder={PLACEHOLDERS[current]}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={3}
        />
        <button onClick={submit} disabled={busy || !draft.trim()}>
          Stuur
        </button>
      </div>
    </div>
  );
}
