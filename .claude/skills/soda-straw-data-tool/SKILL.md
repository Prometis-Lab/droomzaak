---
name: soda-straw-data-tool
description: Use when an agent tool needs to read analytical data in Droomzaak — peer benchmarks, location scoring, rent, permits, subsidies, demographics. Encodes the posture that EVERY analytical datum the agent reasons over flows through the Soda Straw MCP in front of Postgres, the thin-wrapper call shape, the read/enrich-only rule, the allowlist, and the feature-flagged local-Postgres failover that must stay OFF for the demo.
---

# Making an analytical tool route through Soda Straw

The pitch claim is "every datum the agent surfaces flows through Soda Straw" (PRD §3.4, §5.4). The debug overlay must show every analytical step routed through one straw, one Postgres connection, one audit log. **Rigid.** See also `.claude/rules/data-tiers.md`.

## The rule
- **Analytical/data tools** (`peer_benchmarks_statbel`, `score_locations`, `rent_benchmark`, `permit_checklist_for`, `subsidies_for`, demographics lookups, …) are **thin wrappers around a Soda Straw MCP `query` call**. No direct Postgres/DuckDB reads.
- **Behaviour tools stay native** (NOT through the straw): `apply_map_actions`, `query_osm`, `geocode`, `isochrone`, `route`, `places_search`, Street View, `web_search`.
- **Data tools never produce map state** — they return data; the model commits via `apply_map_actions`.

## Wiring the client (one-time, backend startup — data-shortlist §7.2)
A teammate wires this; the contract: open **one MCP session at FastAPI startup** (lifespan), reused per request — python `mcp` SDK, streamable-HTTP, **one `agent_*`-scoped bearer token**. Call `list_tools()` once at startup to discover the straw's tool shape (likely a generic `query(straw, sql)` — confirm by calling it). Build thin wrappers around it. Implement a small broker module (e.g. `agent_straw.py`): JSON-RPC over HTTP/SSE, a tool-list cache (~5 min), an allowlist via `SODA_STRAW_TOOL_ALLOWLIST`.

## Call shape (per tool)
1. Build parameterized `query` args for the `droomzaak` schema — **never string-format model/user input into SQL** (get SQL from `warehouse-schema-expert`).
2. Dispatch through the straw client.
3. Map rows into the compact JSON your tool returns — round, label proxies (rent is a sector proxy), cap rows, make "no data" explicit.
4. On straw error, `return {"error","hint"}` — never crash the loop.

## Failover (PRD §6.1 risk #1)
Soda Straw is the single dependency for all analytical tools. Keep a **local-Postgres-direct failover behind `DATA_BACKEND=postgres_direct`** running the SAME SQL via asyncpg, wrapped in a short timeout + circuit-breaker. It is **OFF by default** (`soda_straw`) and used only if the straw breaks live. The reviewer fails the build if analytical reads bypass the straw by default.

## Smoke test (Friday, PRD §4.4)
Exercise every analytical tool from a local MCP client against the registered straw: it lists the tool, the query returns expected rows, the audit log records the call.

## Checklist
- [ ] Tool calls Soda Straw `query`, not Postgres/DuckDB directly
- [ ] SQL parameterized; results compact + proxies labelled + "no data" explicit
- [ ] Behaviour tools left native
- [ ] Straw errors returned as `{error,hint}`; loop never crashes
- [ ] Local-direct failover exists, behind the flag, OFF by default
- [ ] Smoke-tested from an MCP client against the registered straw
