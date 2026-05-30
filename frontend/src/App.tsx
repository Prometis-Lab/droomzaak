import { useEffect, useState } from "react";
import { ChapterRail, type ChapterId } from "./components/ChapterRail";
import { MapCanvas } from "./components/MapCanvas";
import { Droomkaart } from "./components/Droomkaart";

export default function App() {
  const [current] = useState<ChapterId>("1_droom");
  const [health, setHealth] = useState<string>("…");

  useEffect(() => {
    fetch("/api/admin/health")
      .then((r) => r.json())
      .then((d) => setHealth(d.ok ? `backend ✓ (${d.provider})` : "backend ?"))
      .catch(() => setHealth("backend offline"));
  }, []);

  return (
    <div className="app">
      <ChapterRail current={current} />
      <MapCanvas />
      <div className="agent-panel">
        <Droomkaart />
        <div className="agent-shell">
          Chat met Droomzaak komt hier (Hoofdstuk {current.replace("_", " ")}).
          <br />
          <small>{health}</small>
        </div>
      </div>
    </div>
  );
}
