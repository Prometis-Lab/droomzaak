"""Canonical: disruption_events_gent — public-domain works, events & traffic detours (Q3).

Three Gent GIPOD-style layers unioned to one point-per-event table, each assigned its
statistical sector by point-in-polygon. `duration_days` is end - start. Detours
(`omleidingen`) are line geometries in EPSG:31370 — we take the reprojected centroid.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import connect, load_sectors, src, write  # noqa: E402


def build() -> Path:
    con = connect()
    load_sectors(con)

    werken = src("snapshots/gent/inname-openbaar-domein-werken-gent/snapshot_*.parquet")
    events = src(
        "snapshots/gent/inname-openbaar-domein-evenementen-gent/snapshot_*.parquet"
    )
    omleid = src("snapshots/gent/omleidingen-en-onderbrekingen/snapshot_*.parquet")

    union = f"""
        SELECT 'werken' AS kind,
               CAST(gipodid AS VARCHAR) AS event_id,
               description,
               owner,
               TRY_CAST(startdatetime AS TIMESTAMP) AS start_ts,
               TRY_CAST(enddatetime AS TIMESTAMP) AS end_ts,
               TRY_CAST(coordinaat_1 AS DOUBLE) AS lon,
               TRY_CAST(coordinaat_2 AS DOUBLE) AS lat
        FROM read_parquet('{werken}')
        UNION ALL
        SELECT 'evenement' AS kind,
               CAST(gipodid AS VARCHAR) AS event_id,
               description,
               owner,
               TRY_CAST(startdatetime AS TIMESTAMP) AS start_ts,
               TRY_CAST(enddatetime AS TIMESTAMP) AS end_ts,
               ST_X(ST_GeomFromGeoJSON(coordinate)) AS lon,
               ST_Y(ST_GeomFromGeoJSON(coordinate)) AS lat
        FROM read_parquet('{events}')
        UNION ALL
        SELECT 'omleiding' AS kind,
               CAST(vergunningid AS VARCHAR) AS event_id,
               json_extract_string("type", '$.label') AS description,
               NULL AS owner,
               TRY_CAST(startdatum AS TIMESTAMP) AS start_ts,
               TRY_CAST(einddatum AS TIMESTAMP) AS end_ts,
               ST_X(ST_Transform(ST_Centroid(ST_GeomFromText(lijn)), 'EPSG:31370', 'EPSG:4326', always_xy := true)) AS lon,
               ST_Y(ST_Transform(ST_Centroid(ST_GeomFromText(lijn)), 'EPSG:31370', 'EPSG:4326', always_xy := true)) AS lat
        FROM read_parquet('{omleid}')
    """
    select = f"""
        WITH e AS ({union})
        SELECT
            e.kind, e.event_id, e.description, e.owner,
            e.start_ts, e.end_ts,
            date_diff('day', e.start_ts, e.end_ts) AS duration_days,
            e.lon, e.lat,
            s.nis9_code, s.wijknr
        FROM e
        LEFT JOIN sectors s ON ST_Contains(s.geom, ST_Point(e.lon, e.lat))
        WHERE e.lon IS NOT NULL AND e.lat IS NOT NULL
    """
    return write(con, select, "disruption_events_gent")


if __name__ == "__main__":
    build()
