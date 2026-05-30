"""Canonical: footfall_sector_gent — per-sector footfall composite (Q3 score_locations).

There is no per-street city-wide footfall source for Ghent, so this is a proxy composite
(shortlist §6), normalized 0–1 per statistical sector:

    footfall_score = 0.65·transit + 0.25·cyclist + 0.10·bike_parking      (min-max per sector)

Weights follow the shortlist's `0.40·transit + 0.25·boardings + 0.25·telraam + 0.10·micro`
with the **NMBS station-boardings term folded into transit** — that feed is not on disk, and
the shortlist's own fallback is "fold its weight into transit_access". Inputs, all on T7:

  - transit  → `transit_access_sector_gent` (De Lijn GTFS departures/sector — already built)
  - cyclist  → Stad Gent `fietstelpaal-*` counters: 2025 annual `totaal` per pole, placed in a
               sector via the `fietstelpalen-gent` master layer (pole `code` → lat/lon). Only
               ~12 poles exist, so this is a sparse *measured* boost where a counter sits, 0
               elsewhere — honest, not city-wide.
  - bike_parking → `fietsenstallingen-gent` capacity summed per sector (static micromobility
               supply; the real-time occupancy feeds are single snapshots, not usable history).

One row per Ghent sector (the geo_sectors spine), score in [0,1]. The druktemeting pedestrian
counters (Korenmarkt/Kouter/Veldstraat) are ground-truth for *calibrating* these weights but
carry no coordinates in the time-series; weight calibration is deferred (see joins.md).
"""

from __future__ import annotations

import sys
from glob import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import CANONICAL, DATA_ROOT, connect, load_sectors, src, write  # noqa: E402

# Latest complete calendar year of counter data (the current year is partial).
COUNTER_YEAR = "2025"


def _newest_counter_snapshots() -> list[str]:
    """One newest snapshot Parquet per `fietstelpaal-*-{YEAR}-gent` pole-year folder.

    Each pole-year folder holds several dated `snapshot_*.parquet`; globbing them all would
    double-count, so we keep only the newest snapshot per folder.
    """
    pattern = str(
        DATA_ROOT / f"snapshots/gent/fietstelpaal-*-{COUNTER_YEAR}-gent/snapshot_*.parquet"
    )
    by_folder: dict[str, str] = {}
    for path in glob(pattern):
        folder = str(Path(path).parent)
        by_folder[folder] = max(by_folder.get(folder, ""), path)
    if not by_folder:
        raise FileNotFoundError(f"No fietstelpaal {COUNTER_YEAR} snapshots under {pattern}")
    return sorted(by_folder.values())


def build() -> Path:
    con = connect()
    load_sectors(con)

    transit = CANONICAL / "transit_access_sector_gent.parquet"
    if not transit.exists():
        raise FileNotFoundError("Run transit_access/clean.py first (needs transit_access_sector_gent)")
    poles = src("snapshots/gent/fietstelpalen-gent/snapshot_*.parquet")
    stalling = src("snapshots/gent/fietsenstallingen-gent/snapshot_*.parquet")
    counters = "[" + ",".join(f"'{p}'" for p in _newest_counter_snapshots()) + "]"

    select = f"""
        WITH base AS (
            SELECT DISTINCT nis9_code, wijknr FROM sectors
        ),
        transit AS (
            SELECT nis9_code, departures_total AS transit_departures
            FROM read_parquet('{transit}')
        ),
        counts AS (
            -- `totaal` ships ~2% genuine float NaN readings; SQL sum() ignores NULL but
            -- propagates NaN, which would poison the cross-sector min-max below. Map NaN→NULL
            -- so sum() drops those quarter-hours cleanly.
            SELECT code,
                   sum(CASE WHEN isnan(TRY_CAST(totaal AS DOUBLE)) THEN NULL
                            ELSE TRY_CAST(totaal AS DOUBLE) END) AS cnt
            FROM read_parquet({counters})
            GROUP BY code
        ),
        cyclist AS (
            SELECT s.nis9_code, sum(c.cnt) AS cyclist_count
            FROM counts c
            JOIN read_parquet('{poles}') m USING (code)
            JOIN sectors s ON ST_Contains(s.geom, ST_Point(m.long, m.lat))
            GROUP BY s.nis9_code
        ),
        bike AS (
            SELECT s.nis9_code, sum(TRY_CAST(f.capaciteit AS DOUBLE)) AS bike_parking_capacity
            FROM read_parquet('{stalling}') f
            JOIN sectors s ON ST_Contains(
                s.geom,
                ST_Point(
                    TRY_CAST(split_part(f.geo_point_2d, ', ', 2) AS DOUBLE),
                    TRY_CAST(split_part(f.geo_point_2d, ', ', 1) AS DOUBLE)
                )
            )
            GROUP BY s.nis9_code
        ),
        comp AS (
            SELECT
                b.nis9_code,
                b.wijknr,
                coalesce(t.transit_departures, 0)    AS transit_departures,
                coalesce(c.cyclist_count, 0)         AS cyclist_count,
                coalesce(k.bike_parking_capacity, 0) AS bike_parking_capacity
            FROM base b
            LEFT JOIN transit t USING (nis9_code)
            LEFT JOIN cyclist c USING (nis9_code)
            LEFT JOIN bike k USING (nis9_code)
        ),
        norm AS (
            SELECT *,
                (transit_departures - min(transit_departures) OVER ())
                    / nullif(max(transit_departures) OVER () - min(transit_departures) OVER (), 0) AS n_transit,
                (cyclist_count - min(cyclist_count) OVER ())
                    / nullif(max(cyclist_count) OVER () - min(cyclist_count) OVER (), 0) AS n_cyclist,
                (bike_parking_capacity - min(bike_parking_capacity) OVER ())
                    / nullif(max(bike_parking_capacity) OVER () - min(bike_parking_capacity) OVER (), 0) AS n_bike
            FROM comp
        )
        SELECT
            nis9_code,
            wijknr,
            transit_departures,
            cyclist_count,
            bike_parking_capacity,
            round(
                0.65 * coalesce(n_transit, 0)
                + 0.25 * coalesce(n_cyclist, 0)
                + 0.10 * coalesce(n_bike, 0),
                4
            ) AS footfall_score
        FROM norm
    """
    return write(con, select, "footfall_sector_gent")


if __name__ == "__main__":
    build()
