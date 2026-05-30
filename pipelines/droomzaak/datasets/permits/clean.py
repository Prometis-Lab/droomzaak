"""Canonical: permits_events_gent — Omgevingsloket environment-permit applications (Q4).

Source: three Vlaanderen Omgevingsloket GeoPackages (iioa = classified activities,
kh = retail handelingen, gd = stedenbouwkundige handelingen). No municipality column,
so we clip to the Gent bbox (EPSG:31370) via GDAL's spatial filter (pushdown — the gd
layer is 760k rows Flanders-wide), then point-in-polygon the centroid onto sectors.
One row per application.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import connect, load_sectors, src, write  # noqa: E402

# Gent bbox in EPSG:31370 as a BOX_2D for ST_Read's spatial_filter_box pushdown.
BBOX_31370 = "{'min_x': 94000.0, 'min_y': 190000.0, 'max_x': 110000.0, 'max_y': 205000.0}::BOX_2D"

# layer kind -> (folder, SQL expr for a human-readable `detail` field)
LAYERS = {
    "iioa": ("lu_omv_iioa_v2", "omschrijving_projecttype || ' / ' || klasse_iioa"),
    "kh": ("lu_omv_kh_v2", "handeling_omschrijving"),
    "gd": ("lu_omv_gd_v2", "handeling_omschrijving"),
}


def build() -> Path:
    con = connect()
    load_sectors(con)

    parts = []
    for kind, (folder, detail_expr) in LAYERS.items():
        gpkg = src(f"raw/vlaanderen-omgevingsloket/{folder}/*/{folder}.lb72.gpkg")
        parts.append(f"""
            SELECT '{kind}' AS kind,
                   CAST(projectnummer AS VARCHAR) AS projectnummer,
                   CAST(project_type_code AS VARCHAR) AS project_type_code,
                   CAST(aanvrager AS VARCHAR) AS aanvrager,
                   TRY_CAST(datum_indiening AS TIMESTAMP) AS datum_indiening,
                   CAST(huidige_toestand AS VARCHAR) AS huidige_toestand,
                   CAST({detail_expr} AS VARCHAR) AS detail,
                   ST_Transform(ST_Centroid(geom), 'EPSG:31370', 'EPSG:4326', always_xy := true) AS pt
            FROM ST_Read('{gpkg}', spatial_filter_box := {BBOX_31370})
        """)
    union = "\nUNION ALL\n".join(parts)
    select = f"""
        WITH e AS ({union})
        SELECT
            e.kind, e.projectnummer, e.project_type_code, e.aanvrager,
            e.datum_indiening, e.huidige_toestand, e.detail,
            ST_X(e.pt) AS lon, ST_Y(e.pt) AS lat,
            s.nis9_code, s.wijknr
        FROM e
        LEFT JOIN sectors s ON ST_Contains(s.geom, e.pt)
    """
    return write(con, select, "permits_events_gent")


if __name__ == "__main__":
    build()
