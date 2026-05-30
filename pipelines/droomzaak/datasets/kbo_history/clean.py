"""Canonical: business_registry_history_gent — establishment lifespans from the KBO academic extract (Q2).

Source: KBO academic business-units extract, Gent (NIS = 44021). One row per
establishment with open/close dates and end reason — the layer that lets us reason
about survival and churn. Municipality-level only (no per-sector geocoding here; link
via `ent` to the geocoded `business_registry_gent` for coordinates).

Licence: KBO academic — academic use only, no raw redistribution. Output stays under
canonical/ (gitignored).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import GENT_REFNIS5, connect, nace5, norm_ent, src, write  # noqa: E402


def build() -> Path:
    con = connect()
    bu = src("snapshots/kbo/kbo-academic-business-units/kbo_business_units_*.parquet")
    select = f"""
        SELECT
            {norm_ent("VAT")} AS ent,
            establishment_number,
            {nace5("NaceActivities[1]")} AS nace5,
            try_strptime("linked_enterprises.linked_enterprise_validity.begin", '%d/%m/%Y') AS open_date,
            try_strptime("linked_enterprises.linked_enterprise_validity.end", '%d/%m/%Y') AS close_date,
            "linked_enterprises.linked_enterprise_end_reason" AS end_reason,
            "addresses.address_address_codings.address_coding_post_code" AS postal,
            "linked_enterprises.linked_enterprise_validity.end" IS NULL AS is_active
        FROM read_parquet('{bu}')
        WHERE "addresses.address_address_codings.address_coding_nis_code" = '{GENT_REFNIS5}'
    """
    return write(con, select, "business_registry_history_gent")


if __name__ == "__main__":
    build()
