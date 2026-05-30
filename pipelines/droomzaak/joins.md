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
| Q2 financials | `business_registry_gent` ⋈ `business_financials_gent` | `USING(ent)` — 18,671 matched (Belfirst vintage gap) |
| Q2 growth/bankruptcy | Statbel TF_STARTERS_45 (region overlay) · TF_BANKRUPTCIES (`refnis5`+nace4) · TF_VAT_NACE_EMPL (`refnis5`+`nace5`+size) | by key once fetched |
| Q3 scoring | demographics/income/rent-proxy | `nis9_code` |
| Q3 competition/footfall/disruption | KBO points · druktemeting/parking · inname/GIPOD | **spatial** (point-in-polygon to sector) |
| Q4 permits/subsidies | `permit_rules`, `subsidies` (curated) | `nace5` + attributes |
| Q4 evidence/zoning | omgevingsloket · gewestplan/RUP | **spatial** clip to candidate point/sector |

## Canonical outputs (in `data/canonical/`, gitignored)

| File | Rows | Key(s) | Licence |
|---|---|---|---|
| `kbo_geocode_gent.parquet` | 93,612 | address 5-tuple → `lon/lat/nis9_code/capakey` | academic — no redistribution |
| `business_registry_gent.parquet` | 36,627 (98% geocoded) | `ent`, `nace5`, `nis9_code`, `lon/lat` | open (KBO) + academic-derived coords |
| `business_financials_gent.parquet` | 34,235 | `ent`, `nace5` | Belfirst — proprietary, aggregates only |

## Known caveats

- **Belfirst↔KBO 66%** and skewed to postcode 9000 — vintage + `Gemeente='Gent'` extract artifact, not a format issue. Joining to academic history recovers more.
- **KBO seat vs trading address** — handled by direct-address geocoding above; still cross-check niche counts with OSM/Places (PRD risk).
- Statbel TF_* / De Lijn / GIPOD / gewestplan are **not yet on disk** — join keys above are predicted; verify formats on fetch.
