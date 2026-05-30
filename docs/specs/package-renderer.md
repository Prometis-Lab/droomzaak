# Spec — Package renderer (Commit 4)

**Status:** lean spec · **Track:** A (backend) + light B (frontend link)
**Goal:** Render the session's accumulated state into a server-rendered, printable
*Droomzaak-pakket* — the Chapter-5 payoff the PRD promises ("one sentence → a
printable pakket"). No database required: reads the DuckDB session/render tier.

## Why now
- `compose_package` already assembles + persists `package_json` (see
  `droomzaak_tools.handle_compose_package`). Data is done; only rendering is missing.
- Needs **no Postgres** — closes the journey end-to-end on plain localhost even
  before chapters 2–4 go live against the warehouse (operator step still pending).

## Data shapes (VERIFIED against the codebase — v1 had these wrong)
> The first draft of this section invented field names; spec-critic caught it (4/10).
> These are the REAL shapes from `handle_compose_package` (droomzaak_tools.py) and
> `_CHAPTER_KEYS` (droomzaak_chapters.py). The implementation follows these.

`store.load_package(session_id)` → the `package` dict written by `compose_package`:
```
session_id, generated_at (ISO date str), dream_profile{}, niche_signals{},
chosen_location{}, candidate_locations[], permit_checklist[], subsidies[],
legal_form{}, dream_narrative (str), tuesday_morning (str)
```
Fallback source — `store.load_chapter_state(session_id)` → **None** for a fresh
session; otherwise `_CHAPTER_KEYS` (same names as above minus session_id/generated_at,
plus `current_chapter`, `package_url`). All list/object fields can be `None`.

Notes that drove the fixes:
- Narrative is `dream_narrative` (a **string**, top-level) — there is no
  `narrative_markdown` and no nested `narrative` object. `tuesday_morning` is its
  own top-level string and gets its **own card** (PRD §6.3 payoff).
- There is **no `peer_summary`** field anywhere (compose_package copies none) — the
  pakket shows no peer section; the disclaimer is scoped to what's actually rendered.
- `generated_at` (not `generated_at_label`); stamped only on the finalise path.
- `permit_checklist` (not `permits`); `niche_signals` (not `niche`).
- legal_form keys: `recommended`, `alternative`, `rationale_nl`,
  `estimated_setup_cost_eur`, `notes_nl` (not `recommended_form`).
- Frontend: there is no `package_ready`; the button keys off
  `current_chapter === "5_pakket"`, and the existing card off `package_url`.
- `build_package_dict(state, session_id)` is the single shared shape definition,
  used by both the renderer fallback and `compose_from_state`.

## Design

### New module `backend/app/package_view.py`
- `build_package_context(store, session_id) -> dict | None`
  1. `pkg = store.load_package(session_id)` — if present, use it.
  2. Else synthesize from `store.load_chapter_state(session_id)`: map the same
     fields; pull `narrative_markdown` from `state["narrative"]`. If the state is
     still the empty default (no dream_profile **and** no chosen_location and no
     permits/subsidies), return `None` (nothing worth rendering yet).
  3. Else (no session row at all) return `None`.
  - Normalise into a view dict with `narrative_paragraphs: list[str]` (split the
    narrative_markdown string on blank lines **in Python here**, not the template;
    **no markdown dep**), and pass lists/objs straight through.
  - `generated_at_label` is rendered only when truthy (the template hides the date
    line when `""`). Do **not** stamp `datetime.now()` in the renderer — the
    fallback path simply has no date line. (If a label is ever wanted on the
    fallback path, stamp it in `compose_from_state`, never in the template.)
- `compose_from_state(store, session_id) -> dict | None` — read chapter_state,
  build the same `package` shape, `store.save_package(...)`, return it (or None if
  empty). Reuses the exact field mapping; lets the frontend "finalise" the pakket
  without relying on the agent having called `compose_package`.

### Jinja2 template `backend/templates/pakket.html`
- **Self-contained** — all CSS inline in a `<style>` block, **no external assets,
  no web fonts, no JS** so it prints/PDFs anywhere offline (audit + demo safe).
- **autoescape ON** (Jinja2 `select_autoescape(["html"])`) — user/model content is
  escaped; this is the injection boundary for rendered free text. **Forbidden
  anywhere in the template: `| safe` and `{% autoescape false %}`** — they would
  silently break that boundary (test #5 guards it on the narrative field). Narrative
  renders as `{% for para in narrative_paragraphs %}<p>{{ para }}</p>{% endfor %}`.
- **Defensive rendering of free-form objects.** `chosen_location`, `peer_summary`,
  `legal_form` are `additionalProperties: True` — no key is guaranteed. Read the
  expected keys with `{% if %}` guards (e.g. `chosen_location.address`,
  `.sector_name_nl`, `.scores`), and skip a section when its object is empty. Never
  assume a key exists; never enable `StrictUndefined`.
- **Item shapes** (pin to what the tools/config return, `{% if %}`-guard optionals):
  permits → `permit_name, authority, deep_link, estimated_cost_eur,
  estimated_processing_days, notes_nl`; subsidies → `name, authority,
  max_amount_eur, deep_link, description_nl, status`. Verify against
  `permit_checklist_for` / `subsidies_for` return shapes before finalising the
  template; render only keys that are present.
- `deep_link` is rendered as `<a href>`. **Trusted curated-config only** — if a
  future change ever pipes model output into a link, the URL scheme must be
  validated (no `javascript:`). Add this as a comment in the template.
- Sections, in order: header (dream one-liner + `generated_at_label`) → narrative
  (Chapter-5 story) → chosen location (address/sector/scores) → peer summary →
  permits checklist → subsidies (each with status; `status == "ended_2025"`
  rendered **greyed-out** with a "vervallen in 2025" tag) → legal form → footer
  disclaimer.
- **Never fake certainty (CRITICAL RULE 3):** footer states rent/figures are
  sector **proxies, not per-address quotes**, and points to **OOG / FAVV / Stad
  Gent** for confirmation. Any `label_nl`/proxy labels on data objects are rendered
  verbatim, not stripped.
- **Brand (Track B):** warm earth tones, generous serif headings, a passion-project
  moodboard feel — **never a tax form**. `@media print` stylesheet: hide nothing
  essential, page-break-avoid inside cards, black-on-cream.

### Route `backend/app/main.py`
- `GET /pakket/{session_id}` → `HTMLResponse`.
  - `ctx = build_package_context(store, session_id)`; if `None` → `404`
    ("Nog geen pakket voor deze sessie").
  - Render the Jinja2 template with `ctx`, return `HTMLResponse(html)`.
- `POST /api/droomzaak/package/{session_id}` → JSON.
  - `pkg = compose_from_state(store, session_id)`; if `None` → `404`.
  - return `{"package_url": f"/pakket/{session_id}", "ready": True}`.
- Jinja2 `Environment(loader=FileSystemLoader(...), autoescape=select_autoescape(["html"]))`
  built once at module load. **Templates dir resolution (exact):**
  `FileSystemLoader(str(Path(__file__).resolve().parent.parent / "templates"))`
  from `package_view.py` → resolves to `backend/templates/`. This works for the
  hackathon source runs (`uv run`). **If a wheel build is ever used**, hatchling
  excludes `.html` by default — `backend/templates/*.html` must be added via
  `[tool.hatch.build.targets.wheel] artifacts` / `force-include` in `pyproject.toml`.
  (Source-run only is fine for the demo; noted so a future packaging step knows.)
- `HTMLResponse` imported from `fastapi.responses`.

### Frontend (light)
- In the Droomkaart sidebar (or Chapter-5 view), when `chapter_state.package_ready`
  or `current_chapter == "pakket"`, show a **"Bekijk je Droomzaak-pakket"** button
  → opens `/pakket/{sessionId}` in a new tab. (Backend route is same-origin via the
  Vite proxy / relative URL.) The button **POSTs the finalise endpoint first**, then
  opens the URL — so the pakket is composed from the latest chapter_state regardless
  of whether the agent called `compose_package`.

## Tests `backend/tests/test_package_renderer.py`
Use an in-memory `CatalogStore(":memory:")` via `set_store` (no real DB/APIs).
**Autouse fixture (required):** set `settings.DROOMZAAK_POSTGRES_URL = ""` and
`set_store(CatalogStore(":memory:"))` before each test; tear down with
`set_store(None)`. Then use `with TestClient(app) as client:` so the lifespan runs
in **degraded mode** (no DataGateway connect). Without this, a demo/CI shell that
exports `DROOMZAAK_POSTGRES_URL`/`DROOMZAAK_PG_DSN`/`SUPABASE_DB_URL` would make
the lifespan open a real pool and the run would hang/fail.
1. **Renders a saved package** — save a full package, `GET /pakket/{id}` → 200,
   HTML contains the dream one-liner, a permit name, a subsidy name, the legal form.
2. **Greys out ended subsidies** — a `status: "ended_2025"` subsidy renders with the
   "vervallen" marker / greyed class; an `active` one does not.
3. **Fallback from chapter_state** — no package saved but chapter_state populated →
   200 and renders (exercises `build_package_context` synth path).
4. **Empty session → 404** — fresh/default session → `GET /pakket/{id}` 404.
5. **Autoescape** — a `<script>` injected into the **narrative** field (the one most
   likely to be wrongly marked `| safe`) appears escaped (`&lt;script&gt;`) in the
   output, not as a live tag.
6. **compose_from_state** — POST finalise on a populated chapter_state writes a
   package (`load_package` non-None) and returns the `package_url`.

Use FastAPI `TestClient` for the route tests.

## Invariants honoured
- DataGateway boundary: renderer reads **only** the render/session tier (DuckDB),
  never Postgres — correct; the pakket is presentation, not analytical reasoning.
- Never fake certainty: proxy labels rendered verbatim + disclaimer footer.
- No new heavy deps (jinja2 already present; no markdown lib).
- Tests never hit real APIs.

## Spec-critic resolution (v2)
Fixes applied for items 1–6: TestClient/lifespan autouse fixture (degraded mode);
exact templates-dir resolution + wheel-packaging note; `generated_at_label` hidden
when empty (no `now()` in renderer); `| safe`/`autoescape false` forbidden + test #5
targets narrative; defensive `{% if %}` rendering of free-form dicts; pinned
permit/subsidy item keys; `deep_link` trusted-config note; POST finalise promoted
from optional to required (test #6).

## Out of scope
- Server-side PDF generation (browser "Print → Save as PDF" is the path).
- i18n beyond the existing nl-primary copy.
- Styling polish beyond "credible + on-brand" (Track-B can refine later).
