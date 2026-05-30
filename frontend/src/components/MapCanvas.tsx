import { useEffect, useRef } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import type { TransientDataset } from "../droomzaak/types";

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

// MapLibre filter expression — null means "clear the filter".
export type FilterExpr = unknown[] | null;

type Props = {
  datasets: Record<string, TransientDataset>;
  markers: MapMarker[];
  filters?: Record<string, FilterExpr>;
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

export function MapCanvas({ datasets, markers, filters = {} }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);
  const markerObjsRef = useRef<maplibregl.Marker[]>([]);

  // Watch the outer section for size changes → keep MapLibre canvas correct.
  useMapResize(sectionRef, mapRef);

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
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
  }, []);

  // Render transient datasets — points as circle, polygons as fill+line.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const bounds = new maplibregl.LngLatBounds();
      let any = false;
      for (const ds of Object.values(datasets)) {
        if (!ds.geojson) continue;
        const srcId = `ds-${ds.dataset_id}`;
        const layerId = `${srcId}-layer`;
        const isPolygon = hasPolygonGeometry(ds.geojson as { features: Array<{ geometry: { type: string } }> });
        const existing = map.getSource(srcId) as maplibregl.GeoJSONSource | undefined;
        if (existing) {
          existing.setData(ds.geojson as never);
        } else {
          map.addSource(srcId, { type: "geojson", data: ds.geojson as never });
          if (isPolygon) {
            // Fill layer — semi-transparent terracotta.
            map.addLayer({
              id: layerId,
              type: "fill",
              source: srcId,
              paint: {
                "fill-color": "#c0613a",
                "fill-opacity": 0.18,
              },
            });
            // Outline layer — same terracotta, solid.
            map.addLayer({
              id: `${layerId}-outline`,
              type: "line",
              source: srcId,
              paint: {
                "line-color": "#c0613a",
                "line-width": 1.8,
                "line-opacity": 0.7,
              },
            });
          } else {
            map.addLayer({
              id: layerId,
              type: "circle",
              source: srcId,
              paint: {
                "circle-radius": 6,
                "circle-color": "#c0613a",
                "circle-stroke-width": 1.5,
                "circle-stroke-color": "#fff",
              },
            });
          }
        }
        // Extend bounds for all geometry types.
        for (const f of (ds.geojson as { features: Array<{ geometry: { type: string; coordinates: unknown } }> }).features) {
          if (extendBoundsFromGeometry(bounds, f.geometry)) any = true;
        }
      }
      if (any) map.fitBounds(bounds, { padding: 80, maxZoom: 15, duration: 600 });
    };
    if (loadedRef.current) apply();
    else map.once("load", apply);
  }, [datasets]);

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
      markerObjsRef.current.push(marker);
    }
    if (markers.length === 1) map.flyTo({ center: markers[0].coordinates, zoom: 15, duration: 600 });
  }, [markers]);

  return (
    <section ref={sectionRef} className="map-canvas">
      <div className="map-overlay-title">Gent · jouw Droomkaart</div>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
    </section>
  );
}
