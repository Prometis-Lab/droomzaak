import { useEffect, useRef } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import type { TransientDataset } from "../droomzaak/types";

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

type Props = {
  datasets: Record<string, TransientDataset>;
  markers: MapMarker[];
};

export function MapCanvas({ datasets, markers }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);
  const markerObjsRef = useRef<maplibregl.Marker[]>([]);

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

  // Render transient point datasets.
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
        const existing = map.getSource(srcId) as maplibregl.GeoJSONSource | undefined;
        if (existing) {
          existing.setData(ds.geojson as never);
        } else {
          map.addSource(srcId, { type: "geojson", data: ds.geojson as never });
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
        for (const f of ds.geojson.features) {
          const g = f.geometry;
          if (g.type === "Point") {
            bounds.extend(g.coordinates as [number, number]);
            any = true;
          }
        }
      }
      if (any) map.fitBounds(bounds, { padding: 80, maxZoom: 15, duration: 600 });
    };
    if (loadedRef.current) apply();
    else map.once("load", apply);
  }, [datasets]);

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
    <section className="map-canvas">
      <div className="map-overlay-title">Gent · jouw Droomkaart</div>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
    </section>
  );
}
