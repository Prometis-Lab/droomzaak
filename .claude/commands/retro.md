---
description: Session retrospective — analyze workflow/agents/skills, abstract principles, propose ≤3 validated edits to improve the toolkit.
argument-hint: [plan-file | 'session' | focus area]
---

# /retro $ARGUMENTS

Run the **`retrospective`** skill on this session (scope to `$ARGUMENTS` if given). Use it after finalizing a plan/spec, after completing an implementation, at the end of a long session, or when we hit recurring friction.

Work the skill's steps:
1. **Workflow analysis** — time sinks, mistakes, what worked, repeated instructions, permission/gate friction.
2. **Agent effectiveness** — evaluate the agents used (and any that *should* have run), per the skill's dimensions.
3. **Skill/command evaluation** — completeness, gates, overlap, stale references.
4. **Abstract principles** — apply the "good vs bad memory" test (a principle that changes how you think about a category, not an incident replay).
5. **Classify** findings → Memory / Rule / Agent / Skill / Command / Permission.
6. **Propose ≤3 budgeted edits** (add/delete/replace, reflecting on success vs failure separately) and **validate each** with the vendored `skill-creator` scripts (`uv run python .claude/skills/vendored/skill-creator/scripts/quick_validate.py …`; `run_eval.py` for trigger-line edits). **Keep only edits that pass.**
7. **Summarize**, then ask which changes to apply; save durable learnings as **feedback** memories (update, don't duplicate).

Keep it to ~5–10 minutes. Be honest about what didn't work, including your own mistakes.
