# Droomzaak warehouse — quick reference

Hand-maintained lookup for the `droomzaak` schema on Supabase. **Keep in sync** with `schema.sql` after every migration. Canonical set + sources = `droomzaak-data-shortlist.md` §2 (authoritative). Join keys: **NIS9 statistical sector**, **REFNIS 44021**, **wijk id**.

> Tables below are the planned set — fill in real columns/types as migrations land. The `warehouse-schema-expert` agent reads `migrations/` + `schema.sql` as ground truth and updates this file.

## Analytical tables
| Table | Feeds | Source | Notes |
|---|---|---|---|
| `geo_admin_units` | joins, map | statistische-sectoren + stadswijken | base geometry (sector + wijk) |
| `nace_ref` | extract_dream_profile | KBO `code.csv` + synonyms | code ↔ label ↔ synonyms |
| `demographics_sector_annual` | score_locations | Statbel pop + cars/hh + FOD fiscal income | sector × year |
| `business_registry` | Ch2 count, spatial_count | KBO entities flat | geocoded via prometis_toolkit → lat/lon + NIS9 |
| `business_financials` | peer_benchmarks_statbel, Tuesday sim | **Belfirst** jaarrekeningen | proprietary → **aggregates only** |
| `peer_demography_nace` | peer_benchmarks_statbel | Statbel TF_VAT_NACE_EMPL + TF_BANKRUPTCIES + TF_STARTERS_45 | mixed granularity (label region-only starters) |
| `housing_price_sector` | rent_benchmark | Statbel TF_IMMO_SECTOR (NIS9) | **sale €, a rent PROXY** — never per-address |
| `footfall_sector` | score_locations | composite (see belgian-open-data-ingest) | 0–1; 0.40·transit+0.25·boardings+0.25·telraam+0.10·micro |
| `transit_access_sector` | score_locations | De Lijn GTFS | departures/week aggregated |
| `disruption_events` | score_locations, Ch3 | inname + omleidingen + GIPOD | point + window |
| `permits_events` | permit_checklist_for (evidence) | Omgevingsloket IIOA + kleinhandel | clipped to Gent |
| `zoning` | Ch4 "may I open here" | Gewestplan + RUP DSI | bestemmingscategorie |
| `demand_proxies` | score_locations | kotzones + bloklocaties + POI + buurtmonitor | demand-side weighting |

## Config tables (curated → loaded)
| Table | Feeds | Notes |
|---|---|---|
| `permit_rules` | permit_checklist_for | NACE × attributes → permit + url + cost + lead_time + depends_on |
| `subsidies` | subsidies_for | per scheme; `status: active|ended_2025`; scope/need_type/eligibility flags |
| `sector_attributes` | Ch1 questions + Ch4 branching | the "company topology" (single source of truth) |

## RPCs / functions
| Function | Used by | Notes |
|---|---|---|
| _(none yet)_ | | add as migrations land; parameterized; SELECT-only for analytical paths |
