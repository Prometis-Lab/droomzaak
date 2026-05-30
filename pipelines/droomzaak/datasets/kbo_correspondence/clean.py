"""Canonical: kbo_geocode_gent — the address → coordinate bridge.

Source: the two academic-licence geocoded correspondence tables (enterprises +
business-units). They are *unique addresses* produced by the Prometis geocoder,
keyed back to the KBO academic extract via the address columns.

This script slices Ghent (nis5 = 44021), unions both, dedups one row per address
(best match wins), and reprojects x/y (EPSG:3812 Belgian Lambert) → WGS84 lon/lat.

Licence: FOD Economie KBO academic — academic use only, no raw redistribution.
Output stays under data/canonical/ (gitignored).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import GENT_REFNIS5, connect, lonlat, src, write  # noqa: E402

SHARED_COLS = [
    "street", "house_nbr", "box", "postal", "city", "x", "y",
    "nis9_code", "nis5_code", "CaPaKey", "match_granularity",
    "match_probability", "is_imputed",
]


def build() -> Path:
    con = connect()
    cols = ", ".join(SHARED_COLS)
    lon_expr, lat_expr = lonlat()
    union = f"""
        SELECT {cols} FROM read_parquet('{src("snapshots/kbo/kbo-academic-enterprises-geocoded/kbo_enterprises_*.parquet")}')
            WHERE nis5_code = '{GENT_REFNIS5}'
        UNION ALL
        SELECT {cols} FROM read_parquet('{src("snapshots/kbo/kbo-academic-business-units-geocoded/kbo_business_units_*.parquet")}')
            WHERE nis5_code = '{GENT_REFNIS5}'
    """
    # One row per physical address; prefer the highest-confidence, non-imputed match.
    select = f"""
        SELECT
            street, house_nbr, box, postal, city,
            x, y, {lon_expr} AS lon, {lat_expr} AS lat,
            nis9_code, nis5_code, CaPaKey AS capakey,
            match_granularity, match_probability, is_imputed
        FROM ({union})
        QUALIFY row_number() OVER (
            PARTITION BY street, house_nbr, box, postal, city
            ORDER BY is_imputed ASC, match_probability DESC NULLS LAST
        ) = 1
    """
    return write(con, select, "kbo_geocode_gent")


if __name__ == "__main__":
    build()
