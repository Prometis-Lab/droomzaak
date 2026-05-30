# Handover — footfall_sector + demand_proxies_sector (warehouse → 18 tables)

**2026-05-30 16:03 · track-a-backend · johannes**

## State now
Two new Q3 `score_locations` analytical tables are **built, loaded live on Supabase, committed, pushed, and PR'd** — nothing half-done on the data side.

- `droomzaak.footfall_sector` (254 rows) — per-sector footfall composite, score 0–0.709, 204/254 non-zero, no NaN.
- `droomzaak.demand_proxies_sector` (254 rows) — student study density (29/254 sectors, 3,791 seats).
- Warehouse is now **18 tables** (was 16). Verified live via the loader DSN.
- **PR #4 open:** https://github.com/Prometis-Lab/droomzaak/pull/4 (`feat/data-pipeline → main`, clean merge, no conflicts).

## What I just did
- Designed + built both tables from on-disk T7 Gent ODS layers, following the `gent_points`/`transit_access` clean-script pattern.
- Applied the DDL to Supabase by reusing `load_to_supabase.resolve_dsn()` + DuckDB `postgres_execute` (the Supabase MCP is `--read-only` in `.mcp.json` and was unauthorized this session — it **cannot** do DDL), then loaded both tables.
- Folded staged DDL into a migration, synced the mirror, shipped via `/ship` (review APPROVED · simplify · security gate exit 0).
- Commit **`96d02a0`** `feat(data): footfall & demand_proxies sector tables` (rebased onto `origin/feat/data-pipeline` `9bdfa2c`, pushed).

## Next concrete step
**Wire the two tables into `score_locations`.** `main` now reads analytical data via the internal **DataGateway** (`backend/app/data_gateway.py`, from the YC-branch PR #3 — `e9f0fcf` "replace Soda Straw with internal DataGateway"), and tools were rewritten against the real warehouse (`f786075`). `score_locations` (`backend/app/droomzaak_tools.py` / `agent_tools.py`) does **not** yet read `footfall_sector` or `demand_proxies_sector` — add those joins on `nis9_code` and surface `footfall_score` + `study_seats` as scoring dimensions.

## Open questions / decisions
- **NMBS station-boardings (the folded 0.25 term):** confirm whether boardings are sourceable for Gent-Sint-Pieters/Dampoort. If yes, un-fold and re-weight to `0.40·transit + 0.25·boardings + 0.25·cyclist + 0.10·bike`. Currently folded into transit (0.65) — documented, not a bug.
- **Footfall weight calibration:** the 4 `druktemeting` pedestrian counters (Korenmarkt/Kouter/Veldstraat) are ground-truth but carry **no coordinates** in their time-series — calibration regression deferred. Weights are taken from shortlist §6 as-is.
- **demand_proxies tourism term:** `toeristische-attracties-visit-gent.geo` is **corrupt** (latitudes read ~2.0); needs address geocoding before it can be added.

## Exact entry points
- Clean scripts: `pipelines/droomzaak/datasets/footfall/clean.py`, `pipelines/droomzaak/datasets/demand_proxies/clean.py`
- Wiring: `pipelines/droomzaak/build.py` (ORDER), `pipelines/droomzaak/load_to_supabase.py` (`TABLES`)
- Schema: `supabase/migrations/20260530154400_add_footfall_demand_tables.sql`, `supabase/schema.sql`, `supabase/QUICK_REFERENCE.md`
- Join contract + all caveats: `pipelines/droomzaak/joins.md` (footfall + demand bullets at the end of "Known caveats")
- Rebuild canonical: `uv run python pipelines/droomzaak/datasets/footfall/clean.py` (needs `transit_access_sector_gent.parquet` first) + `.../demand_proxies/clean.py`
- Re-load to Supabase: `uv run python pipelines/droomzaak/load_to_supabase.py footfall_sector` / `demand_proxies_sector` (DSN from gitignored `.env.demo`)

## Gotchas hit
- **Branch got switched mid-session** (`feat/data-pipeline` → `docs/readme-prd-alignment`), which removed the untracked pipeline scaffolding from the tree. If `_common.py`/`build.py` vanish, you're on the wrong branch — `git checkout feat/data-pipeline`.
- **`fietstelpaal` `totaal` ships ~2% genuine float NaN** (19,008/902,112 across 2025). SQL `sum()` ignores NULL but **propagates NaN** → poisons the cross-sector min-max. Fix is `CASE WHEN isnan(...) THEN NULL` before summing (see `footfall/clean.py` `counts` CTE). Don't remove it.
- **`kotzones` don't discriminate** — the 20 student districts tile the whole municipality, so `in_kotzone` was True for all 254 sectors. Dropped; kept only the bloklocaties signal.
- **Counter time-series have no coordinates** — only a `code`/`locatie` name; coords come from the `fietstelpalen-gent` master layer (~10/12 codes map: `DAZK`/`LOU` have no master row).
- **Supabase MCP can't apply DDL** (`--read-only` flag in `.mcp.json` + no token this session). DDL goes over the Postgres DSN (psql / SQL editor / the loader's own `resolve_dsn()` + `postgres_execute`).

## Verification
```bash
uv run pytest pipelines/droomzaak/tests   # → 6 passed
uv run ruff check pipelines/droomzaak/datasets/footfall pipelines/droomzaak/datasets/demand_proxies  # clean
# live row counts (reads .env.demo DSN; never prints the secret):
uv run python -c "import sys; sys.path.insert(0,'pipelines/droomzaak'); import duckdb, load_to_supabase as l; c=duckdb.connect(); l.attach_postgres(c,l.resolve_dsn()); print({t: c.execute(f'SELECT count(*) FROM pg.droomzaak.{t}').fetchone()[0] for t in ('footfall_sector','demand_proxies_sector')})"
# expected: {'footfall_sector': 254, 'demand_proxies_sector': 254}
```
