# Handover — phased journey + embedding-router spec (gated, ready to build)

**Track:** track-a-backend · **Author:** milan · **Branch:** `milan_dev` · **2026-05-30 13:07**

## State now
- **Spec written and gated at 8/10 (GO).** No code yet — this is a planning artifact only.
- Spec: [`docs/specs/2026-05-30-phased-journey-and-embedding-router.md`](../../specs/2026-05-30-phased-journey-and-embedding-router.md), committed `79b7a9c` (docs-only, security gate passed clean).
- Backend does **not** exist yet (clean-room). The spec is the *layer*; it assumes the hour 0–2 foundation (provider-neutral loop, `agent_sessions`, Soda Straw broker `agent_straw.py`, `DataGateway`) which is **not built**. `reference/` holds only its README (no prior impl to mine).

## What I just did
1. Investigated ZeroEntropy as an embedder → **declined for Saturday** (corpus too small for model quality to matter; new-vendor risk). Locked **OpenAI `text-embedding-3-small`**. ZeroEntropy `zerank-2` reranker = V2 bet.
2. Pinned the interaction model = the chapter state machine: deterministic *open* per phase (live tools, never canned), free agent+map interaction until the on-brand exit click, **forward-only recompute** on re-entry (drop downstream derived+chosen, keep current-chapter chosen).
3. Wrote the spec (2 coupled parts: chapter state machine + embedding router for off-script table/column routing), ran `spec-critic`: 7→8/10. Commit `79b7a9c`.
4. Recorded 2 durable decisions in project memory (`phase-reentry-forward-only`, `embedding-vendor-restraint`).

## Next concrete step
Build the **foundation first** (PRD §5.2 hours 0–2) — the spec can't run without it: provider-neutral loop + `agent_sessions` + the Soda Straw broker (`soda-straw-data-tool` skill §"Wiring the client", data-shortlist §7.2). Then implement the spec via `subagent-driven-development`:
- `agent-tool-builder` → `set_chapter_state` + `search_datasets` (`add-agent-tool` skill).
- `warehouse-schema-expert` → the `match_catalog` SQL + the `catalog_embedding` DDL.
- DDL ships via `supabase-schema-sync` (STOP-and-wait): `supabase/scripts/2026-05-30_catalog_embedding.sql` + `..._agent_sessions_chapter_state.sql` → operator runs → fold into `migrations/`, regen `schema.sql`, update `QUICK_REFERENCE.md`.

## Open questions / blockers
- **R1 (spec §7): Soda Straw `query` param contract is undocumented.** Must `list_tools()` at broker startup to learn if it takes typed bind params. `match_catalog` passes a 1536-float `::vector` — needs a param or the strict self-serialized-literal fallback (never user text in SQL). **Confirm before wiring `search_datasets`.**
- **Soda Straw token** not yet in `.env.demo` (sign up at `sodastraw.ai/trial/start`, mint one `agent_*` token — data-shortlist §7.2).
- `OPENAI_API_KEY` must be in `.env.demo` for `search_datasets` + `embed_catalog.py` (PRD §3.7 says provisioned — verify).
- Open product call (spec §7): ship `kind:dataset` (60+ catalogue) Saturday or table/column only? Recommend **table/column only**.

## Exact entry points
- Spec: `docs/specs/2026-05-30-phased-journey-and-embedding-router.md` (§1 state machine, §2 embedding router, §3 file map, §5 tests, §7 risks).
- Governing skills: `chapter-state-machine`, `soda-straw-data-tool`, `add-agent-tool`, `supabase-schema-sync`.
- Authoritative data doc: `droomzaak-data-shortlist.md` (§2 table set, §3 tool→data, §7 Soda Straw, §9 corrections). Wins over PRD on data/tools.
- Memory: `phase-reentry-forward-only`, `embedding-vendor-restraint` (in the project memory dir).

## Gotchas hit (so you don't re-hit them)
- **PRD §6.3 #2 trap:** Ch1 (`extract_dream_profile`=LLM) and Ch5 (`compose_package`=pure Python) have *no* analytical tool → naive advance gate forces **zero** Soda Straw calls there. Spec fix: Ch1 grounds NACE via a `nace_ref` straw read, Ch5 re-reads `business_financials` aggregates; a `straw_read_logged` flag gates advance. **The state machine sets that flag** (it owns `chapter_state`), NOT the chapter-unaware broker.
- "Deterministic" = orchestration/ordering, **never** output. Output must be live or a jury picking a non-Vrijdagmarkt address (§6.3 #6) breaks.
- Embedding split: query-embed is a **behaviour** call (native, like the LLM) → NOT through Soda Straw; only `match_catalog` SELECT goes through the straw.
- `embed_catalog.py` is a **build-time loader** (writes DML direct via `SUPABASE_DB_URL`, like the Friday dump job) — but the extension/table/RPC **DDL** still goes through the migration STOP-and-wait flow.

## Verification
- Spec exists + committed: `git show 79b7a9c --stat` → 1 file, +292.
- Gate evidence: `spec-critic` returned 8/10 GO (round 2). No build/test to run yet — backend not scaffolded.
- When code lands, the §6 acceptance gate is `uv run pytest backend/tests/test_chapter_state.py backend/tests/test_embed_catalog.py backend/tests/test_agent.py -k "search_datasets or chapter or embed"` (all real APIs monkeypatched).
