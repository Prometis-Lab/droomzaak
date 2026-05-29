# Data tiers & the Soda Straw boundary (non-negotiable)

This is the architectural rule that makes or breaks the pitch (PRD §3.4, §5.4: *"every datum the agent surfaces flows through Soda Straw"*). The `demo-readiness-reviewer` will fail the build if it's violated.

## Two tiers, never crossed

| Tier | What | Path | Feeds |
|---|---|---|---|
| **RENDER** | DuckDB + cached GeoJSON | local, native | the MapLibre layer cache **only** — keeps panning instant |
| **REASON** | Postgres 16 (`droomzaak` schema) | **only** via the Soda Straw MCP | every analytical claim the agent makes |

**The render tier never feeds the agent's analytical reasoning. The reason tier is reached only through Soda Straw.**

## Rules

1. **Analytical/data tools** (`peer_benchmarks_statbel`, `score_locations`, `rent_benchmark`, `permit_checklist_for`, `subsidies_for`, demographics lookups, …) are **thin wrappers around a Soda Straw `query` call**. No direct Postgres/DuckDB reads in these tools.
2. **Behaviour tools stay native** and do NOT go through Soda Straw: `apply_map_actions`, `query_osm`, `geocode`, `isochrone`, `route`, Google Places (`places_search`), Street View, `web_search` (Tavily). These are *actions*, not analytical data.
3. **Parameterized SQL only** — never string-format user/model input into SQL. Correctness *and* an injection boundary.
4. **Label proxies; never fake certainty.** Rent is a sector-median **proxy** (FOD/Statbel sale-price), never a per-address quote. Where data is thin or a rule is unconfirmed, say so and point to OOG / FAVV / Stad Gent (PRD §1.4).
5. **Failover stays OFF by default.** The local-Postgres-direct path (`DATA_BACKEND=postgres_direct`) exists behind a flag for a live emergency only (PRD §6.1 risk #1). Default is `soda_straw`. A reviewer fails the build if analytical reads bypass the straw by default.
6. **No data tool mutates map state.** Read/enrich tools return data; the model commits visual change through `apply_map_actions`.

See the `soda-straw-data-tool` skill for the call shape and the `warehouse-schema-expert` agent for the schema + SQL.
