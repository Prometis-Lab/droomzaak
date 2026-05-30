---
description: Scaffold a new Droomzaak agent tool end-to-end via the agent-tool-builder + add-agent-tool skill.
argument-hint: <tool_name>
---

# /new-tool $ARGUMENTS

Add one new agent tool end-to-end, to the provider-neutral contract.

1. **Check the spec source (precedence):** confirm `$ARGUMENTS` against `droomzaak-data-shortlist.md` §3 (authoritative) and `droomzaak-prd.md` §3.5. Refuse/flag dead tools — there is **no `places_popular_times`**. Confirm the backing (analytical → DataGateway; behaviour → native; `peer_benchmarks_statbel` → Belfirst aggregates + Statbel).
2. If a spec doesn't exist yet and the tool is non-trivial, run `/spec $ARGUMENTS` first (≥8/10 gate).
3. Dispatch the **`agent-tool-builder`** agent (it invokes the `add-agent-tool` skill, and `data-tool` for data tools; gets SQL from `warehouse-schema-expert`). It delivers: neutral spec + handler + validation wiring + DataGateway brokering (or native) + a fake-client test (real APIs monkeypatched).
4. Verify: `uv run pytest backend/tests/test_agent.py` passes. Report files touched + the test result.
5. When done, run `/ship`.
