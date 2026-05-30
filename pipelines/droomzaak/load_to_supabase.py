"""Load canonical Parquet into the Supabase Postgres `droomzaak` schema.

    uv run python pipelines/droomzaak/load_to_supabase.py business_registry
    uv run python pipelines/droomzaak/load_to_supabase.py all

The path: clean.py writes `data/canonical/<stem>.parquet` → this loader pushes it into
the `droomzaak.<table>` Postgres table via DuckDB's postgres extension (ATTACH + INSERT).

Boundary contract (see supabase-schema-sync + data-tiers.md):
  - **Schema is migration-managed**, not loader-managed. The target table must already
    exist (created by an idempotent migration the operator applied). This loader only
    moves rows — it never runs DDL. It DELETE+INSERTs so a re-run is idempotent.
  - The DSN is read from the environment (`DROOMZAAK_PG_DSN`, else `SUPABASE_DB_URL`),
    never hardcoded. Use the **direct/session** connection (port 5432), not the
    transaction pooler (6543) — bulk loads need session mode.
  - `INSERT … SELECT *` matches columns **by position**: the migration must declare
    columns in the same order the clean.py SELECT produces them.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import CANONICAL, REPO_ROOT  # noqa: E402

PG_SCHEMA = "droomzaak"

# Postgres table name (in the droomzaak schema) → canonical Parquet stem in
# data/canonical/. One row per table the migration (supabase/scripts/canonical_tables.sql)
# declares; column ORDER in that migration must match each clean.py SELECT (position-based
# INSERT). Build with: uv run python pipelines/droomzaak/build.py
TABLES = {
    "nace_ref": "nace_ref",
    "business_registry": "business_registry_gent",
    "business_financials": "business_financials_gent",
    "business_registry_history": "business_registry_history_gent",
    "demographics_sector": "demographics_sector_gent",
    "housing_price_sector": "housing_price_sector_gent",
    "transit_access_sector": "transit_access_sector_gent",
    "footfall_sector": "footfall_sector_gent",
    "demand_proxies_sector": "demand_proxies_sector_gent",
    "disruption_events": "disruption_events_gent",
    "permits_events": "permits_events_gent",
    "gent_points": "gent_points_gent",
    "peer_vat_nace_empl_gentarr": "peer_vat_nace_empl_gentarr",
    "peer_bankruptcies": "peer_bankruptcies_gent",
    "peer_starters_flanders": "peer_starters_flanders",
    "geo_sectors": "geo_sectors_gent",
    "geo_wijken": "geo_wijken_gent",
    "kbo_geocode": "kbo_geocode_gent",
}

# Per-table DuckDB SELECT list for the INSERT (defaults to "*"). The geo spine carries a
# GeoParquet GEOMETRY column that has no Postgres equivalent without PostGIS, so we ship it
# as raw WKB into a `bytea` column. `* REPLACE` swaps only that column in place, keeping the
# position-based column count intact (the render tier holds the usable polygons anyway).
_GEOM_TO_WKB = "* REPLACE (ST_AsWKB(geom_wkb) AS geom_wkb)"
SELECT_LIST = {
    "geo_sectors": _GEOM_TO_WKB,
    "geo_wijken": _GEOM_TO_WKB,
}


def resolve_dsn() -> str:
    """Postgres connection string from the env; .env.demo (gitignored) is loaded if present.

    Only a value that actually looks like a Postgres URI counts — a blank or a stray
    comment left in .env.demo (e.g. `DROOMZAAK_PG_DSN= # …`) is skipped, not connected
    to. Without this guard a non-URI placeholder in the preferred var would shadow a
    valid fallback and the loader would dial a garbage target.
    """
    load_dotenv(REPO_ROOT / ".env.demo")
    for var in ("DROOMZAAK_PG_DSN", "SUPABASE_DB_URL"):
        value = (os.environ.get(var) or "").strip()
        if value.startswith(("postgres://", "postgresql://")):
            return value
    raise RuntimeError(
        "No usable Postgres DSN — set DROOMZAAK_PG_DSN or SUPABASE_DB_URL to a "
        "postgres://… URI (see .env.demo)."
    )


# SAST note: the `# nosemgrep` lines below interpolate ONLY code-internal values into SQL
# — `dsn` (env var, operator-controlled .env.demo), `alias`/`schema` (constants), and `name`
# (a key from the internal TABLES dict, gated by the KeyError above). SQL identifiers and the
# ATTACH connection string can never be bind parameters; the variable runtime value (the
# Parquet path) IS bound via `?`. No user/model input reaches these strings.
def attach_postgres(
    con: duckdb.DuckDBPyConnection, dsn: str, alias: str = "pg"
) -> None:
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute("INSTALL spatial; LOAD spatial;")  # ST_AsWKB for geo-spine bytea load
    con.execute(f"ATTACH '{dsn}' AS {alias} (TYPE postgres)")  # nosemgrep


def load_canonical(
    con: duckdb.DuckDBPyConnection,
    name: str,
    alias: str = "pg",
    schema: str = PG_SCHEMA,
) -> int:
    """DELETE+INSERT one canonical Parquet into `{alias}.{schema}.{name}`; return rows landed.

    `con` must already have the target attached as `alias` (a real Postgres via
    attach_postgres, or — in tests — an in-memory DuckDB with the same schema/table).
    """
    if name not in TABLES:
        raise KeyError(f"Unknown table {name!r}; known: {', '.join(sorted(TABLES))}")
    parquet = CANONICAL / f"{TABLES[name]}.parquet"
    if not parquet.exists():
        raise FileNotFoundError(
            f"Missing {parquet} — run the clean.py for {name} first."
        )

    target = f"{alias}.{schema}.{name}"
    pq = str(parquet)
    # The INSERT is position-based (`SELECT *`): clean.py emits KBO-cased names
    # (KBO_ID, EntityType) while the table is snake_case, so a name-matched INSERT isn't
    # possible — column ORDER is the contract (documented in the migration). Guard it: a
    # column-count mismatch means clean.py and the migration have drifted; fail loudly
    # rather than silently misalign. (A reorder of two same-type columns still slips — the
    # column order in supabase/scripts/canonical_tables.sql is the source of truth.)
    n_parquet = len(
        con.execute("SELECT * FROM read_parquet(?) LIMIT 0", [pq]).description
    )
    n_target = len(con.execute(f"DESCRIBE {target}").fetchall())  # nosemgrep
    if n_parquet != n_target:
        raise ValueError(
            f"{name}: Parquet has {n_parquet} columns but {target} has {n_target} — "
            "clean.py and the migration have drifted; update the migration to match."
        )

    src_rows = con.execute("SELECT count(*) FROM read_parquet(?)", [pq]).fetchone()[0]
    con.execute("BEGIN")
    try:
        con.execute(f"DELETE FROM {target}")  # nosemgrep
        con.execute(  # nosemgrep
            f"INSERT INTO {target} SELECT {SELECT_LIST.get(name, '*')} FROM read_parquet(?)",
            [pq],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    landed = con.execute(f"SELECT count(*) FROM {target}").fetchone()[0]  # nosemgrep
    logger.success(f"{name}: {landed:,} rows → {target} (source had {src_rows:,})")
    return landed


def main(argv: list[str]) -> None:
    if not argv or argv[0] in {"-h", "--help"}:
        logger.info(
            f"usage: load_to_supabase.py <table|all>   (tables: {', '.join(sorted(TABLES))})"
        )
        return
    names = sorted(TABLES) if argv[0] == "all" else argv

    con = duckdb.connect()
    attach_postgres(con, resolve_dsn())
    for name in names:
        load_canonical(con, name)
    logger.success("supabase load complete")


if __name__ == "__main__":
    main(sys.argv[1:])
