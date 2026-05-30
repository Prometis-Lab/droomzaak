import { useEffect, useRef } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";

const GHENT_CENTER: [number, number] = [3.7257, 51.0543];

// Key-free raster style (OSM tiles) — good enough street-level base for dev/demo.
// Swap to a vector style + key later without touching the rest of the app.
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

export function MapCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

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
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return (
    <section className="map-canvas">
      <div className="map-overlay-title">Gent · jouw Droomkaart</div>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />
    </section>
  );
}
