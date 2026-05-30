"""Canonical: gent_points_gent — assorted Gent point layers for context (Q3).

Business centres, points-of-interest, and study/'blok' locations unioned to one
point-per-feature table, each tagged with its statistical sector by point-in-polygon.
`category` keeps the source layer; `name`/`subtype` are the layer's label fields.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import connect, load_sectors, src, write  # noqa: E402


def build() -> Path:
    con = connect()
    load_sectors(con)

    centra = src("snapshots/gent/bedrijvencentra-gent/snapshot_*.parquet")
    poi = src("snapshots/gent/points-of-interest-poi-stam-gent/snapshot_*.parquet")
    blok = src("snapshots/gent/bloklocaties-gent/snapshot_*.parquet")

    union = f"""
        SELECT 'bedrijvencentrum' AS category,
               naam AS name,
               CAST("type" AS VARCHAR) AS subtype,
               ST_X(ST_GeomFromGeoJSON(geometry)) AS lon,
               ST_Y(ST_GeomFromGeoJSON(geometry)) AS lat
        FROM read_parquet('{centra}')
        UNION ALL
        SELECT 'poi' AS category,
               name_nl AS name,
               CAST(status AS VARCHAR) AS subtype,
               ST_X(ST_GeomFromGeoJSON(geometry)) AS lon,
               ST_Y(ST_GeomFromGeoJSON(geometry)) AS lat
        FROM read_parquet('{poi}')
        UNION ALL
        SELECT 'bloklocatie' AS category,
               titel AS name,
               CAST(label_1 AS VARCHAR) AS subtype,
               TRY_CAST(split_part(geo_punt, ', ', 2) AS DOUBLE) AS lon,
               TRY_CAST(split_part(geo_punt, ', ', 1) AS DOUBLE) AS lat
        FROM read_parquet('{blok}')
    """
    select = f"""
        WITH p AS ({union})
        SELECT
            p.category, p.name, p.subtype, p.lon, p.lat,
            s.nis9_code, s.wijknr
        FROM p
        LEFT JOIN sectors s ON ST_Contains(s.geom, ST_Point(p.lon, p.lat))
        WHERE p.lon IS NOT NULL AND p.lat IS NOT NULL
    """
    return write(con, select, "gent_points_gent")


if __name__ == "__main__":
    build()
