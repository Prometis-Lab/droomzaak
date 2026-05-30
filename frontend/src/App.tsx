import { useEffect, useRef, useState, useCallback } from "react";
import { ChapterRail, type ChapterId } from "./components/ChapterRail";
import { MapCanvas, type MapMarker } from "./components/MapCanvas";
import { Droomkaart } from "./components/Droomkaart";
import { AgentPanel, type ChatMessage } from "./components/AgentPanel";
import { DreamLanding } from "./components/DreamLanding";
import { getChapter, getSessionId, newSession, putChapter, sendChat } from "./droomzaak/api";
import type { ChapterState, HeatmapSpec, TransientDataset } from "./droomzaak/types";

// ── localStorage persistence helpers ─────────────────────────────
const LS = {
  get: (key: string, fallback: number) => {
    try { const v = localStorage.getItem(`droomzaak.${key}`); return v ? Number(v) : fallback; } catch { return fallback; }
  },
  getBool: (key: string, fallback: boolean) => {
    try { const v = localStorage.getItem(`droomzaak.${key}`); return v !== null ? v === "1" : fallback; } catch { return fallback; }
  },
  set: (key: string, value: number | boolean) => {
    try { localStorage.setItem(`droomzaak.${key}`, String(value === true ? "1" : value === false ? "0" : value)); } catch { /* ignore */ }
  },
};

const PANEL_MIN = 280;
const PANEL_MAX = 640;
const PANEL_DEFAULT = 360;
const SPLIT_MIN = 48; // px — minimum section height (header-only)

// ── Mobile breakpoint ─────────────────────────────────────────────
// Phones get a stacked layout (rail+map on top, chat below, Droomkaart as a
// sheet); desktop keeps the resizable three-column grid. Drives a separate
// render branch rather than CSS-only because the panel structure differs.
function useIsMobile(query = "(max-width: 768px)") {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setIsMobile(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);
  return isMobile;
}

// ── Chevron icon ──────────────────────────────────────────────────
function Chevron({ open, vertical = false }: { open: boolean; vertical?: boolean }) {
  const angle = vertical
    ? open ? 0 : 180   // points up when open (collapsed = points down)
    : open ? 0 : 180;  // left when open (collapsed = right)
  return (
    <svg
      width="14" height="14"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ transform: `rotate(${angle}deg)`, transition: "transform 0.2s", display: "block", flexShrink: 0 }}
    >
      {vertical
        ? <polyline points="2,9 7,4 12,9" />
        : <polyline points="9,2 4,7 9,12" />}
    </svg>
  );
}

export default function App() {
  // ── App state ─────────────────────────────────────────────────
  const [sessionId, setSessionId] = useState(getSessionId);
  const [chapterState, setChapterState] = useState<ChapterState | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [datasets, setDatasets] = useState<Record<string, TransientDataset>>({});
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [filters, setFilters] = useState<Record<string, unknown[] | null>>({});
  const [heatmaps, setHeatmaps] = useState<Record<string, HeatmapSpec>>({});
  const [hiddenLayers, setHiddenLayers] = useState<string[]>([]);
  const [layerStyles, setLayerStyles] = useState<Record<string, string>>({});
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [landed, setLanded] = useState(false);
  const chatInputRef = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();
  const [mobileKaartOpen, setMobileKaartOpen] = useState(false);

  // ── Layout state (persisted) ──────────────────────────────────
  const [panelWidth, setPanelWidth] = useState(() => LS.get("panelWidth", PANEL_DEFAULT));
  const [splitPx, setSplitPx] = useState(() => LS.get("splitPx", 0)); // 0 = natural 48/52 split
  const [panelCollapsed, setPanelCollapsed] = useState(() => LS.getBool("panelCollapsed", false));
  const [droomCollapsed, setDroomCollapsed] = useState(() => LS.getBool("droomCollapsed", false));
  const [chatCollapsed, setChatCollapsed] = useState(() => LS.getBool("chatCollapsed", false));

  // ── Drag state refs (no re-render during drag) ─────────────────
  const draggingPanel = useRef(false);
  const draggingRow = useRef(false);
  const dragStartX = useRef(0);
  const dragStartW = useRef(0);
  const dragStartY = useRef(0);
  const dragStartSplit = useRef(0);
  const rightColRef = useRef<HTMLDivElement>(null);

  // ── Persist on change ─────────────────────────────────────────
  useEffect(() => { LS.set("panelWidth", panelWidth); }, [panelWidth]);
  useEffect(() => { LS.set("splitPx", splitPx); }, [splitPx]);
  useEffect(() => { LS.set("panelCollapsed", panelCollapsed); }, [panelCollapsed]);
  useEffect(() => { LS.set("droomCollapsed", droomCollapsed); }, [droomCollapsed]);
  useEffect(() => { LS.set("chatCollapsed", chatCollapsed); }, [chatCollapsed]);

  // ── Session / chapter load ────────────────────────────────────
  useEffect(() => {
    getChapter(sessionId)
      .then((d) => {
        setChapterState(d.chapter_state);
        if (d.chapter_state?.dream_profile) setLanded(true);
      })
      .catch(() => void 0);
  }, [sessionId]);

  const current: ChapterId = chapterState?.current_chapter ?? "1_droom";

  function handleNewChat() {
    if (busy) return;
    const id = newSession();
    setSessionId(id);
    setChapterState(null);
    setMessages([]);
    setDatasets({});
    setMarkers([]);
    setFilters({});
    setHeatmaps({});
    setHiddenLayers([]);
    setLayerStyles({});
    setSelectedDatasetId(null);
    setLanded(false);
  }

  async function handleSend(text: string) {
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      // Tell the agent what the founder is currently looking at: the visible
      // (non-hidden) layers and the dataset they last clicked. The backend
      // renders these into <map_state> and widens its action candidate_map.
      const context = {
        active_layers: Object.keys(datasets).filter((id) => !hiddenLayers.includes(id)),
        selected_dataset_id: selectedDatasetId,
      };
      const res = await sendChat(text, sessionId, context);
      setMessages((m) => [...m, { role: "agent", text: res.reply }]);
      if (res.chapter_state) {
        setChapterState(res.chapter_state);
        // A completed chat turn with a confirmed location commits it — lock
        // against further marker clicks overwriting the agent's (or user's) choice.
        if (res.chapter_state.chosen_location != null) provisionalRef.current = false;
      }
      if (res.datasets) setDatasets((d) => ({ ...d, ...res.datasets }));
      const newMarkers: MapMarker[] = [];
      const newFilters: Record<string, unknown[] | null> = {};
      const newHeatmaps: Record<string, HeatmapSpec> = {};
      const hide = new Set<string>();
      const show = new Set<string>();
      const newStyles: Record<string, string> = {};
      for (const a of res.actions || []) {
        if (a.type === "place_marker" && Array.isArray(a.markers)) {
          for (const mk of a.markers) newMarkers.push({ coordinates: mk.coordinates, label: mk.label });
        }
        if (a.type === "set_layer_filter" && typeof a.dataset_id === "string") {
          // null clears the filter; any array applies it.
          newFilters[a.dataset_id] = Array.isArray(a.filter) ? (a.filter as unknown[]) : null;
        }
        if (a.type === "set_layer_heatmap" && typeof a.dataset_id === "string" && typeof a.field === "string") {
          newHeatmaps[a.dataset_id] = { field: a.field, palette: a.palette, label: a.label };
        }
        if (a.type === "hide_layer" && typeof a.dataset_id === "string") hide.add(a.dataset_id);
        if (a.type === "show_layer" && typeof a.dataset_id === "string") show.add(a.dataset_id);
        if (a.type === "set_layer_style" && typeof a.dataset_id === "string") {
          const color = (a.style as { color?: unknown } | undefined)?.color;
          if (typeof color === "string") newStyles[a.dataset_id] = color;
        }
      }
      if (newMarkers.length) setMarkers(newMarkers);
      if (Object.keys(newFilters).length) {
        setFilters((prev) => ({ ...prev, ...newFilters }));
      }
      if (Object.keys(newHeatmaps).length) {
        setHeatmaps((prev) => ({ ...prev, ...newHeatmaps }));
      }
      if (hide.size || show.size) {
        // show_layer wins over hide_layer if the agent emits both for one id.
        setHiddenLayers((prev) => [...new Set([...prev, ...hide])].filter((id) => !show.has(id)));
      }
      if (Object.keys(newStyles).length) {
        setLayerStyles((prev) => ({ ...prev, ...newStyles }));
      }
    } catch {
      setMessages((m) => [...m, { role: "agent", text: "Er ging iets mis. Probeer het opnieuw." }]);
    } finally {
      setBusy(false);
    }
  }

  // ── Marker click → chosen location ───────────────────────────
  // provisional = true means the user has clicked a marker but the conversation
  // has not yet processed a turn that confirms chosen_location.  While provisional,
  // subsequent clicks overwrite the stored location (last click wins).
  // Once a chat turn completes with a non-null chosen_location the flag is cleared
  // (committed) and further clicks become no-ops.
  //
  // putChapter routes through the same validate_set_chapter_state path the agent
  // uses — safe, audited, no parallel mutation. We use the marker label as a
  // display value (never fabricate an address); coordinates are always exact.
  const provisionalRef = useRef(false);

  const handleMarkerClick = useCallback(
    (mk: MapMarker) => {
      // Committed = a chat turn has already confirmed chosen_location. Lock out clicks.
      if (chapterState?.chosen_location != null && !provisionalRef.current) return;
      const patch = {
        chosen_location: {
          coordinates: mk.coordinates,
          // Use the label as the address display value when no real address is known.
          // The agent will overwrite this with a proper address when it calls set_chapter_state.
          address: mk.label ?? null,
          wijk_nl: null,
        },
      };
      provisionalRef.current = true;
      putChapter(sessionId, patch)
        .then((d) => setChapterState(d.chapter_state))
        .catch(() => void 0); // non-blocking: UI still shows the marker
    },
    [chapterState, sessionId],
  );

  // ── Drag: vertical handle (panel width) ───────────────────────
  const onPanelHandlePointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    draggingPanel.current = true;
    dragStartX.current = e.clientX;
    dragStartW.current = panelWidth;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
  }, [panelWidth]);

  const onPanelHandlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!draggingPanel.current) return;
    const delta = dragStartX.current - e.clientX; // handle is on the LEFT of the panel
    const next = Math.min(PANEL_MAX, Math.max(PANEL_MIN, dragStartW.current + delta));
    setPanelWidth(next);
  }, []);

  const onPanelHandlePointerUp = useCallback(() => {
    if (!draggingPanel.current) return;
    draggingPanel.current = false;
    document.body.style.userSelect = "";
    document.body.style.cursor = "";
  }, []);

  // ── Drag: horizontal handle (row split) ───────────────────────
  const onRowHandlePointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    draggingRow.current = true;
    dragStartY.current = e.clientY;
    dragStartSplit.current = splitPx;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    document.body.style.userSelect = "none";
    document.body.style.cursor = "row-resize";
  }, [splitPx]);

  const onRowHandlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!draggingRow.current) return;
    const col = rightColRef.current;
    if (!col) return;
    const totalH = col.clientHeight;
    const delta = e.clientY - dragStartY.current;
    const base = dragStartSplit.current || totalH * 0.48;
    const next = Math.min(totalH - SPLIT_MIN, Math.max(SPLIT_MIN, base + delta));
    setSplitPx(next);
  }, [splitPx]);

  const onRowHandlePointerUp = useCallback(() => {
    if (!draggingRow.current) return;
    draggingRow.current = false;
    document.body.style.userSelect = "";
    document.body.style.cursor = "";
  }, []);

  // ── Collapsed panel re-open tab (always visible on the right edge) ──
  const collapsedTab = (
    <button
      type="button"
      className="panel-collapsed-tab"
      onClick={() => setPanelCollapsed(false)}
      title="Open zijpaneel"
    >
      <Chevron open={false} vertical={false} />
    </button>
  );

  // ── Grid column template ──────────────────────────────────────
  const gridCols = panelCollapsed
    ? `88px 1fr 0px`
    : `88px 1fr ${panelWidth}px`;

  // ── Droomkaart height (flex basis override when split is set) ─
  const droomH = splitPx > 0 ? `${splitPx}px` : undefined;

  // Shared between the desktop and mobile branches so the map and the
  // fresh-session landing overlay stay in lock-step across layouts.
  const mapCanvas = (
    <MapCanvas
      datasets={datasets}
      markers={markers}
      filters={filters}
      heatmaps={heatmaps}
      hiddenLayers={hiddenLayers}
      layerStyles={layerStyles}
      onSelectDataset={setSelectedDatasetId}
      onMarkerClick={handleMarkerClick}
    />
  );

  const landingOverlay = !landed && (
    <DreamLanding
      targetRef={chatInputRef}
      onDream={(text) => void handleSend(text)}
      onExited={() => setLanded(true)}
    />
  );

  // ── Mobile layout: rail + map on top, chat full-width below, Droomkaart
  //    reachable as a full-screen sheet. Resize/collapse chrome is dropped. ──
  if (isMobile) {
    return (
      <div className="app app--mobile">
        <ChapterRail current={current} />
        {mapCanvas}
        <div className="mobile-chat">
          <div className="mobile-chat-bar">
            <button
              type="button"
              className="mobile-kaart-btn"
              onClick={() => setMobileKaartOpen(true)}
              title="Bekijk je Droomkaart en pakket"
            >
              Droomkaart
            </button>
            <button
              type="button"
              className="new-chat-btn"
              onClick={handleNewChat}
              disabled={busy}
              title="Begin een nieuwe droom"
            >
              + Nieuwe droom
            </button>
          </div>
          <AgentPanel current={current} messages={messages} busy={busy} onSend={handleSend} chatInputRef={chatInputRef} />
        </div>
        {mobileKaartOpen && (
          <div className="mobile-sheet">
            <button
              type="button"
              className="mobile-sheet-close"
              onClick={() => setMobileKaartOpen(false)}
              title="Sluiten"
            >
              ×
            </button>
            <Droomkaart state={chapterState} sessionId={sessionId} />
          </div>
        )}
        {landingOverlay}
      </div>
    );
  }

  return (
    <div
      className="app"
      style={{ gridTemplateColumns: gridCols }}
    >
      <ChapterRail current={current} />

      {mapCanvas}

      {panelCollapsed ? (
        collapsedTab
      ) : (
        <div
          ref={rightColRef}
          className="agent-panel"
        >
          {/* Vertical drag handle — absolutely positioned on the left edge of the panel */}
          <div
            className="resize-handle resize-handle--col"
            onPointerDown={onPanelHandlePointerDown}
            onPointerMove={onPanelHandlePointerMove}
            onPointerUp={onPanelHandlePointerUp}
            onPointerCancel={onPanelHandlePointerUp}
          />
          {/* Panel header (title + collapse toggle + Nieuwe droom) */}
          <div className="agent-panel-header">
            <span className="agent-panel-title">Droomzaak</span>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <button
                type="button"
                className="new-chat-btn"
                onClick={handleNewChat}
                disabled={busy}
                title="Begin een nieuwe droom — wist het gesprek en de kaart"
              >
                + Nieuwe droom
              </button>
              <button
                type="button"
                className="icon-toggle-btn"
                onClick={() => setPanelCollapsed(true)}
                title="Zijpaneel inklappen"
              >
                <Chevron open={true} vertical={false} />
              </button>
            </div>
          </div>

          {/* Droomkaart section */}
          <div
            className={`droomkaart-section${droomCollapsed ? " droomkaart-section--collapsed" : ""}`}
            style={!droomCollapsed && droomH ? { flexBasis: droomH, flexGrow: 0, flexShrink: 0 } : undefined}
          >
            <div className="section-collapse-header droomkaart-collapse-header">
              <button
                type="button"
                className="section-collapse-btn"
                onClick={() => setDroomCollapsed((v) => !v)}
                title={droomCollapsed ? "Droomkaart uitklappen" : "Droomkaart inklappen"}
              >
                <Chevron open={!droomCollapsed} vertical={true} />
                <span>Jouw Droomkaart</span>
              </button>
            </div>
            {!droomCollapsed && (
              <Droomkaart state={chapterState} sessionId={sessionId} />
            )}
          </div>

          {/* Horizontal drag handle (row resize) — only when both sections open */}
          {!droomCollapsed && !chatCollapsed && (
            <div
              className="resize-handle resize-handle--row"
              onPointerDown={onRowHandlePointerDown}
              onPointerMove={onRowHandlePointerMove}
              onPointerUp={onRowHandlePointerUp}
              onPointerCancel={onRowHandlePointerUp}
            />
          )}

          {/* Chat / AgentPanel section */}
          <div
            className={`chat-section${chatCollapsed ? " chat-section--collapsed" : ""}`}
            style={!chatCollapsed && droomH && !droomCollapsed ? { flex: "1 1 0", minHeight: 0 } : undefined}
          >
            <div className="section-collapse-header chat-collapse-header">
              <button
                type="button"
                className="section-collapse-btn"
                onClick={() => setChatCollapsed((v) => !v)}
                title={chatCollapsed ? "Chat uitklappen" : "Chat inklappen"}
              >
                <Chevron open={!chatCollapsed} vertical={true} />
                <span>Gesprek</span>
              </button>
            </div>
            {!chatCollapsed && (
              <AgentPanel current={current} messages={messages} busy={busy} onSend={handleSend} chatInputRef={chatInputRef} />
            )}
          </div>
        </div>
      )}

      {/* Overlay stays mounted through its exit animation; onExited flips `landed`. */}
      {landingOverlay}
    </div>
  );
}
