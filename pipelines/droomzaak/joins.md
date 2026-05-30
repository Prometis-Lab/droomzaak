# Droomzaak join contract

How the shortlisted datasets join, per PRD question. Every fact here is verified on
disk (2026-05-29) — hit-rates are measured, not assumed. The cleaning scripts under
`datasets/<name>/clean.py` produce canonical tables that already carry these keys.

## Canonical join keys (the spine)

| Key | Canonical form | Produced by | Notes |
|---|---|---|---|
| `nis9_code` | 9-char sector, e.g. `44021A32K` | `_common` (correspondence as-is; Statbel `CD_REFNIS‖CD_SECTOR`; Gent geom `'44021'‖sectorcode`) | the spatial spine |
| `refnis5` | `44021` (Gent) | `nis5_code` / `CD_REFNIS` | municipality-level Statbel joins |
| `wijknr` | district number | Gent sector geom ↔ stadswijken | both carry `wijknr` |
| `ent` | 10 digits, e.g. `0857474555` | `norm_ent()` = strip non-digits | KBO dots, Belfirst spaces, VAT `BE` prefix all collapse here |
| `nace5` | undotted 5-digit, e.g. `56101` | `nace5()` = strip dots | ⚠️ config writes `56.101`; data is `56101` |
| address 5-tuple | `(street, house_nbr, box, postal, city)` | raw KBO address cols | NULL-safe join (`box` mostly NULL) |
| `lon`/`lat` | WGS84 | `lonlat()` reprojects EPSG:3812→4326 | correspondence ships Lambert x/y, **not** lat/lon |

## Format mismatches that need cleaning (verified)

| Join | Raw formats | Fix |
|---|---|---|
| enterprise number | KBO `0857.474.555` · Belfirst `0420 383 548` · VAT `BE1002284469` | `norm_ent` → 10 digits |
| NACE | KBO `NACEMain`=`84119` · Belfirst `10711` (aligned) · config `56.101` (dotted) | `nace5` undot |
| sector code | corresp `44021A32K` · Statbel split `44021`+`A32K` · Gent geom suffix `A32K` | build 9-char form |
| coordinates | corresp `x/y` EPSG:3812 | reproject → lon/lat |

## The geocoding chain (the part that needed care)

The geocode correspondence is **deduplicated unique addresses → x/y/nis9**, built from
the *academic* extract and keyed by the address columns. Two routes were measured:

- **Direct (used for `business_registry_gent`):** flat's own address → correspondence on
  `(street, house_nbr, postal, city)` = **98.0%**. Resolves each row to its real trading
  address (correspondence unions enterprise + establishment addresses).
- **VAT chain (for the historical layer):** public ──VAT(99.6%)──► academic ──address(94.8%)──►
  correspondence. Correct for *history/financials* where only the academic extract has the
  data, but **collapses establishments onto the enterprise seat** → only ~70% for the current
  layer. So: geocode current data by address; use `ent`/VAT only to link financials + history.

## Per-question join paths

| PRD step | Tables | Join |
|---|---|---|
| Q1 dream→NACE | `nace_ref` (KBO `code.csv`) | label↔`nace5`; live geocode for the anchor |
| Q2 count peers | `business_registry_gent` | filter `nace5`, already geocoded (`lon/lat/nis9_code`) |
| Q2 financials | `business_registry_gent` ⋈ `business_financials_gent` | `USING(ent)` — 17,373 enterprises matched (Belfirst vintage gap) |
| Q2 growth/bankruptcy | `peer_starters_flanders` (region, **`nace2`** = `left(firm.nace5,2)`) · `peer_bankruptcies_gent` (muni, `nace4` = `left(firm.nace5,4)`) · `peer_vat_nace_empl_gentarr` (arrond., `nace5`+size) | by NACE key at the cube's own level |
| Q3 scoring | demographics/income/rent-proxy | `nis9_code` |
| Q3 competition/footfall/disruption | KBO points · druktemeting/parking · inname/GIPOD | **spatial** (point-in-polygon to sector) |
| Q4 permits/subsidies | `permit_rules`, `subsidies` (curated) | `nace5` + attributes |
| Q4 evidence/zoning | omgevingsloket · gewestplan/RUP | **spatial** clip to candidate point/sector |

## Measured merge rates (audited 2026-05-30)

Final observation counts when the relevant tables are linked per question. Numbers are
the live merge against the canonical outputs, not estimates.

| Question | Merge | Rate |
|---|---|---|
| Q1 | firm `nace5` → `nace_ref` label | 24,455 / 36,627 firms (**67%**; **100%** of firms that *have* a NACE) |
| Q2 | enterprises ⋈ `business_financials_gent` on `ent` | 17,373 / 34,223 (**51%**) — Belfirst vintage gap |
| Q2 | enterprises ⋈ `business_registry_history_gent` on `ent` | 21,546 / 34,223 (**63%**) |
| Q2 | firms → `peer_vat_nace_empl_gentarr` on `nace5` | 19,289 / 36,627 (**53%**; 79% of firms-with-NACE) |
| Q2 | firms → `peer_bankruptcies_gent` on `nace4` | 20,340 / 36,627 (**56%**) |
| Q2 | firms → `peer_starters_flanders` on `nace2` | 24,455 / 36,627 (**67%**; **100%** of firms-with-NACE) |
| Q3 | sectors with demographics (income) | 223 / 254 (**88%**) |
| Q3 | sectors with housing-price proxy | 108 / 254 (**43%**, via NIS8 re-grain) — remaining gap is Statbel median suppression in low-transaction sectors |
| Q3 | sectors with transit access | 197 / 254 (**78%**) |
| Q3 | sectors with disruption events | 173 / 254 (**68%**) |
| Q3 | sectors with permits | 239 / 254 (**94%**) |
| Q3 | sectors with gent-points | 71 / 254 (**28%**) |
| Q3 | sectors with **all of** income + transit + price | 96 / 254 (**38%**) |
| Q4 | permit events placed in a sector | 33,913 / 44,408 (**76%**) |

The Q2 NACE-keyed rates are now capped only by the 33% of firms with no NACE at all (the
`NACEMain` truncation fix resolved the rest). The Q3 spine is 254 sectors; demographics
covers all 254 (income 223) and housing price 108 (the rest is Statbel suppression) — so
location scoring is dense.

## Canonical outputs (in `canonical/`, gitignored)

| File | Rows | Key(s) | Licence |
|---|---|---|---|
| `kbo_geocode_gent.parquet` | 93,612 | address 5-tuple → `lon/lat/nis9_code/capakey` | academic — no redistribution |
| `business_registry_gent.parquet` | 36,627 (98% geocoded) | `ent`, `nace5`, `nis9_code`, `lon/lat` | open (KBO) + academic-derived coords |
| `business_financials_gent.parquet` | 34,235 | `ent`, `nace5` | Belfirst — proprietary, aggregates only |
| `geo_sectors_gent.parquet` | 254 | `nis9_code`, `wijknr` (+ `geom_wkb`) | open (Gent ODS) |
| `geo_wijken_gent.parquet` | 25 | `wijknr` (+ `geom_wkb`) | open (Gent ODS) |
| `nace_ref.parquet` | 3,324 | `nace5` → `label_nl`/`label_fr` | open (KBO) |
| `demographics_sector_gent.parquet` | 255 | `nis9_code` | open (Statbel) |
| `peer_vat_nace_empl_gentarr.parquet` | 2,608 | `nace5` × size, arrondissement 44000 | open (Statbel) |
| `peer_bankruptcies_gent.parquet` | 5,175 | `nace4`, municipality 44021 | open (Statbel) |
| `peer_starters_flanders.parquet` | 10,680 | **`nace2`** (2-digit division), region 02000 | open (Statbel) |
| `housing_price_sector_gent.parquet` | 795 | `nis9_code` (sale-€ proxy, NIS8-regrained to spine) | open (Statbel) |
| `transit_access_sector_gent.parquet` | 197 | `nis9_code` (stop→sector) | open (De Lijn GTFS) |
| `disruption_events_gent.parquet` | 814 | `nis9_code` (point→sector) | open (Gent ODS) |
| `permits_events_gent.parquet` | 44,408 | `nis9_code` (centroid→sector) | open (Omgevingsloket) |
| `gent_points_gent.parquet` | 215 | `nis9_code` (point→sector) | open (Gent ODS) |
| `business_registry_history_gent.parquet` | 83,967 | `ent`, `nace5` | KBO academic — aggregates only |
| `footfall_sector_gent.parquet` | 254 | `nis9_code` (composite, score 0–1) | open (De Lijn + Gent ODS) |
| `demand_proxies_sector_gent.parquet` | 254 | `nis9_code` (point→sector) | open (Gent ODS) |

## Join grain & fan-out (read before any `ent` join)

`ent` is an **enterprise**-level key, but the three firm tables are at different grains, so
a naive `USING(ent)` can multiply rows. Measured on disk (2026-05-30):

| Table | Grain | Rows per `ent` |
|---|---|---|
| `business_financials_gent` | one row per **enterprise** | **1** (unique). 6,550 rows have NULL `ent` — Belfirst entries with no enterprise number; `norm_ent` nulls them so they never join |
| `business_registry_gent` | one row per **establishment** | up to **317** (a chain with 317 Gent branches) |
| `business_registry_history_gent` | one row per **establishment × validity window** | up to **544** |

Safe patterns:

- **`business_registry_gent` ⋈ `business_financials_gent` `USING(ent)`** — fine: financials is unique per `ent`, so each establishment simply inherits its enterprise's financials. **Count firms with `count(DISTINCT ent)`, not row count** (else a 317-branch chain dominates). Result: 18,671 rows / 17,373 distinct enterprises.
- **`business_registry_gent` ⋈ `business_registry_history_gent` `USING(ent)` → DON'T** — both are establishment-level, so the link is a 10.8× cartesian (232,576 rows from 21,546 enterprises). Aggregate history to one row per enterprise first, then join:
  ```sql
  WITH hist AS (
    SELECT ent, min(open_date) AS first_open, max(close_date) AS last_close,
           bool_or(is_active) AS any_active, count(*) AS n_establishments
    FROM business_registry_history_gent GROUP BY ent)
  SELECT r.*, h.* FROM business_registry_gent r LEFT JOIN hist h USING(ent)
  ```
  The establishment numbers do **not** bridge the two sources (`EstablishmentNumber` in the KBO flat vs `establishment_number` in the academic extract share 0 values), so there is no 1:1 establishment path — aggregate per `ent` is the join.

## Known caveats

- **Belfirst↔KBO 66%** and skewed to postcode 9000 — vintage + `Gemeente='Gent'` extract artifact, not a format issue. Joining to academic history recovers more.
- **KBO seat vs trading address** — handled by direct-address geocoding above; still cross-check niche counts with OSM/Places (PRD risk).
- **Demographics sector vintage (NIS8 join).** Population/geometry use the finest NIS9 division (255 Gent sub-sectors); the cars and income cubes use a coarser/older division (~195–198 sectors) whose 9th NIS character differs, so an exact NIS9 join resolves only ~88/255. `demographics/clean.py` joins on **NIS8** (parent sector), lifting coverage to ~243/255 (cars) and ~224/255 (income). The **rate** columns (`cars_per_hh`, `median_income`, `avg_income`) are sound per sub-sector; the **absolute** columns (`households`, `cars`, `n_declarations`) are NIS8-parent totals — do not re-sum across sub-sectors. A proper NIS9↔NIS8 crosswalk would close the gap if needed.
- **Statbel geography levels:** the VAT cube (`peer_vat_nace_empl_gentarr`) is **arrondissement** Gent (`CD_ADM_DSTR_REFNIS='44000'`, no municipality breakdown) and starters (`peer_starters_flanders`) is **region** Vlaams Gewest (`CD_REGION='02000'`) — label both honestly in the UI. Bankruptcies is municipality (44021).
- **Peer cubes are published at different NACE levels** — VAT at **5-digit** (`nace5`), bankruptcies at **4-digit** (`nace4` = `left(nace5,4)`), starters at **2-digit division** (`nace2` = `left(nace5,2)`). Join each at its own level; do not join starters on `nace5` (it resolves ~2%, not ~67%).
- **Firm registry NACE quality (caps Q1/Q2).** `business_registry_gent.nace5` is **NULL for 33%** of firms (KBO entities with no registered activity) — irreducible. The non-null values used to span 2–7 digits (KBO `NACEMain` carries 6–7 digit sub-codes); `kbo_entities_flat` now **truncates to 5 digits** (`left(nace5,5)`), so 100% of firms-with-a-NACE resolve against `nace_ref` and the peer cubes. The 67% Q1/Q2 ceiling is now purely the NULL-NACE firms.
- **NACE vintage = NACE-BEL 2008 throughout the load-bearing joins.** NACE is a *join key* only for Q1 (firm → `nace_ref` label) and Q2 (firm → Statbel peer cubes); everywhere else it rides along an `ent`/address merge as an attribute. On both sides of those joins the codes are **NACE-BEL 2008** (firm `NACEMain` 86%, VAT cube 97%, bankruptcies 99% resolve in the 2008 set), so they are version-coherent. NACE-BEL 2008 is a multi-level nomenclature (1/2/3/4/5/**7**-digit — the 7-digit is a Belgian sub-level, *not* a 2003 artifact); every 6- and 7-digit `NACEMain` value left-5's to a valid 2008 5-digit code, so `left(nace5,5)` is lossless to the join level. `business_registry_history_gent.nace5` is **mixed-vintage** (its `NaceActivities` 7-digit codes sit ~52% in 2008 / ~55% in 2003 and overlap), but history joins on `ent`, so its NACE is a passenger — slice survival by sector via the registry's NACE, not the history's. **Refresh watch:** the 2026-05-29 KBO zip ships a `Nace2025` dictionary (6,520 codes) but records are *not* recoded to it yet; a future snapshot may flip `NACEMain` to 2025, at which point `nace_ref` (2008-only) and the Statbel cubes (Rev 2 = 2008) would silently fall out of alignment — re-check the version mix on each refresh.
- Statbel TF_* (VAT/bankruptcies/starters/immo) and De Lijn GTFS are **on disk and built** (verified 2026-05-30). Still not on disk: GIPOD, gewestplan/RUP zoning, NMBS station boardings.
- **`footfall_sector_gent` is a proxy composite, not a measured footfall count.** `footfall_score` = `0.65·transit + 0.25·cyclist + 0.10·bike_parking`, each min-max normalized across the 254 sectors. Weights follow shortlist §6 (`0.40 transit + 0.25 boardings + 0.25 telraam + 0.10 micro`) with the **NMBS station-boardings term folded into transit** (not on disk; the shortlist's own fallback). Inputs: `transit_access_sector_gent` (De Lijn), Stad Gent `fietstelpaal-*` 2025 annual totals placed via the `fietstelpalen-gent` master layer (pole `code`→lat/lon; ~10 of 12 codes map, so the cyclist term is a sparse *measured* boost, 0 elsewhere — `totaal` ships ~2% float NaN, mapped to NULL before summing), and `fietsenstallingen-gent` bike-parking capacity. Score spans 0–0.709 (no sector tops all three terms). **Weight calibration against the druktemeting pedestrian counters is deferred** — those time-series carry no coordinates.
- **`demand_proxies_sector_gent` v1 = student study density only** (UGent `bloklocaties-gent`: `n_blok_locations` + `study_seats`, 29/254 sectors). Deferred: tourism (`toeristische-attracties-visit-gent` `geo` is corrupt — latitudes ~2.0, needs geocoding) and workplace/jobs population (buurtmonitor, gemeente-only). `kotzones-gent` was evaluated and dropped — the 20 student-housing *districts* tile the whole municipality, so every sector intersects one (no sector-level signal).
