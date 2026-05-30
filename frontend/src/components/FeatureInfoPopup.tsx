// Info card shown when the founder clicks a point or sector on the Droomkaart.
// It curates the feature's properties down to founder-relevant fields (Dutch
// labels, technical keys hidden) — the raw geometry/ids never surface. Rendered
// via a React portal into the MapLibre Popup's DOM content (see MapCanvas).

type Props = {
  properties: Record<string, unknown> | null;
  onClose(): void;
};

// Dutch labels for the fields we know how to show. Anything not listed and not
// hidden falls back to its raw key (rare — most features carry only these).
const FIELD_LABELS: Record<string, string> = {
  sectornaam: "Buurt",
  score: "Geschiktheidsscore",
  address: "Adres",
  rating: "Beoordeling",
  user_ratings_total: "Reviews",
  types: "Soort",
  wijknr: "Wijk",
};

// Technical keys that mean nothing to a founder — never shown as a row.
const HIDDEN_FIELDS = new Set(["nis9_code", "place_id", "id", "name", "sector_id"]);

// Display order: identity-ish fields first, technical-ish last.
const FIELD_ORDER = ["address", "rating", "user_ratings_total", "score", "types", "wijknr"];

function prettifyType(t: string): string {
  return t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Parse a value MapLibre may have JSON-stringified back into an array. */
function asArray(value: unknown): string[] | null {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === "string" && value.trim().startsWith("[")) {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) return parsed.map(String);
    } catch {
      /* not JSON — fall through */
    }
  }
  return null;
}

/** Format one field value for display; returns "" to skip the row. */
function formatValue(key: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  if (key === "score") {
    const n = Number(value);
    return Number.isFinite(n) ? `${Math.round(n * 100)} / 100` : "";
  }
  if (key === "rating") {
    const n = Number(value);
    return Number.isFinite(n) ? `${n.toLocaleString("nl-BE")} ★` : "";
  }
  if (key === "user_ratings_total") {
    const n = Number(value);
    return Number.isFinite(n) ? n.toLocaleString("nl-BE") : "";
  }
  if (key === "types") {
    const arr = asArray(value);
    return arr ? arr.slice(0, 3).map(prettifyType).join(", ") : "";
  }
  if (typeof value === "object") return "";
  return String(value);
}

export function FeatureInfoPopup({ properties, onClose }: Props) {
  if (!properties) return null;

  const title = String(properties.name ?? properties.sectornaam ?? "Locatie");
  const rows = FIELD_ORDER
    .filter((k) => k in properties && !HIDDEN_FIELDS.has(k))
    .map((k) => ({ key: k, label: FIELD_LABELS[k] ?? k, value: formatValue(k, properties[k]) }))
    .filter((r) => r.value !== "");

  return (
    <div className="dz-feature-popup" role="dialog" aria-label="Locatiedetails">
      <button type="button" className="dz-feature-popup__close" aria-label="Sluiten" onClick={onClose}>
        ×
      </button>
      <h3 className="dz-feature-popup__title">{title}</h3>
      {rows.length === 0 ? (
        <p className="dz-feature-popup__empty">Geen extra info.</p>
      ) : (
        <dl className="dz-feature-popup__rows">
          {rows.map((r) => (
            <div className="dz-feature-popup__row" key={r.key}>
              <dt>{r.label}</dt>
              <dd>{r.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
