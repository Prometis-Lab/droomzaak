"""Canonical: business_registry_gent — the current-state competitor layer.

Source: KBO Open Data flat (open licence). Ghent slice via postcode 9000-9052.

Geocoding: each flat row is geocoded by its OWN address against kbo_geocode_gent
(street, house_nbr, postal, city — the flat has no box). The correspondence unions
enterprise + establishment addresses, so this resolves each row to its actual
trading address at ~98% — better than routing through the enterprise seat.

`ent` (normalized 10-digit enterprise number) is the link key to:
  - business_financials_gent (Belfirst), and
  - the academic historical layer via VAT (public ──VAT(99.6%)──► academic).
The VAT chain is for *history/financials*, not for current geocoding (which would
collapse establishments onto the enterprise seat). See joins.md.

Requires canonical/kbo_geocode_gent.parquet first (run kbo_correspondence/clean.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import (  # noqa: E402
    CANONICAL,
    connect,
    gent_postcode_filter,
    nace5,
    norm_ent,
    src,
    write,
)

# Flat address column → geocode-correspondence canonical name (flat has no box).
ADDR = {
    "street": "StreetNL",
    "house_nbr": "HouseNumber",
    "postal": "Zipcode",
    "city": "MunicipalityNL",
}


def build() -> Path:
    geocode = CANONICAL / "kbo_geocode_gent.parquet"
    if not geocode.exists():
        raise FileNotFoundError(
            "Run kbo_correspondence/clean.py first (needs kbo_geocode_gent.parquet)"
        )

    con = connect()
    flat = src("snapshots/kbo/kbo-entities-flat/kbo_*.parquet")

    # Collapse the geocode to one row per (street, house_nbr, postal, city) so the 4-tuple
    # join (flat carries no box) can't multiply rows.
    con.execute(f"""
        CREATE TEMP TABLE geo4 AS
        SELECT street, house_nbr, postal, city, lon, lat, nis9_code, capakey FROM read_parquet('{geocode}')
        QUALIFY row_number() OVER (
            PARTITION BY street, house_nbr, postal, city
            ORDER BY is_imputed ASC, match_probability DESC NULLS LAST
        ) = 1
    """)

    on = " AND ".join(
        f"f.{src_col} IS NOT DISTINCT FROM g.{canon}" for canon, src_col in ADDR.items()
    )
    select = f"""
        SELECT
            f.KBO_ID, f.EntityType,
            f.EnterpriseNumber, {norm_ent("f.EnterpriseNumber")} AS ent, f.EstablishmentNumber,
            coalesce(f.CommercialName, f.OfficialName, f.Abbreviation) AS name,
            -- KBO NACEMain carries 6-7 digit sub-codes; truncate to the 5-digit
            -- NACE-BEL 2008 so it resolves against nace_ref and the peer cubes.
            left({nace5("f.NACEMain")}, 5) AS nace5, f.JuridicalForm AS juridical_form,
            f.Zipcode AS postal, f.MunicipalityNL AS city, f.StreetNL AS street, f.HouseNumber AS house_nbr,
            g.lon, g.lat, g.nis9_code, g.capakey,
            (g.lon IS NOT NULL) AS geocoded
        FROM read_parquet('{flat}') f
        LEFT JOIN geo4 g ON {on}
        WHERE {gent_postcode_filter("f.Zipcode")}
    """
    return write(con, select, "business_registry_gent")


if __name__ == "__main__":
    build()
