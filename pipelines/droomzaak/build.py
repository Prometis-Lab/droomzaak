"""Run every Droomzaak cleaning script in dependency order.

    uv run python pipelines/droomzaak/build.py

Order matters: geo_admin builds the spatial spine (geo_sectors_gent) that every
point-in-polygon script depends on, so it runs first. kbo_correspondence produces the
geocode bridge that kbo_entities_flat consumes via the address join.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from loguru import logger

DATASETS = Path(__file__).resolve().parent / "datasets"
# Dependency order, not alphabetical. geo_admin first: it produces geo_sectors_gent,
# the spatial spine every point-in-polygon script loads via _common.load_sectors.
ORDER = [
    "geo_admin",
    "kbo_correspondence",
    "kbo_entities_flat",
    "belfirst",
    "nace_ref",
    "demographics",
    "statbel_peers",
    "immo_sector",
    "transit_access",
    "footfall",  # depends on transit_access (reads transit_access_sector_gent)
    "demand_proxies",
    "disruption",
    "permits",
    "gent_points",
    "kbo_history",
]


def _run(name: str) -> None:
    path = DATASETS / name / "clean.py"
    spec = importlib.util.spec_from_file_location(f"droomzaak_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.build()


def main() -> None:
    for name in ORDER:
        logger.info(f"building {name} …")
        _run(name)
    logger.success("droomzaak canonical build complete")


if __name__ == "__main__":
    main()
