# Supabase — local mirror of the Droomzaak warehouse

The `droomzaak` analytical warehouse (PRD §3 REASON tier) is hosted on **Supabase Postgres**. We keep a **full local copy of the schema + RPCs** here so we can: (1) query/inspect it locally, (2) **re-deploy the whole DB anywhere in minutes** (demo-day resilience, PRD §6.1 failover), and (3) review every schema change in git.

> **Architecture boundary (don't blur it):** at runtime the agent reaches analytical data **only through Soda Straw → this Postgres** (the pitch, `.claude/rules/data-tiers.md`). The Supabase MCP + this mirror are **dev/deploy tooling**, never the agent's read path. The render tier (DuckDB + GeoJSON) is separate again.

## Layout
- `migrations/` — **source of truth for change history.** Timestamped, idempotent SQL (`CREATE TABLE … IF NOT EXISTS`, `CREATE OR REPLACE FUNCTION`). Applied with `supabase db push` or `supabase migration up`.
- `schema.sql` — **full current schema + RPC snapshot** (`supabase db dump`/`pg_dump --schema-only`). The queryable/redeployable mirror; regenerate after every applied migration so it always matches the live DB.
- `functions/` — RPC/SQL function definitions (also captured in migrations; kept here for easy reading).
- `scripts/` — ad-hoc idempotent SQL the operator runs by hand; once applied + folded into a migration, move it to `scripts/archive/`.
- `QUICK_REFERENCE.md` — fast lookup of tables, keys, and RPCs (hand-maintained).

## Change workflow (STOP-and-wait)
The Supabase MCP is **READ-ONLY** (inspection only). Schema/RPC changes go through reviewed SQL, never the MCP:
1. **Pre-validate** — inspect the live schema via the read-only Supabase MCP (`list_tables`, `execute_sql` SELECTs); verify column names / function signatures against `schema.sql`.
2. **Write an idempotent script** in `scripts/` (re-runnable; `IF NOT EXISTS` / `CREATE OR REPLACE`).
3. **STOP** — ask the operator to run it (`supabase db push`, the SQL editor, or `psql`).
4. **WAIT** — don't proceed until they confirm success.
5. **Integrate** — fold the change into a timestamped `migrations/` file, **regenerate `schema.sql`**, update `QUICK_REFERENCE.md`, and move the ad-hoc script to `scripts/archive/`.

## Query locally / redeploy
- **Query locally:** load `schema.sql` into a local Postgres (`psql -f schema.sql`) or `supabase start` (local stack), then explore. Great for writing/`EXPLAIN`-ing the SQL behind analytical tools without touching the hosted DB.
- **Redeploy from scratch:** `supabase db reset` (local) or apply `migrations/` to a fresh project — the whole `droomzaak` schema + RPCs come back. This is the failover insurance: if the hosted DB or Soda Straw wobbles on stage, you can stand up the same Postgres anywhere and flip `DATA_BACKEND=postgres_direct`.

## Setup
`supabase init` (creates `config.toml`), `supabase link --project-ref $SUPABASE_PROJECT_REF`. Secrets (`SUPABASE_ACCESS_TOKEN`, `SUPABASE_PROJECT_REF`, `SUPABASE_DB_URL`) live in gitignored `.env.demo` — never commit them. See the `supabase-schema-sync` skill for the agent-facing contract.
