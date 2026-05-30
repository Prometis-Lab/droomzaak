---
name: data-tool
description: Use when an agent tool needs to read analytical data in Droomzaak — peer benchmarks, location scoring, rent, permits, subsidies, demographics. Encodes the posture that EVERY analytical datum the agent reasons over flows through ONE internal DataGateway (parameterized SQL over the droomzaak Postgres), the thin-wrapper call shape, the read/enrich-only rule, and the parameterized-SQL injection boundary.
---

# Making an analytical tool route through the DataGateway

The posture: **every analytical datum the agent surfaces flows through one audited seam** — the `DataGateway`, a single module that runs parameterized SQL against the `droomzaak` Postgres. The debug overlay shows every analytical step routed through that one gateway, one connection, one audit log. **Rigid.** See also `.claude/rules/data-tiers.md`.

## The rule
- **Warehouse/analytical tools** (`peer_benchmarks_statbel`, `score_locations`, `rent_benchmark`, demographics lookups, …) are **thin wrappers around a `DataGateway.query(...)` call**. No direct, scattered Postgres/DuckDB reads in tool bodies — they all funnel through the one gateway.
- **Curated-config tools** (`permit_checklist_for`, `subsidies_for`) are the exception: they read frozen git-versioned YAML under `config/` directly (no gateway, no Postgres). Deterministic file load → filter by NACE/attributes/profile → documented shape. Not this skill's pattern.
- **Behaviour tools stay native** (NOT through the gateway): `apply_map_actions`, `query_osm`, `geocode`, `isochrone`, `route`, Street View, `web_search`.
- **Data tools never produce map state** — they return data; the model commits via `apply_map_actions`.

## Wiring the gateway (one-time, backend startup)
The contract: open **one connection pool at FastAPI startup** (lifespan), reused per request — `asyncpg`/`psycopg` against the `droomzaak` schema. `DataGateway` exposes a single `query(sql, params)` chokepoint plus a `health_check()`. Every analytical tool handler calls `DataGateway.query(...)` rather than touching Postgres directly; that one method is the audited seam and the architectural commitment.

## Call shape (per tool)
1. Build a **parameterized** statement for the `droomzaak` schema — **never string-format model/user input into SQL** (get the SQL from `warehouse-schema-expert`). Parameter binding is both correctness and the injection boundary.
2. Dispatch through `DataGateway.query(sql, params)`.
3. Map rows into the compact JSON your tool returns — round, label proxies (rent is a sector proxy, never per-address), cap rows, make "no data" explicit.
4. On a gateway/DB error, `return {"error","hint"}` — never crash the loop.

## Smoke test (Friday)
Exercise every analytical tool against the gateway: the query returns expected rows, errors degrade to `{error,hint}`, and the call is recorded in the gateway's audit log.

## Checklist
- [ ] Tool calls `DataGateway.query`, not Postgres/DuckDB directly
- [ ] SQL parameterized; results compact + proxies labelled + "no data" explicit
- [ ] Behaviour tools left native
- [ ] Gateway/DB errors returned as `{error,hint}`; loop never crashes
- [ ] Smoke-tested against the gateway

> **Dev tooling note.** Soda Straw remains available as a *Claude Code dev-time MCP* (see `.mcp.json`) for the team's own exploration — it is **not** part of the product runtime or the agent's read path.
