"""Run every Droomzaak cleaning script in dependency order.

    uv run python pipelines/droomzaak/build.py

Order matters: geo_admin builds the spatial spine; kbo_correspondence produces the
geocode bridge that kbo_entities_flat (business_registry) consumes by address.

Cleaning scripts land here one-by-one; add each name to ORDER in dependency order as
it lands.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from loguru import logger

DATASETS = Path(__file__).resolve().parent / "datasets"
# Dependency order, not alphabetical.
ORDER = ["geo_admin", "kbo_correspondence", "kbo_entities_flat"]


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
