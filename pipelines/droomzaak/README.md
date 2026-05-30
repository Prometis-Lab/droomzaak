# pipelines/droomzaak

Cleaning scripts that turn the shortlisted source datasets into small canonical Parquet
tables, plus the loader that pushes them into the Supabase `droomzaak` schema. The join
contract (which keys join what, with measured hit-rates) is in [`joins.md`](joins.md).

The scripts read raw data from the **T7 SSD** (`$MAP_PILOT_DATA_DIR`) and write small
canonical Parquet tables; the loader pushes those into the warehouse. Clean scripts are
added one per source as each table is finalised.

## Layout

```
pipelines/droomzaak/
├── _common.py              # paths, canonical join-key helpers (norm_ent, nace5, lonlat, …)
├── build.py                # run clean scripts in dependency order (edit ORDER as tables land)
├── load_to_supabase.py     # DuckDB → Postgres: load canonical/* into the droomzaak schema
├── joins.md                # the join contract (read this first)
├── datasets/<name>/clean.py# one cleaning script per source
└── tests/                  # monkeypatched — never touch T7 / network / real Supabase

data/canonical/             # outputs (repo-root, gitignored — large + licence-restricted)
```

## Run

```bash
uv sync                                                   # one-time: env + deps

# 1) clean: raw (T7) → data/canonical/*.parquet
uv run python pipelines/droomzaak/build.py                # all, in dependency order
uv run python pipelines/droomzaak/datasets/kbo_entities_flat/clean.py   # one dataset

# 3) load: data/canonical/*.parquet → Supabase droomzaak.*
uv run python pipelines/droomzaak/load_to_supabase.py business_registry
uv run python pipelines/droomzaak/load_to_supabase.py all
```

Raw source data is read from `$MAP_PILOT_DATA_DIR` (default `/Volumes/T7/map-pilot-data`).

## The local → Supabase path (four stages)

How a dataset in any source format becomes data your colleagues can query in Supabase.
**Schema is operator-managed (migrations); data is loader-managed (this code).**

1. **Clean** — `clean.py` reads the raw source from T7 (xlsx/csv/gpkg/shp/parquet) through
   DuckDB, normalizes join keys (`norm_ent`, `nace5`, `lonlat` reproject EPSG:3812→4326),
   filters to Ghent (REFNIS 44021 / postcode 9000–9052), and `write()`s one deterministic
   Parquet to `data/canonical/<stem>.parquet`.
2. **Schema** — hand-write an idempotent migration (`CREATE SCHEMA IF NOT EXISTS droomzaak;`
   + `CREATE TABLE IF NOT EXISTS droomzaak.<table> (…)`), columns **in the clean.py SELECT
   order**. Follow `supabase/README.md` STOP-and-wait: stage the SQL in `supabase/scripts/`,
   the operator applies it (`psql "$SUPABASE_DB_URL" -f …`), then fold it into
   `supabase/migrations/` and regenerate `supabase/schema.sql`. The Supabase MCP is read-only;
   this loader never runs DDL.
3. **Load** — `load_to_supabase.py` `ATTACH`es the Postgres DSN via DuckDB's postgres
   extension and `DELETE`+`INSERT`s the Parquet into the migration-defined table (idempotent
   re-load; `INSERT … SELECT *` is **position-based**). DSN from env (`DROOMZAAK_PG_DSN`,
   else `SUPABASE_DB_URL`) — never hardcoded; use the **direct/session** connection (port
   5432), not the transaction pooler (6543).
4. **Access** — colleagues reach it two ways: the **agent** via Soda Straw → Supabase (the
   product path, `.claude/rules/data-tiers.md`); **devs** via `psql "$SUPABASE_DB_URL"` or
   the read-only Supabase MCP. The table/column contract is documented in
   `supabase/QUICK_REFERENCE.md`.

## Adding a clean script

1. Drop the finished `clean.py` into `pipelines/droomzaak/datasets/<name>/clean.py`
   (it imports `_common` via `parents[2]`, which resolves to the pipeline root).
2. If it needs a new `_common` helper or source constant, add that too.
3. Add `<name>` to `ORDER` in `build.py` in dependency order.
4. Run it → confirm the row count / hit-rate against `joins.md`.
5. Write the table's migration (stage 2) and add it to `TABLES` in `load_to_supabase.py`.

## Status

Built (on-disk sources): `geo_admin`, `kbo_correspondence`, `kbo_entities_flat`
(→ `business_registry_gent`, the proof-of-path table). Loadable: `business_registry`.

To add as each is finalised: `belfirst` (→ `business_financials`), the Statbel
TF_* peers, demographics, immo (rent proxy), De Lijn / GIPOD / zoning, the Gent ODS point
layers, and the curated config (`permit_rules`, `subsidies`, `nace_ref`, `sector_attributes`).

## Licence

`data/canonical/` is gitignored: it holds academic-licence (KBO academic) and proprietary
(Belfirst) derived data — aggregates / client-side only, no raw redistribution.
