# Droomzaak build — kickoff progress & plan

**Date:** 2026-05-30 · **Branch:** YC-branch · **Author:** Claude (Opus 4.8) session
**Status:** Research complete, no code written yet. Resume at "Build order" below.

## Critical context (read before building)

1. **Clean-room build.** Per CLAUDE.md, this is built from scratch from the PRD +
   data-shortlist. The build docs in `reference/map-pilot-build-docs/` (00–09 + snippets)
   are an excellent, detailed spec — **but they assume a fork of "Map Pilot v2" that does
   NOT exist in this repo** (no `backend/`, no `frontend/`, no `agent_loop.py`). So we must
   build the foundation (agent loop, provider adapters, validation, MapLibre canvas, session
   store) ourselves too — lean, but honoring the docs' invariants. Build a LEAN subset of
   "reused" tools (only what chapters need), not all 16 Map Pilot tools.

2. **Source-of-truth precedence:** `droomzaak-data-shortlist.md` > `droomzaak-prd.md` >
   the map-pilot-build-docs. Where the build docs conflict with the data-shortlist, the
   data-shortlist wins. Key corrections already confirmed from data-shortlist §1:
   - **`places_popular_times` does NOT exist** (not in Google Places API New). DROP it.
     Footfall = warehouse `footfall_sector` composite + live `places_search` density.
   - **`web_search` (Tavily) IS a tool** (chapters 2,4 fallback). Add it.
   - **`peer_benchmarks_statbel`** keeps its name but is backed by **Belfirst jaarrekeningen
     + Statbel cohort** (aggregates only — proprietary licence).
   - **geocode** = inherited `prometis_toolkit` (BeSt) in `inherited/` (gitignored).
   - Rent is a **sale-€ sector proxy** (`housing_price_sector`), never per-address.

3. **Authoritative tool surface** (data-shortlist §1, supersedes build-doc 05):
   `extract_dream_profile`(1), `peer_benchmarks_statbel`(2), `places_search`(2,3),
   `score_locations`(3), `rent_benchmark`(3), `permit_checklist_for`(4), `subsidies_for`(4),
   `legal_form_advisor`(4), `generate_dream_narrative`(5), `compose_package`(5),
   `set_chapter_state`(all, sub-action inside apply_map_actions), `web_search`(2,4),
   `query_osm`(2,3), `geocode`(3), `apply_map_actions`(all), `report_problem`(all).
   → Chapter-3 allowlist must DROP `places_popular_times`; otherwise follow build-doc 04 §5
   allowlists and build-doc snippets/chapter-states.md for the state machine.

## Architecture invariants (non-negotiable — from CLAUDE.md + rules/data-tiers.md)

- **DataGateway boundary:** every analytical datum flows through ONE `DataGateway.query(sql, params)`
  (parameterized SQL → Postgres `droomzaak` schema). Behaviour tools (query_osm, geocode,
  places_search, web_search, apply_map_actions) stay native, NOT through the gateway.
- **Parameterized SQL only.** Never string-format model/user input into SQL.
- **Two tiers:** RENDER = DuckDB + cached GeoJSON → MapLibre only. REASON = Postgres via
  DataGateway → agent reasoning only. Never cross them.
- **Never fake certainty** — label proxies; point to OOG/FAVV/Stad Gent when unsure.
- **uv only** for Python (`uv venv`/`uv sync`/`uv run`). Never pip/bare python.
- **Tests never hit real APIs** — monkeypatch gateway, Places, ORS, the model.
- **Provider-neutral tools** — one spec, one handler, no `if provider==` in tool bodies.
- The agent loop's 5 hard-earned behaviours (build-doc 04 §0.3): plan capture,
  commit-enforcement nudge, synthesis fallback, JSON-envelope unwrap, early-break-after-commit.
  Build these into our from-scratch loop.

## Toolchain (verified present)
uv 0.9.21 · node v22.13.1 · npm 10.9.2 · python 3.13.7. Env template at `.env.demo.example`
(documents ANTHROPIC/OPENAI keys, AGENT_PROVIDER, DROOMZAAK_POSTGRES_URL, GOOGLE_MAPS_API_KEY,
OPENROUTESERVICE, OVERPASS_API_URL, TAVILY_API_KEY, CORS_ALLOW_ORIGINS, etc.).
Postgres schema DDL is in build-doc 03 §3 (droomzaak.* tables); a supabase/ scaffold exists.

## Build order (commit after each — user wants frequent commits + fast localhost)

**Commit 1 — bootable full-stack scaffold (DO THIS FIRST, no DB/keys needed to boot):**
- `pyproject.toml` (uv): fastapi, uvicorn[standard], pydantic, pydantic-settings, httpx,
  anthropic, openai, asyncpg, duckdb, jinja2, pyyaml, python-dotenv; dev: pytest,
  pytest-asyncio, anyio.
- `backend/app/{__init__,settings,main}.py`: FastAPI + CORS + `GET /api/admin/health` +
  lifespan that calls `gateway.connect()` only if DROOMZAAK_POSTGRES_URL set (graceful skip).
- `frontend/`: Vite + React + TS + maplibre-gl. `App.tsx` = MapLibre canvas (Ghent center
  3.7257,51.0543) + ChapterRail shell (5 steps) + Droomkaart sidebar shell + agent panel shell.
  Vite proxy `/api`→localhost:8000. Use a free demotiles/OSM raster style to avoid key needs.
- Verify: `uv run uvicorn backend.app.main:app` health 200; `npm run dev` renders map; `npm run build` clean.

**Commit 2 — agent core:** agent_loop.py (+ ProviderAdapter Protocol, ProviderResponse,
ToolCall, AgentRun), agent_anthropic.py, agent_openai.py, agent_tools.py (base: apply_map_actions,
report_problem, query_osm, geocode, web_search), agent_validation.py, data_gateway.py,
sessions store (DuckDB `agent_sessions` w/ `chapter_state_json`), droomzaak_tools.py (the 11),
droomzaak_prompt.py (VERBATIM from snippets/system-prompt.md — do not paraphrase),
droomzaak_chapters.py (wrapper: load/save/default chapter state, apply_state_patch,
chapter-aware prompt+tool filter, run_droomzaak_turn), droomzaak_validation.py
(validate_set_chapter_state + TRANSIENT_PREFIXES += places-/score-locations-). Routes:
`POST /api/agent/chat`, `POST/GET/DELETE /api/agent/session`, `GET/PUT /api/droomzaak/chapter/{sid}`.
Tests (monkeypatched): test_droomzaak_chapters, _tools, _validation, _e2e_lisa (build-doc 09).

**Commit 3 — frontend chapter flow:** ChapterRail, Droomkaart, Chapter1Intro..Chapter5PakketCTA,
droomzaak/{api.ts,chapter-state.ts,chapter-machine.ts}, wire chat response → setChapterState.

**Commit 4 — package renderer:** `GET /pakket/{sid}` Jinja2 + print CSS (build-doc 08 §5),
compose_package writes package_json, `POST /api/droomzaak/package/{sid}`.

**Commit 5 — data layer:** apply build-doc 03 §3 schema to Postgres/Supabase, seed Lisa-path
fixtures (peer cohort 56.101, sectors, rent, permit_rules YAML, subsidies YAML), wire DataGateway,
smoke-test each analytical tool. Until then analytical chapters return the documented
`{error,hint}` envelope — app still boots & chapters 1/5 (pure-LLM) work.

## Parallelization notes (user wants speed)
Build commit 1 + the shared contracts of commit 2 (loop, validation, gateway, state shapes)
in the MAIN session first — parallel agents would clash on these shared files. THEN fan out:
- `agent-tool-builder` agents (one per droomzaak tool) once tool_specs()/dispatch/gateway exist.
- `maplibre-canvas-builder` for frontend chapter components (commit 3) in parallel.
- `warehouse-schema-expert` + `open-data-ingest-specialist` for commit 5 in parallel with FE.
Reviewers/critics are read-only. Commit only via `/ship` from main session; never push.

## Key file references in the spec
- Loop invariants + wrapper: `reference/map-pilot-build-docs/04-agent-loop.md`
- 12 tool specs: `05-agent-tools.md` (but apply data-shortlist §1 corrections above)
- Verbatim prompt + chapter blocks: `snippets/system-prompt.md`
- State schema/exit conditions/Lisa trajectory: `snippets/chapter-states.md`
- Validation (set_chapter_state, transient prefixes): `07-validation.md`
- Endpoints + frontend components + pakket renderer: `08-api-frontend.md`
- Postgres schema + DataGateway code: `03-data-layer.md`
- Test plan: `09-testing.md`
