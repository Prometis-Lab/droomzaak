# Handover — permit_rules curated config live on Supabase

**2026-05-30 17:26 · track-a-backend · johannes**

## State now
The **rules half of Chapter-4 permits** is built, tested, and live. `droomzaak.permit_rules`
exists on Supabase with **12 rows loaded** (1 baseline + 8 horeca + 2 retail; consultants
covered by baseline). The pre-existing **evidence half** (`permits_events`) was already there —
together they back the future `permit_checklist_for` tool. Full pipeline test suite: **18 passed**,
ruff clean. Branch `feat/permit-rules` is **pushed** (3 commits); not merged to `main`.

## What I just did
Executed `docs/specs/2026-05-30-permit-rules-plan.md` Tasks 1–5 (spec-critic'd 9/10), each via `/ship`:
- `6d89702` — `permit_rules.yaml` + `clean.py` (load/validate/build) + 11 tests + `pyyaml` dep.
- `36b691f` — migration `supabase/migrations/20260530160000_add_permit_rules_table.sql` + loader `TABLES` + `build.py ORDER` + loader idempotency test + schema.sql/QUICK_REFERENCE mirror.
- `6e40c97` — curated full 12-rule catalogue + QUICK_REFERENCE marked loaded.
Migration applied to live Supabase via the **loader DSN** (not the MCP — MCP is read-only) and the
rows loaded with `load_to_supabase.py permit_rules`.

## Next concrete step
Human browser-verify the **3 flagged rows** (all flagged inline in the YAML, `status: active` but provisional):
1. **Omgevingsvergunning (VLAREM)** — confirm rubrics `45.4.d` (frituren) / `16.3.2°` (koeling ≥5 kW) + klasse 2/3 boundaries at `vlaremwegwijzer.navigator.emis.vito.be` (JS wizard → use the **`browser-data-curation`** skill / Claude-in-Chrome MCP; that MCP was **not connected this session** — re-probe before trusting).
2. **Drank gegiste vs sterke** — §4a models two permits (gegiste = positief bericht; sterke = +college machtiging, strafregister model 596). The live stad.gent `drankvergunning-vaste-drankgelegenheid` page reads as **one** drankvergunning covering both, folded into the horeca-attest. Decide which reflects 2026 reality; both rules currently point at that page.
3. **`capacity_seats: {gte: 100}`** proxies "≥100 m²" (brandweer trigger) — the `attributes` taxonomy has no `area_m2`. Add one when `sector_attributes.yaml` is built.
After any YAML edit: re-run the validation test, `clean.py`, then `load_to_supabase.py permit_rules`.

## Open questions / decisions needed
- None blocking. The 3 above are accuracy refinements, not blockers — the agent points users to the official page rather than asserting.
- Whether to merge `feat/permit-rules` → `main` now or after the verification pass.

## Exact entry points
- Data artifact: `pipelines/droomzaak/datasets/permit_rules/permit_rules.yaml` (the curated source of truth; `attributes:` vocab + `rules:`; `applies_when` grammar documented at the top).
- Builder + validator: `pipelines/droomzaak/datasets/permit_rules/clean.py` (`load`/`validate`/`build`; `COLUMNS` is the loader contract).
- Tests: `pipelines/droomzaak/tests/test_permit_rules.py` (11) + the `permit_rules` case in `tests/test_load_to_supabase.py`.
- Schema: `supabase/migrations/20260530160000_add_permit_rules_table.sql` + mirror in `supabase/schema.sql`; `supabase/QUICK_REFERENCE.md` row.
- Plan + design: `docs/specs/2026-05-30-permit-rules-plan.md`, `…-permit-rules-curated-config-design.md`.
- Skills/agents: `belgian-open-data-ingest` / `open-data-ingest-specialist` (curation), `supabase-schema-sync` / `warehouse-schema-expert` (schema), `browser-data-curation` (VLAREM/VLAIO).

## Commands / verification
```
uv run pytest pipelines/droomzaak/tests/ -q          # expect 18 passed
uv run python pipelines/droomzaak/datasets/permit_rules/clean.py   # expect "permit_rules: 12 rows → …"
```
Live check (DSN from gitignored `.env.demo` — `DROOMZAAK_PG_DSN` / `SUPABASE_DB_URL`, session port 5432):
```python
import sys; sys.path.insert(0, "pipelines/droomzaak")
import load_to_supabase as L, duckdb
con = duckdb.connect(); L.attach_postgres(con, L.resolve_dsn())
con.execute("SELECT count(*) FROM pg.droomzaak.permit_rules").fetchone()        # 12
con.execute("SELECT count(*) FROM pg.droomzaak.permit_rules WHERE nace_prefix @> ARRAY['56']").fetchone()  # 10
```

## Gotchas hit
- **Position-based load is order-sensitive.** The loader does `INSERT … SELECT *`; the migration column order MUST match `clean.COLUMNS`. The count guard catches a mismatch but not a same-type reorder — verified order via DuckDB's `SELECT * … LIMIT 0` cursor (the authoritative INSERT target), NOT `information_schema.columns` (DuckDB misreports the attached PG's `ordinal_position` — it looked scrambled but the physical table was correct).
- **No `psql`** on this machine → applied DDL through DuckDB `postgres_execute('pg', …)` (reuses `loader.attach_postgres`), which passes native PG SQL (needed for `TEXT[]` + the GIN index DuckDB can't represent).
- **`text[]` marshaling works** (DuckDB LIST → PG `text[]`) — no `SELECT_LIST` cast needed; confirmed by the live round-trip above. `permit_rules` is the first array-column table in `TABLES`.
- **Never invent fees** — calculator-based costs (terras-belasting, Unisono, EPB, VLAREM) are `cost: {type: simulator, url}`; €0 (uithangbord, free) is `{type: fixed, eur: 0}`.
- WAF: never `WebFetch` `vlaio.be` / VLAREM (403/JS) — browser-curate.

## Out of scope (separate follow-ups)
- `permit_checklist_for` agent tool — thin Soda Straw → Postgres wrapper that reads `permit_rules` and evaluates `applies_when` (grammar: `{}`=always, `[a,b]`=∈, `true`=bool, `{gte:N}`=threshold) in Python. Build via `/new-tool` + `add-agent-tool` + `soda-straw-data-tool`.
- `sector_attributes.yaml` — must adopt the inline `attributes:` keys from the YAML verbatim, plus `area_m2` (see #3).
