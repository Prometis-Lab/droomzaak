---
name: belgian-open-data-ingest
description: Use when sourcing, clipping, or joining a Belgian open dataset for Droomzaak — adding an OpenDataSoft / Statbel / FOD Financiën source, clipping to Ghent, joining to statistical sectors, geocoding KBO/Belfirst, or loading a canonical warehouse table. Encodes REFNIS 44021 filtering, the 2024-vs-2025 sector-vintage rule, CRS reprojection, encoding fallbacks, centroid-in-polygon joins, the footfall composite formula, the prometis_toolkit geocoder, and subsidy status flags.
---

# Ingesting Belgian open data

Build the ingest layer (`ingest.py` + `sources/*.py` + `storage.py`). Adding/clipping a dataset is a known recipe with traps that silently produce empty or mis-joined layers. **Rigid on the traps**, flexible on structure.

> Per-source patterns (ODS / Statbel ZIP / FOD local file) with code-level detail are in `reference/source-patterns.md`. Canonical warehouse tables + sources live in `droomzaak-data-shortlist.md` §2 (authoritative — overrides the older PRD names). The data-shortlist cites a `phase1_gent_entrepreneur.md` ingest doc that is **not in this repo**; use it only if provided.

## Pick the source shape
- **OpenDataSoft v2.1** (`data.stad.gent`) → `sources/ghent.py` pattern (catalogue → metadata → records/GeoJSON export).
- **Statbel** (sectors, demographics, cars, VAT/faillissementen/starters, immo) → `sources/statbel.py` pattern (ZIP download, in-archive parse, REFNIS filter, reproject).
- **FOD Financiën** (income, real-estate transactions) → `sources/fod.py` pattern (operator drops files locally, DuckDB reads XLSX/CSV).
- **WAF-blocked / JS-rendered** (VLAIO `vlaio.be` 403, VLAREM-wegwijzer) → **do not `WebFetch`**; use the `browser-data-curation` skill (Claude-in-Chrome MCP) or hand-pick static JSON.

## The traps (silent failures)
1. **REFNIS 44021** = Ghent. Filter every Statbel/FOD row by it.
2. **Sector vintage 2024 vs 2025.** Income (≤2023, e.g. fiscal income) → **2024** geometries; 2024 data (e.g. transactions) → **2025**. Pre-download both vintages; match on full code AND 4-digit suffix.
3. **CRS.** Statbel sectors = Lambert 2008 (EPSG:3812), accidents = Lambert 72 (EPSG:31370) → reproject to WGS84 (EPSG:4326), `pyproj`, `always_xy=True`, transformers built once.
4. **Encoding.** Statbel ZIPs are pipe-delimited; UTF-8-sig then CP1252.
5. **Geometry fallback (ODS).** Walk `geometry.geometry` → `geo_shape.geometry` → `geo_point_2d` → `geopoint` → lat/lon columns.
6. **Geo-join.** Centroid-in-polygon via Shapely `STRtree.query` (candidates) + `.covers()` (exact). Fill 0 for unmatched. **Print the match rate** — a low rate usually means a vintage or REFNIS mistake.
7. **Cache threshold.** Layers ≤ `MAX_CACHEABLE_FEATURES` (2500) pre-fetched to GeoJSON for the render tier; larger sampled (500) for cheat sheets.

## Geocoding — inherited `prometis_toolkit` (RESOLVED, data-shortlist §10)
Geocode KBO `business_registry` + Belfirst `business_financials` with the inherited toolkit (`inherited/`, gitignored): address → lat/lon + full NIS hierarchy incl. **NIS9 sector** + confidence (bundled BeSt centroids). Vague place-names ("Vrijdagmarkt") fall back to Nominatim `geocode`. `geo_core` also gives NIS9 centroids for `score_locations` distance maths.

## Data corrections (data-shortlist overrides PRD)
- **Peer financials = Belfirst** (`business_financials`, proprietary → aggregate per sector/wijk, never per-company on the founder path). CBSO deferred to V2.
- **Rent = `housing_price_sector`** (Statbel `TF_IMMO_SECTOR`, **sale-€ proxy**, NIS9) — label it; never per-address.
- **Footfall `footfall_sector`** = `0.40·transit_access + 0.25·station_boardings + 0.25·telraam_measured + 0.10·micromobility`, normalized 0–1 (fold Telraam's weight into transit if no token). Calibrate against on-disk druktemeting (Korenmarkt/Kouter/Veldstraat) + fietstelpaal ground-truth.
- **Subsidies `status`** — many Stad Gent premies cancelled for 2026; encode `status: active|ended_2025` so cancelled ones render greyed-out (demo reads as current, not stale).

## Cheat sheets
After loading, build a per-field profile (top values, distinct count, min/max, operators); drop `top_values` for unique-IDs and opaque content. This is what the agent reads to plan — don't skip it.

## Warehouse note
Analytical target = **Postgres** (`droomzaak` schema), loaded Friday from DuckDB/Parquet dumps, reached only via Soda Straw. Render tier stays DuckDB+GeoJSON. Keep the tiers separate (`rules/data-tiers.md`).

## Verify
uv only · idempotent re-ingest (size-check downloads, freshness-check cheat sheets) · **never reach real APIs from tests — monkeypatch `httpx`** · print every geo-join match rate.
