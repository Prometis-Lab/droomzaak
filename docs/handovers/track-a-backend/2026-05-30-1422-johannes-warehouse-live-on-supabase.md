# Handover — warehouse LIVE on Supabase (16 tables loaded + verified)

**Track:** track-a-backend · **Author:** johannes · **Branch:** `feat/data-pipeline` · **HEAD:** `e0d6f67` (committed via `/ship`, not pushed)

## State now
- **The Supabase warehouse is live and fully loaded.** Connection blocker from the prior handover is resolved: `SUPABASE_DB_URL` is now the **Session pooler** URI (host `aws-1-…pooler.supabase.com`, user `postgres.knwnjhbdmmdkqnmakqkr`, **port 5432**), in gitignored `.env.demo`. DB password was reset this session (the prior-session leak is invalidated).
- **DDL applied + all 16 tables loaded**, every row count matches source/`joins.md` exactly (read-back verified live): `business_registry` 36,627 · `business_financials` 34,235 · `permits_events` 44,408 · `business_registry_history` 83,967 · `geo_sectors` 254 · (+ the other 11).
- **`/ship` passed** all gates (review APPROVED, simplify, security gate exit 0) and committed the pipeline as `e0d6f67`.

## What I just did
1. Fixed the DSN → `CONNECTED ✓` via a leak-proof probe (reuses `load_to_supabase.resolve_dsn`, never prints the DSN).
2. Applied `supabase/scripts/canonical_tables.sql` via DuckDB `postgres_execute` (the **Supabase MCP is read-only** — `apply_migration` returned "read-only mode", and `list_tables` returned "Unauthorized"; both routes dead this session).
3. Loaded all 16 tables: `uv run python pipelines/droomzaak/load_to_supabase.py all`.
4. `/ship`ped the branch.

## Next concrete step
1. **Schema-sync bookkeeping** (`supabase-schema-sync` skill): fold `supabase/scripts/canonical_tables.sql` into a timestamped `supabase/migrations/`, regenerate `supabase/schema.sql`, fill `supabase/QUICK_REFERENCE.md`. (DDL was applied as a one-off script, not yet a migration.)
2. **Then the real work:** the first Soda-Straw-brokered analytical tool — `peer_benchmarks_statbel` or `score_locations` — per the per-question join paths in `pipelines/droomzaak/joins.md` + `.claude/rules/data-tiers.md`. Use `warehouse-schema-expert` for the SQL, `add-agent-tool` + `soda-straw-data-tool` skills for the wiring.

## Open questions / blockers
- **🔴 Sub-agent committed autonomously during `/ship`** — a Bash-capable reviewer agent (likely `security-reviewer`, runs last) ran `git commit` itself (created `821dacb`, which I amended to `e0d6f67`), violating `.claude/rules/git-operations.md`. No harm this time, but the three reviewer agents are *described* read-only yet have `Bash`, so nothing mechanically stops it. **Proposed fix (not yet applied):** add an explicit "never `git add/commit` — you are a `/ship` sub-stage, return findings only" guard to `code-reviewer`/`code-simplifier`/`security-reviewer` agent defs.
- **Supabase MCP unusable this session** (read-only + token unauthorized). To use it for inspection later: set `SUPABASE_ACCESS_TOKEN` and drop `--read-only`. Not blocking — the loader's `resolve_dsn`/DuckDB path is the reliable route. Re-probe before trusting it (see the new `external-service-state-is-ephemeral` memory).
- **Uncommitted, owned by another session:** `.claude/skills/writing-handovers/SKILL.md` + the `~/.claude/.../memory/` retro edits — another Claude is finishing those; don't commit them here.

## Exact entry points
- Loader: `pipelines/droomzaak/load_to_supabase.py` — `TABLES` (16), `resolve_dsn()`, `SELECT_LIST` (geo→bytea).
- DDL: `supabase/scripts/canonical_tables.sql`. Join contract + measured rates: `pipelines/droomzaak/joins.md`.
- Leak-proof connection probe (inline, reusable):
  ```bash
  uv run python -c "
  import duckdb, sys; sys.path.insert(0,'pipelines/droomzaak')
  from load_to_supabase import attach_postgres, resolve_dsn
  con=duckdb.connect()
  try:
      attach_postgres(con, resolve_dsn())
      print('CONNECTED ✓', con.execute(\"SELECT * FROM postgres_query('pg','select current_database()')\").fetchone()[0])
  except Exception as e: print('FAILED →', type(e).__name__, '(DSN not printed)')
  "
  ```

## Gotchas hit
- **Supabase Table Editor defaults to the `public` schema** → switch the schema dropdown to **`droomzaak`** or it looks empty.
- **MCP write tools are *listed* but the server is read-only** — a tool appearing in the schema ≠ the server permitting it. Don't trust a prior handover's "MCP has write access" claim; re-probe.
- DDL applied fine via DuckDB `CALL postgres_execute('pg', <full sql file>)` — multi-statement in one call works.

## Verification
- `git show -s --oneline HEAD` → `e0d6f67 feat(data): cleaning pipeline + warehouse staging`.
- Live read-back (the probe above + `SELECT count(*) FROM droomzaak.business_registry` → 36,627).
- `uv run pytest pipelines/droomzaak/tests -q` → 6 passed · `uv run ruff check pipelines/droomzaak/` → clean.
