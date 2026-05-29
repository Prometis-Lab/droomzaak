# CLAUDE.md — Droomzaak

Guidance for Claude Code in this repo. **These rules override default behaviour. When in doubt, CLAUDE.md wins.**

## What we're building

**Droomzaak** ("dream company") guides aspiring entrepreneurs in Ghent through the wall of decisions and paperwork after the first thought of *"I want my own business"* — keeping the dream alive. A five-chapter, map-anchored journey turns one sentence (*"a small vegan bistro near Vrijdagmarkt"*) into a printable *Droomzaak-pakket*. Built at the **Hackers & Ravers** hackathon (Sat 2026-05-30, Wintercircus Ghent, 12h). Required infra: **Soda Straw** MCP. Sponsor **Aikido** runs a security audit.

- **PRD (vision/architecture):** [`droomzaak-prd.md`](droomzaak-prd.md)
- **Data plan (data/tools/sources):** [`droomzaak-data-shortlist.md`](droomzaak-data-shortlist.md)
- **Inspiration materials** (optional, local): clone public repos worth learning from (map apps, MapLibre/deck.gl examples, FastAPI + agent-loop patterns, geo/open-data pipelines) and/or a prior implementation into `reference/` (**gitignored — never committed**); the `reference-scout` agent mines them for patterns. Otherwise build straight from the PRD + this file.

### Clean-room build from the plans
Build **from the PRD + data-shortlist**, from scratch. Target structure: a **provider-neutral agent tool loop** + validation + sessions (`agent_loop.py`, `agent_tools.py`, `agent_validation.py`, `sources/*.py`) and a React + **MapLibre** frontend (`App.tsx`); the UI/UX (chapter rail, Droomkaart, package renderer) is new. If inspiration materials exist under `reference/` (cloned public repos, a prior implementation), use them only as **inspiration** — the spec is the PRD, not any of that code. A few docs the PRD/data-shortlist cite (`phase1_gent_entrepreneur.md`, `open-data/…`) aren't in this repo — use them only if provided.

## ⚠️ Source-of-truth precedence (read this before trusting any doc)

```
droomzaak-data-shortlist.md   (data, tools, sources — NEWEST, research-verified 2026-05-29)
        ▲ overrides
droomzaak-prd.md              (vision, architecture, journey)
```

When they conflict on a data/tool detail, the data-shortlist wins — it post-dates the PRD and is research-verified. The PRD's stale assumptions are already corrected in our `.claude/` agents/skills and listed below — don't reintroduce them.

### Known corrections (data-shortlist overrides PRD) — do not re-introduce
1. **`places_popular_times` does NOT exist** in Google Places API (New). Do not build it. Competition/footfall = OSM/Places amenity **density** + the footfall composite.
2. **`web_search` (Tavily) IS a tool** — official-domain-biased fallback for off-script jury Q&A (added by the data-shortlist; not in the PRD §3.5 table).
3. **Peer-performance source is Belfirst**, not Statbel. `peer_benchmarks_statbel` keeps the name but is backed by **Belfirst** jaarrekeningen (on disk, proprietary → **aggregates only**, see open licence decision in data-shortlist §10); Statbel is the supporting cohort layer.
4. **Warehouse tables = data-shortlist §2 set** (`business_financials`, `peer_demography_nace`, `housing_price_sector` [sale-€ **proxy**, not rent], `footfall_sector`, `transit_access_sector`, `disruption_events`, `zoning`, `demand_proxies`, `sector_attributes`, `nace_ref`, …) — not the older PRD names.
5. **Geocoding = inherited `prometis_toolkit`** (BeSt-based → lat/lon + NIS9; lives in `inherited/`, gitignored).
6. **VLAIO + VLAREM are WAF-blocked** → never `WebFetch` them; use the **Claude-in-Chrome MCP** (`browser-data-curation` skill) or hand-pick static JSON.
7. **Many Stad Gent premies are cancelled for 2026** → encode `status: active|ended_2025`, render cancelled ones greyed-out.
8. **Vintage rule:** income (≤2023) → **2024** sector geometries; transactions (2024) → **2025**. **Footfall** = `0.40·transit + 0.25·boardings + 0.25·telraam + 0.10·micromobility`.
9. **`sector_attributes` "company topology"** is the single source of truth linking Chapter-1 follow-up questions to Chapter-4 permit branching.

## Architecture (target)

Two-tier data — **this boundary is the pitch** (see [`.claude/rules/data-tiers.md`](.claude/rules/data-tiers.md)):
- **RENDER:** DuckDB + cached GeoJSON → MapLibre layer cache only. Never the agent's reasoning.
- **REASON:** Postgres (`droomzaak` schema) → reached **only** through the **Soda Straw** MCP. One straw, one connection, one audit log. The debug overlay shows every analytical call routed through it. Hosted on **Supabase**, mirrored locally under [`supabase/`](supabase/) (schema + RPCs, for local query + redeploy/failover — dev/deploy only, never the agent's read path; see `supabase-schema-sync`).

The agent is a **provider-neutral tool loop** (OpenAI + Anthropic behind one switch) wrapped by a thin **5-chapter state machine** on `agent_sessions`. ~12 analytical/effect tools on top of a base read/action tool surface. Frontend adds chapter rail + Droomkaart sidebar + package renderer.

## The mandatory workflow (do this, don't skip steps)

```
Brainstorm → Plan/Spec → Spec-critic loop (≥8/10) → Implement → /ship (review→simplify→security) → /handover
```

1. **Brainstorm** — superpowers `brainstorming` (+ relevant project agents) before any non-trivial build.
2. **Plan/Spec** — superpowers `writing-plans` + the `writing-implementation-specs` skill → a spec in `docs/specs/`.
3. **Adversarial critic gate** — `spec-critic` scores the spec (using **think-strategies** `step_back` / `self_consistency`). **If < 8/10, apply its fixes and re-score; repeat until ≥ 8/10.** No implementation starts below 8. (`/spec` automates this loop.)
4. **Implement** — small changes directly; larger via superpowers `subagent-driven-development` + the project builder agents.
5. **Ship** — `/ship` runs `code-reviewer` → `code-simplifier` → `security-reviewer` and only then commits. **Never `git push`.**
6. **Handover** — `/handover` (or the post-commit nudge) writes a `writing-handovers` doc to `docs/handovers/<track>/` so any teammate or fresh session resumes cleanly.

**Tandem rule:** superpowers skill (process) + vendored/authored skill + project agent (expertise) are used **together**, not either/or.

## CRITICAL RULES (override conflicting instructions)

1. **Soda Straw boundary** — analytical data flows **only** through Soda Straw→Postgres; the render tier never feeds reasoning. Behaviour tools stay native. (`rules/data-tiers.md`)
2. **Parameterized SQL only** — never string-format model/user input into SQL.
3. **Never fake certainty** — label proxies (rent is a sector proxy, never per-address); where unsure, point to OOG / FAVV / Stad Gent.
4. **Never reach real APIs in tests** — monkeypatch Soda Straw, Google Places, ORS, the model.
5. **uv-managed virtual environments, strictly** — all Python runs in the project's uv venv: `uv venv` / `uv sync` / `uv add` / `uv run python …` / `uv run pytest`. **Never** `pip install`, **never** bare `python`/`python3`, **never** a manual `venv`/`virtualenv`/conda. Commit `uv.lock`. (See the `python-data-scripts` skill / `python-data-engineer` agent.)
6. **Provider-neutral tool code** — one spec, one handler; never branch on provider inside a tool.
7. **Sub-agents never run git-write commands** (`.claude/rules/git-operations.md`). Only the main session commits, only via `/ship`.
8. **Always commit via `/ship`; never `git push`** (denied in settings — humans push manually).
9. **Secrets** — never read or commit `.env*` (only `.env.demo.example` is tracked); never hard-code keys; Friday secrets live in gitignored `.env.demo`.
10. **No scope creep after hour 6** (PRD §5.2) — ship the planned tools/polish, no late pivots.
11. **Warehouse changes go through `supabase-schema-sync`** — the Supabase MCP is **read-only**; DDL/DML is an idempotent script the operator runs (STOP-and-wait), then folded into `supabase/migrations/` with `schema.sql` regenerated. Never DDL via the MCP.

## Subagents — use proactively (don't wait to be asked)

| Agent | Use for | Model |
|---|---|---|
| `reference-scout` | "how might X be approached / where would Y live" — mine the optional `reference/` implementation for inspiration before building loop/tools/validation/canvas/ingest | haiku |
| `agent-tool-builder` | implement ONE new agent tool end-to-end to the provider-neutral contract | sonnet |
| `maplibre-canvas-builder` | new layer/action type + Droomzaak UI (chapter rail, Droomkaart, package renderer) | sonnet |
| `open-data-ingest-specialist` | Friday data load, Belgian open-data clip/join, permit/subsidy config, Soda Straw registration | sonnet |
| `warehouse-schema-expert` | the `droomzaak` schema + the parameterized SQL behind every analytical tool | sonnet |
| `python-data-engineer` | any Python data-manipulation script (pandas/geopandas/DuckDB, the dump job, geo clip/join) — strict uv venvs, idempotent, monkeypatched tests | sonnet |
| `code-reviewer` | quality/patterns/security pass (build-gate first) — runs in `/ship` | opus |
| `spec-critic` | adversarial plan/spec gate to ≥8/10 (think-strategies) | opus |
| `security-reviewer` | Aikido-aligned scan + checklist — runs in `/ship` | opus |
| `code-simplifier` | reduce complexity on the changed diff without behaviour change — runs in `/ship` | sonnet |
| `demo-readiness-reviewer` | adversarial pre-rehearsal/pitch check vs PRD §6.3 (think-strategies) | opus |

Reviewers/critics are **read-only** (no Edit/Write/git). Proactively dispatch: SQL/warehouse → `warehouse-schema-expert`; canvas/UI → `maplibre-canvas-builder`; before a rehearsal → `demo-readiness-reviewer`.

## Skills — what to reach for

**Project (the contracts):** `add-agent-tool` · `soda-straw-data-tool` · `wire-agent-action-to-canvas` · `chapter-state-machine` · `belgian-open-data-ingest` · `dream-narrative-style` · `supabase-schema-sync`.
**Authored (cross-cutting):** `writing-implementation-specs` · `writing-handovers` · `security-scan` · `browser-data-curation` · `python-data-scripts` · `retrospective`.
**Vendored (Apache-2.0, in `skills/vendored/`):** `frontend-design` · `webapp-testing` · `mcp-builder` · `skill-creator` · `claude-api`.
**Via superpowers plugin:** `brainstorming` · `writing-plans` · `test-driven-development` · `systematic-debugging` · `subagent-driven-development` · `verification-before-completion` · `git-worktrees`.

Skill auto-activation is imperfect — this table is the backstop. When a task matches a skill, invoke it.

| When you're… | Skill |
|---|---|
| adding/extending an agent tool | `add-agent-tool` (+ `soda-straw-data-tool` if it reads analytical data) |
| wiring an agent action to the map / new layer / Droomzaak surface | `wire-agent-action-to-canvas` |
| building/extending the 5-chapter journey | `chapter-state-machine` |
| sourcing/clipping/joining a Belgian dataset, or curating permit/subsidy config | `belgian-open-data-ingest` |
| extracting from WAF-blocked/JS sources (VLAIO, VLAREM) | `browser-data-curation` (Claude-in-Chrome MCP) |
| writing Chapter-5 narrative / Tuesday-morning card | `dream-narrative-style` |
| changing/inspecting the Supabase warehouse schema or RPCs | `supabase-schema-sync` (+ `warehouse-schema-expert`) |
| writing/fixing a Python data script (pandas/geopandas/DuckDB) | `python-data-scripts` (+ `python-data-engineer` agent) |
| after a session, to sharpen skills/agents | `retrospective` (`/retro`) |
| writing a spec before building | `writing-implementation-specs` → `spec-critic` |
| ending a session / handing off a track | `writing-handovers` (`/handover`) |
| before any commit | `security-scan` (inside `/ship`) |
| Track-B UI polish | `frontend-design` |
| smoke-testing the chapter flow | `webapp-testing` |
| wrapping a live API as an MCP (Soda-Straw-brokered stretch) | `mcp-builder` |
| authoring a new project skill | `skill-creator` |
| building/optimizing the LLM-agent app or migrating models | `claude-api` |

## Commands

`/spec [thing]` · `/ship` · `/handover [topic]` · `/bootstrap` · `/new-tool [name]` · `/demo-check` · `/retro [focus]`. See `.claude/commands/`.

## Build sequence (PRD §5.2 — the 12 hours)

Pre-event (Fri): Postgres load + Soda Straw connection + secrets + public host. **0–2** wire Soda Straw client, chapter shell, permit YAML. **2–4** `extract_dream_profile`, `score_locations`, `peer_benchmarks_statbel`, `places_search`. **4–6** `permit_checklist_for`, `subsidies_for`, `legal_form_advisor`, `set_chapter_state`, Ch3–4 overlays. **6–8** `generate_dream_narrative`, `compose_package`, package renderer, rehearsal. **Hour 6: feature freeze.** Tracks: A backend/agent, B frontend/canvas, C content/pitch.

## Brand direction (Track B)

Warm earth tones, sketched line-art, a hint of Ghent skyline; warm/concrete/grounded tone. The artefact reads like a passion-project moodboard + a real planning document — never a tax form. Use the vendored `frontend-design` skill for the *how* (avoid AI-slop); this is the *what*. Dutch primary (`AGENT_LANGUAGE=nl`), EN fallback. (`droomzaak.png` is the brand mark.)

## Commands & environment (target)

Python via **uv** (`uv sync`, `uv run pytest backend/tests`). Frontend via npm (`npm run dev`, `npm run build` = `tsc -b && vite build`). The hackathon machine is likely macOS — write portable shell. TypeScript is checked via `tsc -b`. Frontend talks to the backend only through relative `/api` URLs.

## Team setup

New here? Run `/bootstrap` (or read [`TEAM-SETUP.md`](TEAM-SETUP.md)). It enables the superpowers plugin, approves the project MCP servers (you'll be prompted once), checks `.env.demo`, wires the conventional-commits hook (`git config core.hooksPath .githooks`), and tells you what's missing.

## Memory

A persistent memory dir exists for this project. Save **durable principles** (corrections that prevent repeating mistakes, confirmed approaches, guard-rails with rationale) as feedback — not status updates. Don't memorize file paths or anything derivable from the code/PRD. Check for an existing memory before adding a new one.
