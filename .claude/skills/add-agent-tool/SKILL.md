---
name: add-agent-tool
description: Use when adding a new tool to the Droomzaak provider-neutral agent loop (e.g. extract_dream_profile, peer_benchmarks_statbel, score_locations, permit_checklist_for, web_search, set_chapter_state). Covers the neutral spec, handler, self-correcting error shape, candidate-map widening, transient-layer registration, validation wiring, and the fake-client test — plus the loop-contract gotchas (commit enforcement, early-break) that make a new tool work end-to-end on the first run.
---

# Adding an agent tool

The agent loop is **provider-neutral**: one spec, one handler, both providers share it. Adding a tool is a fixed five-part procedure. This skill is **rigid** — the contract keeps the loop deterministic across OpenAI and Anthropic.

> Deep contract details (ProviderAdapter, loop iteration, commit enforcement) are in `reference/tool-contract.md`. Read it once before your first tool.

## 0. Get the tool's spec right FIRST (precedence)
Read the tool's row in **`droomzaak-data-shortlist.md` §3** (authoritative on backing/source) and `droomzaak-prd.md` §3.5. Note the corrections: **no `places_popular_times`** (dead API — use OSM/Places density); **`web_search`** (Tavily, official-domain-biased, native fallback); **`peer_benchmarks_statbel`** is backed by **Belfirst** aggregates + Statbel.

## 1. Neutral spec — in `tool_specs()`
- `name`: snake_case, matches the data-shortlist row.
- `description`: the model's ONLY cue on *when* to call. Concrete trigger + return, 1–2 sentences.
- `parameters`: tight JSON Schema; mark required; constrain enums. Loose schemas → garbage input.

## 2. Handler — register in `_HANDLERS`
1. **Validate input first.** Bad/missing field → `return {"error","hint"}`, never raise. The hint is fed back so the model self-corrects.
2. **Fetch.** Analytical data → `DataGateway.query(...)` (`data-tool`), never direct Postgres/DuckDB. Behaviour (geocode, OSM, routing, Places, web_search) → native client.
3. **Shape the return** compact: round aggressively, trim samples, label proxies, make "no data" explicit.
4. **Widen the candidate map** if the tool surfaces a dataset the model may act on: `run.referenced_dataset_ids.add(dataset_id)`.
5. **Register a transient layer** for features to render: `transient_layers.register(...)`, return the `dataset_id` (10-min TTL → `show_layer` promptly).

## 3. Validation — in `agent_validation.py`
Read-only tool → usually no change. New **action type** → add its validator + payload shape (reuse the layer-filter validator; field names must match dataset metadata). Chapter-state writes go through `set_chapter_state` (`chapter-state-machine`).

## 4. Loop-contract gotchas
Tools never mutate map state (commit visual change only via `apply_map_actions`). Commit enforcement nudges once then synthesizes + auto-logs a problem — a well-described tool returning clean data commits naturally. Early-break after commit (no post-commit tool call). Iteration budget is bounded — return enough in one call.

## 5. Fake-client test — in `backend/tests/test_agent.py`
Use a scripted fake-provider-client (canned tool calls); assert the handler's effect + the `{error,hint}` path. **Never hit real APIs** (the DataGateway, Places, ORS, Tavily, the model) — monkeypatch. Run `uv run pytest backend/tests/test_agent.py` and report the real result.

## Checklist
- [ ] Spec matches data-shortlist §3 (no dead `places_popular_times`); trigger-clear description; tight schema
- [ ] Handler validates input, returns `{error,hint}` on failure
- [ ] Analytical data via the DataGateway; behaviour tools native
- [ ] `referenced_dataset_ids` widened / transient layer registered as needed
- [ ] New action type validated (if any)
- [ ] Fake-client test added, real APIs monkeypatched, suite green
