"""Canonical: permit_rules — curated Chapter-4 permit decision table (Section B config).

Hand-authored YAML (`permit_rules.yaml` in this dir), NOT a fetched dataset. One row per
permit rule. `applies_when`/`cost` are JSON-encoded text; `nace_prefix`/`depends_on` are
text arrays. Column ORDER (see COLUMNS) is the loader contract — keep it in sync with the
migration's CREATE TABLE.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _common import connect, write  # noqa: E402

HERE = Path(__file__).resolve().parent
YAML_PATH = HERE / "permit_rules.yaml"

COLUMNS = (
    "permit", "nace_prefix", "applies_when", "official_url", "explainer",
    "cost", "lead_time_days", "depends_on", "status", "source_url",
)
REQUIRED_KEYS = set(COLUMNS) - {"lead_time_days"}  # lead_time_days may be null
COST_TYPES = {"none_published", "fixed", "simulator"}
PERIODS = {"one_time", "annual"}
STATUSES = {"active", "ended_2025"}


def load() -> dict:
    return yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))


def validate(doc: dict) -> None:
    """Raise ValueError on any contract violation; return None when the doc is valid."""
    attributes = doc.get("attributes", {})
    # Keys are flattened across ALL sectors deliberately (no nace→sector map in this
    # artifact). Trade-off: a mis-sectored trigger (e.g. a horeca rule keyed on the
    # retail-only `food_retail`) is NOT caught here — Task 5 human verification covers it.
    known_attr_keys = {k for sector in attributes.values() for k in sector}
    rules = doc["rules"]
    names = {r["permit"] for r in rules}

    for r in rules:
        permit = r.get("permit", "<unnamed>")
        missing = REQUIRED_KEYS - r.keys()
        if missing:
            raise ValueError(f"{permit}: missing keys {sorted(missing)}")
        if not isinstance(r["applies_when"], dict):
            raise ValueError(f"{permit}: applies_when must be a mapping")
        for key in r["applies_when"]:
            if key not in known_attr_keys:
                raise ValueError(f"{permit}: unknown applies_when key {key!r}")
        for dep in r["depends_on"]:
            if dep not in names:
                raise ValueError(f"{permit}: depends_on {dep!r} is not a known permit")
        if r["status"] not in STATUSES:
            raise ValueError(f"{permit}: status {r['status']!r} not in {STATUSES}")
        if not r["source_url"]:
            raise ValueError(f"{permit}: source_url is required")
        cost = r["cost"]
        if not isinstance(cost, dict):
            raise ValueError(f"{permit}: cost must be a mapping")
        if cost.get("type") not in COST_TYPES:
            raise ValueError(f"{permit}: cost.type {cost.get('type')!r} not in {COST_TYPES}")
        if cost["type"] == "fixed" and "eur" not in cost:
            raise ValueError(f"{permit}: fixed cost requires 'eur'")
        if cost["type"] == "simulator" and "url" not in cost:
            raise ValueError(f"{permit}: simulator cost requires 'url'")
        if "period" in cost and cost["period"] not in PERIODS:
            raise ValueError(f"{permit}: cost.period {cost['period']!r} not in {PERIODS}")


def _row(rule: dict) -> list:
    """One rule → a positional row matching COLUMNS (JSON-encode the two object fields)."""
    return [
        rule["permit"],
        rule["nace_prefix"],
        json.dumps(rule["applies_when"], ensure_ascii=False),
        rule["official_url"],
        rule["explainer"],
        json.dumps(rule["cost"], ensure_ascii=False),
        rule.get("lead_time_days"),
        rule["depends_on"],
        rule["status"],
        rule["source_url"],
    ]


def build() -> Path:
    doc = load()
    validate(doc)
    con = connect()
    con.execute("""
        CREATE TEMP TABLE permit_rules_src (
            permit         VARCHAR,
            nace_prefix    VARCHAR[],
            applies_when   VARCHAR,
            official_url   VARCHAR,
            explainer      VARCHAR,
            cost           VARCHAR,
            lead_time_days BIGINT,
            depends_on     VARCHAR[],
            status         VARCHAR,
            source_url     VARCHAR
        )
    """)
    con.executemany(
        "INSERT INTO permit_rules_src VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [_row(r) for r in doc["rules"]],
    )
    return write(con, "SELECT * FROM permit_rules_src", "permit_rules")


if __name__ == "__main__":
    build()
