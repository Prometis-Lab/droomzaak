# Droomzaak warehouse — quick reference

Hand-maintained lookup for the `droomzaak` schema on Supabase (project `knwnjhbdmmdkqnmakqkr`).
**Live as of 2026-05-30** — 19 tables loaded by `pipelines/droomzaak/load_to_supabase.py`.
Ground truth: `supabase/migrations/` + `supabase/schema.sql`; full join contract + measured hit-rates in
`pipelines/droomzaak/joins.md`. Join keys: **NIS9 statistical sector**, **REFNIS 44021**, **NACE** (5/4/2-digit), **`ent`** (10-digit enterprise no.), **wijk id**.

> The `warehouse-schema-expert` agent reads `migrations/` + `schema.sql` as ground truth and keeps this file in sync. Column-level detail lives in the migration; this is the at-a-glance map.

## Analytical tables (loaded)
| Table | Rows | Key(s) | Feeds | Source / notes |
|---|---|---|---|---|
| `nace_ref` | 3,324 | `nace5` | extract_dream_profile (Q1) | KBO `code.csv`, NACE-BEL 2008; `code_level` = digit count |
| `business_registry` | 36,627 | `ent`, `nace5`, `nis9_code` | Ch2 count / spatial_count | KBO entities flat, 98% geocoded (lon/lat/nis9); `nace5` NULL for ~33% |
| `business_financials` | 34,235 | `ent`, `nace5` | peer_benchmarks_statbel, Tuesday sim | **Belfirst — proprietary, AGGREGATES ONLY**; 1 row/enterprise (`ent` may be NULL) |
| `business_registry_history` | 83,967 | `ent` | Q2 survival/churn | KBO academic — **aggregates only**; establishment-level → aggregate per `ent` before joining (joins.md) |
| `demographics_sector` | 255 | `nis9_code` | score_locations (Q3) | Statbel pop + cars/hh + fiscal income; **absolute cols are NIS8-parent totals — don't re-sum** |
| `housing_price_sector` | 795 | `nis9_code` | rent_benchmark | Statbel IMMO — **sale € PROXY, never per-address**; NIS8-regrained to spine |
| `transit_access_sector` | 197 | `nis9_code` | score_locations / footfall | De Lijn GTFS — `n_stops`, `departures_total` |
| `footfall_sector` | 254 | `nis9_code` | score_locations (Q3) | composite `0.65·transit+0.25·cyclist+0.10·bike_parking` (min-max/sector); cyclist=fietstelpaal 2025, bike=fietsenstallingen. **proxy, not measured** |
| `demand_proxies_sector` | 254 | `nis9_code` | score_locations (Q3) | student study density (UGent bloklocaties): `n_blok_locations`, `study_seats`. tourism/jobs deferred |
| `disruption_events` | 814 | `nis9_code` | score_locations, Ch3 | inname-openbaar-domein + omleidingen (point→sector) |
| `permits_events` | 44,408 | `nis9_code` | permit_checklist_for (evidence) | Omgevingsloket (iioa/kh/gd), clipped to Gent (centroid→sector) |
| `gent_points` | 215 | `nis9_code` | Ch3 context | Gent bedrijvencentra / POI / bloklocaties (point→sector) |
| `peer_vat_nace_empl_gentarr` | 2,608 | `nace5` | peer_benchmarks_statbel | Statbel VAT × size, **arrondissement** Gent (44000) — label geo honestly |
| `peer_bankruptcies` | 5,175 | `nace4` | peer_benchmarks_statbel | Statbel bankruptcies, **municipality** 44021 (4-digit NACE) |
| `peer_starters_flanders` | 10,680 | `nace2` | peer_benchmarks_statbel | Statbel starters, **region** Vlaanderen (02000) — **2-digit** NACE division |
| `geo_sectors` | 254 | `nis9_code`, `wijknr` | joins / map spine | Gent ODS; `geom_wkb` = **WKB bytea** (usable polygons live in the render tier) |
| `geo_wijken` | 25 | `wijknr` | joins / map | Gent ODS; `geom_wkb` = WKB bytea |
| `kbo_geocode` | 93,612 | address 5-tuple → `nis9_code` | build-time geocode bridge | KBO academic — **no redistribution**; intermediate, not a per-question join path |
| `permit_rules` | 12 rules | `permit` (TEXT), `nace_prefix` (TEXT[]), `status` | permit_checklist_for (Q4) | Curated YAML → Parquet → Postgres. `nace_prefix`/`depends_on` are **TEXT[] (Postgres arrays)**; `applies_when`/`cost` are **JSON-encoded TEXT** (parsed in Python, not SQL). GIN index `permit_rules_nace_idx` on `nace_prefix` for `@>`/`&&` containment queries. `status` values: `active`, `ended_2025`. |

## Not yet built (planned — see droomzaak-data-shortlist.md §2 / §5)
| Table | Feeds | Status |
|---|---|---|
| `zoning` | Ch4 "may I open here" | Gewestplan + RUP DSI — **not on disk yet** |
| `subsidies` | subsidies_for | curated; `status: active\|ended_2025` — **not curated yet** |
| `sector_attributes` | Ch1 questions + Ch4 branching | the "company topology" — **not built** |

## RPCs / functions
| Function | Used by | Notes |
|---|---|---|
| _(none yet)_ | | add as migrations land; parameterized; SELECT-only for analytical paths |
