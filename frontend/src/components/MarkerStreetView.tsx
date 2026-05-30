/**
 * MarkerStreetView — floating card that renders a Google Street View Static
 * API image for a given lat/lng. Ported from Map-pilot-v2 pattern: a
 * `suggest_street_view` agent action (or a marker click) sets the coordinates
 * in parent state; this component is rendered conditionally from that state.
 *
 * Props:
 *   lat, lng   — WGS-84 coordinates of the point
 *   heading    — camera heading in degrees (0 = north, default 0)
 *   pitch      — camera pitch in degrees (default 0)
 *   onClose    — called when the user closes the card
 *
 * CSS classes: marker-streetview-card, marker-streetview-img,
 *              marker-streetview-placeholder, marker-streetview-close
 *
 * Key: read from import.meta.env.VITE_GOOGLE_MAPS_API_KEY (never hardcoded).
 */
import { useEffect } from "react";

interface Props {
  lat: number;
  lng: number;
  heading?: number;
  pitch?: number;
  onClose: () => void;
}

const API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;

function buildStreetViewUrl(lat: number, lng: number, heading: number, pitch: number): string {
  const params = new URLSearchParams({
    size: "600x400",
    location: `${lat},${lng}`,
    heading: String(heading),
    pitch: String(pitch),
    key: API_KEY ?? "",
  });
  return `https://maps.googleapis.com/maps/api/streetview?${params.toString()}`;
}

export function MarkerStreetView({ lat, lng, heading = 0, pitch = 0, onClose }: Props) {
  // Close on Escape key.
  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, [onClose]);

  return (
    <div className="marker-streetview-card" role="dialog" aria-label="Street View">
      <button
        type="button"
        className="marker-streetview-close"
        onClick={onClose}
        aria-label="Sluiten"
      >
        ×
      </button>
      {API_KEY ? (
        <img
          className="marker-streetview-img"
          src={buildStreetViewUrl(lat, lng, heading, pitch)}
          alt={`Street View op ${lat.toFixed(5)}, ${lng.toFixed(5)}`}
          loading="lazy"
        />
      ) : (
        <div className="marker-streetview-placeholder">
          <p>Street View niet beschikbaar</p>
          <p style={{ fontSize: "11px", opacity: 0.7 }}>
            Stel <code>VITE_GOOGLE_MAPS_API_KEY</code> in om afbeeldingen te laden.
          </p>
        </div>
      )}
    </div>
  );
}
