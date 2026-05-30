"""Loader tests — exercise the real DELETE+INSERT SQL against an in-memory DuckDB
standing in for Supabase. Never touches T7, the network, or a real Postgres.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import load_to_supabase as loader  # noqa: E402

# Same column order the kbo_entities_flat clean.py SELECT produces (position-based INSERT).
COLUMNS_DDL = """
    kbo_id VARCHAR, entity_type VARCHAR, enterprise_number VARCHAR, ent VARCHAR,
    establishment_number VARCHAR, name VARCHAR, nace5 VARCHAR, juridical_form VARCHAR,
    postal VARCHAR, city VARCHAR, street VARCHAR, house_nbr VARCHAR,
    lon DOUBLE, lat DOUBLE, nis9_code VARCHAR, capakey VARCHAR, geocoded BOOLEAN
"""


def _write_fixture(path: Path) -> None:
    con = duckdb.connect()
    con.execute(f"""
        COPY (
            SELECT * FROM (VALUES
                ('1','EST','0857.474.555','0857474555','2.123','Vegan Bistro','56101','OND','9000','Gent','Vrijdagmarkt','1',3.72,51.05,'44021A00-','C1',true),
                ('2','ENT','0420 383 548','0420383548',NULL,'Boekenwinkel','47610','BV','9050','Gentbrugge','Steenweg','10',3.75,51.03,'44021B00-','C2',false)
            ) AS t(kbo_id, entity_type, enterprise_number, ent, establishment_number, name, nace5, juridical_form, postal, city, street, house_nbr, lon, lat, nis9_code, capakey, geocoded)
        ) TO '{path}' (FORMAT PARQUET)
    """)


def _target(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("ATTACH ':memory:' AS pg")
    con.execute("CREATE SCHEMA pg.droomzaak")
    con.execute(f"CREATE TABLE pg.droomzaak.business_registry ({COLUMNS_DDL})")


def test_load_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "CANONICAL", tmp_path)
    _write_fixture(tmp_path / "business_registry_gent.parquet")

    con = duckdb.connect()
    _target(con)

    assert loader.load_canonical(con, "business_registry") == 2
    # A second run DELETE+INSERTs — must not duplicate.
    assert loader.load_canonical(con, "business_registry") == 2
    assert (
        con.sql("SELECT count(*) FROM pg.droomzaak.business_registry").fetchone()[0]
        == 2
    )


def test_unknown_table_raises():
    with pytest.raises(KeyError):
        loader.load_canonical(duckdb.connect(), "does_not_exist")


def test_missing_parquet_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "CANONICAL", tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.load_canonical(duckdb.connect(), "business_registry")


def test_resolve_dsn_skips_non_uri_placeholder(monkeypatch):
    """A comment/placeholder in the preferred var must not shadow a valid fallback."""
    monkeypatch.setattr(loader, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("DROOMZAAK_PG_DSN", "# the failover DSN; unset for the demo")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://u:p@host:5432/postgres")
    assert loader.resolve_dsn() == "postgresql://u:p@host:5432/postgres"


def test_resolve_dsn_raises_when_no_valid_uri(monkeypatch):
    monkeypatch.setattr(loader, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("DROOMZAAK_PG_DSN", "")
    monkeypatch.setenv("SUPABASE_DB_URL", "not-a-uri")
    with pytest.raises(RuntimeError, match="No usable Postgres DSN"):
        loader.resolve_dsn()


def test_column_drift_raises(tmp_path, monkeypatch):
    """A target table whose column count differs from the Parquet must fail loudly."""
    monkeypatch.setattr(loader, "CANONICAL", tmp_path)
    _write_fixture(tmp_path / "business_registry_gent.parquet")

    con = duckdb.connect()
    con.execute("ATTACH ':memory:' AS pg")
    con.execute("CREATE SCHEMA pg.droomzaak")
    con.execute(
        "CREATE TABLE pg.droomzaak.business_registry (kbo_id VARCHAR, ent VARCHAR)"
    )  # 2 cols, not 17

    with pytest.raises(ValueError, match="drifted"):
        loader.load_canonical(con, "business_registry")
