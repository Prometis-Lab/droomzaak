---
name: chapter-state-machine
description: Use when building or extending Droomzaak's five-chapter journey (Droom → Niche → Waar → Vergunningen & geld → Pakket). Defines the server-side state machine wrapping the reused agent loop — the JSON column on agent_sessions, the typed per-chapter state, the required-tool subset, the exit conditions, set_chapter_state validated persistence, and how the system prompt branches on current_chapter while the UI rail just reflects it.
---

# The Droomzaak chapter state machine

Net-new for Droomzaak (PRD §3.3). A **thin** state machine wrapping the reused agent loop — **not** a parallel orchestrator. Don't rebuild the loop; add state around it. **Rigid** on the contract.

## Shape
- State persisted as **JSON on `agent_sessions`** (one new column). No new orchestration service.
- Five chapters, each with the state it accumulates, a required-tool subset, and an explicit exit condition.

| Chapter | State accumulates | Required tools | Exit condition |
|---|---|---|---|
| 1 *Droom* | `dream_profile` | `extract_dream_profile`, `apply_map_actions` | `dream_profile.sector` set |
| 2 *Niche* | + `niche_signals` | `peer_benchmarks_statbel`, `query_osm`, `search_datasets`, `web_search` | user clicks *Vind je plek* |
| 3 *Waar* | + `candidate_locations[]` | `score_locations`, `nearest_features`, `spatial_count`, `rent_benchmark` | user picks a location |
| 4 *Vergunningen & geld* | + `permit_checklist[]`, `subsidies[]`, `legal_form` | `permit_checklist_for`, `subsidies_for`, `legal_form_advisor` | all items rendered |
| 5 *Pakket* | render-only | `generate_dream_narrative`, `compose_package` | PDF / link delivered |

> **Correction (data-shortlist §9):** Chapter 3 does NOT use `places_popular_times` — that API field doesn't exist. The footfall/competition signal comes from `score_locations` (the `footfall_sector` composite) + OSM/Places amenity density. `web_search` (Tavily) is added to Chapter 2 for off-script jury Q&A.

## The `sector_attributes` link (one source of truth)
`sector_attributes` (the "company topology", data-shortlist §4d) drives BOTH Chapter 1's follow-up questions (ask only the attributes the dream sentence didn't fill, for the recognised NACE) AND Chapter 4's `applies_when` permit branching. Keep the elicitation and the branching keyed off the same taxonomy — adding a sector = adding one block there.

## Rules
1. **System prompt branches on `current_chapter`** — append a small per-chapter block (tools in scope, what to accumulate, the warm dream-first tone) to the reused base prompt.
2. **`set_chapter_state(patch)` is the only writer** — validate the patch against the chapter's typed state before persisting; reject writes that skip an exit condition.
3. **Gated transitions, server-owned.** Advancing requires the exit condition; the UI rail only *reflects* server state. Never gate purely client-side.
4. **Each chapter still commits** — required tools fire, then `apply_map_actions` (demo-success needs a DataGateway call + a committed action per chapter).
5. **Reuse, don't fork** — loop, ProviderAdapter, validation, sessions, canvas unchanged. The machine only loads chapter state pre-turn, exposes it to the prompt, persists the patch post-turn.

## Degraded branches (PRD §5.1)
Horeca polished end-to-end; retail + consultant **scaffolded** (sector recognised, degraded Ch3–4, thinner package). Build sector-agnostic; let *content* (`permit_rules`, `subsidies`, narrative) degrade for non-horeca. A jury member must be able to pick a different sector/address without a crash (PRD §6.3 #6).

## Checklist
- [ ] One JSON column on `agent_sessions`; loaded pre-turn, persisted post-turn
- [ ] Typed state per chapter; `set_chapter_state` validates patches
- [ ] System prompt appends a per-chapter block keyed on `current_chapter`
- [ ] Exit conditions enforced server-side; rail reflects, doesn't gate
- [ ] Each chapter fires its required tools + one `apply_map_actions`
- [ ] `sector_attributes` drives both Ch1 questions and Ch4 branching; engine sector-agnostic
