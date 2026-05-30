-- Droomzaak demo warehouse — idempotent.
-- The analytical tables the DataGateway reads (parameterized SQL only).
-- Demo-path tables are intentionally non-spatial flat tables (no PostGIS needed)
-- so the seam + Lisa path stand up on any Postgres 16. Geometry-heavy scoring is
-- precomputed into sector_scores at ingest.
--
-- Per CLAUDE.md: this is run by the OPERATOR against the droomzaak Postgres
-- (STOP-and-wait); the read-only Supabase MCP never applies DDL.

CREATE SCHEMA IF NOT EXISTS droomzaak;

-- 1. Administrative geographies (lookup; geometry lives in the RENDER tier) ----
CREATE TABLE IF NOT EXISTS droomzaak.geo_admin_units (
    sector_id      TEXT PRIMARY KEY,
    sector_name_nl TEXT,
    wijk_nl        TEXT,
    refnis         TEXT DEFAULT '44021'
);

-- 2. Peer cohort (Belfirst + Statbel aggregates) — peer_benchmarks_statbel -----
CREATE TABLE IF NOT EXISTS droomzaak.peer_demography_nace (
    nace_code     TEXT,
    refnis        TEXT,
    year          INT,
    openings      INT,
    closings      INT,
    bankruptcies  INT,
    active_count  INT,
    btw_evolution NUMERIC,
    PRIMARY KEY (nace_code, refnis, year)
);

-- 3. Per-sector precomputed scoring features — score_locations ------------------
-- Axes normalized 0..1; competition/rent/disruption are penalties.
CREATE TABLE IF NOT EXISTS droomzaak.sector_scores (
    sector_id           TEXT PRIMARY KEY,
    sector_name_nl      TEXT,
    wijk_nl             TEXT,
    demographic_match   NUMERIC,
    competition_density NUMERIC,
    vacancy_score       NUMERIC,
    transit_score       NUMERIC,
    rent_score          NUMERIC,
    disruption_penalty  NUMERIC
);

-- 4. Rent proxy (Statbel TF_IMMO_SECTOR sale-€, NOT rent) — rent_benchmark ------
CREATE TABLE IF NOT EXISTS droomzaak.housing_price_sector (
    sector_id         TEXT,
    asset_type        TEXT,
    year              INT,
    median_eur_per_m2 NUMERIC,
    p25_eur_per_m2    NUMERIC,
    p75_eur_per_m2    NUMERIC,
    sample_n          INT,
    PRIMARY KEY (sector_id, asset_type, year)
);

-- 5. Permit rules (curated YAML) — permit_checklist_for ------------------------
CREATE TABLE IF NOT EXISTS droomzaak.permit_rules (
    rule_id                   TEXT PRIMARY KEY,
    nace_code                 TEXT,
    attribute_filter          JSONB DEFAULT '{}'::jsonb,
    permit_name               TEXT NOT NULL,
    authority                 TEXT NOT NULL,
    deep_link                 TEXT NOT NULL,
    estimated_cost_eur        NUMERIC,
    estimated_processing_days INT,
    notes_nl                  TEXT
);
CREATE INDEX IF NOT EXISTS permit_rules_nace_idx ON droomzaak.permit_rules (nace_code);

-- 6. Subsidies (curated YAML) — subsidies_for ---------------------------------
CREATE TABLE IF NOT EXISTS droomzaak.subsidies (
    subsidy_id                TEXT PRIMARY KEY,
    name                      TEXT NOT NULL,
    authority                 TEXT NOT NULL,
    max_amount_eur            NUMERIC,
    eligibility_filter        JSONB DEFAULT '{}'::jsonb,
    deep_link                 TEXT NOT NULL,
    description_nl            TEXT,
    estimated_processing_days INT,
    status                    TEXT DEFAULT 'active'   -- active | ended_2025
);
