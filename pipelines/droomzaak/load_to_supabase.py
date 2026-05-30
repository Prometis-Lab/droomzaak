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

# Postgres table name → canonical Parquet stem in data/canonical/.
# Add a row here as each table's clean.py + migration land. (geo_* tables carry
# WKB geometry and need a PostGIS-aware migration — added in the fan-out, not here.)
TABLES = {
    "business_registry": "business_registry_gent",
}


def resolve_dsn() -> str:
    """Postgres connection string from the env; .env.demo (gitignored) is loaded if present."""
    load_dotenv(REPO_ROOT / ".env.demo")
    dsn = os.environ.get("DROOMZAAK_PG_DSN") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError(
            "No Postgres DSN — set DROOMZAAK_PG_DSN or SUPABASE_DB_URL (see .env.demo)."
        )
    return dsn


# SAST note: the `# nosemgrep` lines below interpolate ONLY code-internal values into SQL
# — `dsn` (env var, operator-controlled .env.demo), `alias`/`schema` (constants), and `name`
# (a key from the internal TABLES dict, gated by the KeyError above). SQL identifiers and the
# ATTACH connection string can never be bind parameters; the variable runtime value (the
# Parquet path) IS bound via `?`. No user/model input reaches these strings.
def attach_postgres(con: duckdb.DuckDBPyConnection, dsn: str, alias: str = "pg") -> None:
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute(f"ATTACH '{dsn}' AS {alias} (TYPE postgres)")  # nosemgrep: sqlalchemy-execute-raw-query, formatted-sql-query


def load_canonical(
    con: duckdb.DuckDBPyConnection, name: str, alias: str = "pg", schema: str = PG_SCHEMA
) -> int:
    """DELETE+INSERT one canonical Parquet into `{alias}.{schema}.{name}`; return rows landed.

    `con` must already have the target attached as `alias` (a real Postgres via
    attach_postgres, or — in tests — an in-memory DuckDB with the same schema/table).
    """
    if name not in TABLES:
        raise KeyError(f"Unknown table {name!r}; known: {', '.join(sorted(TABLES))}")
    parquet = CANONICAL / f"{TABLES[name]}.parquet"
    if not parquet.exists():
        raise FileNotFoundError(f"Missing {parquet} — run the clean.py for {name} first.")

    target = f"{alias}.{schema}.{name}"
    pq = str(parquet)
    # The INSERT is position-based (`SELECT *`): clean.py emits KBO-cased names
    # (KBO_ID, EntityType) while the table is snake_case, so a name-matched INSERT isn't
    # possible — column ORDER is the contract (documented in the migration). Guard it: a
    # column-count mismatch means clean.py and the migration have drifted; fail loudly
    # rather than silently misalign. (A reorder of two same-type columns still slips — the
    # column order in business_registry.sql is the source of truth.)
    n_parquet = len(con.execute("SELECT * FROM read_parquet(?) LIMIT 0", [pq]).description)
    n_target = len(con.execute(f"DESCRIBE {target}").fetchall())  # nosemgrep: sqlalchemy-execute-raw-query, formatted-sql-query
    if n_parquet != n_target:
        raise ValueError(
            f"{name}: Parquet has {n_parquet} columns but {target} has {n_target} — "
            "clean.py and the migration have drifted; update the migration to match."
        )

    src_rows = con.execute("SELECT count(*) FROM read_parquet(?)", [pq]).fetchone()[0]
    con.execute("BEGIN")
    try:
        con.execute(f"DELETE FROM {target}")  # nosemgrep: sqlalchemy-execute-raw-query, formatted-sql-query
        con.execute(f"INSERT INTO {target} SELECT * FROM read_parquet(?)", [pq])  # nosemgrep: sqlalchemy-execute-raw-query, formatted-sql-query
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    landed = con.execute(f"SELECT count(*) FROM {target}").fetchone()[0]  # nosemgrep: sqlalchemy-execute-raw-query, formatted-sql-query
    logger.success(f"{name}: {landed:,} rows → {target} (source had {src_rows:,})")
    return landed


def main(argv: list[str]) -> None:
    if not argv or argv[0] in {"-h", "--help"}:
        logger.info(f"usage: load_to_supabase.py <table|all>   (tables: {', '.join(sorted(TABLES))})")
        return
    names = sorted(TABLES) if argv[0] == "all" else argv

    con = duckdb.connect()
    attach_postgres(con, resolve_dsn())
    for name in names:
        load_canonical(con, name)
    logger.success("supabase load complete")


if __name__ == "__main__":
    main(sys.argv[1:])
