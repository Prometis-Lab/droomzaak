// Score-heatmap helpers for the Droomkaart choropleth — the frontend half of
// the two-tier boundary. The agent emits `set_layer_heatmap` (field + palette)
// and `score_locations` returns per-sector scores through the DataGateway;
// geometry lives in the render tier (the cached `gent-sectors.geojson` asset).
// These helpers do the score→sector join and build the MapLibre colour ramp.

import type { FeatureCollection, GeoFeature, HeatmapSpec, SectorScore } from "./types";

// Palette names mirror agent_validation.py `_PALETTES`; colour ramps match the
// map-pilot-v2 reference so the visual language is consistent.
export const HEATMAP_PALETTES: Record<string, string[]> = {
  "blue-yellow-red": ["#2c7bb6", "#00a6ca", "#00ccbc", "#90eb9d", "#ffff8c", "#f9d057", "#f29e2e", "#e76818", "#d7191c"],
  "teal-purple": ["#0f766e", "#14b8a6", "#a7f3d0", "#fef3c7", "#f59e0b", "#db2777", "#7c3aed"],
  "orange-red": ["#fff7bc", "#fee391", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#8c2d04"],
};
export const DEFAULT_PALETTE = "blue-yellow-red";

// Default heatmap for a score-locations layer when the agent shows it without an
// explicit set_layer_heatmap action — the score map should still colour itself.
export const DEFAULT_SCORE_HEATMAP: HeatmapSpec = { field: "score", palette: DEFAULT_PALETTE };

/**
 * MapLibre `interpolate` expression mapping a numeric feature field to a colour
 * ramp. Stops are spaced linearly across the observed value range; a degenerate
 * range (all-equal values) is padded so stop inputs stay strictly ascending
 * (MapLibre rejects duplicate stop inputs).
 */
export function heatmapColorExpression(field: string, values: number[], palette?: string): unknown[] {
  const colors = HEATMAP_PALETTES[palette ?? DEFAULT_PALETTE] ?? HEATMAP_PALETTES[DEFAULT_PALETTE];
  const finite = values.filter((v) => Number.isFinite(v));
  let min = finite.length ? Math.min(...finite) : 0;
  let max = finite.length ? Math.max(...finite) : 1;
  if (min === max) {
    const pad = Math.max(1e-6, Math.abs(min) * 0.05);
    min -= pad;
    max += pad;
  }
  const range = max - min || 1;
  const expr: unknown[] = ["interpolate", ["linear"], ["to-number", ["get", field], min]];
  colors.forEach((color, i) => {
    expr.push(min + (range * i) / Math.max(1, colors.length - 1), color);
  });
  return expr;
}

/** Numeric values of `field` across a collection (for the colour-ramp range). */
export function fieldValues(fc: FeatureCollection, field: string): number[] {
  return fc.features
    .map((f) => Number((f.properties as Record<string, unknown>)?.[field]))
    .filter((v) => Number.isFinite(v));
}

/**
 * Join per-sector scores onto the cached sector polygons, producing a
 * FeatureCollection whose features carry a numeric `score` property. Sectors
 * with no matching score are dropped (nothing to colour).
 */
export function joinScoresToSectors(sectors: FeatureCollection, scores: SectorScore[]): FeatureCollection {
  const byNis = new Map(scores.map((s) => [s.nis9_code, s.score]));
  const features: GeoFeature[] = [];
  for (const f of sectors.features) {
    const nis = (f.properties as Record<string, unknown>)?.nis9_code as string | undefined;
    const score = nis != null ? byNis.get(nis) : undefined;
    if (score == null) continue;
    features.push({ ...f, properties: { ...f.properties, score } });
  }
  return { type: "FeatureCollection", features };
}
