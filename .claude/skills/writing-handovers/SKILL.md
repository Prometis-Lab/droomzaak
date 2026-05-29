---
name: writing-handovers
description: Use when ending a work session, handing a track to a teammate, or the user mentions "handover", "resume doc", "where did we leave off", "pick this up later". Writes a self-contained resume/handover doc with a collision-safe name (multiple people commit at once) so a fresh session or another person can continue without context loss. Triggered by /handover and the post-commit nudge.
---

# Writing a handover

A handover beats context-amnesia: a fresh Claude session (or a teammate switching tracks) should resume in minutes, not re-derive everything. **Self-contained** — assume the reader has zero memory of this session.

## Naming & folder convention (collision-safe — several people commit simultaneously)
Write to: `docs/handovers/<track>/<YYYY-MM-DD-HHMM>-<author>-<slug>.md`
- `<track>`: `track-a-backend` · `track-b-frontend` · `track-c-content`.
- `<YYYY-MM-DD-HHMM>`: use the real clock (run `date "+%Y-%m-%d-%H%M"`).
- `<author>`: the person's short handle; `<slug>`: 2–4 kebab words.
- Per-track folder + timestamp + author in the filename → no clobbering, no merge conflicts on a shared file.
Then prepend a one-line pointer to `docs/handovers/INDEX.md` (newest on top): `- [YYYY-MM-DD HH:MM] (track) author — slug → <path>`.

## Content (keep it tight — a screen, not an essay)
1. **State now** — what works, what's half-done, what's broken. Be honest about failures (don't claim done if tests fail).
2. **What I just did** — the change + why; the commit hash(es) if any.
3. **Next concrete step** — the very next action, specific enough to start cold.
4. **Open questions / decisions needed** — esp. anything blocking (e.g. Soda Straw token, Belfirst licence line, a secret).
5. **Exact entry points** — files (`file:line`), the command to run, the spec in `docs/specs/`, the relevant skill/agent.
6. **Gotchas hit** — so the next person doesn't re-hit them.
7. **Verification** — how to confirm the current state (the test/command + expected result).

## Anti-context-amnesia rules
- Link, don't restate: point to the spec, the PRD section, the skill — don't paste them.
- Name real paths/commands, not vibes. A handover that says "fix the agent" is useless; "`score_locations` returns 0 rows — likely the 2024/2025 vintage join in `warehouse-schema-expert`'s SQL; re-check the REFNIS filter" is gold.
- Never put secrets in the handover (it's committed). Reference `.env.demo` keys by name.

A good handover is one the next session can act on without asking you anything.
