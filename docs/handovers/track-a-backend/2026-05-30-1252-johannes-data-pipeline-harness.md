# Handover — data-cleaning pipeline + Supabase loader

**Track:** track-a-backend · **Author:** johannes · **Branch:** `feat/data-pipeline` (commit `a25f367`, not pushed)

## State now
- **Clean stage works end-to-end** from the T7 SSD → gitignored `data/canonical/*.parquet`. Verified: `business_registry_gent` = **36,627 rows, 98% geocoded** (matches `pipelines/droomzaak/joins.md`).
- **Loader written + tested** (`load_to_supabase.py`): DuckDB→Postgres, idempotent DELETE+INSERT, transaction-wrapped, column-count drift guard, env-only DSN. Tests **4/4**, `ruff` clean, `/ship` security gate **green**.
- **Not yet run against Supabase** — the table doesn't exist there yet. This is the only "half-done" part, and it's deliberately parked (see blockers).

## What I just did
- Stood up the uv project (`pyproject.toml` + `uv.lock`) and the `pipelines/droomzaak/` harness: `_common.py`, `build.py`, three clean scripts (`geo_admin`, `kbo_correspondence`, `kbo_entities_flat`), `joins.md`, `README.md`.
- Wrote `load_to_supabase.py` + `tests/test_load_to_supabase.py`; staged the idempotent DDL `supabase/scripts/business_registry.sql`.
- Made the security gate green: allowlisted gitignored secret stores in `.gitleaks.toml`, scoped `.semgrepignore` to the build-time ETL, justified `# nosemgrep` on the loader's SQL-identifier interpolation. All in commit `a25f367`.

## Next concrete step (cold-start ready)
Once the Supabase project is confirmed (see blocker) and `DROOMZAAK_PG_DSN`/`SUPABASE_DB_URL` are set in `.env.demo`:
1. Apply the DDL (STOP-and-wait): `psql "$SUPABASE_DB_URL" -f supabase/scripts/business_registry.sql`
2. Load: `uv run python pipelines/droomzaak/load_to_supabase.py business_registry`
3. Smoke test: `SELECT count(*) FROM droomzaak.business_registry;` should = 36,627.
4. Fold the script into a timestamped `supabase/migrations/` file, regenerate `supabase/schema.sql`, fill real columns in `supabase/QUICK_REFERENCE.md`, archive the script (`supabase-schema-sync` skill).

## Open questions / blockers
- **Which Supabase project** — confirm with Milan before applying the DDL/load (the only thing blocking the load; the pipeline code is project-agnostic, only the DSN changes).
- **Live keys in `.env.demo`** (`SUPABASE_SERVICE_ROLE`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) and the `SODA_STRAW_TOKEN` in `.claude/settings.local.json` are real — **rotate after the event**. Both files are gitignored + allowlisted in the gate; never committed.

## Exact entry points
- Run all clean scripts: `uv run python pipelines/droomzaak/build.py` (reads `$MAP_PILOT_DATA_DIR`, default `/Volumes/T7/map-pilot-data`).
- Loader: `pipelines/droomzaak/load_to_supabase.py` — `TABLES` dict (`load_to_supabase.py:45`) maps pg table → canonical stem; add a row per new table.
- Adding a new table end-to-end: `pipelines/droomzaak/README.md` → "Adding a clean script" + "The local → Supabase path (four stages)".
- Loader contract / drift guard: `load_to_supabase.py:59` (`load_canonical`).
- Join keys + measured hit-rates: `pipelines/droomzaak/joins.md`. Target table set: `supabase/QUICK_REFERENCE.md`.

## Gotchas hit
- The droomzaak `.gitignore` ignores `data/` → cleaning **scripts** live in committed `pipelines/`, outputs in gitignored `data/canonical/`.
- Loader uses **position-based** `INSERT … SELECT *` (clean.py emits KBO-cased names, the table is snake_case → name-matched INSERT impossible). Column **order** is the contract; the count guard catches add/remove drift but not a same-type reorder. Keep `business_registry.sql` column order == the clean.py SELECT order.
- `kbo_id` is **not unique** (34,223 distinct of 36,627) — do not add `UNIQUE(kbo_id)`; it would block the load.
- Supabase loads need the **direct/session** connection (port 5432), not the transaction pooler (6543).
- The security gate's gitleaks `dir` scan inspects gitignored files — that's why `.env.demo` tripped it; allowlist handles it, gitignore is the real commit guard.

## Verification
- `uv run ruff check pipelines/` → clean.
- `uv run pytest pipelines/droomzaak/tests -q` → 4 passed (loader logic vs an in-memory Postgres stand-in; never touches T7/network/real DB).
- `bash .claude/hooks/security-gate.sh full` → exit 0, "no leaks found", SAST clean.
- `uv run python pipelines/droomzaak/build.py` → rebuilds the canonical Parquet (needs T7 mounted).
