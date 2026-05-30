"""permit_rules curated-config tests — pure validation logic, no DB, no network."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "datasets" / "permit_rules"))
import clean  # noqa: E402


def _good_doc() -> dict:
    return {
        "attributes": {"horeca": {"serves_alcohol": ["none", "gegiste", "sterke"], "music": "bool"}},
        "rules": [
            {
                "permit": "Horeca-attest", "nace_prefix": ["56"], "applies_when": {},
                "official_url": "https://stad.gent/x", "source_url": "https://stad.gent/x",
                "explainer": "x", "cost": {"type": "none_published"},
                "lead_time_days": 45, "depends_on": [], "status": "active",
            },
            {
                "permit": "Drank", "nace_prefix": ["56"], "applies_when": {"serves_alcohol": ["gegiste"]},
                "official_url": "https://stad.gent/y", "source_url": "https://stad.gent/y",
                "explainer": "y", "cost": {"type": "simulator", "url": "https://u"},
                "lead_time_days": 30, "depends_on": ["Horeca-attest"], "status": "active",
            },
        ],
    }


def test_seed_yaml_is_valid():
    clean.validate(clean.load())  # the shipped seed must pass


def test_unknown_applies_when_key_raises():
    doc = _good_doc()
    doc["rules"][0]["applies_when"] = {"not_a_real_attr": True}
    with pytest.raises(ValueError, match="unknown applies_when key"):
        clean.validate(doc)


def test_dangling_depends_on_raises():
    doc = _good_doc()
    doc["rules"][1]["depends_on"] = ["No Such Permit"]
    with pytest.raises(ValueError, match="depends_on"):
        clean.validate(doc)


def test_bad_cost_type_raises():
    doc = _good_doc()
    doc["rules"][0]["cost"] = {"type": "free"}
    with pytest.raises(ValueError, match="cost.type"):
        clean.validate(doc)


def test_fixed_cost_requires_eur():
    doc = _good_doc()
    doc["rules"][0]["cost"] = {"type": "fixed"}
    with pytest.raises(ValueError, match="eur"):
        clean.validate(doc)


def test_simulator_cost_requires_url():
    doc = _good_doc()
    doc["rules"][0]["cost"] = {"type": "simulator"}
    with pytest.raises(ValueError, match="url"):
        clean.validate(doc)


def test_bad_period_raises():
    doc = _good_doc()
    doc["rules"][0]["cost"] = {"type": "fixed", "eur": 1.0, "period": "monthly"}
    with pytest.raises(ValueError, match="cost.period"):
        clean.validate(doc)


def test_non_dict_cost_raises():
    doc = _good_doc()
    doc["rules"][0]["cost"] = "oops"
    with pytest.raises(ValueError, match="cost must be a mapping"):
        clean.validate(doc)


def test_non_dict_applies_when_raises():
    doc = _good_doc()
    doc["rules"][0]["applies_when"] = ["music"]
    with pytest.raises(ValueError, match="applies_when must be a mapping"):
        clean.validate(doc)


def test_missing_source_url_raises():
    doc = _good_doc()
    doc["rules"][0]["source_url"] = ""
    with pytest.raises(ValueError, match="source_url"):
        clean.validate(doc)


def test_build_writes_parquet_with_contract_columns(tmp_path, monkeypatch):
    import _common  # write() reads BOTH CANONICAL and REPO_ROOT from here

    # write() ends with out.relative_to(REPO_ROOT); CANONICAL must stay *under* REPO_ROOT
    # or that call raises ValueError. Patch both, keeping CANONICAL a subdir of REPO_ROOT.
    monkeypatch.setattr(_common, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(_common, "CANONICAL", tmp_path / "canonical")
    out = clean.build()

    con = duckdb.connect()
    rel = con.execute(f"SELECT * FROM read_parquet('{out}')")
    assert [d[0] for d in rel.description] == list(clean.COLUMNS)

    rows = con.execute(f"SELECT * FROM read_parquet('{out}')").fetchall()
    assert len(rows) == len(clean.load()["rules"])  # one row per rule

    # nace_prefix is a real array; applies_when/cost are valid JSON text.
    first = con.execute(
        f"SELECT nace_prefix, applies_when, cost FROM read_parquet('{out}') LIMIT 1"
    ).fetchone()
    assert isinstance(first[0], list)
    import json as _json
    _json.loads(first[1])
    _json.loads(first[2])
