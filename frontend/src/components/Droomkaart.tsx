import type { ChapterState } from "../droomzaak/types";
import { finalisePackage } from "../droomzaak/api";

async function openPakket(sessionId: string) {
  try {
    const url = await finalisePackage(sessionId);
    window.open(url, "_blank", "noopener");
  } catch {
    // The render route composes from chapter_state too — open it directly.
    window.open(`/pakket/${sessionId}`, "_blank", "noopener");
  }
}

/** Render only clean primitive signals — drop nulls, empties, and nested objects
 *  so a stray non-founder-facing value can't surface as "[object Object]" junk. */
function nicheEntries(ns: Record<string, unknown>): [string, string][] {
  return Object.entries(ns)
    .filter(([, v]) => (typeof v === "string" || typeof v === "number" || typeof v === "boolean") && String(v).trim() !== "")
    .map(([k, v]) => [k, String(v)]);
}

/** The accumulating-profile sidebar — fills in as chapters complete. */
export function Droomkaart({ state, sessionId }: { state: ChapterState | null; sessionId?: string | null }) {
  const dp = state?.dream_profile;
  const ns = state?.niche_signals as Record<string, unknown> | null | undefined;
  const loc = state?.chosen_location;
  return (
    <aside className="droomkaart">
      <div className="droomkaart-head">
        <h1>Jouw Droomkaart</h1>
        <p>Alles wat we onderweg over je droom leren, verzamelt zich hier.</p>
      </div>
      <div className="droomkaart-body">
        <div className="dk-card">
          <h3>De droom</h3>
          {dp ? (
            <>
              {dp.founder_quote && <p style={{ fontStyle: "italic" }}>“{dp.founder_quote}”</p>}
              <ul className="dk-list">
                {dp.sector && <li>Sector: {dp.sector}</li>}
                {dp.scale && <li>Schaal: {dp.scale}</li>}
                {dp.seats_guess != null && <li>{dp.seats_guess} zitplaatsen</li>}
                {dp.neighbourhood_anchor && <li>Buurt: {dp.neighbourhood_anchor}</li>}
                {dp.vibe && <li>Sfeer: {dp.vibe}</li>}
              </ul>
            </>
          ) : (
            <p className="dk-empty">Vertel hiernaast in één zin wat je wil openen.</p>
          )}
        </div>
        <div className="dk-card">
          <h3>Niche</h3>
          {ns && nicheEntries(ns).length > 0 ? (
            <ul className="dk-list">
              {nicheEntries(ns).map(([k, v]) => (
                <li key={k}>{k.replace(/_/g, " ")}: {v}</li>
              ))}
            </ul>
          ) : (
            <p className="dk-empty">Nog niet verkend.</p>
          )}
        </div>
        <div className="dk-card">
          <h3>Plek</h3>
          {loc?.address ? (
            <p>{loc.address}{loc.wijk_nl ? ` · ${loc.wijk_nl}` : ""}</p>
          ) : (
            <p className="dk-empty">Nog niet gekozen.</p>
          )}
        </div>
        {state?.package_url && (
          <div className="dk-card">
            <h3>Pakket</h3>
            <a href={state.package_url} target="_blank" rel="noreferrer">Open je Droomzaak-pakket →</a>
          </div>
        )}
        {sessionId && state?.current_chapter === "5_pakket" && !state?.package_url && (
          <button className="dk-pakket-btn" onClick={() => openPakket(sessionId)}>
            Stel je Droomzaak-pakket samen →
          </button>
        )}
      </div>
    </aside>
  );
}
