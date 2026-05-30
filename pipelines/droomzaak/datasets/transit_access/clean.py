"""Canonical: transit_access_sector_gent — De Lijn stop density & service per sector (Q3).

Source: De Lijn GTFS (Belgium-wide). We clip stops to the Gent bbox, count scheduled
departures per stop from `stop_times`, then point-in-polygon stops onto sectors and
aggregate to `n_stops` + `departures_total` per sector. This is the main input to the
later footfall composite.
"""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import connect, load_sectors, src, write  # noqa: E402

GENT_BBOX = (3.63, 3.83, 51.01, 51.13)  # lon_min, lon_max, lat_min, lat_max


def build() -> Path:
    con = connect()
    load_sectors(con)
    lon0, lon1, lat0, lat1 = GENT_BBOX

    zip_path = src("raw/gtfs-belgium/de-lijn/*/de-lijn-gtfs.zip")
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as zf:
            stops_txt = zf.extract("stops.txt", tmp)
            times_txt = zf.extract("stop_times.txt", tmp)

        con.execute(f"""
            CREATE TEMP TABLE gent_stops AS
            SELECT CAST(stop_id AS VARCHAR) AS stop_id,
                   stop_name,
                   TRY_CAST(stop_lon AS DOUBLE) AS lon,
                   TRY_CAST(stop_lat AS DOUBLE) AS lat
            FROM read_csv('{stops_txt}')
            WHERE TRY_CAST(stop_lon AS DOUBLE) BETWEEN {lon0} AND {lon1}
              AND TRY_CAST(stop_lat AS DOUBLE) BETWEEN {lat0} AND {lat1}
        """)
        con.execute(f"""
            CREATE TEMP TABLE dep AS
            SELECT CAST(stop_id AS VARCHAR) AS stop_id, count(*) AS departures
            FROM read_csv('{times_txt}')
            WHERE CAST(stop_id AS VARCHAR) IN (SELECT stop_id FROM gent_stops)
            GROUP BY CAST(stop_id AS VARCHAR)
        """)
        select = """
            SELECT
                s.nis9_code,
                s.wijknr,
                count(*) AS n_stops,
                sum(coalesce(d.departures, 0)) AS departures_total
            FROM gent_stops g
            LEFT JOIN dep d USING (stop_id)
            JOIN sectors s ON ST_Contains(s.geom, ST_Point(g.lon, g.lat))
            GROUP BY s.nis9_code, s.wijknr
        """
        return write(con, select, "transit_access_sector_gent")


if __name__ == "__main__":
    build()
