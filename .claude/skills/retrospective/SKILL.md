---
name: retrospective
description: Use at the end of a session, after finalizing a plan/spec, after completing an implementation, or when the user mentions "retro", "retrospective", "improve our workflow/skills/agents". Conducts a structured retrospective — workflow + agent + skill/command analysis, abstracts reusable principles, and proposes a SMALL budgeted set of add/delete/replace edits to our skills/agents, kept only if they validate (vendored skill-creator scripts). Sharpens the toolkit without an eval harness.
---

# Retrospective — improve the workflow & sharpen skills/agents

Two lineages, merged: our proven session-retro workflow (broad: agents, skills, commands, rules, permissions, memories) **plus** the discipline distilled from Microsoft [SkillOpt](https://github.com/microsoft/SkillOpt) (MIT — method borrowed, not vendored: the full optimizer needs labeled train/val/test sets we don't have). Goal: turn one session's friction into a few precise, *validated* improvements. **Time budget: 5–10 minutes**, not a research project.

## Step 1 — Workflow analysis
Review the session. Identify:
1. **Time sinks** — disproportionate time (repeated fixes, back-and-forth, re-explanations).
2. **Mistakes** — wrong assumptions, SQL/CRS errors, UI regressions, scope creep, a stale-assumption slip (e.g. reaching for `places_popular_times`).
3. **What worked** — patterns to reinforce (good agent usage, the ≥8/10 spec gate catching a gap, a clean DataGateway-routed tool).
4. **Repeated instructions** — did the user say the same thing twice? → a missing memory or CLAUDE.md gap.
5. **Permission/gate friction** — needless prompts, or a gate that only added friction.

## Step 2 — Agent effectiveness (our 11 agents)
For each agent used (or that *should* have been): prompt clarity (understood first try?), tool usage (missing/unused tools?), output quality (actionable or heavy rework?), domain knowledge (missing context/skill, stale rule?), scope discipline (stayed in lane?), handoff quality (good input for the next agent?). **Also flag agents that should have run but didn't** — brainstorm skipped before a feature? `spec-critic` skipped before code? `warehouse-schema-expert` not consulted for SQL? `demo-readiness-reviewer` before a rehearsal? `security-reviewer` in `/ship`?

## Step 3 — Skill & command evaluation
For each skill/command used: workflow completeness (missing/misordered steps?), gate effectiveness (caught real issues vs friction?), overlap/ambiguity (unclear which to use?), instruction clarity, duplication (repeats a loaded skill?), **stale references** (files/tools/patterns that no longer exist, or a PRD assumption the data-shortlist corrected?).

## Step 4 — Abstract general principles
**CRITICAL: do NOT save specific incidents as memories — abstract the reusable lesson.**
- Bad (too specific): "Don't join 2023 income to 2025 sector geometry."
- Good (principle): "Verify the join key's *vintage* before trusting a spatial join — a 0-row result is usually a vintage/REFNIS mismatch, not missing data."
- **Abstraction test:** if it only prevents the exact same mistake in the exact same context, it's too specific. If it changes how you think about a *category* of decisions, it's right.

## Step 5 — Classify findings
| Type | Where |
|---|---|
| Memory (abstract principle) | the project `memory/` dir + `MEMORY.md` pointer |
| Rule | `CLAUDE.md` or `.claude/rules/` |
| Agent prompt/tools | `.claude/agents/*.md` |
| Skill | `.claude/skills/*/SKILL.md` |
| Command workflow/gate | `.claude/commands/*.md` |
| Permission | `.claude/settings.json` |

## Step 6 — Propose edits (SkillOpt-budgeted) & validate before keeping
This is the rigor that stops a noisy single session from corrupting good skills:
1. **Reflect on success and failure SEPARATELY** — for failures, "what missing/wrong instruction caused this?"; for successes, "what reusable procedure should we capture?"
2. **Budget: ≤3 edits**, each an explicit **add / delete / replace** on one file, tied to the trajectory that motivates it. Prefer small localized diffs over rewrites (SkillOpt's "textual learning rate"). Don't invent edits to fill the cap.
3. **Validate via the vendored `skill-creator` scripts** (run with uv):
   - `uv run python .claude/skills/vendored/skill-creator/scripts/quick_validate.py <edited file>` — structural/frontmatter gate, on every edit.
   - For any edit to a `description:`/trigger line: `uv run python .claude/skills/vendored/skill-creator/scripts/run_eval.py …` against a **tiny** should-trigger / should-not-trigger query set (uses the session's `claude -p` auth — no extra key, no dataset). `improve_description.py` can rewrite a weak trigger.
4. **Keep-only-if-it-helps:** accept an edit only if `quick_validate` passes AND (trigger edits) `run_eval` doesn't regress. Otherwise discard and report why.

## Step 7 — Summary & apply
Present a concise report, then ask which changes to apply:
```
## Retrospective: <date> — <topic>
### What went well
### Time sinks (root cause → fix)
### Mistakes (what should've happened → prevention)
### Agent evaluation        | agent | used? | effectiveness | issue |
### Skill/command evaluation | name | issue | fix |
### Proposed edits (≤3)      | add/delete/replace | file | validation: kept/discarded + why |
### Principles extracted (abstract, memory-worthy)
### Watch next session
```
Apply approved changes; save durable principles as **feedback** memories (check for an existing one first — update, don't duplicate). Be honest about your own mistakes.

## Guards
Budget cap + keep-if-helps + separate-the-judge (the gate is the scripts, not the model's self-assessment). Single-session signal is noisy — if a trajectory doesn't clearly implicate a skill/agent, log it as "watch next session" instead of editing. We optimize *triggering + structural validity + human-judged trajectories*, not measured task success. No secrets in edits; respect source-of-truth precedence (don't reintroduce a corrected PRD assumption).

Pairs with `/retro`. To author a *new* skill (vs. tune one), use the vendored `skill-creator`.
