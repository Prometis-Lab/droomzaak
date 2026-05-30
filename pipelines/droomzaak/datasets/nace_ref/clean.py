"""Canonical: nace_ref — the NACE-BEL 2008 code → label reference (Q1 dream→NACE).

Source: `code.csv` inside the KBO Open Data Full zip. One row per NACE-BEL 2008 code
with NL + FR descriptions. Codes are undotted; `code_level` is the digit count (2..5)
so the agent can match at the right granularity.
"""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import connect, nace5, src, write  # noqa: E402


def build() -> Path:
    con = connect()
    zip_path = src("raw/kbo/kbo-open-data-full/*/KboOpenData_*_Full.zip")
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as zf:
            csv_path = zf.extract("code.csv", tmp)
        select = f"""
            SELECT
                {nace5("Code")} AS nace5,
                length({nace5("Code")}) AS code_level,
                max(Description) FILTER (WHERE Language = 'NL') AS label_nl,
                max(Description) FILTER (WHERE Language = 'FR') AS label_fr
            FROM read_csv('{csv_path}')
            WHERE Category = 'Nace2008'
            GROUP BY {nace5("Code")}
        """
        return write(con, select, "nace_ref")


if __name__ == "__main__":
    build()
