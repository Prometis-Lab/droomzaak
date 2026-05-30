"""Canonical: Statbel peer-context tables for Q2 (market sizing & dynamics).

Three independent Statbel cubes, each at the finest geography that covers Gent:
  - `peer_vat_nace_empl_gentarr` — VAT-registered firms by NACE x size class,
    arrondissement Gent (CD_ADM_DSTR_REFNIS = 44000; no municipality breakdown).
  - `peer_bankruptcies_gent` — bankruptcies by NACE 4-digit class, Gent municipality.
  - `peer_starters_flanders` — VAT starters/stops, Flanders region (02000; no finer geo).
    NB: this cube is published at **NACE 2-digit division** level, not 5-digit.

Joined to the firm layer by `nace5` (VAT) / `nace4` (bankruptcies) / `nace2` (starters)
+ the matching geography, not spatially. To join starters, truncate the firm's NACE to
2 digits: `left(firm.nace5, 2) = starters.nace2`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import GENT_REFNIS5, connect, nace4, nace5, src, write  # noqa: E402


def build() -> Path:
    con = connect()

    vat = f"""
        SELECT
            {nace5("CD_NACE")} AS nace5,
            TX_NACE_NL_LVL5 AS nace_label,
            CD_NIS_STAT_UNT_CLS AS size_class,
            TX_NIS_STAT_UNT_CLS_NL_LVL1 AS size_label,
            TRY_CAST(MS_NUM_VAT AS INTEGER) AS n_vat,
            TRY_CAST(MS_NUM_VAT_START AS INTEGER) AS n_vat_start,
            TRY_CAST(MS_NUM_VAT_STOP AS INTEGER) AS n_vat_stop
        FROM read_parquet('{src("snapshots/statbel/NodeID5735/snapshot_*.parquet")}')
        WHERE CAST(CD_ADM_DSTR_REFNIS AS VARCHAR) = '44000'
    """
    write(con, vat, "peer_vat_nace_empl_gentarr")

    bankr = f"""
        SELECT
            {nace4("CD_NACE_REV2_CLASS")} AS nace4,
            TX_NACE_REV2_CLASS_NL AS nace_label,
            TRY_CAST(CD_YEAR AS INTEGER) AS year,
            TRY_CAST(CD_MONTH AS INTEGER) AS month,
            CD_COMPANY_DURATION AS duration_class,
            TX_COMPANY_DURATION_NL AS duration_label,
            TRY_CAST(MS_COUNTOF_BANKRUPTCIES AS INTEGER) AS n_bankruptcies
        FROM read_parquet('{src("snapshots/statbel/NodeID4027/snapshot_*.parquet")}')
        WHERE CAST(CD_MUNTY_REFNIS AS VARCHAR) = '{GENT_REFNIS5}'
    """
    write(con, bankr, "peer_bankruptcies_gent")

    starters = f"""
        SELECT
            left({nace5("NACE2")}, 2) AS nace2,
            DESCR_NACE1_NL AS nace_label,
            TRY_CAST(YEAR AS INTEGER) AS year,
            TRY_CAST(MONTH AS INTEGER) AS month,
            TRY_CAST(MS_NUM_VAT_FIRST_STRT AS INTEGER) AS n_first_start,
            TRY_CAST(MS_NUM_VAT_RESTART AS INTEGER) AS n_restart,
            TRY_CAST(MS_NUM_VAT_STOP AS INTEGER) AS n_stop,
            TRY_CAST(MS_NUM_VAT_EOP AS INTEGER) AS n_eop
        FROM read_parquet('{src("snapshots/statbel/NodeID3321/snapshot_*.parquet")}')
        WHERE CAST(CD_REGION AS VARCHAR) = '02000'
    """
    return write(con, starters, "peer_starters_flanders")


if __name__ == "__main__":
    build()
