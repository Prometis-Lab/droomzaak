# Data tiers & the DataGateway boundary (non-negotiable)

This is the architectural rule that makes or breaks the pitch (PRD §3.4, §5.4: *"every analytical **warehouse** datum the agent surfaces flows through one audited seam"*). The `demo-readiness-reviewer` will fail the build if it's violated.

> **Scope note (loosened 2026-05-30).** The seam covers **warehouse/analytical data** — the numeric, sector-level evidence the agent reasons over (peer counts, location scores, rent proxies, demographics). It does **not** cover **curated build-time config** — the small, hand-verified, source-controlled rule sets (`config/permit_rules_horeca.yml`, `config/subsidies.yml`) that `permit_checklist_for` and `subsidies_for` read directly. Those are reviewed artifacts versioned in git, not live data, so they are an **explicitly allowed second read path** (see Rule 1a). Optionally they can still be seeded into Postgres via `scripts/seed_demo.py` + `supabase-schema-sync` and read through the gateway, but reading the YAML directly is sanctioned.

## Two tiers, never crossed

| Tier | What | Path | Feeds |
|---|---|---|---|
| **RENDER** | DuckDB + cached GeoJSON | local, native | the MapLibre layer cache **only** — keeps panning instant |
| **REASON** | Postgres 16 (`droomzaak` schema) | **only** via the internal `DataGateway` (parameterized SQL) | every analytical claim the agent makes |

**The render tier never feeds the agent's analytical reasoning. The reason tier is reached only through the one `DataGateway`.**

## Rules

1. **Warehouse/analytical tools** (`peer_benchmarks_statbel`, `score_locations`, `rent_benchmark`, demographics lookups, …) are **thin wrappers around a `DataGateway.query(...)` call**. No direct, scattered Postgres/DuckDB reads in tool bodies — they all funnel through the one gateway, which is the single audited seam.
1a. **Curated-config tools** (`permit_checklist_for`, `subsidies_for`) read their rule sets directly from the frozen, git-versioned YAML under `config/` — **not** through the gateway. This is the sanctioned exception: the config is a reviewed, source-controlled artifact (auditable by git history), not live analytical data, and a file read has no SQL-injection surface. Keep these tools deterministic and side-effect-free; load the YAML, filter by the founder's NACE/attributes/profile, return the documented shape. (They may *optionally* be seeded into Postgres and read via the gateway instead — both paths are allowed.)
2. **Behaviour tools stay native** and do NOT go through the gateway: `apply_map_actions`, `query_osm`, `geocode`, `isochrone`, `route`, Street View, `web_search` (Tavily). These are *actions*, not analytical data.
3. **Parameterized SQL only** — never string-format user/model input into SQL. Correctness *and* an injection boundary. This is the load-bearing rule now that the gateway is the boundary.
4. **Label proxies; never fake certainty.** Rent is a sector-median **proxy** (FOD/Statbel sale-price), never a per-address quote. Where data is thin or a rule is unconfirmed, say so and point to OOG / FAVV / Stad Gent (PRD §1.4).
5. **One gateway for the warehouse.** All **warehouse/analytical** reads go through `DataGateway.query(...)`; there is no second read path *into Postgres*. A reviewer fails the build if warehouse/analytical reads bypass the gateway. The only sanctioned non-gateway read is the curated-config YAML of Rule 1a — explicitly allowed, not a violation.
6. **No data tool mutates map state.** Read/enrich tools return data; the model commits visual change through `apply_map_actions`.

> **Dev tooling note.** Soda Straw is **not** in the product runtime or the agent's read path. It remains available only as a *Claude Code dev-time MCP* (see `.mcp.json`) for the team's own exploration.

See the `data-tool` skill for the call shape and the `warehouse-schema-expert` agent for the schema + SQL.
