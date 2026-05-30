"""Canonical: demographics_sector_gent — per-sector population, motorization, income (Q3).

Sources (all Statbel, keyed on the NIS statistical sector):
  - population 2025 (NodeID6475) — finest division, 255 Gent sub-sectors
  - cars per household, latest year (NodeID5702) — ~195 coarser sectors
  - fiscal incomes per sector (xlsx — no snapshot parquet exists) — ~198 coarser sectors

One row per Ghent population sub-sector (`nis9_code`, the spine). The cars and income
cubes use a coarser/older sector division whose 9th NIS character differs from the
population/geometry layer, so an exact NIS9 join only resolves ~88/255. We therefore
join on **NIS8** (the first 8 characters = the parent sector), which lifts coverage to
~243/255 (cars) and ~246/255 (income). The coarse sources are deduplicated to one row
per NIS8 first (households/cars summed; income taken from the busiest fine sector).

Consequence: the **rate** columns (`cars_per_hh`, `median_income`, `avg_income`) are
sound — each fine sub-sector inherits its parent sector's scale-invariant rate. The
**absolute** columns (`households`, `cars`, `n_declarations`) are the *parent* (NIS8)
sector totals, so do not re-sum them across sub-sectors. See joins.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import GENT_REFNIS5, connect, src, write  # noqa: E402


def build() -> Path:
    con = connect()
    con.execute("INSTALL excel; LOAD excel;")

    pop = src("snapshots/statbel/NodeID6475/snapshot_*.parquet")
    car = src("snapshots/statbel/NodeID5702/snapshot_*.parquet")
    inc = src(
        "raw/statbel/statbel-extras_fiscale-inkomens-sector-nis9/*/TF_PSNL_INC_TAX_SECTOR.xlsx"
    )

    select = f"""
        WITH pop AS (
            SELECT CD_SECTOR AS nis9_code, left(CD_SECTOR, 8) AS nis8, TOTAL AS population
            FROM read_parquet('{pop}')
            WHERE CD_SECTOR LIKE '{GENT_REFNIS5}%'
        ),
        car_latest AS (
            SELECT cd_sector, MS_TOT_HH, MS_TOT_CARS
            FROM read_parquet('{car}')
            WHERE cd_sector LIKE '{GENT_REFNIS5}%'
            QUALIFY row_number() OVER (PARTITION BY cd_sector ORDER BY TRY_CAST(CD_YEAR AS INTEGER) DESC) = 1
        ),
        car AS (
            SELECT left(cd_sector, 8) AS nis8,
                   sum(MS_TOT_HH) AS households,
                   sum(MS_TOT_CARS) AS cars
            FROM car_latest
            GROUP BY left(cd_sector, 8)
        ),
        inc_latest AS (
            SELECT CD_SECTOR,
                   MS_MEDIAN_NET_TAXABLE_INC AS median_income,
                   MS_AVG_TOT_NET_TAXABLE_INC AS avg_income,
                   MS_NBR_NON_ZERO_INC AS n_declarations
            FROM read_xlsx('{inc}')
            WHERE CAST(CD_MUNTY_REFNIS AS VARCHAR) = '{GENT_REFNIS5}'
            QUALIFY row_number() OVER (PARTITION BY CD_SECTOR ORDER BY TRY_CAST(CD_YEAR AS INTEGER) DESC) = 1
        ),
        inc AS (
            SELECT left(CD_SECTOR, 8) AS nis8,
                   arg_max(median_income, n_declarations) AS median_income,
                   arg_max(avg_income, n_declarations) AS avg_income,
                   sum(n_declarations) AS n_declarations
            FROM inc_latest
            GROUP BY left(CD_SECTOR, 8)
        )
        SELECT
            pop.nis9_code,
            pop.population,
            car.households,
            car.cars,
            TRY_CAST(car.cars AS DOUBLE) / nullif(car.households, 0) AS cars_per_hh,
            inc.median_income,
            inc.avg_income,
            inc.n_declarations
        FROM pop
        LEFT JOIN car USING (nis8)
        LEFT JOIN inc USING (nis8)
    """
    return write(con, select, "demographics_sector_gent")


if __name__ == "__main__":
    build()
