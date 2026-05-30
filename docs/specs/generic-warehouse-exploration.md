# Spec — generic warehouse exploration (`describe_warehouse` + `query_warehouse`)

**Status:** light spec (per request: keep it quick). Additive; bespoke tools unchanged.

## Why
Five canonical tables are loaded but no tool reads them (`business_financials`,
`business_registry_history`, `nace_ref`, `gent_points`, `permits_events`), and the
agent dead-ends on off-script questions. Borrow map-pilot's DISCOVER→ANALYSE pattern,
but re-expressed through the DataGateway (map-pilot filters GeoJSON in Python = render
tier, which our `data-tiers.md` forbids for reasoning).

## Two new tools (in `droomzaak_tools.py`)

### `describe_warehouse` — DISCOVER (pure-python, no gateway)
- Input: `{ table?: string }`.
- No arg → compact list of exposed tables `{table, grain, one_line, licence, caveat_nl}`.
- With `table` → full profile: columns (name + meaning + is_numeric + is_groupable),
  caveat, licence. Reads the static `warehouse_catalog.CATALOG`. Side-effect-free.

### `query_warehouse` — ANALYSE (gateway-backed, parameterized)
- Input: `{ table, agg=count|sum|avg|min|max|median, agg_field?, group_by?, filters?:[{column,op,value}], limit=20 }`.
- **Identifier allowlist is the injection boundary**: `table`, `group_by`, `agg_field`,
  and every filter `column` MUST validate against `CATALOG[table]`. Identifiers are
  taken from the validated catalog entry, never interpolated from the raw model string.
  Op ∈ {=,!=,>,>=,<,<=,like,in}. **Values always parameterized** ($1, $2, …; `in` → ANY($n)).
- `median` → `percentile_cont(0.5) WITHIN GROUP (ORDER BY <agg_field>)`.
- SQL shape: `SELECT [<group_by> AS group_value,] <agg> AS value, count(*) AS n
  FROM droomzaak.<table> [WHERE …] [GROUP BY <group_by>] ORDER BY value DESC NULLS LAST LIMIT $n`.
- Routes through `gateway.query(sql, params, tool_name="query_warehouse")` → audit seam.
- On failure → `_gw_error(exc)` (no fabricate path; exploration tool may degrade).

### Licence / honesty guards
- `aggregates_only` tables (`business_financials`, `business_registry_history`): drop any
  returned row with `n < MIN_COHORT` (=5) and report `suppressed_low_cohort`. Never SELECT *
  (only ever aggregates), so no per-firm row can leak.
- Exclude entirely: `kbo_geocode` (no redistribution), `agent_sessions`, and the per-firm
  identity columns of `business_registry` (`ent`, `kbo_id`, `lon`, `lat`).
- Each table carries `caveat_nl` (sale-price ≠ rent; arrondissement ≠ city; NIS8 absolute
  totals) echoed in every response so the generic path can't fake certainty.

## Steering (chapter state machine)
- Allow `describe_warehouse` + `query_warehouse` in `2_niche`, `3_waar`, `4_vergunningen`.
- One steering line per chapter block pointing at the right tables; bespoke tools stay the
  blessed path for the 5 core answers.

## Tests (monkeypatched gateway — never real)
- `describe_warehouse`: list + per-table profile.
- `query_warehouse`: builds parameterized SQL; happy count+group; median path.
- **injection guard**: non-allowlisted `table`/`group_by`/filter `column` → error, no query.
- **aggregates-only**: low-cohort rows suppressed for `business_financials`.

## Out of scope
Semantic/embeddings catalogue (16 tables — a static dict beats it), free SQL, joins across
tables (single-table aggregates only for v1), map-layer emission from these tools.
