# permit_rules Curated Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land a curated, human-verified `permit_rules` decision table (horeca deep, retail/consultant thin scaffolds) in the `droomzaak` Postgres warehouse, ready for the future `permit_checklist_for` tool.

**Architecture:** A hand-authored `permit_rules.yaml` (the source-of-truth artifact) is validated and materialized to canonical Parquet by `datasets/permit_rules/clean.py`, then loaded into a migration-managed `droomzaak.permit_rules` table by the existing position-based loader. `applies_when`/`cost` ride as JSON-encoded `text`; `nace_prefix`/`depends_on` as `text[]`. No runtime scraping — the YAML is curated once (Friday) from official sources and frozen.

**Tech Stack:** Python 3 (uv venv), DuckDB 1.4.3, PyYAML (new dep), Postgres 16 on Supabase, pytest. Follows the existing `pipelines/droomzaak/` clean→load pattern.

**Design doc:** [`docs/specs/2026-05-30-permit-rules-curated-config-design.md`](2026-05-30-permit-rules-curated-config-design.md)

**Branch:** `feat/permit-rules` (already created off `feat/data-pipeline`).

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `pipelines/droomzaak/datasets/permit_rules/permit_rules.yaml` | The curated decision table (attribute vocabulary + rules). Hand-authored, human-verified, committed. | Create |
| `pipelines/droomzaak/datasets/permit_rules/clean.py` | Load + validate the YAML, materialize one canonical Parquet (`permit_rules.parquet`). | Create |
| `pipelines/droomzaak/tests/test_permit_rules.py` | Validation-logic tests (no DB, no network) + a parquet-shape test. | Create |
| `pipelines/droomzaak/tests/test_load_to_supabase.py` | Add a `permit_rules` loader idempotency test. | Modify |
| `pipelines/droomzaak/build.py` | Add `permit_rules` to the run `ORDER`. | Modify |
| `pipelines/droomzaak/load_to_supabase.py` | Add `permit_rules` to `TABLES`. | Modify |
| `supabase/migrations/<ts>_add_permit_rules_table.sql` | Idempotent DDL for `droomzaak.permit_rules`. | Create (operator applies) |
| `supabase/schema.sql` | Regenerated mirror including `permit_rules`. | Modify |
| `supabase/QUICK_REFERENCE.md` | Document the new table. | Modify |
| `pyproject.toml` / `uv.lock` | Add `pyyaml`. | Modify (via `uv add`) |

**Column order (the loader contract — identical in YAML→clean.py SELECT, migration, and tests):**
`permit, nace_prefix, applies_when, official_url, explainer, cost, lead_time_days, depends_on, status, source_url`

---

## Task 1: YAML schema contract + validation

Establish the data contract test-first: the validator defines what a valid `permit_rules.yaml` is, and a small seed YAML satisfies it. Content gets fleshed out in Task 5.

**Files:**
- Create: `pipelines/droomzaak/datasets/permit_rules/permit_rules.yaml`
- Create: `pipelines/droomzaak/datasets/permit_rules/clean.py` (load + validate only; `build()` added in Task 2)
- Create: `pipelines/droomzaak/tests/test_permit_rules.py`
- Modify: `pyproject.toml`, `uv.lock`

- [ ] **Step 1: Add the PyYAML dependency**

Run: `uv add pyyaml`
Expected: `pyproject.toml` gains `pyyaml`, `uv.lock` updated, install succeeds.

- [ ] **Step 2: Write the seed `permit_rules.yaml`**

A minimal-but-real seed exercising every validation branch (all three `cost` variants, a `depends_on` chain, the attribute vocabulary). URLs below are the verified ones from data-shortlist §4a.

```yaml
# permit_rules.yaml — Droomzaak Chapter-4 permit decision table (curated, frozen).
#
# Source-of-truth artifact: hand-authored + human-verified from official sources, never
# scraped at runtime. Each rule carries a `source_url` for provenance. See
# docs/specs/2026-05-30-permit-rules-curated-config-design.md.
#
# `attributes` is the inline vocabulary `applies_when` keys off. The future canonical
# sector_attributes.yaml MUST adopt these keys verbatim.

attributes:
  horeca:                       # NACE 56.*
    serves_alcohol: [none, gegiste, sterke]
    seating: [none, indoor, terrace]
    takeaway_only: bool
    hot_kitchen_frying: bool
    capacity_seats: int
    renovation: bool
    music: bool
  retail:                       # NACE 47.*
    food_retail: bool
    signage: bool
  consultant:                   # NACE 70/74.*
    home_based: bool
    employees: int

rules:
  - permit: "KBO-inschrijving + BTW-activering"
    nace_prefix: ["56", "47", "70", "74"]
    applies_when: {}                       # every business
    official_url: "https://economie.fgov.be/nl/themas/ondernemingen/een-onderneming/de-administratieve-stappen-om/inschrijving-bij-de-kruispuntbank"
    source_url: "https://economie.fgov.be/nl/themas/ondernemingen/een-onderneming/de-administratieve-stappen-om/inschrijving-bij-de-kruispuntbank"
    explainer: "Inschrijving in de Kruispuntbank van Ondernemingen via een erkend ondernemingsloket, daarna BTW-activering bij MyMinfin."
    cost: {type: fixed, eur: 105.50, period: one_time, note: "KBO-loket inschrijving 2026; BTW gratis via MyMinfin"}
    lead_time_days: 1
    depends_on: []
    status: active

  - permit: "Horeca-attest"
    nace_prefix: ["56"]
    applies_when: {}                       # any horeca
    official_url: "https://stad.gent/nl/ondernemen/horeca/horeca-attest"
    source_url: "https://stad.gent/nl/ondernemen/horeca/horeca-attest"
    explainer: "Umbrella-attest voor een horecazaak in Gent; bundelt o.a. de brandveiligheidscontrole."
    cost: {type: none_published}
    lead_time_days: 45
    depends_on: ["KBO-inschrijving + BTW-activering"]
    status: active

  - permit: "Drankvergunning gegiste dranken"
    nace_prefix: ["56"]
    applies_when: {serves_alcohol: [gegiste, sterke]}
    official_url: "https://stad.gent/nl/ondernemen/horeca/drankvergunning"
    source_url: "https://stad.gent/nl/ondernemen/horeca/drankvergunning"
    explainer: "Vergunning voor het schenken van gegiste dranken (bier en wijn) in een vaste drankgelegenheid."
    cost: {type: none_published}
    lead_time_days: 30
    depends_on: ["Horeca-attest"]
    status: active

  - permit: "Unisono (SABAM + billijke vergoeding)"
    nace_prefix: ["56", "47"]
    applies_when: {music: true}
    official_url: "https://www.unisono.be"
    source_url: "https://www.unisono.be"
    explainer: "Vergoeding voor publiek afgespeelde muziek; bedrag via de officiële simulator (m²/type zaak)."
    cost: {type: simulator, url: "https://www.unisono.be/nl/tarieven-en-simulatoren"}
    lead_time_days: 0
    depends_on: []
    status: active
```

- [ ] **Step 3: Write the failing validation test**

```python
"""permit_rules curated-config tests — pure validation logic, no DB, no network."""

from __future__ import annotations

import sys
from pathlib import Path

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


def test_missing_source_url_raises():
    doc = _good_doc()
    doc["rules"][0]["source_url"] = ""
    with pytest.raises(ValueError, match="source_url"):
        clean.validate(doc)
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `uv run pytest pipelines/droomzaak/tests/test_permit_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clean'` (or `AttributeError: module 'clean' has no attribute 'validate'`).

- [ ] **Step 5: Write `clean.py` (load + validate)**

```python
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
        if cost.get("type") not in COST_TYPES:
            raise ValueError(f"{permit}: cost.type {cost.get('type')!r} not in {COST_TYPES}")
        if cost["type"] == "fixed" and "eur" not in cost:
            raise ValueError(f"{permit}: fixed cost requires 'eur'")
        if cost["type"] == "simulator" and "url" not in cost:
            raise ValueError(f"{permit}: simulator cost requires 'url'")
        if "period" in cost and cost["period"] not in PERIODS:
            raise ValueError(f"{permit}: cost.period {cost['period']!r} not in {PERIODS}")
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `uv run pytest pipelines/droomzaak/tests/test_permit_rules.py -v`
Expected: PASS (all 8 tests).

- [ ] **Step 7: Commit**

```bash
git add pipelines/droomzaak/datasets/permit_rules/permit_rules.yaml \
        pipelines/droomzaak/datasets/permit_rules/clean.py \
        pipelines/droomzaak/tests/test_permit_rules.py \
        pyproject.toml uv.lock
git commit -m "feat(data): permit_rules YAML schema + validation"
```

---

## Task 2: Materialize the YAML to canonical Parquet

Add `build()` to `clean.py` so the validated YAML becomes `data/canonical/permit_rules.parquet` with the exact column order/types the loader expects.

**Files:**
- Modify: `pipelines/droomzaak/datasets/permit_rules/clean.py`
- Modify: `pipelines/droomzaak/tests/test_permit_rules.py`

- [ ] **Step 1: Write the failing parquet-shape test**

Append to `test_permit_rules.py`:

```python
import duckdb  # noqa: E402  (add near the top imports)


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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest pipelines/droomzaak/tests/test_permit_rules.py::test_build_writes_parquet_with_contract_columns -v`
Expected: FAIL with `AttributeError: module 'clean' has no attribute 'build'`.

- [ ] **Step 3: Add `build()` (and a `_row` helper) to `clean.py`**

Append to `clean.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest pipelines/droomzaak/tests/test_permit_rules.py -v`
Expected: PASS (all 9 tests).

- [ ] **Step 5: Smoke-run the script end-to-end**

Run: `uv run python pipelines/droomzaak/datasets/permit_rules/clean.py`
Expected: a loguru success line like `permit_rules: 4 rows → data/canonical/permit_rules.parquet`.

- [ ] **Step 6: Commit**

```bash
git add pipelines/droomzaak/datasets/permit_rules/clean.py \
        pipelines/droomzaak/tests/test_permit_rules.py
git commit -m "feat(data): materialize permit_rules to canonical parquet"
```

---

## Task 3: Migration for `droomzaak.permit_rules`

**This task involves a DDL change. Per CLAUDE.md rule 11 the Supabase MCP is read-only — DDL is an idempotent script the operator runs, then folded into a migration. STOP and wait for the operator to apply it before Task 4's load step. Use the `supabase-schema-sync` skill and the `warehouse-schema-expert` agent for this task.**

**Files:**
- Create: `supabase/migrations/<timestamp>_add_permit_rules_table.sql`
- Modify: `supabase/schema.sql`, `supabase/QUICK_REFERENCE.md`

- [ ] **Step 1: Author the idempotent migration**

Create `supabase/migrations/20260530XXXXXX_add_permit_rules_table.sql` (use the actual apply timestamp; mirror the header style of `20260530154400_add_footfall_demand_tables.sql`). **Column order MUST match `clean.COLUMNS`.** The timestamp **must sort after** the latest existing migration `20260530154400_add_footfall_demand_tables.sql` — a real apply-time stamp guarantees this; do not hand-pick an earlier one.

```sql
-- Migration: add the curated Chapter-4 permit_rules decision table.
-- Idempotent (CREATE … IF NOT EXISTS) — safe to re-run / redeploy.
--
-- Column ORDER matches pipelines/droomzaak/datasets/permit_rules/clean.py COLUMNS so the
-- loader's position-based INSERT … SELECT * lines up. applies_when/cost are JSON-encoded
-- TEXT (the permit_checklist_for tool parses them in Python — no SQL-side JSON needed).

CREATE SCHEMA IF NOT EXISTS droomzaak;

CREATE TABLE IF NOT EXISTS droomzaak.permit_rules (
    permit         TEXT,
    nace_prefix    TEXT[],
    applies_when   TEXT,
    official_url   TEXT,
    explainer      TEXT,
    cost           TEXT,
    lead_time_days BIGINT,
    depends_on     TEXT[],
    status         TEXT,
    source_url     TEXT
);
```

- [ ] **Step 2: STOP — hand the script to the operator to apply**

The operator runs the migration against the loader DSN (direct/session connection, port 5432), exactly as prior migrations were applied. Do not apply DDL via the MCP. Wait for confirmation the table exists.

- [ ] **Step 3: Verify the table via the read-only MCP**

Confirm `droomzaak.permit_rules` exists with the 10 columns in order (e.g. `list_tables`, or a read-only `execute_sql` against `information_schema.columns`).

- [ ] **Step 4: Fold into the local mirror**

Per `supabase-schema-sync`: regenerate `supabase/schema.sql` so it includes `permit_rules`, and add a `permit_rules` entry to `supabase/QUICK_REFERENCE.md` describing the columns + the JSON-as-text note.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/ supabase/schema.sql supabase/QUICK_REFERENCE.md
git commit -m "feat(supabase): add permit_rules table migration"
```

---

## Task 4: Wire the loader + pipeline

Register `permit_rules` in the loader and the build harness, prove idempotency in-memory, then load to Supabase.

**Files:**
- Modify: `pipelines/droomzaak/load_to_supabase.py` (the `TABLES` dict)
- Modify: `pipelines/droomzaak/build.py` (the `ORDER` list)
- Modify: `pipelines/droomzaak/tests/test_load_to_supabase.py`

> **Caveat — `permit_rules` is the first table to load `text[]` columns.** Every existing
> entry in `TABLES` is scalar (or `bytea` for the geo spine). The in-memory test below uses a
> DuckDB-native `VARCHAR[]` target, which proves the loader's SQL + idempotency + column-count
> guard but does **not** exercise the real DuckDB-postgres `LIST → text[]` write path. That can
> only be confirmed against live PG (Step 7).

- [ ] **Step 1: Write the failing loader test**

Append to `test_load_to_supabase.py`:

```python
def _write_permit_rules_fixture(path: Path) -> None:
    con = duckdb.connect()
    con.execute(f"""
        COPY (
            SELECT * FROM (VALUES
                ('KBO', ['56','47'], '{{}}', 'https://e/x', 'baseline',
                 '{{"type":"fixed","eur":105.5}}', 1, [], 'active', 'https://e/x'),
                ('Horeca-attest', ['56'], '{{}}', 'https://s/h', 'umbrella',
                 '{{"type":"none_published"}}', 45, ['KBO'], 'active', 'https://s/h')
            ) AS t(permit, nace_prefix, applies_when, official_url, explainer,
                   cost, lead_time_days, depends_on, status, source_url)
        ) TO '{path}' (FORMAT PARQUET)
    """)


def _permit_rules_target(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("ATTACH ':memory:' AS pg")
    con.execute("CREATE SCHEMA pg.droomzaak")
    con.execute("""
        CREATE TABLE pg.droomzaak.permit_rules (
            permit VARCHAR, nace_prefix VARCHAR[], applies_when VARCHAR,
            official_url VARCHAR, explainer VARCHAR, cost VARCHAR,
            lead_time_days BIGINT, depends_on VARCHAR[], status VARCHAR, source_url VARCHAR
        )
    """)


def test_permit_rules_load_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "CANONICAL", tmp_path)
    _write_permit_rules_fixture(tmp_path / "permit_rules.parquet")

    con = duckdb.connect()
    _permit_rules_target(con)

    assert loader.load_canonical(con, "permit_rules") == 2
    assert loader.load_canonical(con, "permit_rules") == 2  # DELETE+INSERT, no dupes
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest pipelines/droomzaak/tests/test_load_to_supabase.py::test_permit_rules_load_is_idempotent -v`
Expected: FAIL with `KeyError: "Unknown table 'permit_rules'..."`.

- [ ] **Step 3: Register `permit_rules` in the loader**

In `load_to_supabase.py`, add to the `TABLES` dict (stem equals table name — `clean.py` writes `permit_rules.parquet`):

```python
    "permit_rules": "permit_rules",
```

- [ ] **Step 4: Run the loader test to verify it passes**

Run: `uv run pytest pipelines/droomzaak/tests/test_load_to_supabase.py -v`
Expected: PASS (all existing tests + the new one).

- [ ] **Step 5: Add `permit_rules` to the build order**

In `build.py`, append `"permit_rules"` to the `ORDER` list. It has no geo/spine dependency, so position is free; append it after `"permits"` to keep the two permit datasets adjacent.

- [ ] **Step 6: Run the full build to confirm integration**

Run: `uv run python pipelines/droomzaak/build.py`
Expected: the run reaches `building permit_rules …` and emits the `permit_rules: N rows` success line with no errors. (Requires the T7 sources the other datasets read; if T7 is absent, instead run `uv run python pipelines/droomzaak/datasets/permit_rules/clean.py` alone and note the full build is T7-gated.)

- [ ] **Step 7: Load to Supabase (operator / live DB)**

With `DROOMZAAK_PG_DSN` (or `SUPABASE_DB_URL`) set to the session connection:
Run: `uv run python pipelines/droomzaak/load_to_supabase.py permit_rules`
Expected: `permit_rules: N rows → pg.droomzaak.permit_rules (source had N)`.
Verify via the read-only MCP:
- `SELECT count(*) FROM droomzaak.permit_rules` equals the YAML rule count.
- **Array round-trip (the unit test can't prove this):** `SELECT permit, nace_prefix[1], array_length(nace_prefix, 1), depends_on FROM droomzaak.permit_rules LIMIT 3` — confirm `nace_prefix`/`depends_on` are real PG arrays (not a stringified `"['56']"`). If the load errored or these came back as text, the `LIST → text[]` marshaling failed and needs a `SELECT_LIST["permit_rules"]` cast — escalate to `warehouse-schema-expert`.

- [ ] **Step 8: Commit**

```bash
git add pipelines/droomzaak/load_to_supabase.py pipelines/droomzaak/build.py \
        pipelines/droomzaak/tests/test_load_to_supabase.py
git commit -m "feat(data): wire permit_rules into loader + build"
```

---

## Task 5: Curate the full horeca catalogue + thin scaffolds

Flesh out `permit_rules.yaml` from the seed to the full demo scope. This is a **human-in-the-loop curation pass**, not autonomous TDD — the validation test (Task 1) is the safety net that must stay green throughout, and a human verifies every trigger + `depends_on` order. Use the `browser-data-curation` skill for the WAF-blocked/JS sources.

**Files:**
- Modify: `pipelines/droomzaak/datasets/permit_rules/permit_rules.yaml`

- [ ] **Step 1: WebFetch the clean-HTML official pages and draft rows**

For each, draft/confirm the rule fields (`official_url`, `explainer`, `cost`, `lead_time_days`, `depends_on`). Verified targets from data-shortlist §4a:
- `stad.gent` — horeca-attest, drankvergunning (gegiste + sterke → `+college machtiging`, strafregister 596), terrasvergunning (public domain, needs horeca-attest, 9-yr term, annual belasting → `cost: simulator`).
- `favv-afsca.be` — FAVV toelating (food handling; reg free, heffing starter ~€100.58/y → `cost: {type: fixed, eur: 100.58, period: annual, approx: true}`).
- `vlaanderen.be/epb-eisen` — EPB (renovation needing OMV → `cost: simulator`).
- `unisono.be` — Unisono (public music → `cost: simulator`).
- `economie.fgov.be` — KBO + BTW baseline (already seeded).

- [ ] **Step 2: Browser-curate the WAF-blocked / JS sources**

Invoke the `browser-data-curation` skill (Claude-in-Chrome MCP) for:
- **VLAREM-wegwijzer** (`vlaremwegwijzer.navigator.emis.vito.be`) — omgevingsvergunning milieu: frying → **rubriek 45.4.d**; cooling ≥5 kW → **16.3.2°**; class logic (melding kl.3 / vergunning kl.2). Encode as one or more rules with `applies_when: {hot_kitchen_frying: true}` etc.
- VLAIO (`vlaio.be`, 403) — only if a permit-relevant fact is needed (subsidies are a separate artifact).

- [ ] **Step 3: Add the brandweer + remaining horeca rows**

Brandveiligheidsattest (`applies_when: {capacity_seats: …}` / ≥100 m² → folded into the 45-werkdagen horeca-attest track; reference `brandweerzonecentrum.be`). Ensure the full §4a critical-path `depends_on` chain resolves: soc.verzekeringsfonds → KBO → BTW → FAVV → drank → omgevings → horeca-attest → terras → Unisono → EPB.

- [ ] **Step 4: Add the retail + consultant thin scaffolds**

- retail (`nace_prefix: ["47"]`): FAVV (`applies_when: {food_retail: true}`), signage permit (`applies_when: {signage: true}`), KBO/BTW baseline (already covers 47).
- consultant (`nace_prefix: ["70","74"]`): KBO/BTW baseline only (extend the baseline rule's `nace_prefix`; home-based/employees rarely add permits — note this in a YAML comment rather than inventing rules).

- [ ] **Step 5: Keep the validation test green after every edit**

Run: `uv run pytest pipelines/droomzaak/tests/test_permit_rules.py -v`
Expected: PASS. Fix any `unknown applies_when key` (add the attribute to the `attributes` vocabulary) or dangling `depends_on` immediately.

- [ ] **Step 6: Human verification gate**

A human confirms: every `official_url` resolves to a live official page; trigger logic matches the source; `depends_on` ordering is correct; every calculator-based fee is `cost: simulator` (no invented numbers). Record the verifier + date in a YAML header comment.

- [ ] **Step 7: Re-materialize and reload**

Run: `uv run python pipelines/droomzaak/datasets/permit_rules/clean.py`
then `uv run python pipelines/droomzaak/load_to_supabase.py permit_rules` (operator/live DB).
Expected: row count = the new rule count.

- [ ] **Step 8: Commit**

```bash
git add pipelines/droomzaak/datasets/permit_rules/permit_rules.yaml
git commit -m "feat(data): curate full horeca permit_rules + retail/consultant scaffolds"
```

---

## Out of scope (separate follow-ups)

- **`permit_checklist_for` agent tool** — the thin Soda Straw → Postgres wrapper that reads `permit_rules` and evaluates `applies_when` against a profile's `attributes`. Build via `/new-tool` + the `add-agent-tool` + `soda-straw-data-tool` skills.
- **`sector_attributes.yaml`** — the canonical company-topology taxonomy. Must adopt the inline `attributes:` keys from `permit_rules.yaml` verbatim.

## Plan-wide verification

- `uv run pytest pipelines/droomzaak/tests/ -v` — all green (validation + parquet shape + loader idempotency).
- `uv run python pipelines/droomzaak/datasets/permit_rules/clean.py` — produces `permit_rules.parquet`.
- `droomzaak.permit_rules` row count (via read-only MCP) equals the YAML rule count.
- Manual: every horeca `official_url` resolves; every `simulator` cost has no invented number.
