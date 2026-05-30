# Data tiers & the DataGateway boundary (non-negotiable)

This is the architectural rule that makes or breaks the pitch (PRD §3.4, §5.4: *"every analytical datum the agent surfaces flows through one audited seam"*). The `demo-readiness-reviewer` will fail the build if it's violated.

## Two tiers, never crossed

| Tier | What | Path | Feeds |
|---|---|---|---|
| **RENDER** | DuckDB + cached GeoJSON | local, native | the MapLibre layer cache **only** — keeps panning instant |
| **REASON** | Postgres 16 (`droomzaak` schema) | **only** via the internal `DataGateway` (parameterized SQL) | every analytical claim the agent makes |

**The render tier never feeds the agent's analytical reasoning. The reason tier is reached only through the one `DataGateway`.**

## Rules

1. **Analytical/data tools** (`peer_benchmarks_statbel`, `score_locations`, `rent_benchmark`, `permit_checklist_for`, `subsidies_for`, demographics lookups, …) are **thin wrappers around a `DataGateway.query(...)` call**. No direct, scattered Postgres/DuckDB reads in tool bodies — they all funnel through the one gateway, which is the single audited seam.
2. **Behaviour tools stay native** and do NOT go through the gateway: `apply_map_actions`, `query_osm`, `geocode`, `isochrone`, `route`, Google Places (`places_search`), Street View, `web_search` (Tavily). These are *actions*, not analytical data.
3. **Parameterized SQL only** — never string-format user/model input into SQL. Correctness *and* an injection boundary. This is the load-bearing rule now that the gateway is the boundary.
4. **Label proxies; never fake certainty.** Rent is a sector-median **proxy** (FOD/Statbel sale-price), never a per-address quote. Where data is thin or a rule is unconfirmed, say so and point to OOG / FAVV / Stad Gent (PRD §1.4).
5. **One gateway, one path.** All analytical reads go through `DataGateway.query(...)`; there is no second read path. A reviewer fails the build if analytical reads bypass the gateway.
6. **No data tool mutates map state.** Read/enrich tools return data; the model commits visual change through `apply_map_actions`.

> **Dev tooling note.** Soda Straw is **not** in the product runtime or the agent's read path. It remains available only as a *Claude Code dev-time MCP* (see `.mcp.json`) for the team's own exploration.

See the `data-tool` skill for the call shape and the `warehouse-schema-expert` agent for the schema + SQL.
