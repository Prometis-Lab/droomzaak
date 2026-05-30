-- Migration: add the curated Chapter-4 permit_rules decision table.
-- Idempotent (CREATE … IF NOT EXISTS) — safe to re-run / redeploy.
--
-- Column ORDER matches pipelines/droomzaak/datasets/permit_rules/clean.py COLUMNS so the
-- loader's position-based INSERT … SELECT * lines up. applies_when/cost are JSON-encoded
-- TEXT (the permit_checklist_for tool parses them in Python — no SQL-side JSON needed).
-- nace_prefix and depends_on are TEXT[] (Postgres arrays).

CREATE SCHEMA IF NOT EXISTS droomzaak;

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

-- GIN index on nace_prefix: btree cannot index array columns; GIN supports the @>, &&, <@
-- containment operators the permit_checklist_for tool will use to filter by NACE prefix.
-- The existing tables use btree on scalar nis9_code/nace5 — array columns require GIN.
CREATE INDEX IF NOT EXISTS permit_rules_nace_idx ON droomzaak.permit_rules USING GIN (nace_prefix);
