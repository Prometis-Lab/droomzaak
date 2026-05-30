-- Idempotent: add the two new Q3 score_locations tables to the droomzaak warehouse.
-- footfall_sector  — per-sector footfall composite (transit + cyclist counters + bike parking)
-- demand_proxies_sector — per-sector student study-density demand signal
--
-- Column ORDER matches each pipelines/droomzaak/datasets/<name>/clean.py SELECT so the
-- loader's position-based INSERT … SELECT * lines up. Safe to re-run / redeploy.
-- STOP-and-wait: operator applies via  psql "$SUPABASE_DB_URL" -f supabase/scripts/add_footfall_demand_tables.sql
-- then this is folded into supabase/migrations/ and schema.sql is regenerated.

CREATE SCHEMA IF NOT EXISTS droomzaak;

-- Q3 footfall composite, normalized 0–1 per sector:
-- 0.65·transit + 0.25·cyclist + 0.10·bike_parking (NMBS boardings folded into transit;
-- not on disk). See pipelines/droomzaak/datasets/footfall/clean.py.
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
