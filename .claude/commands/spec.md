---
description: Write an implementation spec and gate it with spec-critic until it scores ≥8/10.
argument-hint: <feature or tool to spec>
---

# /spec $ARGUMENTS

Produce a build-ready spec and run the adversarial critic loop. Nothing gets implemented below 8/10.

1. **Ground it.** Read the relevant `droomzaak-prd.md` section AND `droomzaak-data-shortlist.md` (the latter wins on data/tools — carry the Known Corrections). If a reference implementation exists under `reference/`, consult `reference-scout` for inspiration on the contract.
2. **Write the spec** using the `writing-implementation-specs` skill → `docs/specs/YYYY-MM-DD-<slug>.md` (Context · Contract · Files · Edge cases · Tests · Acceptance · Risks).
3. **Critic loop (the gate):** dispatch `spec-critic` (it uses think-strategies). If it scores **< 8/10**, apply every blocker it lists, then **re-run `spec-critic` on the updated spec**. Repeat until **≥ 8/10**.
4. **Report** the final score + the path. Only then is the spec cleared for implementation. If after 3 rounds it still can't reach 8, surface the structural blocker to the user rather than forcing it.
