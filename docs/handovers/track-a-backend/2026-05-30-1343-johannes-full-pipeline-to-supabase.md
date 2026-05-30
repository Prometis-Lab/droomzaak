# Handover — full cleaning pipeline ported + 16-table Supabase warehouse staged

**Track:** track-a-backend · **Author:** johannes · **Branch:** `feat/data-pipeline` (not committed yet — working tree changes)

## State now
- **All 13 cleaning scripts ported + built end-to-end** from T7 → gitignored `data/canonical/*.parquet`. `uv run python pipelines/droomzaak/build.py` produces **16 canonical tables**, and **every row count matches `joins.md` exactly** (business_registry 36,627 · financials 34,235 · permits 44,408 · history 83,967 · 254 sectors · etc.). Verified 2026-05-30.
- **Supabase load fully staged for 16 tables** but **NOT applied/loaded yet** — one blocker (see below): the `SUPABASE_DB_URL` is the *Direct* (IPv6-only) URI and doesn't resolve.
  - DDL: `supabase/scripts/canonical_tables.sql` (idempotent, all 16 tables + indexes). DDL↔parquet column counts cross-checked — **all 16 match** (position-based INSERT contract holds).
  - Loader: `load_to_supabase.py` `TABLES` extended 1→16; geo spine ships `geom_wkb` as `bytea` via `ST_AsWKB` (`SELECT_LIST`); `resolve_dsn()` hardened to skip non-URI values. Tests **6/6**, ruff clean.
- **Project confirmed:** Supabase MCP connects to project **`knwnjhbdmmdkqnmakqkr`** (empty `public`+`droomzaak` — clean dedicated Droomzaak project). The MCP is the *read-only inspection* path; the **loader writes via `SUPABASE_DB_URL`**, which is separate and still needs fixing.

## What I just did
- Ported the friend's verified pipeline from `~/Desktop/Map-Pilot-v2/data/droomzaak/` into `pipelines/droomzaak/`: 10 new `datasets/*/clean.py` + overwrote the 3 existing with the **corrected** versions (the old port was missing two load-bearing fixes — `kbo_entities_flat` now `left(nace5,5)` truncates `NACEMain`; `_common.norm_ent` now `nullif(...,'')`; `_common.load_sectors` now `geom_wkb AS geom` per the friend's advice). Updated `build.py` ORDER (13), ported `joins.md`.
- Generated `supabase/scripts/canonical_tables.sql` from the built parquet schemas; archived the now-superseded `supabase/scripts/business_registry.sql` → `scripts/archive/`.
- Extended + hardened `load_to_supabase.py`; added 2 `resolve_dsn` tests.

## Next concrete step (cold-start ready)
1. **Fix `SUPABASE_DB_URL`** (only blocker): it's currently the **Direct** URI (`db.knwnjhbdmmdkqnmakqkr.supabase.co`, user `postgres`) which is IPv6-only → "could not translate host name". Replace with the **Session pooler** URI from the dashboard (Connect → Session pooler): host `aws-1-<region>.pooler.supabase.com`, user `postgres.knwnjhbdmmdkqnmakqkr`, **port 5432** (not 6543), URL-encoded password. Leave `DROOMZAAK_PG_DSN` blank.
2. **Verify** (read-only): re-run the probe — it should print `CONNECTED ✓` and `matches knwnjhbdmmdkqnmakqkr: True`.
3. **Apply DDL** (STOP-and-wait — operator runs, per CLAUDE.md rule 11; MCP is read-only):
   `psql "$SUPABASE_DB_URL" -f supabase/scripts/canonical_tables.sql`
4. **Load:** `uv run python pipelines/droomzaak/load_to_supabase.py all`
5. **Smoke test:** `SELECT count(*) FROM droomzaak.business_registry;` → 36,627. Then fold `canonical_tables.sql` into a timestamped `supabase/migrations/`, regenerate `supabase/schema.sql`, fill `supabase/QUICK_REFERENCE.md` (supabase-schema-sync skill).
6. **The actual work** then begins on top of this warehouse: the Soda-Straw-brokered analytical tools (`peer_benchmarks_statbel`, `score_locations`, `permit_checklist_for`, demographics) per the per-question join paths in `joins.md` + `.claude/rules/data-tiers.md`.

## Open questions / blockers
- **🔴 Rotate the DB password.** The project password for `knwnjhbdmmdkqnmakqkr` was **printed twice** in this session (DuckDB connection errors echo the full DSN). Reset it: dashboard → Settings → Database → Reset (this also hands you the correct Session pooler URI). My probe is now leak-proof (classifies errors without printing the DSN), but the exposed value must be invalidated.
- **Other live keys** in `.env.demo` (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) + `SODA_STRAW_TOKEN` in `.claude/settings.local.json` — rotate after the event (gitignored, never committed).
- **MCP write tools are available** (`apply_migration`, `execute_sql`) because the added MCP isn't `--read-only`. Project rule 11 still says **stage + operator-apply, never DDL via MCP** — followed here.

## Exact entry points
- Build all: `MAP_PILOT_DATA_DIR=/Volumes/T7/map-pilot-data uv run python pipelines/droomzaak/build.py`.
- Loader: `load_to_supabase.py` — `TABLES` (`:39`) 16 tables; `SELECT_LIST` (`:63`) geo→bytea; `resolve_dsn` (`:69`).
- DDL: `supabase/scripts/canonical_tables.sql`. Join contract + measured rates: `pipelines/droomzaak/joins.md`.
- Source pipeline (reference only, not this repo): `~/Desktop/Map-Pilot-v2/data/droomzaak/`.

## Gotchas hit
- **The old droomzaak port was stale** — missing the `left(nace5,5)` NACE-truncation + `norm_ent` nullif fixes. Always port from `Map-Pilot-v2/data/droomzaak/` (the friend's verified, measured version), then re-verify counts against `joins.md`.
- **DuckDB connection errors echo the DSN** (password included). Never print `str(exception)` from an `ATTACH` — classify the error instead.
- **Supabase Direct host is IPv6-only** → use the Session pooler (5432) for the load; **never the 6543 transaction pooler** (breaks bulk loads).
- `13 scripts → 16 tables` (geo_admin emits 2, statbel_peers emits 3). `kbo_geocode_gent` is a build intermediate (academic, no-redistribution) — included per the load-scope decision.
- Geo `geom_wkb` reads back as native `GEOMETRY` (GeoParquet auto-decode), stored as `bytea` in PG (no PostGIS dep) — the one path not yet tested against the live DB.

## Verification
- `uv run pytest pipelines/droomzaak/tests -q` → 6 passed.
- `uv run ruff check pipelines/droomzaak/` → clean.
- `uv run python pipelines/droomzaak/build.py` → 16 tables, counts match `joins.md`.
- DDL↔parquet column-count cross-check (in this session) → all 16 ✓.
- Connection probe → currently `CONNECT FAILED → DNS` (the Direct-URI blocker above); will flip to `CONNECTED ✓` once the pooler URI is set.
