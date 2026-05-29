# Per-source ingest patterns (reference)

## OpenDataSoft v2.1 (`sources/ghent.py`)

Base: `https://data.stad.gent/api/explore/v2.1`.
- List: `GET /catalog/datasets?limit=100&offset=0` (paginate on `total_count`).
- Metadata: `GET /catalog/datasets/{id}`.
- Records: `GET /catalog/datasets/{id}/records?limit=100&offset=n` (100 max/page).
- GeoJSON export: `GET /catalog/datasets/{id}/exports/geojson?timezone=Europe/Brussels&lang=nl`.
- Timeouts: 60s catalogue/metadata, 120s export.
- Strip HTML from descriptions. Normalize `metas.default.*_nl` with English fallback. Themes can be string or list.
- Geometry fallback chain (see SKILL trap 5).

## Statbel ZIP (`sources/statbel.py`)

- `download_zip(file_name, url, raw_dir)` — idempotent (skip if exists and size>0).
- `iter_pipe_zip_rows(path)` — open ZIP, find `.txt`/`.geojson` entry by extension, decode UTF-8-sig→CP1252, `csv.DictReader(delimiter="|")`.
- `sector_suffix(code, refnis="44021")` — strip the REFNIS prefix to get the 4-digit suffix; index lookups on BOTH full code and suffix.
- `sector_geometry_lookup(...)` — dict keyed on `sectorcode`/`cd_sector`/`CD_SECTOR`/`statsec` (case-insensitive) + suffix.
- Reproject: Lambert 2008 (3812) sectors, Lambert 72 (31370) accident points → WGS84 (4326), `pyproj.Transformer(always_xy=True)`.
- Collections: `build_population_collection` (density = pop/area_km²), `build_cars_collection` (cars/household), `build_accidents_collection` (reproject points). Filter rows to REFNIS; skip rows with missing geometry; return only non-empty collections.
- Four shipped datasets: statistical sectors 2025, population, cars/household 2024, road accidents 2024.

## FOD Financiën (`sources/fod.py`)

- No API — operator drops files into `fod_data/` (`FOD_DATA_DIR`). Discover by exact name then `glob("**/{name}")`.
- DuckDB parse: `LOAD excel;` then `SELECT … FROM read_xlsx(?) WHERE CD_MUNTY_REFNIS=? AND CD_YEAR=?`; CSV via `read_csv(?, delim=';', all_varchar=true) WHERE NISCode LIKE '44021%'`.
- Income (≤2023) → 2024 sector geometries; transactions (2024) → 2025. Reuses the Statbel ZIP download + parse to get both vintages.
- Transactions aggregate to one row/sector with P25/P50/P75 by parcel type (house/apt/land).

## Enrichment (`sources/enrichment.py`)

- Runs AFTER ghent+statbel. Loads cached district + sector GeoJSON, STRtree over districts, centroid-in-polygon to aggregate sector populations into wijken: adds `population_total`, `area_km2` (equirectangular at centroid lat, 111 km/deg), `population_density_km2`. Idempotent (checks fields exist first).

## Storage (`storage.py`)

- Single `CatalogStore` over DuckDB at `data/catalog.duckdb`, per-instance `RLock` (DuckDB holds an OS-level exclusive lock; needed on Windows).
- JSON columns stored as text (`*_json`), round-tripped via `dumps`/`loads`.
- Tables: `datasets`, `layer_cache`, `layer_context_cache`, `map_layer_state`, `map_annotations`, `agent_debug_runs`, `agent_sessions`, `agent_catalogue_cache`, `dataset_embeddings`, plus usage/problem-report tables.
- Semantic search: `intfloat/multilingual-e5-small` (384-dim), `passage:`/`query:` prefixes, vectors as float32 BLOBs, process-global matrix cache invalidated on upsert.

## Ingest CLI (`ingest.py`)

`python -m backend.app.ingest --seed` runs: fetch Ghent catalogue → seed selection → cache small layers → Statbel → FOD → enrich wijken → build cheat sheets → invalidate catalogue cache → embed. Flags: `--no-statbel`, `--no-fod`, `--no-layer-cache`, `--no-embeddings`, `--reembed`, `--no-cheat-sheets`, `--rebuild-cheat-sheets`. Cold ~5–15 min; re-runs near-zero if unchanged.
