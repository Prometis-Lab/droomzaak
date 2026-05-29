---
name: supabase-schema-sync
description: Use when changing or inspecting the Droomzaak Postgres warehouse hosted on Supabase — adding/altering a table or RPC, writing a migration, querying the schema, or redeploying. Keeps a full local mirror (supabase/migrations + schema.sql + QUICK_REFERENCE) so the DB is queryable locally and re-deployable anywhere. Enforces the read-only-MCP + idempotent-script + STOP-and-wait workflow. Use when the user mentions Supabase, schema, migration, RPC, DDL, or "the warehouse".
---

# Supabase schema sync (local mirror + safe changes)

The `droomzaak` analytical warehouse lives on **Supabase Postgres**; we keep a full local copy under `supabase/` so we can query locally and redeploy fast (a saved-me-hours pattern + demo-day failover insurance). Pair with `warehouse-schema-expert` (owns the schema knowledge + SQL). **Rigid** on the boundary + the change workflow.

## Boundary (don't blur)
- **Agent runtime → Soda Straw → this Postgres.** Analytical tools never read Supabase directly (`.claude/rules/data-tiers.md`). The Supabase MCP + the local mirror are **dev/deploy tooling only**.
- **The Supabase MCP is READ-ONLY.** Inspection only (`list_tables`, `execute_sql` SELECTs, schema verification). **Never** run DDL/DML through the MCP.

## The local mirror (`supabase/`)
- `migrations/` — timestamped, **idempotent** SQL (`CREATE TABLE IF NOT EXISTS`, `CREATE OR REPLACE FUNCTION`). The change history + redeploy source.
- `schema.sql` — generated full snapshot (`supabase db dump` / `pg_dump --schema-only`). Queryable + redeployable; **regenerate after every applied migration**.
- `functions/` — RPC definitions (also in migrations).
- `scripts/` + `scripts/archive/` — ad-hoc operator SQL; archive once folded into a migration.
- `QUICK_REFERENCE.md` — tables/keys/RPCs lookup; keep in sync.

## Change workflow (STOP-and-wait — never auto-apply DDL)
1. **Pre-validate** — inspect live schema via the read-only Supabase MCP; verify column names / function signatures against `schema.sql`.
2. **Write an idempotent script** in `supabase/scripts/` (re-runnable; parameterize; `IF NOT EXISTS` / `CREATE OR REPLACE`).
3. **STOP** — ask the operator to run it (`supabase db push`, SQL editor, or `psql "$SUPABASE_DB_URL"`).
4. **WAIT** — do not proceed until they confirm success.
5. **Integrate** — fold into a timestamped `migrations/` file, **regenerate `schema.sql`**, update `QUICK_REFERENCE.md`, move the script to `scripts/archive/`.

## Query locally / redeploy
- **Query:** `psql -f supabase/schema.sql` into a scratch DB, or `supabase start` (local stack) — explore + `EXPLAIN` analytical SQL without touching the hosted DB.
- **Redeploy:** apply `migrations/` to a fresh project (`supabase db push`) or `supabase db reset` locally — the whole schema + RPCs come back. This backs the `DATA_BACKEND=postgres_direct` failover (PRD §6.1): same Postgres, stood up anywhere, in minutes.

## Rules
- Idempotent everything; parameterized SQL; analytical functions are SELECT-only (mutations live in migrations, never the agent path).
- **Never commit secrets** — `SUPABASE_ACCESS_TOKEN` / `SUPABASE_PROJECT_REF` / `SUPABASE_DB_URL` come from gitignored `.env.demo`.
- After a migration, the mirror MUST match the live DB: regenerate `schema.sql` + update `QUICK_REFERENCE.md` in the same change.

## Checklist
- [ ] Inspected via read-only MCP; verified names against `schema.sql`
- [ ] Idempotent script in `scripts/`; operator ran it; confirmed
- [ ] Folded into `migrations/`; `schema.sql` regenerated; `QUICK_REFERENCE.md` updated; script archived
- [ ] No DDL via MCP; no secrets committed; analytical reads still via Soda Straw
