# MapLibre + agent-action helpers (reference)

Frontend: `frontend/src/App.tsx` (the main canvas component), `mapUtils.ts`, `api.ts`, `types.ts`.

## Layer naming convention

Per dataset id: `{id}-fill`, `{id}-line`, `{id}-circle`, `{id}-centroid-circle`, `{id}-label`. Polygon datasets get derived centroid markers in a `{id}-centroids` source. Reserved overlay sources: `__hovered-feature`, `__agent-highlight`, `__agent-annotations`.

## Helper map (what to call for each action)

| Action | Helper(s) |
|---|---|
| `show_layer` / toggle | `addDatasetToMap` → `getLayerFeatures` → add source + fill/line/circle/centroid/label → `applyDatasetStyle` → fit bounds → bring to front |
| `hide_layer` | `removeDatasetLayers` (removes the 5 layers + sources) |
| `set_layer_filter` | `applyDatasetFilter` (`map.setFilter` on each geom layer) + `refreshDatasetFeatureSource` (re-fetch filtered features) |
| `clear_layer_filter` | remove filter + re-fetch all features |
| `set_layer_style` | `applyDatasetStyle` (color/opacity/variant paint props) |
| `set_layer_heatmap` | `applyLayerHeatmap` → `buildLayerHeatmapStyle` (numeric stops) → `applyDatasetStyle` |
| `highlight_features` | `applyDatasetHighlight` (soft glow into `__agent-highlight`; replaces prior) |
| `draw_radius` / `place_marker` / `draw_route` / `add_annotation` | build GeoJSON feature (circle = 73-vertex polygon, route = LineString) → push to `agentAnnotationFeaturesRef` + `agentDrawingsRef` → `updateAgentAnnotations` (`source.setData`) → `addAgentAnnotations` (fit) |

## Filter expression compilation (`conditionExpression` / `filterExpression`)

- `=` → `["==", ["get", f], v]`
- `!=` → `["!=", …]`; `>` `>=` `<` `<=` numeric comparisons
- `contains` → `["in", value, ["downcase", ["to-string", ["get", f]]]]`
- `in` → `["in", ["get", f], ["literal", arrayValue]]`  ← the `literal` wrapper is mandatory
- Combined with geometry filter: `["all", geometryFilter, userFilter]`

Client-side equivalent for agent state lives in `featureMatchesFilter` (avoids a double fetch).

## Context payload the agent receives next turn

```
{
  active_layers: [dataset_id, …],
  active_layer_state: [AgentLayerSnapshot, …],   // filters, styles (no stops), heatmap config
  drawings: [AgentDrawing, …],                    // semantic circles/markers/routes/annotations
  highlights: [AgentHighlight, …],                // dataset_id → filter
  selected_dataset_id, map_marker, selected_feature
}
```

## api.ts retry

`apiGetWithRetry` retries feature fetches with delays `[0, 500, 1500, 3000]`, never retries on `AbortError`. `withTimeout` wraps each attempt (30s default; agent chat 240s). All calls go through relative `/api` (Vite proxy → `127.0.0.1:8000`).
