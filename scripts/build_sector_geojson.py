#!/usr/bin/env python
"""Build the RENDER-tier sector-polygon asset for the Droomkaart score heatmap.

The warehouse stores sector geometry as WKB bytea with **no PostGIS** ("usable
polygons live in the render tier" — see supabase/schema.sql). So the frontend
can't get polygons from the DataGateway; it needs a cached GeoJSON. This script
produces that asset from the same source the pipeline used — the Gent ODS layer
`statistische-sectoren-gent` (WGS84 GeoJSON) — keyed by the canonical nis9_code
(= GENT_REFNIS5 "44021" + sectorcode) so it joins to score_locations output.

    uv run python scripts/build_sector_geojson.py

Idempotent (overwrites the asset). Build-time only — the committed asset is what
the demo loads, so the live ODS call is never on the runtime path.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "gent-sectors.geojson"

GENT_REFNIS5 = "44021"  # mirrors pipelines/droomzaak/_common.py
ODS_URL = (
    "https://data.stad.gent/api/explore/v2.1/catalog/datasets/"
    "statistische-sectoren-gent/exports/geojson"
)
COORD_DP = 5  # ~1.1 m precision — ample for sector boundaries, ~halves the bytes


def _round(coords):
    """Recursively round coordinate numbers to COORD_DP decimals."""
    if isinstance(coords, (int, float)):
        return round(coords, COORD_DP)
    return [_round(c) for c in coords]


def build() -> Path:
    print(f"Fetching Ghent statistical sectors from ODS…\n  {ODS_URL}")
    with urllib.request.urlopen(ODS_URL, timeout=90) as resp:  # noqa: S310 (trusted gov source)
        src = json.load(resp)

    features = []
    skipped = 0
    for feat in src.get("features", []):
        props = feat.get("properties") or {}
        sectorcode = props.get("sectorcode")
        if not sectorcode:
            skipped += 1
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": feat["geometry"]["type"],
                "coordinates": _round(feat["geometry"]["coordinates"]),
            },
            "properties": {
                "nis9_code": f"{GENT_REFNIS5}{sectorcode}",
                "sectornaam": props.get("sectornaam"),
                "wijknr": props.get("wijknr"),
            },
        })

    fc = {"type": "FeatureCollection", "features": features}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    kb = OUT.stat().st_size // 1024
    print(f"Wrote {len(features)} sectors ({skipped} skipped) → {OUT}  ({kb} KB)")
    print(f"  sample nis9_code: {features[0]['properties']['nis9_code']!r}")
    return OUT


if __name__ == "__main__":
    build()
