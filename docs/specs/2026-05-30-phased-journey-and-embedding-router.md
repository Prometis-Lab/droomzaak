# Spec — Phased journey layer + schema/dataset embedding router

_Status: draft for spec-critic gate. Author session: 2026-05-30. Slot: PRD §5.2 hours 0–2 (chapter shell) + 2–4 (`search_datasets` alongside the other analytical tools)._

Two coupled parts, one spec:

1. **Chapter state machine** — the server-side phased interaction layer wrapping the reused agent loop (PRD §3.3, `chapter-state-machine` skill).
2. **Embedding router** — `catalog_embedding` table + `match_catalog` RPC + build-time embed script + the `search_datasets` tool, for routing **off-script** follow-up questions to the right warehouse table/column (`add-agent-tool`, `soda-straw-data-tool`, `supabase-schema-sync`).

---

## 0. Preconditions / dependencies (out of scope here, assumed built)

This spec is the *layer*; it does not re-spec the foundation. It assumes (and is co-sequenced with) the hour 0–2 base:

- **Provider-neutral agent loop** (`agent_loop.py` + `ProviderAdapter`), tool dispatch over `tool_specs()` / `_HANDLERS` (`add-agent-tool` contract). Not built here; `search_datasets` registers into it.
- **`agent_sessions` table** exists (Map-Pilot-style session store). This spec **adds one JSONB column** to it.
- **Soda Straw broker** (`agent_straw.py`) — one MCP session at FastAPI startup, generic `query(straw, sql, params)` wrapper, allowlist (`soda-straw-data-tool` §"Wiring the client", data-shortlist §7.2). Not built here; `match_catalog` is dispatched through it. **Open dependency:** whether the straw `query` accepts typed bind params — see Risks R1.
- **`DataGateway`** with `DATA_BACKEND=soda_straw|postgres_direct` failover (data-shortlist §7.3). `match_catalog` uses it like every analytical read.
- **OpenAI client + key** (`OPENAI_API_KEY`) — already provisioned (PRD §3.7).

If the foundation slips, Part 1 (pure-Python state machine, no DB read) can still land; Part 2's `search_datasets` needs the broker.

---

## PART 1 — Chapter state machine

### 1.1 Context

The journey is **phased**: each phase is a chapter with (a) a deterministic **open** on entry — the chapter's required tools are *guaranteed to have fired* before the user can advance, narrated as they run — and (b) a free-form interaction window (agent + map) until the user clicks the on-brand exit. The open is prompt-driven (best-effort ordering), but the *guarantee* is structural: the advance gate (§1.3, §1.4) refuses to move forward until each required tool's output is present in state. What is **never** deterministic is the tools' **output** — data comes live every turn, so a jury can pick a different address/sector and the chapter re-runs (PRD §6.3 #6). Re-entry to an earlier phase is **forward-only recompute** (decided 2026-05-30; memory `phase-reentry-forward-only`).

### 1.2 State shape — one new JSONB column `chapter_state` on `agent_sessions`

```jsonc
{
  "version": 7,                       // optimistic-concurrency counter, bumped each write
  "current_chapter": 3,               // 1..5, the chapter the agent is acting in
  "max_unlocked_chapter": 3,          // highest reached; rail may show 1..this
  "chapters": {
    "1": { "status": "complete", "straw_read_logged": true,
           "chosen":  { "dream_sentence": "...", "attributes": { "serves_alcohol": "gegiste", "seating": "terrace" } },
           "derived": { "dream_profile": { "sector": "horeca", "nace": ["56.101"], "anchor": {"wijk":"...","lat":..,"lon":..,"nis9":"..."}, "confidence": 0.9 } } },
    "2": { "status": "complete", "straw_read_logged": true,
           "chosen":  { "advanced_via": "vind_je_plek" },
           "derived": { "niche_signals": { "peer_count": 13, "growth_3y_pct": 27, "bankruptcies": {"2024":4,"2023":6}, "cohort_financials": {...} } } },
    "3": { "status": "active", "straw_read_logged": true,
           "chosen":  { "picked_location": null },
           "derived": { "candidate_locations": [ { "address":"...", "nis9":"...", "score":0.81, "why":"..." }, ... ] } },
    "4": { "status": "locked", "straw_read_logged": false, "chosen": {}, "derived": {} },
    "5": { "status": "locked", "straw_read_logged": false, "chosen": {}, "derived": {} }
  }
}
```

Per-chapter state is split into two buckets — **the single most important invariant of this part**:

- **`chosen`** — user decisions / inputs (the dream sentence, the elicited `attributes`, the picked location, the explicit "advance" click). On recompute these are **re-presented / re-asked**, kept only where still valid.
- **`derived`** — everything computed from tools/upstream (`dream_profile` classification, `niche_signals`, `candidate_locations`, the permit/subsidy/legal-form outputs). On recompute these are **silently dropped and rebuilt forward**.

`status` ∈ `locked | active | complete`. `straw_read_logged` (bool) is set by **the state machine itself** (it owns `chapter_state`) when the `current_chapter`'s §1.3-named analytical tool returns successfully — **not** by the broker, which is a generic chapter-unaware `query()` wrapper (§0) and cannot attribute a read to a chapter. The flag is `derived`-class state — cleared on recompute. The rail derives a **stale** display state (no separate status value) for any chapter where `index > current_chapter AND index ≤ max_unlocked_chapter` — i.e. previously reached, now cleared and awaiting rebuild — distinguishing it from a never-reached `locked` chapter.

### 1.3 Per-chapter contract

| Ch | Required tools (the open) | Soda Straw analytical read (the §6.3 #2 call) | `chosen` | `derived` | Exit predicate (server-owned) |
|---|---|---|---|---|---|
| 1 *Droom* | `extract_dream_profile`, `apply_map_actions` | `extract_dream_profile` grounds the NACE classification with a straw read of **`nace_ref`** (code↔label↔synonyms) | `dream_sentence`, `attributes{}` | `dream_profile` | `dream_profile.sector` set **and** every `sector_attributes`-required attribute for the recognised NACE present in `chosen.attributes` |
| 2 *Niche* | `peer_benchmarks_statbel`, `query_osm`, `places_search`, `apply_map_actions` (+ `search_datasets`, `web_search` available) | `peer_benchmarks_statbel` (`peer_demography_nace` + `business_financials`) | `advanced_via:"vind_je_plek"` | `niche_signals` | user click **and** `niche_signals` populated |
| 3 *Waar* | `score_locations`, `nearest_features`, `spatial_count`, `rent_benchmark`, `apply_map_actions` | `score_locations` (weighted join) / `rent_benchmark` | `picked_location` | `candidate_locations[]` (≥3) | `picked_location` set |
| 4 *Vergunningen & geld* | `permit_checklist_for`, `subsidies_for`, `legal_form_advisor`, `apply_map_actions` | `permit_checklist_for` (`permit_rules` + `permits_events`) / `subsidies_for` | — | `permit_checklist[]`, `subsidies[]`, `legal_form` | all three `derived` present (rendered) |
| 5 *Pakket* | `generate_dream_narrative`, `compose_package`, `apply_map_actions` (commits the **final recap pin** — the chosen-location marker + a journey-summary highlight on the Droomkaart, the package's map shot) | `compose_package` sources the Tuesday-morning headline numbers (cohort revenue/margin → covers/take-home) with a fresh straw read of **`business_financials`** aggregates at compose time — so the package's claims carry a live audit trail | — | `narrative`, `package` | `package` composed (PDF/link deliverable) |

> Correction carried (data-shortlist §9, `chapter-state-machine` skill): **no `places_popular_times`** (dead API) — footfall/competition come from `score_locations` (`footfall_sector` composite) + OSM/Places density. `web_search` (Tavily) is in Chapter 2 for off-script Q&A.

**The per-chapter Soda Straw invariant (PRD §6.3 #2).** Each chapter must record **≥1 analytical Soda Straw read** before it can advance — the column above names which required tool provides it for each chapter. Ch1 and Ch5 do **not** have an obviously-analytical tool, so they are wired deliberately: Ch1's `extract_dream_profile` resolves the NACE against `nace_ref` *through the straw* (it genuinely needs that lookup to map "vegan bistro" → 56.101); Ch5's `compose_package` re-reads the `business_financials` cohort aggregate *through the straw* so the package's headline numbers are live-sourced, not just replayed from earlier state. The state machine records a `straw_read_logged` boolean per chapter — **it sets the flag for `current_chapter` when that chapter's §1.3-named analytical tool returns successfully** (the broker stays generic; chapter attribution lives in the layer that owns `chapter_state`). **Advance requires the exit predicate, the required-tool `derived` outputs, AND `straw_read_logged == true`**, plus the recorded click for the user-click chapters (2, 3) and one committed `apply_map_actions`. This blocks advancing past an empty chapter and makes the debug-overlay "a straw call per chapter" claim true rather than hoped-for.

### 1.4 `set_chapter_state(patch)` — the only writer

A validated tool (registered in `_HANDLERS`, validation in `agent_validation.py`). Three operations, one schema. **Every patch carries `expected_version`** — the `chapter_state.version` the caller read pre-turn — for optimistic concurrency:

```jsonc
// op: "update"  — a chapter's tools produced state
{ "op": "update", "expected_version": 7, "chapter": 3, "bucket": "derived", "value": { "candidate_locations": [...] } }
{ "op": "update", "expected_version": 7, "chapter": 3, "bucket": "chosen",  "value": { "picked_location": {...} } }

// op: "advance" — move forward one chapter
{ "op": "advance", "expected_version": 7 }              // current -> current+1; requires §1.3 gate

// op: "reenter" — pivot back (forward-only recompute)
{ "op": "reenter", "expected_version": 7, "chapter": 1 } // current -> 1; see §1.5
```

**Validation rules (reject → `{error,hint}`, never raise):**
1. `update`/`advance` may only target `current_chapter` (no skip-ahead writes; no editing a `complete` future chapter directly — pivot via `reenter`).
2. `advance` runs the full §1.3 gate: the exit predicate **and** required-tool `derived` present **and** `straw_read_logged == true` (plus the recorded click for Ch2/Ch3); on fail → `{error, hint:"<what's missing>"}`.
3. `reenter(n)` requires `1 ≤ n ≤ current_chapter`.
4. **Optimistic concurrency:** the server compares the patch's `expected_version` against the persisted `chapter_state.version`; mismatch → `{error, hint:"state changed; re-read chapter_state and retry"}`. On accept, apply under a row lock and bump `version` by 1. (Single session, but the loop may retry a turn — this prevents a lost update.)
5. Bucket must be `chosen` or `derived`; value validated against the chapter's typed shape (Pydantic models per chapter). `straw_read_logged` is set by the **state machine** on the §1.3 tool's successful return (§1.2), never by a model-issued patch.

### 1.5 Forward-only recompute (the `reenter` semantics)

On `reenter(n)` the server, atomically:
1. For chapters `n+1 … 5`: set `status:"locked"`, `straw_read_logged:false`, **clear both `chosen` and `derived`** (downstream picks die with the data — a Phase-1 pivot can move the niche so the Phase-3 pick is no longer valid).
2. For chapter `n`: set `status:"active"`, `straw_read_logged:false`, **keep `chosen`** (the user's prior inputs), **clear `derived`** (to be rebuilt by the open on the next turn). Exception: if the pivot changes a `chosen` field that invalidates other `chosen` fields in the same chapter (e.g. NACE changes ⇒ the `attributes` set required by `sector_attributes` changes), the now-irrelevant attributes are dropped and the agent re-asks only the newly-required ones.
3. `current_chapter = n`; `max_unlocked_chapter` unchanged (so chapters `n+1 … max_unlocked` render **stale** per the §1.2 derivation — breadcrumbs kept, awaiting rebuild); bump `version`.

No diffing, no partial patching of downstream state — that is the V2 lane (PRD §5.1 "no backtracking polish"). Rebuild-forward happens naturally: re-entering chapter `n` re-runs its required tools (deterministic open), the user re-walks to the exit click, advance proceeds.

### 1.6 System-prompt branching & the free-form window

- The base system prompt is reused; the machine **appends a per-chapter block** keyed on `current_chapter` (`chapter-state-machine` rule 1): the tools in scope, what to accumulate (the `chosen`/`derived` fields), the warm dream-first tone, and the **off-script-router note**: *"For a user question that no in-scope chapter tool answers (e.g. an ad-hoc demographic/economic fact about a sector), call `search_datasets` to find the right table/column, then the matching analytical tool. Do not use it for permits/subsidies — those are config."*
- **Loaded pre-turn, persisted post-turn** — the machine only injects state into the prompt and persists the validated patch; it does not re-implement the loop (rule 5).
- The deterministic open is **prompt-driven**: on entering a chapter the per-chapter block instructs the agent to run the required tools first (narrated), then open the free interaction window. Determinism is enforced structurally by §1.3 (can't advance until the required `derived` exist), not by hard-coding outputs.

---

## PART 2 — Embedding router

### 2.1 Context

Purpose: route an **unscripted** follow-up to the right warehouse table/column — e.g. *"hoeveel auto's per huishouden hier?"* → `demographics_sector_annual.cars_per_hh`. The scripted golden path routes by the agent **picking a tool** (each analytical tool already knows its table); embedding is **not** on the golden path — it is the off-script safety net, beside `web_search`. Embedder: **OpenAI `text-embedding-3-small`** (1536-dim), decided 2026-05-30 (memory `embedding-vendor-restraint`; do **not** introduce ZeroEntropy or any alternative). Permits/subsidies stay structured YAML (`sector_attributes`), **never** vector (data-shortlist §149).

### 2.2 DDL — new objects in the `droomzaak` schema (via `supabase-schema-sync`, STOP-and-wait)

```sql
create extension if not exists vector;

create table if not exists droomzaak.catalog_embedding (
  id          text primary key,            -- 'table:demographics_sector_annual'
                                            -- 'column:demographics_sector_annual.cars_per_hh'
                                            -- 'dataset:<ods-slug>'
  kind        text not null check (kind in ('table','column','dataset')),
  label       text not null,               -- human label ("auto's per huishouden")
  description text not null,               -- the EMBEDDED text: bilingual NL+EN + NACE/synonym hints
  metadata    jsonb not null default '{}', -- {table, column?, join_keys[], source, nace_hints[], source_hash}
  embedding   vector(1536) not null
);

create index if not exists catalog_embedding_hnsw
  on droomzaak.catalog_embedding using hnsw (embedding vector_cosine_ops);

create or replace function droomzaak.match_catalog(
  query_embedding vector(1536),
  match_kind  text default null,
  match_count int  default 5
) returns table (id text, kind text, label text, description text, metadata jsonb, similarity float)
language sql stable parallel safe as $$
  select id, kind, label, description, metadata,
         1 - (embedding <=> query_embedding) as similarity
  from droomzaak.catalog_embedding
  where match_kind is null or kind = match_kind
  order by embedding <=> query_embedding
  limit greatest(1, least(match_count, 20));
$$;
```

`stable` + SELECT-only (analytical-function rule). HNSW is near-cosmetic at this corpus size (≤~80 rows) — a seq scan is fine; the index documents intent and scales to the dataset catalogue. Index built **after** the embed load (HNSW on an empty table is fine but build post-load to be safe).

### 2.3 `search_datasets` tool (provider-neutral, `add-agent-tool`)

**Neutral spec** (`tool_specs()`):
- `name`: `search_datasets`
- `description`: *"Find which Ghent warehouse table or column can answer an off-script question about demographic, economic, location, footfall or business data. Call ONLY for a follow-up question that no other chapter tool already covers; returns the top matching tables/columns and how to query them. NOT for permits or subsidies (those are curated config)."*
- `parameters`: `{ query: string (required), kind: enum["table","column","dataset"] (optional), top_k: integer default 5 min 1 max 20 }`

**Handler** (`_HANDLERS`):
1. **Validate** `query` non-empty → else `{error, hint}`.
2. **Embed** `query` with OpenAI `text-embedding-3-small` via `embeddings.embed_query()` (§2.5) — a **behaviour call, native, NOT through Soda Straw** (like calling the LLM). On embed failure / missing key → `{error, hint:"embedding unavailable; answer from web_search or ask the user"}` (golden path unaffected — embedding is off-script).
3. **Match** via the **Soda Straw** `query` (through `DataGateway`): SQL `select * from droomzaak.match_catalog($1::vector, $2, $3)`, **params** `[vec_literal, kind, top_k]` where `vec_literal` is the embedding serialized as a pgvector literal `"[0.0123,-0.045,...]"`. Parameterized — see R1 for the straw-param contract and the strict-serialization fallback.
4. **Shape** compact return:
```jsonc
{ "matches": [
    { "id":"column:demographics_sector_annual.cars_per_hh", "kind":"column",
      "label":"auto's per huishouden", "table":"demographics_sector_annual",
      "column":"cars_per_hh", "how_to_query":"score_locations / demographics lookup, keyed on NIS9",
      "similarity":0.71 } ],
  "confident": true }                       // false when top similarity < THRESHOLD (default 0.30)
```
   When `confident:false` → include `"hint":"no strong table match; try web_search or ask the user to rephrase"`. Make "no data" explicit; never invent a table.
5. **Do not mutate map state** (read/enrich-only); the model commits any visual via `apply_map_actions`.

### 2.4 Curated source of truth — `backend/data/catalog_descriptions.yaml`

Hand-authored, the input to the embed script. One entry per retrievable thing; **grain = column-level for the demographic/economic tables** (`demographics_sector_annual`, `business_financials`, `peer_demography_nace`, `housing_price_sector`, `footfall_sector`, `transit_access_sector`, `demand_proxies`), **table-level** for the rest (data-shortlist §2 set). Descriptions are **bilingual NL+EN + synonyms** (pull NACE synonyms from `nace_ref`):

```yaml
- id: column:demographics_sector_annual.cars_per_hh
  kind: column
  label: "auto's per huishouden"
  description: >
    Aantal auto's per huishouden per statistische sector (NIS9), per jaar.
    Cars per household per statistical sector, per year. Synoniemen: wagenbezit,
    autobezit, mobiliteit, car ownership. Bron: Statbel.
  metadata: { table: demographics_sector_annual, column: cars_per_hh,
              join_keys: [nis9], source: "Statbel", nace_hints: [] }
```

Datasets (`kind:dataset`) seed from the open-data catalogue (`open-data/portals/<portal>/datasets_index.csv` / `master_index.parquet`, data-shortlist §0/§5) — optional for Saturday; the table/column entries are the demo-critical set.

**Saturday-minimum subset (fits the hour 2–4 slot — author these first, defer the rest).** ~15 entries a jury actually asks about, not all ~80 columns:
- **Tables (table-level, ~6):** `business_registry`, `peer_demography_nace`, `disruption_events`, `permits_events`, `zoning`, `demand_proxies`.
- **Columns (column-level, ~9):** `demographics_sector_annual.{population, fiscal_income, cars_per_hh, age_mix}`, `footfall_sector.score`, `transit_access_sector.departures_per_week`, `housing_price_sector.sale_price_median`, `business_financials.{turnover_median, margin_median}`.

Everything else in §2.2's corpus is a **fast follow** (not before hour 6, PRD §5.2). Authoring is ~15 short bilingual blurbs — a Track-C/Track-A shared 60–90 min, not a from-scratch crawl (most facts already sit in the QUICK_REFERENCE + data-shortlist §2).

### 2.5 Build-time embed loader — `backend/scripts/embed_catalog.py`

A **build-time loader** (like the Friday `dump_duckdb_to_postgres.py`), not an agent-path component. It **writes data (DML upsert)** directly via `SUPABASE_DB_URL` (the DDL — extension/table/index/RPC — goes through the migration workflow, §2.2). uv-managed venv, idempotent, snapshot-and-freeze (no live re-embed during the demo).

- Reads `catalog_descriptions.yaml`.
- For each entry computes `source_hash = sha256(description)`; if a row with the same `id` already has that `source_hash` in `metadata`, **skip** (no re-embed → saves tokens, keeps frozen).
- Else embeds `description` (OpenAI `text-embedding-3-small`, batched) and **upserts**: `insert … on conflict (id) do update set …` (label, description, metadata incl. `source_hash`, embedding).
- Logs counts (inserted / updated / skipped). Re-runnable with no diff when nothing changed.

### 2.6 Native embed client — `backend/app/embeddings.py`

Thin wrapper: `embed_query(text) -> list[float]` and `embed_batch(texts) -> list[list[float]]`, model `text-embedding-3-small`, dim 1536. Used by both `search_datasets` (runtime, one query) and `embed_catalog.py` (build-time, batched). **Native** — never routed through Soda Straw. `embed_query` **asserts the result is a length-1536 list of finite floats** (no NaN/Inf) before returning — a non-finite element would break the `$1::vector` cast or the serialized literal; on failure → raise inside the wrapper, caught by the `search_datasets` handler as `{error,hint}`.

---

## 3. Files (target structure; clean-room — most are new)

| File | Part | Action |
|---|---|---|
| `supabase/scripts/2026-05-30_catalog_embedding.sql` | 2 | **New** DDL (extension + table + index + RPC) → operator runs → fold into `supabase/migrations/`, regen `schema.sql`, update `QUICK_REFERENCE.md` |
| `supabase/scripts/2026-05-30_agent_sessions_chapter_state.sql` | 1 | **New** `alter table … add column if not exists chapter_state jsonb not null default '{}'::jsonb` → same STOP-and-wait flow |
| `backend/app/chapter_state.py` | 1 | **New** — Pydantic per-chapter state models, exit predicates, `reenter` recompute, `apply_set_chapter_state(session, patch)` |
| `backend/app/agent_tools.py` | 1+2 | **Modify** — register `set_chapter_state` + `search_datasets` specs/handlers (file created by the hour 0–2 base) |
| `backend/app/agent_validation.py` | 1 | **Modify** — validate `set_chapter_state` patch shape (reuse existing validator pattern) |
| `backend/app/embeddings.py` | 2 | **New** — native OpenAI embed client |
| `backend/app/agent_straw.py` | 2 | **Use** (built by teammate) — dispatch `match_catalog` through it |
| `backend/data/catalog_descriptions.yaml` | 2 | **New** — curated bilingual descriptions (source of truth) |
| `backend/scripts/embed_catalog.py` | 2 | **New** — build-time idempotent embed loader (uv) |
| `backend/tests/test_chapter_state.py` | 1 | **New** — state-machine unit + fake-client tests |
| `backend/tests/test_embed_catalog.py` | 2 | **New** — idempotent-upsert + hash-skip test (monkeypatched) |
| `backend/tests/test_agent.py` | 2 | **Modify** — `search_datasets` fake-client test (monkeypatched) |

No reference analog to mirror (reference/ holds only its README); design the tool contract from the `add-agent-tool` skill + the foundation built in hours 0–2.

---

## 4. Edge cases

- **Zero / weak match** in `match_catalog` → `confident:false` + hint; agent falls back to `web_search` or asks. Never fabricate a table.
- **Non-horeca sector** → state machine is sector-agnostic; only *content* (`permit_rules`, narrative) degrades (`chapter-state-machine` §"Degraded branches"). `sector_attributes` drives which attributes Ch1 elicits.
- **Jury picks a non-Vrijdagmarkt address mid-Ch3** → an `update`/`chosen.picked_location` write; advancing recomputes Ch4–5 forward. No crash (PRD §6.3 #6).
- **Pivot to Ch1 after Ch4** → `reenter(1)`: Ch2–5 cleared, Ch1 `chosen` kept; if NACE changes, irrelevant `attributes` dropped + re-asked. Downstream picks gone by design.
- **Straw timeout / error on `match_catalog`** → `{error,hint}`; `DataGateway` may fail over (`DATA_BACKEND=postgres_direct`) — same SQL, same RPC.
- **Missing `OPENAI_API_KEY`** → `search_datasets` returns `{error,hint}`; **golden path unaffected** (embedding off-script). `embed_catalog.py` exits non-zero with a clear message.
- **Stale `version` on a `set_chapter_state` patch** → rejected with a hint to re-read state (optimistic concurrency).
- **`advance` before the open completed** → rejected: `{error, hint:"chapter N needs <tool> output / its straw read first"}` — the gate checks `derived` present **and** `straw_read_logged`, enforcing the ≥1-Soda-Straw-call-per-chapter demo criterion even for the LLM/pure-Python chapters (1, 5).
- **Embedding dim drift** (model returns ≠1536) → `embed_query` asserts length 1536; mismatch → `{error,hint}` (guards a silent pgvector cast failure).
- **Re-running `embed_catalog.py`** with unchanged YAML → all rows skipped (hash match); zero tokens, zero diff (idempotent).

## 5. Tests (real APIs monkeypatched — Soda Straw, OpenAI, the model)

**`test_chapter_state.py`** (pure Python, no I/O):
- `advance` blocked when exit predicate false / required `derived` missing → `{error,hint}`.
- `advance` succeeds only when predicate + required `derived` + `straw_read_logged==true` all hold → `current_chapter` increments, `version` bumps.
- **Ch1/Ch5 straw-gate:** `advance` from Ch1 (and from Ch5's compose) is **blocked** while `straw_read_logged==false` even though `derived` is present → `{error,hint}` (guards the §6.3 #2 overclaim the critic caught: an LLM/pure-Python chapter must still log its `nace_ref` / `business_financials` straw read).
- `reenter(1)` after reaching Ch4 → Ch2–5 buckets cleared + `straw_read_logged:false`, Ch1 `chosen` retained, Ch1 `status:active`, `derived` cleared.
- NACE-change pivot drops now-irrelevant `attributes`, keeps valid ones.
- `update` targeting a non-current chapter → rejected.
- Stale `expected_version` → rejected with the re-read hint.
- Fake-provider-client turn: entering Ch2 fires `peer_benchmarks_statbel` (canned, broker sets `straw_read_logged`) then an `apply_map_actions` commit (asserts the open + the per-chapter straw read + the commit are distinct).

**`test_agent.py::test_search_datasets`**:
- Monkeypatch `embeddings.embed_query` → canned 1536-vector; monkeypatch the straw client → canned `match_catalog` rows. Assert compact `matches` shape, `table`/`column` surfaced, `confident:true`.
- Low-similarity rows → `confident:false` + hint path.
- Embed raises (missing key) → `{error,hint}`, loop not crashed.
- **Dim drift:** `embed_query` returns a length-1500 / NaN-containing vector → wrapper raises → handler returns `{error,hint}` (no malformed `::vector` reaches the straw).
- Assert the straw was called with a **parameterized** query (embedding as a bind param / serialized vector literal), never user text string-formatted into SQL.

**`test_embed_catalog.py`**:
- Monkeypatch OpenAI embeddings + a fake DB writer. First run inserts N rows; second run with unchanged YAML skips all (hash match); changing one description re-embeds only that row.

Run: `uv run pytest backend/tests/test_chapter_state.py backend/tests/test_embed_catalog.py backend/tests/test_agent.py -k "search_datasets or chapter or embed"` → report real output.

## 6. Acceptance / "done"

1. The three test files above pass under `uv run pytest` (report real output) — **the primary gate** (no live API contact).
2. Operator applies both `supabase/scripts/*.sql` (STOP-and-wait); a smoke SELECT `select id,similarity from droomzaak.match_catalog((select embedding from droomzaak.catalog_embedding limit 1), null, 3)` returns rows; mirror updated (`migrations/` + `schema.sql` regenerated + `QUICK_REFERENCE.md`).
3. `uv run python backend/scripts/embed_catalog.py` loads the catalog idempotently (second run = all-skipped).
4. Maps to **PRD §6.3 #2** — every chapter logs ≥1 analytical Soda Straw read before advance (§1.3 column; Ch1 via `nace_ref`, Ch5 via `business_financials`), provable in the debug overlay; `match_catalog` is an *additional* off-script straw call — and **§6.3 #6** (forward-only recompute lets a jury-picked address re-run Ch3+ without a crash).

## 7. Risks & open questions

- **R1 — Soda Straw `query` param contract (blocking-ish for Part 2 runtime).** The straw's tool shape is undocumented (`list_tools()` at startup, data-shortlist §7.2). If it accepts only a raw SQL string (no bind params), we **must not** string-format anything user-derived. Mitigation: the only interpolated value is the **model-independent embedding** (1536 floats we serialize ourselves). `embeddings.embed_query` asserts a numeric float list of length 1536 and serializes to a strict `"[f,f,...]"` literal — no user text ever enters SQL; `kind`/`top_k` are an enum + a clamped int. Prefer real bind params when the straw supports them. **Confirm the straw contract before wiring** (depends on the hour 0–2 broker).
- **R2 — Foundation co-dependency.** Part 2 runtime needs the broker + `DataGateway`; Part 1 needs the loop + `agent_sessions`. Both are hour 0–2 work. If the broker slips, Part 1 + the DDL + `embed_catalog.py` + all unit tests still land; only the live `search_datasets` round-trip waits.
- **R3 — `confident` threshold (0.30) needs calibration** against a handful of real Dutch follow-ups Friday; too high → false "no match", too low → wrong table. Tunable constant, logged.
- **R4 — Column-grain corpus size / authoring time.** Column-level for ~7 tables is still tiny (≤~80 rows); no perf concern. Authoring is the real cost, so the Saturday target is the **~15-entry minimum subset (§2.4)**, not the full corpus — the rest is a post-hour-6 fast follow. Don't auto-explode every column; only the ones a founder would actually ask about.
- **R5 — `set_chapter_state` vs the loop's commit enforcement.** The state writer must not count as the per-chapter `apply_map_actions` commit; the chapter still needs a real map commit (`chapter-state-machine` rule 4). Tests assert both fire.
- **Open:** ship `kind:dataset` (the 60+ open-data catalogue) Saturday, or table/column only? Recommend **table/column only for the demo**, dataset entries as a fast follow if Track A has bandwidth (not before hour 6).
