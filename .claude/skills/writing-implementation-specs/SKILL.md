---
name: writing-implementation-specs
description: Use when turning a PRD chapter, agent tool, or feature into a build-ready implementation spec before coding — or when the user mentions "write a spec", "spec this out", "plan this feature". Produces a spec grounded in the Droomzaak reference + the data-shortlist, written to docs/specs/, structured so spec-critic can score it and a builder can execute it without rediscovering context.
---

# Writing an implementation spec

A good spec is clear enough for "an enthusiastic junior engineer with no project context" to execute, and concrete enough for `spec-critic` to score ≥8/10. Pair with superpowers `writing-plans` (structure/decomposition); this skill adds the Droomzaak grounding.

## Before writing — ground it (precedence)
1. Read the relevant PRD section AND `droomzaak-data-shortlist.md` (the latter wins on data/tools/sources). Carry the **Known corrections** (no `places_popular_times`; `web_search` exists; Belfirst peer source; data-shortlist table names; `prometis_toolkit`; subsidy `status`).
2. If a reference implementation exists under `reference/`, ask `reference-scout` for inspiration on the contract (don't guess at `agent_loop.py`/`App.tsx` internals — design them from the PRD).
3. Identify the invariants the change must honor (`rules/data-tiers.md`: DataGateway boundary, parameterized SQL, proxy labels, provider-neutral).

## Spec structure (write to `docs/specs/YYYY-MM-DD-<slug>.md`)
- **Context** — what + why, the PRD/data-shortlist refs, the hour-budget slot (§5.2).
- **Contract** — exact inputs/outputs; for a tool: the neutral spec (name, description, JSON-Schema params, return shape), how it routes (DataGateway vs native), validation/action-type changes.
- **Files** — which files to create/modify (target structure), naming the reference analog to mirror.
- **Edge cases** — empty/zero-row data, non-horeca sector, jury-picked non-Vrijdagmarkt address (must not crash), DataGateway timeout, missing secret.
- **Tests** — the fake-client test(s); real APIs monkeypatched.
- **Acceptance / "done"** — verifiable: which command proves it (a passing test, a `npm run build`, a chapter completing), mapped to a PRD §6.3 criterion where relevant.
- **Risks & open questions** — anything needing a decision before coding.

## Then gate it
Hand to `spec-critic` (it uses think-strategies). **Loop: apply its fixes, re-score, repeat until ≥8/10.** Do not start implementation below 8. `/spec` automates this loop.

## Quality bar
No hand-waving ("handle errors appropriately" → say how). Every claim about the reference verified (ask the scout, don't trust memory). Every number/source cited to the data-shortlist. Scoped to the hour budget — defer anything that belongs past hour 6.
