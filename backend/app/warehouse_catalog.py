"""Curated catalogue of the warehouse tables the generic tools may touch.

This is BOTH the data source for `describe_warehouse` AND the identifier allowlist
that makes `query_warehouse` injection-safe: only tables/columns named here can ever
reach the SQL string (values are always parameterized; identifiers come from this
dict, never from the raw model input).

Every table/column here is verified against supabase/schema.sql — the catalogue is
the allowlist, so a name that doesn't exist in the DB would be both a runtime error
AND an unvalidated identifier. Keep it in lockstep with the schema (see the
catalog-vs-schema test in backend/tests/test_droomzaak.py).

Deliberately excluded: kbo_geocode (no-redistribution bridge), agent_sessions
(not data), geometry columns (geom_wkb — render tier), date/timestamp columns, and
per-firm identity columns (ent, kbo_id, enterprise_number, establishment_number,
name/naam, ondernemingsnummer, street, house_nbr, lon, lat, capakey, aanvrager) —
the generic surface only ever returns aggregates, never identities.

A column is `numeric` if it can be an agg_field (sum/avg/min/max/median); `groupable`
if it can be a group_by. `aggregates_only` tables (Belfirst / KBO academic) suppress
any result row whose underlying cohort is smaller than MIN_COHORT.
"""

from __future__ import annotations

MIN_COHORT = 5  # aggregates-only: drop any group/total backed by fewer rows than this


def _col(meaning: str, *, numeric: bool = False, groupable: bool = False) -> dict:
    return {"meaning": meaning, "numeric": numeric, "groupable": groupable}


# table → {grain, one_line, licence, aggregates_only, caveat_nl, columns:{name:meta}}
CATALOG: dict[str, dict] = {
    "business_registry": {
        "grain": "one row per KBO establishment (a chain has many)",
        "one_line": "Geocoded KBO firms in Gent — count active businesses by NACE/sector/form.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Vestigingsniveau (een keten telt meermaals); tellingen zijn vestigingen, geen unieke ondernemingen. NACE-label staat in nace_ref, wijk-naam in geo_wijken.",
        "columns": {
            "nace5": _col("5-digit NACE-BEL 2008 code", groupable=True),
            "nis9_code": _col("statistical sector (spine key)", groupable=True),
            "juridical_form": _col("legal form", groupable=True),
            "entity_type": _col("entity vs establishment row", groupable=True),
            "city": _col("city/municipality", groupable=True),
        },
    },
    "business_financials": {
        "grain": "one row per enterprise (Belfirst)",
        "one_line": "Belfirst enterprise financials — peer turnover/result/size, AGGREGATES ONLY.",
        "licence": "aggregates_only",
        "aggregates_only": True,
        "caveat_nl": "Belfirst (proprietair): alleen geaggregeerd, nooit per onderneming; cohorten < 5 worden onderdrukt. Bedragen in €.",
        "columns": {
            "nace5": _col("5-digit NACE code", groupable=True),
            "gemeente": _col("municipality", groupable=True),
            "laatste_jaar": _col("year of latest accounts", numeric=True, groupable=True),
            "omzet_eur": _col("turnover €", numeric=True),
            "ebitda_eur": _col("EBITDA €", numeric=True),
            "ebit_eur": _col("EBIT €", numeric=True),
            "eigen_vermogen_eur": _col("equity €", numeric=True),
            "totaal_activa_eur": _col("total assets €", numeric=True),
            "werknemers": _col("employee count", numeric=True),
            "solvency_pct": _col("solvency %", numeric=True),
            "profit_margin_pct": _col("profit margin %", numeric=True),
            "roe_pct": _col("return on equity %", numeric=True),
        },
    },
    "business_registry_history": {
        "grain": "one row per establishment × validity window (KBO academic)",
        "one_line": "Establishment lifespans — survival/churn signal, AGGREGATES ONLY.",
        "licence": "aggregates_only",
        "aggregates_only": True,
        "caveat_nl": "KBO academisch: alleen geaggregeerd; cohorten < 5 onderdrukt. Tel met count; open/close-datums zijn niet als veld ontsloten.",
        "columns": {
            "nace5": _col("5-digit NACE code", groupable=True),
            "is_active": _col("establishment currently active", groupable=True),
            "end_reason": _col("reason the establishment closed", groupable=True),
        },
    },
    "demographics_sector": {
        "grain": "one row per statistical sector (Statbel)",
        "one_line": "Population, motorization & income per sector.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Absolute kolommen (households, cars, n_declarations) zijn NIS8-ouderniveau — niet hersommeren; ratio's (median_income, cars_per_hh) zijn per sector correct.",
        "columns": {
            "nis9_code": _col("statistical sector", groupable=True),
            "population": _col("inhabitants", numeric=True),
            "households": _col("households (NIS8-parent total)", numeric=True),
            "cars": _col("cars (NIS8-parent total)", numeric=True),
            "cars_per_hh": _col("cars per household", numeric=True),
            "median_income": _col("median income € (per-sector, sound)", numeric=True),
            "avg_income": _col("average income €", numeric=True),
            "n_declarations": _col("tax declarations (NIS8-parent total)", numeric=True),
        },
    },
    "housing_price_sector": {
        "grain": "one row per sector × property_type × year (Statbel)",
        "one_line": "Residential SALE-price proxy per sector — NOT rent, NOT €/m².",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Residentiële VERKOOPPRIJS (€ totaal, NIET huur, NIET €/m²) — locatiekostproxy.",
        "columns": {
            "nis9_code": _col("statistical sector", groupable=True),
            "property_type": _col("property type", groupable=True),
            "year": _col("transaction year", numeric=True, groupable=True),
            "n_transactions": _col("number of sales", numeric=True),
            "median_price": _col("median sale price €", numeric=True),
            "p25_price": _col("25th-percentile sale price €", numeric=True),
            "p75_price": _col("75th-percentile sale price €", numeric=True),
        },
    },
    "transit_access_sector": {
        "grain": "one row per sector (De Lijn GTFS)",
        "one_line": "Public-transit access per sector (stops, departures).",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "De Lijn GTFS; bus/tram-aanbod, geen NMBS-treinen.",
        "columns": {
            "nis9_code": _col("statistical sector", groupable=True),
            "wijknr": _col("district number", groupable=True),
            "n_stops": _col("stop count", numeric=True),
            "departures_total": _col("daily departures", numeric=True),
        },
    },
    "disruption_events": {
        "grain": "one row per public-domain disruption (GIPOD-style)",
        "one_line": "Road works / events / detours — count disruptions per sector.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Stad Gent open data; tel met count(*) per sector/kind. Momentopname van geplande verstoringen.",
        "columns": {
            "nis9_code": _col("statistical sector", groupable=True),
            "kind": _col("disruption kind", groupable=True),
            "owner": _col("owning authority", groupable=True),
            "wijknr": _col("district number", groupable=True),
            "duration_days": _col("duration in days", numeric=True),
        },
    },
    "permits_events": {
        "grain": "one row per Omgevingsloket permit application",
        "one_line": "Environmental/building permit applications — count permit activity per sector.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Omgevingsloket; tel met count(*). VergunningsACTIVITEIT, geen uitspraak over één pand.",
        "columns": {
            "nis9_code": _col("statistical sector", groupable=True),
            "kind": _col("application kind", groupable=True),
            "project_type_code": _col("project type code", groupable=True),
            "huidige_toestand": _col("current status", groupable=True),
            "wijknr": _col("district number", groupable=True),
        },
    },
    "gent_points": {
        "grain": "one row per point of interest (Gent ODS)",
        "one_line": "Points of interest — count POIs per sector by category.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Stad Gent open data; tel met count(*). Dekt ~28% van de sectoren — kruis met OSM/Places.",
        "columns": {
            "nis9_code": _col("statistical sector", groupable=True),
            "category": _col("POI category", groupable=True),
            "subtype": _col("POI subtype", groupable=True),
            "wijknr": _col("district number", groupable=True),
        },
    },
    "peer_vat_nace_empl_gentarr": {
        "grain": "one row per NACE5 × employee-size (Statbel, arrondissement 44000)",
        "one_line": "Active-VAT cohort by NACE and firm size — Gent arrondissement.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Arrondissement Gent (44000), niet de stad; nace5-niveau.",
        "columns": {
            "nace5": _col("5-digit NACE code", groupable=True),
            "nace_label": _col("NACE label", groupable=True),
            "size_class": _col("employee size class", groupable=True),
            "size_label": _col("employee size label", groupable=True),
            "n_vat": _col("active VAT registrations", numeric=True),
            "n_vat_start": _col("VAT starts", numeric=True),
            "n_vat_stop": _col("VAT stops", numeric=True),
        },
    },
    "peer_bankruptcies": {
        "grain": "one row per NACE4 × year × month (Statbel, municipality 44021)",
        "one_line": "Bankruptcies by NACE4 over time — Gent municipality.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Gemeente Gent (44021); nace4-niveau.",
        "columns": {
            "nace4": _col("4-digit NACE code", groupable=True),
            "nace_label": _col("NACE label", groupable=True),
            "year": _col("year", numeric=True, groupable=True),
            "month": _col("month", numeric=True, groupable=True),
            "n_bankruptcies": _col("bankruptcies", numeric=True),
        },
    },
    "peer_starters_flanders": {
        "grain": "one row per NACE2 × year × month (Statbel, Flanders 02000)",
        "one_line": "Business starters/stops by NACE2 over time — Flanders region.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Vlaams Gewest (02000), niet Gent; nace2-divisieniveau.",
        "columns": {
            "nace2": _col("2-digit NACE division", groupable=True),
            "nace_label": _col("NACE label", groupable=True),
            "year": _col("year", numeric=True, groupable=True),
            "month": _col("month", numeric=True, groupable=True),
            "n_first_start": _col("first-time starts", numeric=True),
            "n_restart": _col("restarts", numeric=True),
            "n_stop": _col("stops", numeric=True),
            "n_eop": _col("active at end of period", numeric=True),
        },
    },
    "nace_ref": {
        "grain": "one row per NACE code (KBO code.csv)",
        "one_line": "NACE-BEL 2008 code → Dutch/French label lookup.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "NACE-BEL 2008 nomenclatuur.",
        "columns": {
            "nace5": _col("NACE code", groupable=True),
            "label_nl": _col("Dutch label", groupable=True),
            "label_fr": _col("French label", groupable=True),
            "code_level": _col("digit depth of the code", numeric=True, groupable=True),
        },
    },
    "geo_sectors": {
        "grain": "one row per statistical sector (254)",
        "one_line": "Sector → name → district spine for labels.",
        "licence": "open",
        "aggregates_only": False,
        "caveat_nl": "Ruimtelijke ruggengraat (Gent ODS); geometrie leeft in de render-tier.",
        "columns": {
            "nis9_code": _col("statistical sector", groupable=True),
            "sectorcode": _col("sector code suffix", groupable=True),
            "wijknr": _col("district number", groupable=True),
            "sectornaam": _col("sector name", groupable=True),
            "stadcode": _col("city code", groupable=True),
        },
    },
}


def is_table(table: str) -> bool:
    return table in CATALOG


def column_meta(table: str, column: str) -> dict | None:
    return CATALOG.get(table, {}).get("columns", {}).get(column)


def list_tables() -> list[dict]:
    """Compact one-liner per exposed table (the no-arg describe_warehouse view)."""
    return [
        {
            "table": name,
            "grain": meta["grain"],
            "one_line": meta["one_line"],
            "licence": meta["licence"],
            "caveat_nl": meta["caveat_nl"],
        }
        for name, meta in CATALOG.items()
    ]


def describe(table: str) -> dict | None:
    """Full profile of one table (the describe_warehouse(table=...) view)."""
    meta = CATALOG.get(table)
    if not meta:
        return None
    columns = [
        {
            "name": col,
            "meaning": cm["meaning"],
            "numeric": cm["numeric"],
            "groupable": cm["groupable"],
        }
        for col, cm in meta["columns"].items()
    ]
    return {
        "table": table,
        "grain": meta["grain"],
        "one_line": meta["one_line"],
        "licence": meta["licence"],
        "aggregates_only": meta["aggregates_only"],
        "caveat_nl": meta["caveat_nl"],
        "columns": columns,
        "numeric_fields": [c["name"] for c in columns if c["numeric"]],
        "groupable_fields": [c["name"] for c in columns if c["groupable"]],
    }
