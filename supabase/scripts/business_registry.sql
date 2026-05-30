-- Idempotent DDL — droomzaak.business_registry (proof-of-path table).
-- Columns are in the exact order pipelines/droomzaak/datasets/kbo_entities_flat/clean.py
-- produces them, so load_to_supabase.py's `INSERT … SELECT *` matches by position.
--
-- STOP-and-wait (supabase/README.md): the operator runs this, then it is folded into a
-- timestamped supabase/migrations/ file and schema.sql is regenerated.
--   psql "$SUPABASE_DB_URL" -f supabase/scripts/business_registry.sql

CREATE SCHEMA IF NOT EXISTS droomzaak;

CREATE TABLE IF NOT EXISTS droomzaak.business_registry (
    kbo_id               TEXT,                          -- not unique: 34,223 distinct of 36,627 (entity + establishment rows)
    entity_type          TEXT,
    enterprise_number    TEXT,
    ent                  TEXT NOT NULL,                 -- join key to business_financials (USING(ent)); never null in source
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

-- Lookups the analytical tools hit: NACE filter + sector join (Ch2 count / spatial_count).
CREATE INDEX IF NOT EXISTS business_registry_nace5_idx ON droomzaak.business_registry (nace5);
CREATE INDEX IF NOT EXISTS business_registry_nis9_idx  ON droomzaak.business_registry (nis9_code);
