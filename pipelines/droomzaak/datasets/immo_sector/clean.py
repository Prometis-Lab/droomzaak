"""Canonical: housing_price_sector_gent — real-estate sale prices per sector (Q3 rent proxy).

Source: Statbel IMMO per statistical sector (NodeID1758). Median/quartile sale prices
per sector x property type x year. Used as a *proxy* for premises cost — Belgium has no
public per-sector commercial rent series.

The IMMO cube uses a finer/older sector vintage (~318 Gent sectors) that does not align
with the geometry spine's NIS9 on the 9th character, so an exact NIS9 join covers only
~63/254 spine sectors. We therefore re-grain to the **spine** by matching on **NIS8**
(parent sector), which lifts coverage to ~108/254. Per spine sector x property type we
keep the busiest IMMO sub-sector (most transactions) as the representative price, so all
percentiles come from one coherent row. Output keys cleanly to `geo_sectors_gent` on
`nis9_code`. The remaining gap is Statbel's own suppression of medians in low-transaction
sectors — not recoverable. Requires geo_admin/clean.py to have run first.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import GEO_SECTORS, GENT_REFNIS5, connect, src, write  # noqa: E402


def build() -> Path:
    con = connect()
    select = f"""
        WITH immo AS (
            SELECT
                left(CD_STAT_SECTOR, 8) AS nis8,
                CD_TYPE_NL AS property_type,
                TRY_CAST(CD_YEAR AS INTEGER) AS year,
                TRY_CAST(MS_TRANSACTIONS AS INTEGER) AS n_transactions,
                TRY_CAST("MS_P50 (MEDIAN_PRICE)" AS DOUBLE) AS median_price,
                TRY_CAST(MS_P25 AS DOUBLE) AS p25_price,
                TRY_CAST(MS_P75 AS DOUBLE) AS p75_price,
                TRY_CAST(MS_P10 AS DOUBLE) AS p10_price,
                TRY_CAST(MS_P90 AS DOUBLE) AS p90_price
            FROM read_parquet('{src("snapshots/statbel/NodeID1758/snapshot_*.parquet")}')
            WHERE CD_STAT_SECTOR LIKE '{GENT_REFNIS5}%'
            QUALIFY row_number() OVER (
                PARTITION BY CD_STAT_SECTOR, CD_TYPE_NL ORDER BY TRY_CAST(CD_YEAR AS INTEGER) DESC
            ) = 1
        ),
        spine AS (
            SELECT nis9_code, left(nis9_code, 8) AS nis8
            FROM read_parquet('{GEO_SECTORS}')
        ),
        joined AS (
            SELECT
                s.nis9_code, i.property_type, i.year, i.n_transactions,
                i.median_price, i.p25_price, i.p75_price, i.p10_price, i.p90_price,
                row_number() OVER (
                    PARTITION BY s.nis9_code, i.property_type
                    ORDER BY i.n_transactions DESC NULLS LAST
                ) AS rn
            FROM spine s
            JOIN immo i USING (nis8)
        )
        SELECT
            nis9_code, property_type, year, n_transactions,
            median_price, p25_price, p75_price, p10_price, p90_price
        FROM joined
        WHERE rn = 1
    """
    return write(con, select, "housing_price_sector_gent")


if __name__ == "__main__":
    build()
