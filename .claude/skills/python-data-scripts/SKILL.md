---
name: python-data-scripts
description: Use when writing or fixing a Python data-manipulation script for Droomzaak — pandas/geopandas/shapely/pyproj transforms, DuckDB queries, GeoParquet I/O, geo clip/join to Ghent sectors, the dump_duckdb_to_postgres job, or any ETL/analysis script. Enforces strict uv-managed virtualenvs, idempotency, CRS correctness, and monkeypatched (never-live) tests. Use when the user mentions a Python script, pandas, geopandas, DuckDB, or "data manipulation".
---

# Python data scripts (Droomzaak)

The deterministic contract for any Python data script. Rigid on the uv rule, CRS correctness, idempotency, and test isolation; flexible on structure. For the agent that drives this, use `python-data-engineer`; for sourcing traps, `belgian-open-data-ingest`; for SQL/schema, `warehouse-schema-expert`.

## 1. uv-managed virtualenv — STRICT (the one rule we never bend)
```bash
uv venv && uv sync            # create + install from pyproject.toml + uv.lock
uv add geopandas duckdb       # runtime dep   (uv add --dev pytest ruff for dev)
uv run python scripts/x.py    # run a script
uv run pytest                 # run tests
uv run python -c "import duckdb"   # one-liner
```
**Never** `pip install`, **never** bare `python`/`python3`, **never** a manual `venv`/`virtualenv`/conda. Commit `uv.lock`. Deps are authoritative in `pyproject.toml`.

## 2. CRS correctness (the silent-wrong-answer trap)
- Verify `gdf.crs` before any spatial op; if missing, **fail loudly** (don't assume).
- Reproject explicitly: `gdf.to_crs(31370)` for metric math (area/length/buffer/distance), `to_crs(4326)` only for web output. Belgian sources ≈ EPSG:31370 (Lambert 72) / 3812 (Lambert 2008); web ≈ 4326.
- pyproj transformers built once, `always_xy=True` (lon/lat axis-order trap).

## 3. Geo clip/join to Ghent statistical sectors
Same CRS first → `make_valid`/`buffer(0)` invalid geometry → `sjoin`/`sjoin_nearest` with explicit `predicate` → explicit sector key, dedupe many-to-one. Centroid-in-polygon: Shapely `STRtree.query` (candidates) + `.covers()` (exact); fill 0 for unmatched; **print rows-matched / rows-in**.

## 4. DuckDB ↔ pandas / GeoParquet
Heavy aggregation/joins in DuckDB SQL; `duckdb.sql(q).df()` to pandas; `con.register("name", df)` to expose a frame. `INSTALL spatial; LOAD spatial;` for geo; prefer **GeoParquet** between DuckDB and geopandas over pushing big geometries through pandas. Parameterize SQL.

## 5. Idempotent & re-runnable
Deterministic outputs · `CREATE OR REPLACE TABLE` / upsert · atomic writes (temp + rename) · explicit input→output paths. Mark the one-shot `dump_duckdb_to_postgres` as a one-time migration, idempotent.

## 6. Tests never touch the network (monkeypatch-first)
The network fetch is one injectable seam → `monkeypatch.setattr(...)` to a trimmed fixture → assert parsing/transform, not live data. Keep a small fixtures dir of sample responses. `uv run pytest`.

## 7. Two-tier boundary
Render tier (DuckDB + GeoJSON) → map only. Analytical tier (Postgres) → agent only via the DataGateway (`.claude/rules/data-tiers.md`). Scripts land/curate data; they aren't the agent's runtime read path.

## Checklist
- [ ] All commands via `uv run` / `uv add` / `uv sync`; `uv.lock` committed; no pip / bare python
- [ ] CRS verified + explicit reprojection; metric math in 31370, not 4326
- [ ] Geo-join prints a match rate; invalid geometry fixed first
- [ ] DuckDB for heavy SQL; GeoParquet for geo I/O; SQL parameterized
- [ ] Script idempotent (re-run safe); atomic writes
- [ ] Test monkeypatches the network; `uv run pytest` green

> See also (MIT, can be vendored if the team wants more boilerplate): `wshobson/agents` skills `uv-package-manager` + `python-testing-patterns`. Our skill already covers the load-bearing bits for the Droomzaak stack.
