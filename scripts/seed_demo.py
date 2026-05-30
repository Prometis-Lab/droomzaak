#!/usr/bin/env python
"""Idempotent demo seed for the droomzaak warehouse (Lisa horeca path + scaffolds).

Applies migrations/0001_droomzaak_demo.sql then loads demo fixtures. Re-running is
safe (TRUNCATE + INSERT). Run by the operator against the droomzaak Postgres:

    DROOMZAAK_POSTGRES_URL=postgresql://… uv run python scripts/seed_demo.py

Parameterized SQL only. Snapshot-frozen for the demo (PRD §4.5).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import asyncpg
import yaml

from backend.app import settings

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "supabase" / "migrations" / "0001_droomzaak_demo.sql"
CONFIG = ROOT / "config"

GEO = [
    ("44021A23B", "Vrijdagmarkt", "Binnenstad"),
    ("44021A18C", "Patershol", "Binnenstad"),
    ("44021A05A", "Sint-Jacobs", "Binnenstad"),
    ("44021B12D", "Brugse Poort", "Brugse Poort-Rooigem"),
    ("44021B30E", "Sluizeken", "Sluizeken-Tolhuis-Ham"),
    ("44021C07F", "Dampoort", "Dampoort"),
    ("44021C44G", "Ledeberg", "Ledeberg"),
    ("44021D21H", "Gentbrugge", "Gentbrugge"),
]

PEER = [
    ("56.101", "44021", 2021, 5, 3, 6, 10, 1.04),
    ("56.101", "44021", 2022, 6, 3, 5, 11, 1.10),
    ("56.101", "44021", 2023, 5, 3, 6, 11, 1.12),
    ("56.101", "44021", 2024, 6, 2, 4, 13, 1.18),
    ("47.610", "44021", 2023, 2, 2, 1, 8, 1.01),
    ("47.610", "44021", 2024, 3, 1, 1, 9, 1.03),
]

SCORES = [
    ("44021A23B", 0.92, 0.15, 0.80, 0.78, 0.55, 0.00),
    ("44021A18C", 0.85, 0.35, 0.40, 0.70, 0.62, 0.10),
    ("44021A05A", 0.80, 0.45, 0.55, 0.72, 0.50, 0.05),
    ("44021B12D", 0.74, 0.20, 0.70, 0.55, 0.30, 0.20),
    ("44021B30E", 0.70, 0.25, 0.65, 0.58, 0.32, 0.15),
    ("44021C07F", 0.68, 0.30, 0.60, 0.65, 0.35, 0.25),
    ("44021C44G", 0.60, 0.18, 0.62, 0.50, 0.28, 0.10),
    ("44021D21H", 0.55, 0.12, 0.58, 0.45, 0.25, 0.05),
]

RENT = [
    ("44021A23B", "commercial", 2024, 145, 110, 180, 24),
    ("44021A18C", "commercial", 2024, 158, 120, 195, 18),
    ("44021A05A", "commercial", 2024, 140, 105, 175, 21),
    ("44021B12D", "commercial", 2024, 95, 75, 120, 30),
    ("44021B30E", "commercial", 2024, 98, 78, 124, 27),
    ("44021C07F", "commercial", 2024, 105, 82, 132, 22),
    ("44021C44G", "commercial", 2024, 88, 70, 110, 19),
    ("44021D21H", "commercial", 2024, 82, 65, 102, 16),
]


async def _seed_table(conn, table, columns, rows, jsonb_cols=()):
    placeholders = ", ".join(
        f"${i + 1}::jsonb" if columns[i] in jsonb_cols else f"${i + 1}"
        for i in range(len(columns))
    )
    await conn.execute(f"TRUNCATE droomzaak.{table}")
    await conn.executemany(
        f"INSERT INTO droomzaak.{table} ({', '.join(columns)}) VALUES ({placeholders})",
        rows,
    )
    print(f"  {table}: {len(rows)} rows")


def _load_yaml(name):
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


async def main():
    dsn = settings.DROOMZAAK_POSTGRES_URL
    if not dsn:
        raise SystemExit("Set DROOMZAAK_POSTGRES_URL (or SUPABASE_DB_URL) first.")
    conn = await asyncpg.connect(dsn)
    try:
        print("applying migration…")
        await conn.execute(MIGRATION.read_text(encoding="utf-8"))

        print("seeding fixtures…")
        await _seed_table(conn, "geo_admin_units",
                          ["sector_id", "sector_name_nl", "wijk_nl"], GEO)
        await _seed_table(conn, "peer_demography_nace",
                          ["nace_code", "refnis", "year", "openings", "closings",
                           "bankruptcies", "active_count", "btw_evolution"], PEER)
        await _seed_table(conn, "sector_scores",
                          ["sector_id", "demographic_match", "competition_density",
                           "vacancy_score", "transit_score", "rent_score",
                           "disruption_penalty"], SCORES)
        await conn.execute(
            """UPDATE droomzaak.sector_scores s SET sector_name_nl = g.sector_name_nl,
               wijk_nl = g.wijk_nl FROM droomzaak.geo_admin_units g
               WHERE s.sector_id = g.sector_id"""
        )
        await _seed_table(conn, "housing_price_sector",
                          ["sector_id", "asset_type", "year", "median_eur_per_m2",
                           "p25_eur_per_m2", "p75_eur_per_m2", "sample_n"], RENT)

        permits = _load_yaml("permit_rules_horeca.yml")
        permit_rows = [
            (r["rule_id"], r["nace_code"], json.dumps(r.get("attribute_filter", {})),
             r["permit_name"], r["authority"], r["deep_link"],
             r.get("estimated_cost_eur"), r.get("estimated_processing_days"),
             r.get("notes_nl")) for r in permits
        ]
        await _seed_table(conn, "permit_rules",
                          ["rule_id", "nace_code", "attribute_filter", "permit_name",
                           "authority", "deep_link", "estimated_cost_eur",
                           "estimated_processing_days", "notes_nl"], permit_rows,
                          jsonb_cols=["attribute_filter"])

        subs = _load_yaml("subsidies.yml")
        sub_rows = [
            (s["subsidy_id"], s["name"], s["authority"], s.get("max_amount_eur"),
             json.dumps(s.get("eligibility_filter", {})), s["deep_link"],
             s.get("description_nl"), s.get("estimated_processing_days"),
             s.get("status", "active")) for s in subs
        ]
        await _seed_table(conn, "subsidies",
                          ["subsidy_id", "name", "authority", "max_amount_eur",
                           "eligibility_filter", "deep_link", "description_nl",
                           "estimated_processing_days", "status"], sub_rows,
                          jsonb_cols=["eligibility_filter"])
        print("OK — demo warehouse seeded.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
