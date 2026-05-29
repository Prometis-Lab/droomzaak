---
name: wire-agent-action-to-canvas
description: Use when connecting an agent map action to the React + MapLibre frontend in Droomzaak — adding a new action type the agent commits (layer, filter, style, heatmap, highlight, draw, chapter overlay), rendering a new layer, or serializing new map state back into the agent context. Encodes the full path (type → server validation → executeAgentAction → MapLibre → context) plus the canvas gotchas that otherwise cost iterations.
---

# Wiring an agent action to the canvas

The agent returns `actions`; the frontend executes them against MapLibre, then reports the resulting state back in the next turn's `context`. Fixed path from action type to pixels. **Rigid** on the path + gotchas; flexible on visual design.

> Extended helper-by-helper notes are in `reference/maplibre-gotchas.md`.

## The full path
1. **Type** — add the action/state shape to `types.ts` (mirror an existing union member).
2. **Server validation** — must validate in `agent_validation.py` (payload shape, `dataset_id` in the candidate map, filter/style/heatmap constraints). The frontend should never receive an unvalidated action.
3. **Execute** — branch in `executeAgentAction` (`App.tsx`): resolve `dataset_id` → ensure the layer is on the map (`showDatasetLayer`) → mutate.
4. **Mutate MapLibre** — via the existing helpers (`addDatasetToMap`, `applyDatasetFilter` + `refreshDatasetFeatureSource`, `applyDatasetStyle`, `applyLayerHeatmap`, `applyDatasetHighlight`, `updateAgentAnnotations`).
5. **Serialize back** — push new state into the refs (`activeLayersRef`, `agentDrawingsRef`, `agentHighlightsRef`) so the next `context` (`active_layer_state`, `drawings`, `highlights`, chapter state) tells the agent what's on screen.

## Gotchas (each is a real, previously-hit bug)
- **Map readiness:** `waitForMapReady` → `map.once("idle", …)`, NEVER `map.once("load", …)` after mount. 8s timeout fallback.
- **Z-order:** re-assert after adding — dataset layers front, then hover, then highlights. Zoom breakpoints 10/13/16 hide small points if changed blindly.
- **Centroids:** skip for the default base layer, already-Point features, and median geometry > 0.002°.
- **Ref vs state:** `activeLayersRef` is the sync copy async executors read (avoids stale closures); keep both in sync. Same for annotation/drawing/highlight refs.
- **Highlights are transient** (each replaces the prior overlay).
- **Action groups:** `planAgentActionGroups` runs same-dataset actions sequentially, independent ones in parallel — slot new types into the right group.
- **Filter `in`** needs `["in", ["get", field], ["literal", array]]`.
- **Abort:** a new chat aborts in-flight execution via the signal — stop mutating on abort.
- **Persistence:** layout sizes persist to `localStorage` `ghent-map.*`; the agent session does NOT (refresh = new session).

## Droomzaak surfaces
Chapter overlays (Ch3 scoring heatmaps, Ch4 checklist pins) are normal layer/highlight actions driven by chapter state — reuse the path, don't invent a parallel renderer. Rail gating is server-owned (`chapter-state-machine`).

## Verify
No frontend test suite — run `npm run build` (`tsc -b && vite build`); click the new action through the agent panel once.
