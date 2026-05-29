---
description: Write a collision-safe resume/handover doc so a teammate or fresh session can continue.
argument-hint: [topic / track]
---

# /handover $ARGUMENTS

Use the `writing-handovers` skill to capture the current state so work can resume without context loss.

1. Determine the **track** (`track-a-backend` / `track-b-frontend` / `track-c-content`) from `$ARGUMENTS` or the work in progress.
2. Get the timestamp: run `date "+%Y-%m-%d-%H%M"`.
3. Write to `docs/handovers/<track>/<timestamp>-<author>-<slug>.md` (author = the person's short handle; ask if unknown). Per-track folder + timestamp + author = no clobbering when several people commit at once.
4. Fill the sections from the skill: **state now · what I just did (+ commit hashes) · next concrete step · open questions/blockers · exact entry points (file:line, command, spec) · gotchas hit · verification**.
5. Prepend a one-line pointer to `docs/handovers/INDEX.md` (newest on top).
6. Keep it to ~a screen, link don't restate, **no secrets** (the file is committed — reference `.env.demo` keys by name).
