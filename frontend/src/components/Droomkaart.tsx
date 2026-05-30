/** The accumulating-profile sidebar. Commit-1 shell; fills in per chapter later. */
export function Droomkaart() {
  return (
    <aside className="droomkaart">
      <div className="droomkaart-head">
        <h1>Jouw Droomkaart</h1>
        <p>Alles wat we onderweg over je droom leren, verzamelt zich hier.</p>
      </div>
      <div className="droomkaart-body">
        <div className="dk-card">
          <h3>De droom</h3>
          <p className="dk-empty">Vertel hiernaast in één zin wat je wil openen.</p>
        </div>
        <div className="dk-card">
          <h3>Niche</h3>
          <p className="dk-empty">Nog niet verkend.</p>
        </div>
        <div className="dk-card">
          <h3>Plek</h3>
          <p className="dk-empty">Nog niet gekozen.</p>
        </div>
      </div>
    </aside>
  );
}
