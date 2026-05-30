"""Canonical: business_financials_gent — peer-performance financials.

Source: Belfirst jaarrekeningen Gent (proprietary — aggregates / client-side only).
One row per company, latest available accounting year.

No geometry: this table joins to business_registry_gent via `ent` (normalized 10-digit
enterprise number), and inherits the sector (nis9_code) from there. Belfirst's own
`Gemeente='Gent'` extract is skewed to postcode 9000 — see joins.md coverage note.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import connect, nace5, norm_ent, src, write  # noqa: E402

# Curated demo-relevant subset: source column → canonical name.
COLUMNS = {
    "Ondernemingsnummer": "ondernemingsnummer",
    "Naam": "naam",
    "Gemeente": "gemeente",
    "Postcode": "postcode",
    "Laatste jaar": "laatste_jaar",
    "Omzet EUR Laatst beschikb. jr": "omzet_eur",
    "EBITDA EUR Laatst beschikb. jr": "ebitda_eur",
    "EBIT  EUR Laatst beschikb. jr": "ebit_eur",
    "Eigen vermogen / Sociale fondsen EUR Laatst beschikb. jr": "eigen_vermogen_eur",
    "Totaal der activa EUR Laatst beschikb. jr": "totaal_activa_eur",
    "Gemiddeld aantal werknemers Laatst beschikb. jr": "werknemers",
    "Solvency ratio  % Laatst beschikb. jr": "solvency_pct",
    "Profit margin  % Laatst beschikb. jr": "profit_margin_pct",
    "Current ratio  Laatst beschikb. jr": "current_ratio",
    "Return on shareholders funds % Laatst beschikb. jr": "roe_pct",
    "Return on capital employed  % Laatst beschikb. jr": "roce_pct",
}


def build() -> Path:
    con = connect()
    renamed = [f'"{srccol}" AS {name}' for srccol, name in COLUMNS.items()]
    select = f"""
        SELECT
            {norm_ent('"Ondernemingsnummer"')} AS ent,
            {nace5('"NACE BEL 2008, primaire code"')} AS nace5,
            {", ".join(renamed)}
        FROM read_parquet('{src("raw/belfirst/belfirst-jaarrekeningen-gent-*/*/jaarrekeningen.parquet")}')
    """
    return write(con, select, "business_financials_gent")


if __name__ == "__main__":
    build()
