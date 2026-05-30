"""Canonical: demand_proxies_sector_gent — per-sector demand-side signals (Q3 score_locations).

Where customers *want* a concept, not where they pass by (that's footfall_sector). v1 captures
the strongest open Ghent demand signal — **student study density** (~80k students) — from the
on-disk Gent ODS `bloklocaties-gent` layer, aggregated to the statistical-sector spine:

  - n_blok_locations → count of UGent study spots in the sector
  - study_seats      → total `totale_capaciteit` of those spots (daytime student concentration)

One row per Ghent sector. Deferred (noted in joins.md):
  - tourism proximity (`toeristische-attracties-visit-gent`) — its `geo` field is corrupt
    (latitudes read ~2.0); needs address geocoding before it can be placed in a sector.
  - daytime/workplace population (buurtmonitor jobs) — gemeente-only, not on disk.
  - `kotzones-gent` was evaluated and dropped: the 20 student-housing *districts* tile the whole
    municipality (e.g. Haven 47 km²), so every sector intersects one — no sector-level signal.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import connect, load_sectors, src, write  # noqa: E402


def build() -> Path:
    con = connect()
    load_sectors(con)

    blok = src("snapshots/gent/bloklocaties-gent/snapshot_*.parquet")

    select = f"""
        WITH base AS (
            SELECT DISTINCT nis9_code, wijknr FROM sectors
        ),
        blok_pts AS (
            SELECT
                TRY_CAST(split_part(geo_punt, ', ', 2) AS DOUBLE) AS lon,
                TRY_CAST(split_part(geo_punt, ', ', 1) AS DOUBLE) AS lat,
                TRY_CAST(totale_capaciteit AS DOUBLE) AS capaciteit
            FROM read_parquet('{blok}')
        ),
        blok AS (
            SELECT
                s.nis9_code,
                count(*) AS n_blok_locations,
                sum(p.capaciteit) AS study_seats
            FROM blok_pts p
            JOIN sectors s ON ST_Contains(s.geom, ST_Point(p.lon, p.lat))
            WHERE p.lon IS NOT NULL AND p.lat IS NOT NULL
            GROUP BY s.nis9_code
        )
        SELECT
            base.nis9_code,
            base.wijknr,
            coalesce(blok.n_blok_locations, 0) AS n_blok_locations,
            coalesce(blok.study_seats, 0)      AS study_seats
        FROM base
        LEFT JOIN blok USING (nis9_code)
    """
    return write(con, select, "demand_proxies_sector_gent")


if __name__ == "__main__":
    build()
