import { useEffect, useState } from "react";
import { ChapterRail, type ChapterId } from "./components/ChapterRail";
import { MapCanvas, type MapMarker } from "./components/MapCanvas";
import { Droomkaart } from "./components/Droomkaart";
import { AgentPanel, type ChatMessage } from "./components/AgentPanel";
import { getChapter, getSessionId, sendChat } from "./droomzaak/api";
import type { ChapterState, TransientDataset } from "./droomzaak/types";

export default function App() {
  const [sessionId] = useState(getSessionId);
  const [chapterState, setChapterState] = useState<ChapterState | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [datasets, setDatasets] = useState<Record<string, TransientDataset>>({});
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getChapter(sessionId)
      .then((d) => setChapterState(d.chapter_state))
      .catch(() => void 0);
  }, [sessionId]);

  const current: ChapterId = chapterState?.current_chapter ?? "1_droom";

  async function handleSend(text: string) {
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const res = await sendChat(text, sessionId);
      setMessages((m) => [...m, { role: "agent", text: res.reply }]);
      if (res.chapter_state) setChapterState(res.chapter_state);
      if (res.datasets) setDatasets((d) => ({ ...d, ...res.datasets }));
      const newMarkers: MapMarker[] = [];
      for (const a of res.actions || []) {
        if (a.type === "place_marker" && Array.isArray(a.markers)) {
          for (const mk of a.markers) newMarkers.push({ coordinates: mk.coordinates, label: mk.label });
        }
      }
      if (newMarkers.length) setMarkers(newMarkers);
    } catch {
      setMessages((m) => [...m, { role: "agent", text: "Er ging iets mis. Probeer het opnieuw." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <ChapterRail current={current} />
      <MapCanvas datasets={datasets} markers={markers} />
      <div className="agent-panel">
        <Droomkaart state={chapterState} />
        <AgentPanel current={current} messages={messages} busy={busy} onSend={handleSend} />
      </div>
    </div>
  );
}
