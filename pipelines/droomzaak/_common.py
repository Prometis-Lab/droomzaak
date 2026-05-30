"""Shared paths, constants, and canonical join-key helpers for the Droomzaak build.

Every cleaning script under `datasets/<name>/clean.py` reads source data from the
T7 drive and writes one canonical Parquet to `data/canonical/` (repo-root, gitignored).
The canonical join keys these scripts produce are documented in `joins.md` — keep the
two in sync.

Canonical outputs land under the repo-root gitignored `data/` tier (not next to the
scripts, which live in the committed `pipelines/` tree). Cleaning scripts import from
`_common` via `parents[2]`, which resolves to this directory.

Run a single dataset:   uv run python pipelines/droomzaak/datasets/<name>/clean.py
Run everything:         uv run python pipelines/droomzaak/build.py
"""

from __future__ import annotations

import os
from glob import glob
from pathlib import Path

import duckdb
from loguru import logger

# --- locations -------------------------------------------------------------
DATA_ROOT = Path(os.environ.get("MAP_PILOT_DATA_DIR", "/Volumes/T7/map-pilot-data"))
DROOMZAAK = Path(__file__).resolve().parent
# Canonical outputs land in the repo-root data tier (gitignored), NOT under pipelines/.
REPO_ROOT = DROOMZAAK.parents[1]
CANONICAL = REPO_ROOT / "data" / "canonical"

# The spatial spine — Ghent statistical sectors with WGS84 geometry (built by
# geo_admin/clean.py). Point layers point-in-polygon against it via load_sectors().
GEO_SECTORS = CANONICAL / "geo_sectors_gent.parquet"

# Source files on T7. Globbed so a fresher snapshot (different date suffix) is picked up.
KBO_FLAT = "snapshots/kbo/kbo-entities-flat/kbo_*.parquet"
ACADEMIC_ENTERPRISES = (
    "snapshots/kbo/kbo-academic-enterprises/kbo_enterprises_*.parquet"
)
GEOCODE_ENTERPRISES = (
    "snapshots/kbo/kbo-academic-enterprises-geocoded/kbo_enterprises_*.parquet"
)
GEOCODE_BUSINESS_UNITS = (
    "snapshots/kbo/kbo-academic-business-units-geocoded/kbo_business_units_*.parquet"
)
BELFIRST = "raw/belfirst/belfirst-jaarrekeningen-gent-*/*/jaarrekeningen.parquet"

# --- Ghent slice -----------------------------------------------------------
GENT_REFNIS5 = "44021"
GENT_POSTCODE_MIN, GENT_POSTCODE_MAX = 9000, 9052

# --- canonical join-key SQL expressions (DuckDB dialect) -------------------
# See joins.md for why each normalization is needed.


def norm_ent(col: str) -> str:
    """Enterprise number → 10-digit string (KBO uses dots, Belfirst spaces, VAT a 'BE' prefix).

    Returns NULL when the source has no digits (Belfirst ships ~6.5k rows with a blank
    `Ondernemingsnummer`). NULL never satisfies a join, so this prevents an empty-string
    `ent` from cartesian-exploding any `USING(ent)` link.
    """
    return f"nullif(regexp_replace({col}, '[^0-9]', '', 'g'), '')"


def nace5(col: str) -> str:
    """NACE-BEL → undotted 5-digit string (curated config writes '56.101', the data uses '56101')."""
    return f"replace({col}, '.', '')"


def nace4(col: str) -> str:
    """NACE-BEL → undotted 4-digit class (Statbel bankruptcies are keyed at 4 digits)."""
    return f"left({nace5(col)}, 4)"


def gent_postcode_filter(col: str) -> str:
    return f"TRY_CAST({col} AS INTEGER) BETWEEN {GENT_POSTCODE_MIN} AND {GENT_POSTCODE_MAX}"


def lonlat(x: str = "x", y: str = "y") -> tuple[str, str]:
    """SQL expressions reprojecting EPSG:3812 (Belgian Lambert 2008) → WGS84 lon/lat."""
    pt = (
        f"ST_Transform(ST_Point({x}, {y}), 'EPSG:3812', 'EPSG:4326', always_xy := true)"
    )
    return f"ST_X({pt})", f"ST_Y({pt})"


# --- io --------------------------------------------------------------------
def src(pattern: str) -> str:
    """Resolve a globbed source pattern under DATA_ROOT to its newest match."""
    matches = sorted(glob(str(DATA_ROOT / pattern)))
    if not matches:
        raise FileNotFoundError(f"No source file matches {DATA_ROOT / pattern}")
    return matches[-1]


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    return con


def load_sectors(con: duckdb.DuckDBPyConnection) -> None:
    """Register a TEMP `sectors(nis9_code, wijknr, geom)` table from geo_sectors_gent.

    `geom` is WGS84. Spatial cleaning scripts assign each feature its sector with
    `LEFT JOIN sectors s ON ST_Contains(s.geom, ST_Point(lon, lat))`. Requires
    geo_admin/clean.py to have run first.
    """
    if not GEO_SECTORS.exists():
        raise FileNotFoundError(
            "Run geo_admin/clean.py first (needs geo_sectors_gent.parquet)"
        )
    con.execute(f"""
        CREATE TEMP TABLE sectors AS
        SELECT nis9_code, wijknr, geom_wkb AS geom
        FROM read_parquet('{GEO_SECTORS}')
    """)


def write(con: duckdb.DuckDBPyConnection, select_sql: str, name: str) -> Path:
    """Materialize a SELECT to data/canonical/<name>.parquet and log the row count."""
    CANONICAL.mkdir(parents=True, exist_ok=True)
    out = CANONICAL / f"{name}.parquet"
    con.execute(f"COPY ({select_sql}) TO '{out}' (FORMAT PARQUET)")
    n = con.sql(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
    logger.success(f"{name}: {n:,} rows → {out.relative_to(REPO_ROOT)}")
    return out
