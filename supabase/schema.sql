-- ============================================================================
-- Droomzaak warehouse — full schema snapshot of the `droomzaak` schema (local mirror)
-- ============================================================================
-- GENERATED — do not hand-edit. The QUERYABLE, RE-DEPLOYABLE copy of the live schema
-- on Supabase (project knwnjhbdmmdkqnmakqkr). Change history lives in supabase/migrations/.
--
-- Regenerate after every applied migration so it matches the live DB. Preferred (when the
-- tools are installed — neither was on the build machine, so this snapshot was derived
-- from migrations/20260530143210_droomzaak_canonical_tables.sql, which the live DB matches):
--     supabase db dump --schema droomzaak -f supabase/schema.sql
--   # or:
--     pg_dump --schema-only --no-owner --no-privileges --schema=droomzaak "$SUPABASE_DB_URL" > supabase/schema.sql
--
-- Geometry note: geo_sectors/geo_wijken store WKB as bytea (no PostGIS dependency); the
-- usable polygons live in the render tier (DuckDB/GeoJSON), per .claude/rules/data-tiers.md.

CREATE SCHEMA IF NOT EXISTS droomzaak;

-- Q1 dream→NACE label reference (KBO code.csv, NACE-BEL 2008).
CREATE TABLE IF NOT EXISTS droomzaak.nace_ref (
    nace5                TEXT,
    code_level           BIGINT,
    label_nl             TEXT,
    label_fr             TEXT
);
CREATE INDEX IF NOT EXISTS nace_ref_nace5_idx ON droomzaak.nace_ref (nace5);

-- Q2 the geocoded firm layer (KBO, 98% geocoded). kbo_id NOT unique (entity + establishment rows).
CREATE TABLE IF NOT EXISTS droomzaak.business_registry (
    kbo_id               TEXT,
    entity_type          TEXT,
    enterprise_number    TEXT,
    ent                  TEXT NOT NULL,                 -- join key to financials/history (USING(ent))
    establishment_number TEXT,
    name                 TEXT,
    nace5                TEXT,
    juridical_form       TEXT,
    postal               TEXT,
    city                 TEXT,
    street               TEXT,
    house_nbr            TEXT,
    lon                  DOUBLE PRECISION,
    lat                  DOUBLE PRECISION,
    nis9_code            TEXT,                          -- nullable: ~2% ungeocoded
    capakey              TEXT,
    geocoded             BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS business_registry_nace5_idx ON droomzaak.business_registry (nace5);
CREATE INDEX IF NOT EXISTS business_registry_nis9_idx  ON droomzaak.business_registry (nis9_code);
CREATE INDEX IF NOT EXISTS business_registry_ent_idx   ON droomzaak.business_registry (ent);

-- Q2 peer-performance financials (Belfirst — proprietary, AGGREGATES ONLY in tool output).
CREATE TABLE IF NOT EXISTS droomzaak.business_financials (
    ent                  TEXT,                          -- nullable: ~6.5k Belfirst rows have no enterprise number
    nace5                TEXT,
    ondernemingsnummer   TEXT,
    naam                 TEXT,
    gemeente             TEXT,
    postcode             TEXT,
    laatste_jaar         BIGINT,
    omzet_eur            BIGINT,
    ebitda_eur           BIGINT,
    ebit_eur             BIGINT,
    eigen_vermogen_eur   BIGINT,
    totaal_activa_eur    BIGINT,
    werknemers           BIGINT,
    solvency_pct         DOUBLE PRECISION,
    profit_margin_pct    DOUBLE PRECISION,
    current_ratio        DOUBLE PRECISION,
    roe_pct              DOUBLE PRECISION,
    roce_pct             DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS business_financials_ent_idx   ON droomzaak.business_financials (ent);
CREATE INDEX IF NOT EXISTS business_financials_nace5_idx ON droomzaak.business_financials (nace5);

-- Q2 establishment lifespans (KBO academic — AGGREGATES ONLY). Aggregate per ent before joining (joins.md).
CREATE TABLE IF NOT EXISTS droomzaak.business_registry_history (
    ent                  TEXT,
    establishment_number TEXT,
    nace5                TEXT,
    open_date            TIMESTAMP,
    close_date           TIMESTAMP,
    end_reason           TEXT,
    postal               TEXT,
    is_active            BOOLEAN
);
CREATE INDEX IF NOT EXISTS business_registry_history_ent_idx   ON droomzaak.business_registry_history (ent);
CREATE INDEX IF NOT EXISTS business_registry_history_nace5_idx ON droomzaak.business_registry_history (nace5);

-- Q3 per-sector population / motorization / income (Statbel; absolute cols are NIS8-parent totals — see joins.md).
CREATE TABLE IF NOT EXISTS droomzaak.demographics_sector (
    nis9_code            TEXT,
    population           DOUBLE PRECISION,
    households           DOUBLE PRECISION,
    cars                 DOUBLE PRECISION,
    cars_per_hh          DOUBLE PRECISION,
    median_income        DOUBLE PRECISION,
    avg_income           DOUBLE PRECISION,
    n_declarations       DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS demographics_sector_nis9_idx ON droomzaak.demographics_sector (nis9_code);

-- Q3 sale-price PROXY for premises cost (Statbel IMMO; NIS8-regrained to the spine).
CREATE TABLE IF NOT EXISTS droomzaak.housing_price_sector (
    nis9_code            TEXT,
    property_type        TEXT,
    year                 INTEGER,
    n_transactions       INTEGER,
    median_price         DOUBLE PRECISION,
    p25_price            DOUBLE PRECISION,
    p75_price            DOUBLE PRECISION,
    p10_price            DOUBLE PRECISION,
    p90_price            DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS housing_price_sector_nis9_idx ON droomzaak.housing_price_sector (nis9_code);

-- Q3 De Lijn stop density & service per sector (footfall composite input).
CREATE TABLE IF NOT EXISTS droomzaak.transit_access_sector (
    nis9_code            TEXT,
    wijknr               BIGINT,
    n_stops              BIGINT,
    departures_total     DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS transit_access_sector_nis9_idx ON droomzaak.transit_access_sector (nis9_code);

-- Q3 public-domain works / events / detours, point→sector (GIPOD-style Gent layers).
CREATE TABLE IF NOT EXISTS droomzaak.disruption_events (
    kind                 TEXT,
    event_id             TEXT,
    description          TEXT,
    owner                TEXT,
    start_ts             TIMESTAMP,
    end_ts               TIMESTAMP,
    duration_days        BIGINT,
    lon                  DOUBLE PRECISION,
    lat                  DOUBLE PRECISION,
    nis9_code            TEXT,
    wijknr               BIGINT
);
CREATE INDEX IF NOT EXISTS disruption_events_nis9_idx ON droomzaak.disruption_events (nis9_code);

-- Q4 Omgevingsloket environment-permit applications, centroid→sector.
CREATE TABLE IF NOT EXISTS droomzaak.permits_events (
    kind                 TEXT,
    projectnummer        TEXT,
    project_type_code    TEXT,
    aanvrager            TEXT,
    datum_indiening      TIMESTAMP,
    huidige_toestand     TEXT,
    detail               TEXT,
    lon                  DOUBLE PRECISION,
    lat                  DOUBLE PRECISION,
    nis9_code            TEXT,
    wijknr               BIGINT
);
CREATE INDEX IF NOT EXISTS permits_events_nis9_idx ON droomzaak.permits_events (nis9_code);

-- Q3 assorted Gent point layers (business centres / POI / blok), point→sector.
CREATE TABLE IF NOT EXISTS droomzaak.gent_points (
    category             TEXT,
    name                 TEXT,
    subtype              TEXT,
    lon                  DOUBLE PRECISION,
    lat                  DOUBLE PRECISION,
    nis9_code            TEXT,
    wijknr               BIGINT
);
CREATE INDEX IF NOT EXISTS gent_points_nis9_idx ON droomzaak.gent_points (nis9_code);

-- Q2 VAT-registered firms by NACE×size, arrondissement Gent (44000). Join on nace5.
CREATE TABLE IF NOT EXISTS droomzaak.peer_vat_nace_empl_gentarr (
    nace5                TEXT,
    nace_label           TEXT,
    size_class           TEXT,
    size_label           TEXT,
    n_vat                INTEGER,
    n_vat_start          INTEGER,
    n_vat_stop           INTEGER
);
CREATE INDEX IF NOT EXISTS peer_vat_nace_empl_gentarr_nace5_idx ON droomzaak.peer_vat_nace_empl_gentarr (nace5);

-- Q2 bankruptcies by NACE 4-digit class, Gent municipality (44021). Join on nace4.
CREATE TABLE IF NOT EXISTS droomzaak.peer_bankruptcies (
    nace4                TEXT,
    nace_label           TEXT,
    year                 INTEGER,
    month                INTEGER,
    duration_class       DOUBLE PRECISION,
    duration_label       TEXT,
    n_bankruptcies       INTEGER
);
CREATE INDEX IF NOT EXISTS peer_bankruptcies_nace4_idx ON droomzaak.peer_bankruptcies (nace4);

-- Q2 VAT starters/stops, Flanders region (02000), published at NACE 2-digit division. Join on nace2.
CREATE TABLE IF NOT EXISTS droomzaak.peer_starters_flanders (
    nace2                TEXT,
    nace_label           TEXT,
    year                 INTEGER,
    month                INTEGER,
    n_first_start        INTEGER,
    n_restart            INTEGER,
    n_stop               INTEGER,
    n_eop                INTEGER
);
CREATE INDEX IF NOT EXISTS peer_starters_flanders_nace2_idx ON droomzaak.peer_starters_flanders (nace2);

-- Spatial spine — sectors (geom_wkb = WKB bytea; usable polygons live in the render tier).
CREATE TABLE IF NOT EXISTS droomzaak.geo_sectors (
    nis9_code            TEXT,
    sectorcode           TEXT,
    wijknr               BIGINT,
    sectornaam           TEXT,
    stadcode             TEXT,
    geom_wkb             BYTEA
);
CREATE INDEX IF NOT EXISTS geo_sectors_nis9_idx ON droomzaak.geo_sectors (nis9_code);

-- Spatial spine — districts (wijken).
CREATE TABLE IF NOT EXISTS droomzaak.geo_wijken (
    wijknr               BIGINT,
    wijk_naam            TEXT,
    wijk                 TEXT,
    geom_wkb             BYTEA
);

-- Build-time geocode bridge (KBO academic — no redistribution). Deduped unique addresses → x/y/nis9.
CREATE TABLE IF NOT EXISTS droomzaak.kbo_geocode (
    street               TEXT,
    house_nbr            TEXT,
    box                  TEXT,
    postal               TEXT,
    city                 TEXT,
    x                    DOUBLE PRECISION,
    y                    DOUBLE PRECISION,
    lon                  DOUBLE PRECISION,
    lat                  DOUBLE PRECISION,
    nis9_code            TEXT,
    nis5_code            TEXT,
    capakey              TEXT,
    match_granularity    TEXT,
    match_probability    DOUBLE PRECISION,
    is_imputed           BOOLEAN
);
CREATE INDEX IF NOT EXISTS kbo_geocode_nis9_idx ON droomzaak.kbo_geocode (nis9_code);

-- Q3 footfall composite (0.65·transit + 0.25·cyclist + 0.10·bike_parking), normalized 0–1/sector.
CREATE TABLE IF NOT EXISTS droomzaak.footfall_sector (
    nis9_code             TEXT,
    wijknr                BIGINT,
    transit_departures    DOUBLE PRECISION,
    cyclist_count         DOUBLE PRECISION,
    bike_parking_capacity DOUBLE PRECISION,
    footfall_score        DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS footfall_sector_nis9_idx ON droomzaak.footfall_sector (nis9_code);

-- Q3 demand-side: student study density (UGent bloklocaties) per sector.
CREATE TABLE IF NOT EXISTS droomzaak.demand_proxies_sector (
    nis9_code             TEXT,
    wijknr                BIGINT,
    n_blok_locations      BIGINT,
    study_seats           DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS demand_proxies_sector_nis9_idx ON droomzaak.demand_proxies_sector (nis9_code);

-- Q4 curated Chapter-4 permit decision table (NACE × company-attributes → permit/url/cost/lead_time).
-- applies_when/cost are JSON-encoded TEXT (parsed in Python by permit_checklist_for — no SQL-side JSON).
-- nace_prefix/depends_on are TEXT[] (Postgres arrays). GIN index on nace_prefix for @>/&& containment.
CREATE TABLE IF NOT EXISTS droomzaak.permit_rules (
    permit         TEXT,
    nace_prefix    TEXT[],
    applies_when   TEXT,
    official_url   TEXT,
    explainer      TEXT,
    cost           TEXT,
    lead_time_days BIGINT,
    depends_on     TEXT[],
    status         TEXT,
    source_url     TEXT
);
CREATE INDEX IF NOT EXISTS permit_rules_nace_idx ON droomzaak.permit_rules USING GIN (nace_prefix);
