"""Canonical: the spatial spine — Ghent statistical sectors + districts as WGS84 geometry.

Source: Gent ODS layers `statistische-sectoren-gent` (sectors) and `stadswijken-gent`
(districts). Both ship GeoJSON polygons already in WGS84.

`geo_sectors_gent` is what every spatial cleaning script point-in-polygons against
(via `_common.load_sectors`), so this script must run first. Geometry is stored as WKB
(`geom_wkb`) because Parquet has no native geometry type.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import GENT_REFNIS5, connect, src, write  # noqa: E402


def build() -> Path:
    con = connect()

    wijken = f"""
        SELECT
            wijknr,
            naam AS wijk_naam,
            wijk,
            ST_AsWKB(ST_GeomFromGeoJSON(geometry)) AS geom_wkb
        FROM read_parquet('{src("snapshots/gent/stadswijken-gent/snapshot_*.parquet")}')
    """
    write(con, wijken, "geo_wijken_gent")

    # Built last so its path is what build() returns; load_sectors() depends on it.
    sectors = f"""
        SELECT
            '{GENT_REFNIS5}' || sectorcode AS nis9_code,
            sectorcode,
            wijknr,
            sectornaam,
            stadcode,
            ST_AsWKB(ST_GeomFromGeoJSON(geometry)) AS geom_wkb
        FROM read_parquet('{src("snapshots/gent/statistische-sectoren-gent/snapshot_*.parquet")}')
    """
    return write(con, sectors, "geo_sectors_gent")


if __name__ == "__main__":
    build()
