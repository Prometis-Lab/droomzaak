import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import type { FeatureCollection, HeatmapSpec, TransientDataset } from "../droomzaak/types";
import {
  DEFAULT_SCORE_HEATMAP,
  fieldValues,
  heatmapColorExpression,
  joinScoresToSectors,
} from "../droomzaak/heatmap";
import { FeatureInfoPopup } from "./FeatureInfoPopup";
import { MarkerStreetView } from "./MarkerStreetView";

// Cached render-tier asset: all 254 Ghent statistical-sector polygons, keyed by
// nis9_code. Built by scripts/build_sector_geojson.py. Score data (REASON tier)
// is joined onto these at render time — geometry never crosses the DataGateway.
const SECTORS_URL = "/gent-sectors.geojson";

// Polygon fill opacities. The score heatmap stays fairly transparent so the
// basemap and the point layers riding on top of it stay legible.
const HEATMAP_FILL_OPACITY = 0.4;
const FLAT_FILL_OPACITY = 0.18;
// Resting radius of point/circle dataset layers (venue dots, score points).
const POINT_RADIUS = 4;

// ResizeObserver hook — watches the container and calls map.resize() on every
// size change so MapLibre's canvas stays in sync when panels are dragged.
function useMapResize(
  containerRef: React.RefObject<HTMLElement | null>,
  mapRef: React.RefObject<maplibregl.Map | null>
) {
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let rafId: number;
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        mapRef.current?.resize();
      });
    });
    ro.observe(el);
    return () => {
      cancelAnimationFrame(rafId);
      ro.disconnect();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

const GHENT_CENTER: [number, number] = [3.7257, 51.0543];

const OSM_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

export interface MapMarker {
  coordinates: [number, number];
  label?: string;
}

// Overlay source feeding the hover halo. Its three layers (fill/line/circle)
// draw a highlight over whatever feature is under the cursor — points grow, a
// polygon brightens with a thicker outline.
const HOVER_SOURCE = "dz-hover";
const HOVER_LAYERS = [`${HOVER_SOURCE}-fill`, `${HOVER_SOURCE}-line`, `${HOVER_SOURCE}-circle`];

// MapLibre filter selecting only features of the given geometry family.
const polyFilter = ["match", ["geometry-type"], ["Polygon", "MultiPolygon"], true, false];
const pointFilter = ["match", ["geometry-type"], ["Point", "MultiPoint"], true, false];

// The dataset layers a user can interact with: `ds-<id>-layer` (the fill or
// circle), but not the `-outline` companion or our own hover overlay.
function interactiveLayerIds(map: maplibregl.Map): string[] {
  return map
    .getStyle()
    .layers.map((l) => l.id)
    .filter((id) => /^ds-.+-layer$/.test(id) && map.getLayer(id));
}

// Feed the hovered feature's geometry into the halo source (empty = no hover)
// and lift the halo above any later-added dataset layers so it stays visible.
function setHoverFeature(map: maplibregl.Map, feature?: maplibregl.MapGeoJSONFeature) {
  const src = map.getSource(HOVER_SOURCE) as maplibregl.GeoJSONSource | undefined;
  if (!src) return;
  src.setData({
    type: "FeatureCollection",
    features: feature?.geometry
      ? [{ type: "Feature", geometry: feature.geometry, properties: {} }]
      : [],
  } as never);
  if (feature) HOVER_LAYERS.forEach((id) => map.getLayer(id) && map.moveLayer(id));
}

// MapLibre filter expression — null means "clear the filter".
export type FilterExpr = unknown[] | null;

type Props = {
  datasets: Record<string, TransientDataset>;
  markers: MapMarker[];
  filters?: Record<string, FilterExpr>;
  heatmaps?: Record<string, HeatmapSpec>;
  // Dataset ids the agent has hidden (hide_layer); their layers get visibility:none.
  hiddenLayers?: string[];
  // Per-dataset colour overrides from set_layer_style ({ datasetId: "#rrggbb" }).
  layerStyles?: Record<string, string>;
  // Reports which dataset a map click landed on (null when the click hit nothing)
  // so the agent can be told the founder's selected_dataset_id next turn.
  onSelectDataset?: (datasetId: string | null) => void;
  // Called when the user clicks an agent-placed marker — provides the marker's
  // coordinates and label so the parent can persist it as chosen_location.
  onMarkerClick?: (marker: MapMarker) => void;
};

/** Determine whether a GeoJSON FeatureCollection contains polygon geometry. */
function hasPolygonGeometry(geojson: { features: Array<{ geometry: { type: string } }> }): boolean {
  return geojson.features.some(
    (f) => f.geometry.type === "Polygon" || f.geometry.type === "MultiPolygon"
  );
}

/** Collect all coordinate pairs from any geometry type for bounds extension. */
function extendBoundsFromGeometry(
  bounds: maplibregl.LngLatBounds,
  geometry: { type: string; coordinates: unknown }
): boolean {
  type LngLat = [number, number];

  function addPair(pair: unknown) {
    if (Array.isArray(pair) && pair.length >= 2 && typeof pair[0] === "number" && typeof pair[1] === "number") {
      bounds.extend(pair as LngLat);
    }
  }

  function walkRing(ring: unknown[]) {
    for (const pt of ring) addPair(pt);
  }

  switch (geometry.type) {
    case "Point":
      addPair(geometry.coordinates);
      return true;
    case "MultiPoint":
      for (const pt of geometry.coordinates as unknown[]) addPair(pt);
      return true;
    case "LineString":
      walkRing(geometry.coordinates as unknown[]);
      return true;
    case "MultiLineString":
      for (const ring of geometry.coordinates as unknown[][]) walkRing(ring);
      return true;
    case "Polygon":
      // outer ring only (sufficient for bounds)
      walkRing((geometry.coordinates as unknown[][])[0] ?? []);
      return true;
    case "MultiPolygon":
      for (const poly of geometry.coordinates as unknown[][][]) walkRing(poly[0] ?? []);
      return true;
    default:
      return false;
  }
}

export function MapCanvas({ datasets, markers, filters = {}, heatmaps = {}, hiddenLayers = [], layerStyles = {}, onSelectDataset, onMarkerClick }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);
  const markerObjsRef = useRef<maplibregl.Marker[]>([]);
  // Latest onSelectDataset, read by the once-attached click handler (avoids a
  // stale closure without re-binding the map listener every render).
  const onSelectRef = useRef(onSelectDataset);
  onSelectRef.current = onSelectDataset;
  // Latest onMarkerClick callback — kept in a ref so the marker effect's closure
  // always reads the current value without needing to re-run on every render.
  const onMarkerClickRef = useRef(onMarkerClick);
  onMarkerClickRef.current = onMarkerClick;
  // Cached sector polygons (render tier), loaded once; version bump retriggers
  // the dataset effect when the async fetch resolves after mount.
  const sectorsRef = useRef<FeatureCollection | null>(null);
  const [sectorsVersion, setSectorsVersion] = useState(0);
  // Dataset ids already framed — so the city-wide score choropleth doesn't keep
  // hijacking the camera when a later, focused layer (an isochrone) is added.
  const fittedRef = useRef<Set<string>>(new Set());

  // Street View popup: set when user clicks an agent-placed marker.
  const [streetView, setStreetView] = useState<{ lat: number; lng: number; heading?: number } | null>(null);
  // Stable ref so the marker click closure always calls the latest setter
  // without requiring the marker effect to re-run (avoids stale closures).
  const setStreetViewRef = useRef(setStreetView);
  setStreetViewRef.current = setStreetView;

  // Click-to-inspect: the feature popup's content + anchor. Rendered via portal
  // into a container that doubles as the MapLibre Popup's DOM content.
  const [selected, setSelected] = useState<{ properties: Record<string, unknown>; lngLat: [number, number] } | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const popupContainerRef = useRef<HTMLDivElement | null>(null);
  if (!popupContainerRef.current && typeof document !== "undefined") {
    popupContainerRef.current = document.createElement("div");
  }

  // Watch the outer section for size changes → keep MapLibre canvas correct.
  useMapResize(sectionRef, mapRef);

  // Load the cached sector-polygon asset once (render tier — never the gateway).
  useEffect(() => {
    let cancelled = false;
    fetch(SECTORS_URL)
      .then((r) => (r.ok ? r.json() : null))
      .then((fc: FeatureCollection | null) => {
        if (!cancelled && fc?.features?.length) {
          sectorsRef.current = fc;
          setSectorsVersion((v) => v + 1);
        }
      })
      .catch(() => void 0);
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: OSM_STYLE,
      center: GHENT_CENTER,
      zoom: 13,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      loadedRef.current = true;
      // Hover halo: an overlay that highlights whatever feature is under the
      // cursor. Created once; the dataset effect adds layers on top, so the
      // halo is re-raised in setHoverFeature whenever it gains a feature.
      map.addSource(HOVER_SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: `${HOVER_SOURCE}-fill`, type: "fill", source: HOVER_SOURCE, filter: polyFilter as never, paint: { "fill-color": "#d8a23a", "fill-opacity": 0.3 } });
      map.addLayer({ id: `${HOVER_SOURCE}-line`, type: "line", source: HOVER_SOURCE, paint: { "line-color": "#9c4a2a", "line-width": 3, "line-opacity": 0.95 } });
      map.addLayer({ id: `${HOVER_SOURCE}-circle`, type: "circle", source: HOVER_SOURCE, filter: pointFilter as never, paint: { "circle-radius": 8, "circle-color": "#d8a23a", "circle-opacity": 0.9, "circle-stroke-color": "#fff", "circle-stroke-width": 2 } });
    });

    // Hover: highlight the top interactive feature + show a pointer cursor.
    const onMove = (e: maplibregl.MapMouseEvent) => {
      const layers = interactiveLayerIds(map);
      if (!layers.length) {
        map.getCanvas().style.cursor = "";
        setHoverFeature(map);
        return;
      }
      const feature = map.queryRenderedFeatures(e.point, { layers })[0];
      map.getCanvas().style.cursor = feature ? "pointer" : "";
      setHoverFeature(map, feature);
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = "";
      setHoverFeature(map);
    };
    // Click: open the info popup for the top interactive feature (or dismiss),
    // and report the clicked layer's dataset id up so the agent learns the
    // founder's selected_dataset_id next turn.
    const onClick = (e: maplibregl.MapMouseEvent) => {
      const layers = interactiveLayerIds(map);
      const feature = layers.length ? map.queryRenderedFeatures(e.point, { layers })[0] : undefined;
      if (!feature) {
        setSelected(null);
        onSelectRef.current?.(null);
        return;
      }
      const src = typeof feature.layer?.source === "string" ? feature.layer.source : "";
      const datasetId = src.startsWith("ds-") ? src.slice(3) : null;
      setSelected({
        properties: feature.properties ? { ...feature.properties } : {},
        lngLat: [e.lngLat.lng, e.lngLat.lat],
      });
      onSelectRef.current?.(datasetId);
    };
    map.on("mousemove", onMove);
    map.on("mouseleave", onLeave);
    map.on("click", onClick);

    mapRef.current = map;
    return () => {
      map.off("mousemove", onMove);
      map.off("mouseleave", onLeave);
      map.off("click", onClick);
      popupRef.current?.remove();
      popupRef.current = null;
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
  }, []);

  // Drive the MapLibre Popup from `selected`: position it at the click point
  // and bind its DOM content to the portal container (once).
  useEffect(() => {
    const map = mapRef.current;
    const container = popupContainerRef.current;
    if (!map || !container) return;
    if (!selected) {
      popupRef.current?.remove();
      return;
    }
    if (!popupRef.current) {
      popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: "300px", offset: 14, className: "dz-popup", anchor: "bottom" });
      popupRef.current.setDOMContent(container);
    }
    popupRef.current.setLngLat(selected.lngLat).addTo(map);
  }, [selected]);

  // Render transient datasets as MapLibre layers. A dataset draws either its own
  // geojson, or — for a score-locations layer carrying per-sector `scores` — the
  // cached sector polygons joined to those scores. Geometry is painted flat
  // (terracotta) unless a heatmap is active, in which case the fill/circle colour
  // is a data-driven ramp over the heatmap field. Only newly-added datasets frame
  // the camera, so the city-wide score map doesn't override a later focused layer.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const bounds = new maplibregl.LngLatBounds();
      let fitAny = false;
      const pointLayerIds: string[] = []; // collected here, re-raised above fills below
      for (const ds of Object.values(datasets)) {
        // Resolve geometry to draw + whether a heatmap colours it.
        let fc: FeatureCollection | undefined = ds.geojson;
        let heatmap: HeatmapSpec | undefined = heatmaps[ds.dataset_id];
        if (!fc && ds.scores?.length && sectorsRef.current) {
          fc = joinScoresToSectors(sectorsRef.current, ds.scores);
          heatmap = heatmap ?? DEFAULT_SCORE_HEATMAP; // a score map always colours itself
        }
        if (!fc || !fc.features.length) continue;

        const srcId = `ds-${ds.dataset_id}`;
        const layerId = `${srcId}-layer`;
        const isPolygon = hasPolygonGeometry(fc);
        const colorExpr = heatmap
          ? heatmapColorExpression(heatmap.field, fieldValues(fc, heatmap.field), heatmap.palette)
          : null;

        const existing = map.getSource(srcId) as maplibregl.GeoJSONSource | undefined;
        if (existing) {
          existing.setData(fc as never);
        } else if (isPolygon) {
          map.addSource(srcId, { type: "geojson", data: fc as never });
          map.addLayer({ id: layerId, type: "fill", source: srcId, paint: { "fill-color": "#c0613a", "fill-opacity": FLAT_FILL_OPACITY } });
          map.addLayer({ id: `${layerId}-outline`, type: "line", source: srcId, paint: { "line-color": "#c0613a", "line-width": 1.8, "line-opacity": 0.7 } });
        } else {
          map.addSource(srcId, { type: "geojson", data: fc as never });
          map.addLayer({ id: layerId, type: "circle", source: srcId, paint: { "circle-radius": POINT_RADIUS, "circle-color": "#c0613a", "circle-stroke-width": 1, "circle-stroke-color": "#fff" } });
        }

        // (Re)apply paint each run so a heatmap toggle reaches an existing layer.
        if (isPolygon) {
          map.setPaintProperty(layerId, "fill-color", (colorExpr ?? "#c0613a") as never);
          map.setPaintProperty(layerId, "fill-opacity", colorExpr ? HEATMAP_FILL_OPACITY : FLAT_FILL_OPACITY);
          if (map.getLayer(`${layerId}-outline`)) {
            // Heatmap: a barely-there hairline so sectors melt into a continuous
            // wash instead of a hard grid. Plain polygons keep their crisp edge.
            map.setPaintProperty(`${layerId}-outline`, "line-color", colorExpr ? "#5b4636" : "#c0613a");
            map.setPaintProperty(`${layerId}-outline`, "line-opacity", colorExpr ? 0.12 : 0.7);
            map.setPaintProperty(`${layerId}-outline`, "line-width", colorExpr ? 0.5 : 1.8);
          }
        } else {
          map.setPaintProperty(layerId, "circle-color", (colorExpr ?? "#c0613a") as never);
          pointLayerIds.push(layerId); // points ride above polygon fills (see z-order below)
        }

        // Frame only datasets we haven't framed before.
        if (!fittedRef.current.has(ds.dataset_id)) {
          fittedRef.current.add(ds.dataset_id);
          for (const f of fc.features) {
            if (extendBoundsFromGeometry(bounds, f.geometry as { type: string; coordinates: unknown })) fitAny = true;
          }
        }
      }
      // Z-order: lift every point layer above the polygon fills/outlines so
      // venue dots and score markers stay legible over the choropleth.
      for (const id of pointLayerIds) if (map.getLayer(id)) map.moveLayer(id);
      // Forget datasets that are gone (e.g. after a new chat) so they reframe if reused.
      fittedRef.current.forEach((id) => { if (!datasets[id]) fittedRef.current.delete(id); });
      if (fitAny) map.fitBounds(bounds, { padding: 80, maxZoom: 15, duration: 600 });
    };
    if (loadedRef.current) apply();
    else map.once("load", apply);
  }, [datasets, heatmaps, sectorsVersion]);

  // Apply layer filters from the agent's set_layer_filter actions.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      for (const [datasetId, filterExpr] of Object.entries(filters)) {
        const layerId = `ds-${datasetId}-layer`;
        if (!map.getLayer(layerId)) continue;
        // null = clear the filter; any array = apply it.
        map.setFilter(layerId, filterExpr as maplibregl.FilterSpecification | null | undefined);
        // Also apply to the outline layer if it exists.
        const outlineId = `${layerId}-outline`;
        if (map.getLayer(outlineId)) {
          map.setFilter(outlineId, filterExpr as maplibregl.FilterSpecification | null | undefined);
        }
      }
    };
    if (loadedRef.current) apply();
    else map.once("load", apply);
  }, [filters]);

  // Apply layer visibility from the agent's hide_layer / show_layer actions.
  // Declared after the dataset effect so a layer exists before we toggle it;
  // both depend on `datasets`, so a new layer picks up its hidden state too.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const hidden = new Set(hiddenLayers);
    const apply = () => {
      for (const id of Object.keys(datasets)) {
        const vis = hidden.has(id) ? "none" : "visible";
        for (const layerId of [`ds-${id}-layer`, `ds-${id}-layer-outline`]) {
          if (map.getLayer(layerId)) map.setLayoutProperty(layerId, "visibility", vis);
        }
      }
    };
    if (loadedRef.current) apply();
    else map.once("load", apply);
  }, [hiddenLayers, datasets]);

  // Apply per-layer colour overrides from set_layer_style actions. A style colour
  // wins over the default terracotta; if the agent also set a heatmap on the same
  // layer the ramp is applied by the dataset effect, so it won't set both.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      for (const [id, color] of Object.entries(layerStyles)) {
        const layerId = `ds-${id}-layer`;
        if (!map.getLayer(layerId)) continue;
        const prop = map.getLayer(layerId)?.type === "fill" ? "fill-color" : "circle-color";
        map.setPaintProperty(layerId, prop, color as never);
      }
    };
    if (loadedRef.current) apply();
    else map.once("load", apply);
  }, [layerStyles, datasets]);

  // Render markers.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markerObjsRef.current.forEach((m) => m.remove());
    markerObjsRef.current = [];
    for (const mk of markers) {
      const marker = new maplibregl.Marker({ color: "#9c4a2a" })
        .setLngLat(mk.coordinates)
        .setPopup(mk.label ? new maplibregl.Popup().setText(mk.label) : undefined)
        .addTo(map);

      // Click on the marker element: open the Street View card. Derive heading
      // as the bearing from the map center toward the marker so the image looks
      // at the location from street level, consistent with the Map-pilot-v2 pattern.
      const el = marker.getElement();
      el.style.cursor = "pointer";
      const [lng, lat] = mk.coordinates;
      const clickHandler = (e: Event) => {
        e.stopPropagation(); // don't also fire the map's generic click
        const center = map.getCenter();
        const dLng = lng - center.lng;
        const dLat = lat - center.lat;
        // Simple planar bearing (good enough at city scale).
        const heading = (Math.atan2(dLng, dLat) * 180) / Math.PI;
        setStreetViewRef.current({ lat, lng, heading: Math.round(heading) });
        // Notify the parent that this marker was clicked so it can persist it
        // as the chosen business location if none has been explicitly set yet.
        onMarkerClickRef.current?.(mk);
      };
      el.addEventListener("click", clickHandler);

      markerObjsRef.current.push(marker);
    }
    if (markers.length === 1) map.flyTo({ center: markers[0].coordinates, zoom: 15, duration: 600 });
  }, [markers]);

  return (
    <section ref={sectionRef} className="map-canvas">
      <div className="map-overlay-title">Gent · jouw Droomkaart</div>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
      {popupContainerRef.current &&
        createPortal(
          <FeatureInfoPopup properties={selected?.properties ?? null} onClose={() => setSelected(null)} />,
          popupContainerRef.current
        )}
      {streetView && (
        <MarkerStreetView
          lat={streetView.lat}
          lng={streetView.lng}
          heading={streetView.heading}
          onClose={() => setStreetView(null)}
        />
      )}
    </section>
  );
}
